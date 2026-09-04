# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import json
import random
from pathlib import Path

from PySide6.QtCore import Property, QStandardPaths, QTimer, QUrl, Signal, Slot

from rastermint.core import builtin_presets, palette_library
from rastermint.core.extensions import asset_files
from rastermint.core.history import UndoHistory
from rastermint.core.palette_json import load_palette_json, slugify_palette_name, write_palette_json
from rastermint.core.presets import (
    load_preset,
    load_preset_payload,
    merge_preset_with_current_crop,
    save_preset,
    slugify_preset_name,
)
from rastermint.core.preset_mutation import generate_preset_mutations
from rastermint.core.settings import ProcessingSettings
from rastermint.qmlui.backend import RasterMintBackend as BaseRasterMintBackend
from rastermint.qmlui.workers import ProcessingWorker


DEFAULT_HISTORY_LIMIT = 50
MIN_HISTORY_LIMIT = 10
MAX_HISTORY_LIMIT = 200
DEFAULT_LAYER_CACHE_ENABLED = True
DEFAULT_LAYER_CACHE_MEGABYTES = 192
MIN_LAYER_CACHE_MEGABYTES = 64
MAX_LAYER_CACHE_MEGABYTES = 2048
DEFAULT_TILED_PROCESSING_ENABLED = True
DEFAULT_PROCESSING_TILE_SIZE = 1024
DEFAULT_SLIDER_WHEEL_CONTROL = False
DEFAULT_DEBOUNCE_SLIDER_UPDATES = False
DEFAULT_LIMIT_LARGE_IMPORTS_TO_FULL_HD = False
DEFAULT_PRESERVE_CROPPING_POSITION = False


def _processor_call(name: str, *args, **kwargs):
    from rastermint.core import processor
    return getattr(processor, name)(*args, **kwargs)


def target_raster_size(size, settings):
    return _processor_call("target_raster_size", size, settings)


def make_preview_source(source, *, max_side: int, settings):
    return _processor_call("make_preview_source", source, max_side=max_side, settings=settings)


def make_preview_settings(settings, final_size, preview_size):
    return _processor_call("make_preview_settings", settings, final_size, preview_size)


def _clamp_history_limit(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_HISTORY_LIMIT
    return max(MIN_HISTORY_LIMIT, min(MAX_HISTORY_LIMIT, parsed))


def _local_path(value: str | QUrl) -> Path:
    if isinstance(value, QUrl):
        return Path(value.toLocalFile() if value.isLocalFile() else value.toString())
    text = str(value or "")
    url = QUrl(text)
    if url.isValid() and url.isLocalFile():
        return Path(url.toLocalFile())
    return Path(text)


def _app_data_root() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return Path(base) if base else Path.home() / ".rastermint"


class RasterMintBackend(BaseRasterMintBackend):
    """RasterMint backend with persistent UI preferences and user libraries."""

    historyLimitChanged = Signal()
    performanceSettingsChanged = Signal()
    importSettingsChanged = Signal()
    userPaletteLibraryChanged = Signal()
    presetLibraryChanged = Signal()
    presetMutationsChanged = Signal()

    def __init__(self, image_provider, parent=None) -> None:
        super().__init__(image_provider, parent)
        self._history_limit = _clamp_history_limit(
            self.app_settings.value("historyLimitQml", DEFAULT_HISTORY_LIMIT)
        )
        # The base backend creates history during construction, before any user
        # edits can exist. Recreate it with the persisted depth immediately.
        self._history = UndoHistory(limit=self._history_limit)
        self._layer_cache_enabled = str(self.app_settings.value("performance/layerCacheEnabled", "true")).lower() not in {"0", "false", "no"}
        try:
            self._layer_cache_megabytes = max(
                MIN_LAYER_CACHE_MEGABYTES,
                min(MAX_LAYER_CACHE_MEGABYTES, int(self.app_settings.value("performance/layerCacheMegabytes", DEFAULT_LAYER_CACHE_MEGABYTES))),
            )
        except (TypeError, ValueError):
            self._layer_cache_megabytes = DEFAULT_LAYER_CACHE_MEGABYTES
        self._tiled_processing_enabled = str(self.app_settings.value("performance/tiledProcessingEnabled", "true")).lower() not in {"0", "false", "no"}
        try:
            raw_tile = int(self.app_settings.value("performance/tileSize", DEFAULT_PROCESSING_TILE_SIZE))
        except (TypeError, ValueError):
            raw_tile = DEFAULT_PROCESSING_TILE_SIZE
        choices = (256, 512, 1024, 2048, 4096)
        self._processing_tile_size = min(choices, key=lambda value: abs(value - raw_tile))
        self._slider_wheel_control = str(self.app_settings.value("interaction/sliderWheelControl", "false")).lower() in {"1", "true", "yes", "on"}
        self._debounce_slider_updates = str(self.app_settings.value("interaction/debounceSliderUpdates", "false")).lower() in {"1", "true", "yes", "on"}
        self._limit_large_imports_to_full_hd = str(self.app_settings.value("import/limitLargeToFullHD", "false")).lower() in {"1", "true", "yes", "on"}
        self._preserve_cropping_position = str(self.app_settings.value("import/preserveCroppingPosition", "false")).lower() in {"1", "true", "yes", "on"}
        self._slider_interaction_active = False

        self._debounce_full_timer = QTimer(self)
        self._debounce_full_timer.setSingleShot(True)
        self._debounce_full_timer.timeout.connect(lambda: self._request_preview(self._safe_full_side()))

        self._user_palettes: dict[str, dict[str, object]] = {}
        self._user_presets: dict[str, dict[str, object]] = {}
        self._extension_presets: dict[str, dict[str, object]] = {}
        self._preset_mutations: dict[str, ProcessingSettings] = {}
        self._preset_mutation_items: list[dict[str, object]] = []
        self._preset_mutation_generation = 0
        self._load_user_palettes()
        self._load_user_presets()
        self._load_extension_presets()
        self._preset_meta = self._load_preset_meta()

    # ---------- history preference ----------
    def _get_history_limit(self) -> int:
        return self._history_limit

    @Slot(int)
    def _set_history_limit(self, limit: int) -> None:
        value = _clamp_history_limit(limit)
        if value == self._history_limit:
            return
        self._history_limit = value
        self._history.set_limit(value)
        self.app_settings.setValue("historyLimitQml", value)
        self.historyLimitChanged.emit()
        self._set_status(f"Undo history: {value} actions")

    historyLimit = Property(
        int,
        _get_history_limit,
        _set_history_limit,
        notify=historyLimitChanged,
    )

    # ---------- performance preferences ----------
    @Property(bool, notify=performanceSettingsChanged)
    def layerCacheEnabled(self) -> bool:
        return bool(self._layer_cache_enabled)

    @Slot(bool)
    def setLayerCacheEnabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._layer_cache_enabled:
            return
        self._layer_cache_enabled = enabled
        self.app_settings.setValue("performance/layerCacheEnabled", enabled)
        if not enabled:
            self._clear_layer_render_cache()
        self.performanceSettingsChanged.emit()
        self._set_status(f"Layer cache: {'On' if enabled else 'Off'}")

    @Property(int, notify=performanceSettingsChanged)
    def layerCacheMegabytes(self) -> int:
        return int(self._layer_cache_megabytes)

    @Slot(int)
    def setLayerCacheMegabytes(self, megabytes: int) -> None:
        value = max(MIN_LAYER_CACHE_MEGABYTES, min(MAX_LAYER_CACHE_MEGABYTES, int(megabytes)))
        if value == self._layer_cache_megabytes:
            return
        self._layer_cache_megabytes = value
        self.app_settings.setValue("performance/layerCacheMegabytes", value)
        if self._layer_render_cache is not None:
            self._layer_render_cache.set_budget(value)
        self.performanceSettingsChanged.emit()
        self._set_status(f"Layer cache budget: {value} MB")

    @Property(bool, notify=performanceSettingsChanged)
    def tiledProcessingEnabled(self) -> bool:
        return bool(self._tiled_processing_enabled)

    @Slot(bool)
    def setTiledProcessingEnabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._tiled_processing_enabled:
            return
        self._tiled_processing_enabled = enabled
        self.app_settings.setValue("performance/tiledProcessingEnabled", enabled)
        self.performanceSettingsChanged.emit()
        self._set_status(f"Large-image tiling: {'On' if enabled else 'Off'}")

    @Property(int, notify=performanceSettingsChanged)
    def processingTileSize(self) -> int:
        return int(self._processing_tile_size)

    @Slot(int)
    def setProcessingTileSize(self, size: int) -> None:
        choices = (256, 512, 1024, 2048, 4096)
        value = min(choices, key=lambda option: abs(option - int(size)))
        if value == self._processing_tile_size:
            return
        self._processing_tile_size = value
        self.app_settings.setValue("performance/tileSize", value)
        self.performanceSettingsChanged.emit()
        self._set_status(f"Processing tile: {value} px")

    @Property(bool, notify=performanceSettingsChanged)
    def sliderWheelControl(self) -> bool:
        return bool(self._slider_wheel_control)

    @Slot(bool)
    def setSliderWheelControl(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._slider_wheel_control:
            return
        self._slider_wheel_control = enabled
        self.app_settings.setValue("interaction/sliderWheelControl", enabled)
        self.performanceSettingsChanged.emit()
        self._set_status(f"Slider wheel control: {'On' if enabled else 'Off'}")

    @Property(bool, notify=performanceSettingsChanged)
    def debounceSliderUpdates(self) -> bool:
        return bool(self._debounce_slider_updates)

    @Slot(bool)
    def setDebounceSliderUpdates(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._debounce_slider_updates:
            return
        self._debounce_slider_updates = enabled
        if not enabled:
            self._slider_interaction_active = False
            self._debounce_full_timer.stop()
        self.app_settings.setValue("interaction/debounceSliderUpdates", enabled)
        self.performanceSettingsChanged.emit()
        self._set_status(f"Slider render debounce: {'On' if enabled else 'Off'}")

    # ---------- import preferences ----------
    @Property(bool, notify=importSettingsChanged)
    def limitLargeImportsToFullHD(self) -> bool:
        return bool(self._limit_large_imports_to_full_hd)

    @Slot(bool)
    def setLimitLargeImportsToFullHD(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._limit_large_imports_to_full_hd:
            return
        self._limit_large_imports_to_full_hd = enabled
        self.app_settings.setValue("import/limitLargeToFullHD", enabled)
        self.importSettingsChanged.emit()
        self._set_status(f"Limit large imports to Full HD: {'On' if enabled else 'Off'}")

    @Property(bool, notify=importSettingsChanged)
    def preserveCroppingPosition(self) -> bool:
        return bool(self._preserve_cropping_position)

    @Slot(bool)
    def setPreserveCroppingPosition(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._preserve_cropping_position:
            return
        self._preserve_cropping_position = enabled
        self.app_settings.setValue("import/preserveCroppingPosition", enabled)
        self.importSettingsChanged.emit()
        self._set_status(f"Preserve cropping position: {'On' if enabled else 'Off'}")

    @Slot()
    def beginDebouncedSliderInteraction(self) -> None:
        if self._debounce_slider_updates:
            self._slider_interaction_active = True

    @Slot()
    def endDebouncedSliderInteraction(self) -> None:
        if not self._slider_interaction_active:
            return
        self._slider_interaction_active = False
        self.flushDebouncedPreview()

    @Slot()
    def flushDebouncedPreview(self) -> None:
        if not self._debounce_slider_updates or not self.hasSource:
            return
        self._quick_timer.stop(); self._stable_timer.stop(); self._debounce_full_timer.stop()
        if self._preview_mode == "Quick":
            self._quick_timer.start(0)
            self._stable_timer.start(330)
        elif self._preview_mode == "Stable":
            self._stable_timer.start(0)
        else:
            self._request_preview(self._safe_full_side())

    @Slot()
    @Slot(bool)
    def schedulePreview(self, force: bool = False) -> None:
        if force or not self._debounce_slider_updates or not self._slider_interaction_active:
            super().schedulePreview(force)
            return
        if not self.hasSource:
            return
        self._quick_timer.stop(); self._stable_timer.stop(); self._debounce_full_timer.stop()
        if self._preview_mode == "Quick":
            self._quick_timer.start(220)
            self._stable_timer.start(520)
        elif self._preview_mode == "Stable":
            self._stable_timer.start(320)
        else:
            # Full mode has no proxy tier, so use a dedicated debounce timer.
            self._debounce_full_timer.stop()
            self._debounce_full_timer.start(280)

    @Slot()
    def clearLayerCache(self) -> None:
        self._clear_layer_render_cache()
        self._set_status("Layer cache cleared")

    @Slot()
    def resetSettings(self) -> None:
        super().resetSettings()
        changed = self._history_limit != DEFAULT_HISTORY_LIMIT
        self._history_limit = DEFAULT_HISTORY_LIMIT
        self._history.set_limit(DEFAULT_HISTORY_LIMIT)
        self.app_settings.setValue("historyLimitQml", DEFAULT_HISTORY_LIMIT)
        if changed:
            self.historyLimitChanged.emit()
        performance_changed = (
            self._layer_cache_enabled != DEFAULT_LAYER_CACHE_ENABLED
            or self._layer_cache_megabytes != DEFAULT_LAYER_CACHE_MEGABYTES
            or self._tiled_processing_enabled != DEFAULT_TILED_PROCESSING_ENABLED
            or self._processing_tile_size != DEFAULT_PROCESSING_TILE_SIZE
            or self._slider_wheel_control != DEFAULT_SLIDER_WHEEL_CONTROL
            or self._debounce_slider_updates != DEFAULT_DEBOUNCE_SLIDER_UPDATES
        )
        import_changed = (
            self._limit_large_imports_to_full_hd != DEFAULT_LIMIT_LARGE_IMPORTS_TO_FULL_HD
            or self._preserve_cropping_position != DEFAULT_PRESERVE_CROPPING_POSITION
        )
        self._layer_cache_enabled = DEFAULT_LAYER_CACHE_ENABLED
        self._layer_cache_megabytes = DEFAULT_LAYER_CACHE_MEGABYTES
        self._tiled_processing_enabled = DEFAULT_TILED_PROCESSING_ENABLED
        self._processing_tile_size = DEFAULT_PROCESSING_TILE_SIZE
        self._slider_wheel_control = DEFAULT_SLIDER_WHEEL_CONTROL
        self._debounce_slider_updates = DEFAULT_DEBOUNCE_SLIDER_UPDATES
        self._limit_large_imports_to_full_hd = DEFAULT_LIMIT_LARGE_IMPORTS_TO_FULL_HD
        self._preserve_cropping_position = DEFAULT_PRESERVE_CROPPING_POSITION
        self._slider_interaction_active = False
        self.app_settings.setValue("performance/layerCacheEnabled", DEFAULT_LAYER_CACHE_ENABLED)
        self.app_settings.setValue("performance/layerCacheMegabytes", DEFAULT_LAYER_CACHE_MEGABYTES)
        self.app_settings.setValue("performance/tiledProcessingEnabled", DEFAULT_TILED_PROCESSING_ENABLED)
        self.app_settings.setValue("performance/tileSize", DEFAULT_PROCESSING_TILE_SIZE)
        self.app_settings.setValue("interaction/sliderWheelControl", DEFAULT_SLIDER_WHEEL_CONTROL)
        self.app_settings.setValue("interaction/debounceSliderUpdates", DEFAULT_DEBOUNCE_SLIDER_UPDATES)
        self.app_settings.setValue("import/limitLargeToFullHD", DEFAULT_LIMIT_LARGE_IMPORTS_TO_FULL_HD)
        self.app_settings.setValue("import/preserveCroppingPosition", DEFAULT_PRESERVE_CROPPING_POSITION)
        self._clear_layer_render_cache()
        if performance_changed:
            self.performanceSettingsChanged.emit()
        if import_changed:
            self.importSettingsChanged.emit()

    @Slot()
    def shutdown(self) -> None:
        self._debounce_full_timer.stop()
        super().shutdown()

    # ---------- persistent user palette library ----------
    @staticmethod
    def _user_palette_folder() -> Path:
        return _app_data_root() / "palettes"

    def _load_user_palettes(self) -> None:
        self._user_palettes.clear()
        folder = self._user_palette_folder()
        if not folder.is_dir():
            return

        builtin_ids = {item.id for item in palette_library.PALETTE_LIBRARY}
        for path in sorted(folder.glob("*.json"), key=lambda item: item.name.casefold()):
            try:
                payload = load_palette_json(path)
            except Exception:
                continue
            palette_id = str(payload["id"])
            if palette_id in builtin_ids:
                continue
            payload["file"] = str(path)
            payload["user"] = True
            self._user_palettes[palette_id] = payload

    @Property("QVariantList", notify=userPaletteLibraryChanged)
    def allPaletteLibrary(self) -> list[dict[str, object]]:
        builtins = [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "description": item.description,
                "colors": list(item.colors),
                "user": False,
            }
            for item in palette_library.PALETTE_LIBRARY
        ]
        users = [
            {
                "id": str(item["id"]),
                "name": str(item["name"]),
                "category": str(item["category"]),
                "description": str(item.get("description", "")),
                "colors": list(item["colors"]),
                "user": True,
            }
            for item in self._user_palettes.values()
        ]
        users.sort(key=lambda item: (str(item["category"]).casefold(), str(item["name"]).casefold()))
        return builtins + users

    def _find_user_palette(self, name_or_id: str) -> dict[str, object] | None:
        key = str(name_or_id)
        record = self._user_palettes.get(key)
        if record is not None:
            return record
        key_cf = key.casefold()
        return next(
            (
                item
                for item in self._user_palettes.values()
                if str(item.get("name", "")).casefold() == key_cf
            ),
            None,
        )

    @Slot(str)
    def applyPalette(self, name_or_id: str) -> None:
        record = self._find_user_palette(str(name_or_id))
        if record is None:
            super().applyPalette(name_or_id)
            return

        colors = list(record["colors"])
        data = self.settings.to_dict()
        data.update(
            palette=colors,
            palette_locks=[False] * len(colors),
            palette_name=str(record["name"]),
            palette_author="",
            palette_source=str(record.get("file", "User palette library")),
        )
        self._replace_settings(
            ProcessingSettings.from_dict(data),
            action=f"Palette: {record['name']}",
        )

    @Slot(str)
    def importPalette(self, value: str) -> None:
        path = _local_path(value)
        if path.suffix.lower() != ".json":
            super().importPalette(value)
            return
        try:
            payload = load_palette_json(path)
            colors = list(payload["colors"])
            data = self.settings.to_dict()
            data.update(
                palette=colors,
                palette_locks=[False] * len(colors),
                palette_name=str(payload["name"]),
                palette_author="",
                palette_source=str(path),
            )
            self._replace_settings(
                ProcessingSettings.from_dict(data),
                action=f"Imported palette: {payload['name']}",
            )
        except Exception as exc:
            self.errorOccurred.emit("Could not import palette", str(exc))

    @Slot(str, str)
    def savePaletteToLibrary(self, name: str, category: str) -> None:
        clean_name = str(name or "").strip() or "Custom Palette"
        clean_category = str(category or "").strip() or "Custom"
        slug = slugify_palette_name(clean_name)
        palette_id = f"user-{slug}"
        folder = self._user_palette_folder()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{slug}.json"

        try:
            write_palette_json(
                path,
                palette_id=palette_id,
                name=clean_name,
                category=clean_category,
                colors=self.settings.palette,
                description=f"Custom {len(self.settings.palette)}-color palette.",
                source="User palette library",
            )
            payload = load_palette_json(path)
            payload["file"] = str(path)
            payload["user"] = True
            self._user_palettes[palette_id] = payload
            self.userPaletteLibraryChanged.emit()

            data = self.settings.to_dict()
            data.update(
                palette_name=clean_name,
                palette_author="",
                palette_source=str(path),
            )
            self._replace_settings(
                ProcessingSettings.from_dict(data),
                schedule=False,
                action=f"Saved palette: {clean_name}",
                record_history=False,
            )
        except Exception as exc:
            self.errorOccurred.emit("Could not save palette", str(exc))

    @Slot(str)
    def deletePaletteFromLibrary(self, palette_id: str) -> None:
        record = self._user_palettes.get(str(palette_id))
        if record is None:
            return
        try:
            file_path = Path(str(record.get("file", "")))
            if file_path.is_file():
                file_path.unlink()
            name = str(record.get("name", "Palette"))
            del self._user_palettes[str(palette_id)]
            self.userPaletteLibraryChanged.emit()
            self._set_status(f"Removed palette from library: {name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not remove palette", str(exc))

    @Slot(str)
    def exportPaletteJson(self, value: str) -> None:
        try:
            path = _local_path(value)
            if path.suffix.lower() != ".json":
                path = path.with_suffix(".json")
            name = str(self.settings.palette_name or "").strip()
            if not name or name == "Custom":
                name = path.stem.replace("-", " ").title() or "Custom Palette"
            write_palette_json(
                path,
                palette_id=slugify_palette_name(name),
                name=name,
                category="Custom",
                colors=self.settings.palette,
                description=f"RasterMint {len(self.settings.palette)}-color palette.",
                source="",
            )
            self._set_status(f"Saved palette {path.name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not export palette", str(exc))

    # ---------- persistent user preset library ----------
    @staticmethod
    def _user_preset_folder() -> Path:
        return _app_data_root() / "presets"

    def _load_user_presets(self) -> None:
        self._user_presets.clear()
        folder = self._user_preset_folder()
        if not folder.is_dir():
            return

        builtin_ids = {item.id for item in builtin_presets.BUILTIN_PRESETS}
        for path in sorted(folder.glob("*.json"), key=lambda item: item.name.casefold()):
            try:
                payload = load_preset_payload(path)
            except Exception:
                continue

            preset_id = str(payload.get("id") or f"user-{slugify_preset_name(path.stem)}")
            if not preset_id.startswith("user-"):
                preset_id = f"user-{slugify_preset_name(preset_id)}"
            if preset_id in builtin_ids:
                continue

            payload["id"] = preset_id
            payload["file"] = str(path)
            payload["user"] = True
            self._user_presets[preset_id] = payload

    def _load_extension_presets(self) -> None:
        self._extension_presets.clear()
        reserved_ids = {item.id for item in builtin_presets.BUILTIN_PRESETS}
        reserved_ids.update(self._user_presets)
        for path in asset_files("presets"):
            try:
                payload = load_preset_payload(path)
            except Exception:
                continue
            preset_id = str(payload.get("id") or f"extension-{slugify_preset_name(path.stem)}").strip()
            if not preset_id or preset_id in reserved_ids or preset_id in self._extension_presets:
                continue
            payload["id"] = preset_id
            payload["file"] = str(path)
            payload["user"] = False
            payload["extension"] = True
            self._extension_presets[preset_id] = payload

    _PRESET_META_KEY = "presetLibraryMetaV1"

    def _load_preset_meta(self) -> dict[str, object]:
        raw = self.app_settings.value(self._PRESET_META_KEY, "{}")
        try:
            payload = json.loads(str(raw or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}
        return {
            "favorites": [str(v) for v in payload.get("favorites", [])] if isinstance(payload, dict) else [],
            "recent": [str(v) for v in payload.get("recent", [])] if isinstance(payload, dict) else [],
            "categories": {str(k): str(v) for k, v in dict(payload.get("categories", {})).items()} if isinstance(payload, dict) and isinstance(payload.get("categories"), dict) else {},
        }

    def _save_preset_meta(self) -> None:
        self.app_settings.setValue(self._PRESET_META_KEY, json.dumps(self._preset_meta, ensure_ascii=False))
        self.app_settings.sync()

    def _touch_recent_preset(self, preset_id: str) -> None:
        recent = [str(v) for v in self._preset_meta.get("recent", []) if str(v) != str(preset_id)]
        recent.insert(0, str(preset_id))
        self._preset_meta["recent"] = recent[:20]
        self._save_preset_meta()
        self.presetLibraryChanged.emit()

    @Property("QStringList", notify=presetLibraryChanged)
    def presetUserCategories(self) -> list[str]:
        values = {str(v) for v in dict(self._preset_meta.get("categories", {})).values() if str(v).strip()}
        return sorted(values, key=str.casefold)

    @Slot(str)
    def togglePresetFavorite(self, preset_id: str) -> None:
        key = str(preset_id)
        favorites = [str(v) for v in self._preset_meta.get("favorites", [])]
        if key in favorites:
            favorites.remove(key)
        else:
            favorites.append(key)
        self._preset_meta["favorites"] = favorites
        self._save_preset_meta()
        self.presetLibraryChanged.emit()

    @Slot(str, str)
    def setPresetCategory(self, preset_id: str, category: str) -> None:
        preset_key = str(preset_id)
        if preset_key not in self._user_presets:
            return
        categories = dict(self._preset_meta.get("categories", {}))
        clean = str(category or "").strip()
        if clean:
            categories[preset_key] = clean
        else:
            categories.pop(preset_key, None)
        self._preset_meta["categories"] = categories
        self._save_preset_meta()
        self.presetLibraryChanged.emit()
        self._set_status(f"Preset category: {clean or 'Uncategorized'}")

    @Property("QVariantList", notify=presetLibraryChanged)
    def allPresets(self) -> list[dict[str, object]]:
        builtins = [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "user": False,
            }
            for item in builtin_presets.BUILTIN_PRESETS
        ]
        extensions = [
            {
                "id": str(item["id"]),
                "name": str(item.get("name") or Path(str(item.get("file", "preset"))).stem),
                "description": str(item.get("description", "")),
                "user": False,
                "extension": True,
            }
            for item in self._extension_presets.values()
        ]
        extensions.sort(key=lambda item: str(item["name"]).casefold())
        users = [
            {
                "id": str(item["id"]),
                "name": str(item.get("name") or Path(str(item.get("file", "preset"))).stem),
                "description": str(item.get("description", "")),
                "user": True,
                "extension": False,
            }
            for item in self._user_presets.values()
        ]
        users.sort(key=lambda item: str(item["name"]).casefold())
        favorites = set(str(v) for v in self._preset_meta.get("favorites", []))
        recent = [str(v) for v in self._preset_meta.get("recent", [])]
        categories = dict(self._preset_meta.get("categories", {}))
        result = builtins + extensions + users
        for item in result:
            preset_id = str(item.get("id", ""))
            item["favorite"] = preset_id in favorites
            item["recentRank"] = recent.index(preset_id) if preset_id in recent else -1
            item["userCategory"] = str(categories.get(preset_id, ""))
        return result

    @Slot(str)
    def applyPreset(self, preset_id: str) -> None:
        preset_key = str(preset_id)
        record = self._user_presets.get(preset_key) or self._extension_presets.get(preset_key)
        if record is None:
            super().applyBuiltinPreset(preset_key)
            self._touch_recent_preset(preset_key)
            return
        try:
            path = Path(str(record.get("file", "")))
            loaded = merge_preset_with_current_crop(load_preset(path), self.settings)
            self._replace_settings(
                loaded,
                action=f"Applied preset: {record.get('name') or path.stem}",
            )
            self._touch_recent_preset(preset_key)
        except Exception as exc:
            self.errorOccurred.emit("Could not apply preset", str(exc))

    @Property("QVariantList", notify=presetMutationsChanged)
    def presetMutations(self) -> list[dict[str, object]]:
        return [dict(item) for item in self._preset_mutation_items]

    def _settings_for_preset_mutation(self, preset_id: str) -> tuple[ProcessingSettings, str]:
        key = str(preset_id)
        record = self._user_presets.get(key) or self._extension_presets.get(key)
        if record is not None:
            path = Path(str(record.get("file", "")))
            settings = merge_preset_with_current_crop(load_preset(path), self.settings)
            return settings, str(record.get("name") or path.stem)
        preset = next((item for item in builtin_presets.BUILTIN_PRESETS if item.id == key), None)
        if preset is None:
            raise KeyError(f"Unknown preset: {key}")
        return builtin_presets.build_builtin_preset(key, self.settings), preset.name

    @Slot(str, int, float)
    def generatePresetMutations(self, preset_id: str, count: int = 8, amount: float = 0.35) -> None:
        try:
            source_settings, source_name = self._settings_for_preset_mutation(str(preset_id))
            count = max(6, min(12, int(count)))
            amount = max(0.05, min(1.0, float(amount)))
            seed = random.SystemRandom().randrange(1, 2**31 - 1)
            generated = generate_preset_mutations(
                source_settings.to_dict(), count=count, amount=amount, seed=seed
            )
            self._preset_mutation_generation += 1
            generation = self._preset_mutation_generation
            self._preset_mutations.clear()
            self._preset_mutation_items.clear()
            self._preset_thumbnail_revision += 1

            for item in generated:
                number = int(item.get("variant", len(self._preset_mutation_items) + 1))
                mutation_id = f"mutation-{generation}-{number}"
                settings = ProcessingSettings.from_dict(dict(item.get("settings") or {}))
                summary = str(item.get("summary") or "Controlled variation")
                self._preset_mutations[mutation_id] = settings
                self._preset_mutation_items.append({
                    "id": mutation_id,
                    "name": f"{source_name} · {number}",
                    "description": summary,
                    "mutation": True,
                    "user": False,
                    "favorite": False,
                    "recentRank": -1,
                    "userCategory": "",
                    "sourcePresetId": str(preset_id),
                })
                if self.hasSource:
                    self._queue_preset_thumbnail(mutation_id, settings)

            self.presetMutationsChanged.emit()
            self._set_status(f"Generated {len(self._preset_mutation_items)} mutations from {source_name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not mutate preset", str(exc))

    @Slot(str)
    def applyPresetMutation(self, mutation_id: str) -> None:
        settings = self._preset_mutations.get(str(mutation_id))
        if settings is None:
            return
        label = next((str(item.get("name")) for item in self._preset_mutation_items if str(item.get("id")) == str(mutation_id)), "Preset mutation")
        loaded = merge_preset_with_current_crop(ProcessingSettings.from_dict(settings.to_dict()), self.settings)
        self._replace_settings(loaded, action=f"Applied mutation: {label}")

    @Slot()
    def clearPresetMutations(self) -> None:
        if not self._preset_mutation_items:
            return
        self._preset_mutations.clear()
        self._preset_mutation_items.clear()
        self.presetMutationsChanged.emit()
        self._set_status("Cleared preset mutations")

    @Slot(str, str)
    def savePresetToLibrary(self, name: str, description: str) -> None:
        clean_name = str(name or "").strip() or "Custom Preset"
        clean_description = str(description or "").strip()
        slug = slugify_preset_name(clean_name)
        preset_id = f"user-{slug}"
        folder = self._user_preset_folder()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{slug}.json"

        try:
            save_preset(
                path,
                self.settings,
                preset_id=preset_id,
                name=clean_name,
                description=clean_description,
            )
            payload = load_preset_payload(path)
            payload["file"] = str(path)
            payload["user"] = True
            self._user_presets[preset_id] = payload
            self.presetLibraryChanged.emit()
            self._set_status(f"Saved preset to library: {clean_name}")
            self._refresh_user_preset_thumbnail(preset_id)
        except Exception as exc:
            self.errorOccurred.emit("Could not save preset", str(exc))

    @Slot(str, str)
    def duplicatePresetInLibrary(self, preset_id: str, new_name: str) -> None:
        source = self._user_presets.get(str(preset_id))
        if source is None:
            return
        try:
            settings = load_preset(Path(str(source.get("file", ""))))
            clean = str(new_name or "").strip() or f"{source.get('name', 'Preset')} Copy"
            slug = slugify_preset_name(clean)
            new_id = f"user-{slug}"
            folder = self._user_preset_folder(); folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{slug}.json"
            save_preset(path, settings, preset_id=new_id, name=clean, description=str(source.get("description", "")))
            payload = load_preset_payload(path); payload.update(file=str(path), user=True, id=new_id)
            self._user_presets[new_id] = payload
            category = dict(self._preset_meta.get("categories", {})).get(str(preset_id), "")
            if category:
                categories = dict(self._preset_meta.get("categories", {})); categories[new_id] = category; self._preset_meta["categories"] = categories; self._save_preset_meta()
            self.presetLibraryChanged.emit(); self._refresh_user_preset_thumbnail(new_id)
            self._set_status(f"Duplicated preset: {clean}")
        except Exception as exc:
            self.errorOccurred.emit("Could not duplicate preset", str(exc))

    @Slot(str, str, str, str, result=str)
    def updatePresetInLibrary(
        self,
        preset_id: str,
        new_name: str,
        description: str,
        category: str,
    ) -> str:
        old_id = str(preset_id)
        source = self._user_presets.get(old_id)
        clean_name = str(new_name or "").strip()
        if source is None or not clean_name:
            return ""

        clean_description = str(description or "").strip()
        clean_category = str(category or "").strip()
        try:
            settings = load_preset(Path(str(source.get("file", ""))))
            old_file = Path(str(source.get("file", "")))
            slug = slugify_preset_name(clean_name)
            new_id = f"user-{slug}"
            existing = self._user_presets.get(new_id)
            if new_id != old_id and existing is not None:
                raise ValueError(f"A custom preset named '{clean_name}' already exists.")

            folder = self._user_preset_folder()
            folder.mkdir(parents=True, exist_ok=True)
            new_file = folder / f"{slug}.json"
            save_preset(
                new_file,
                settings,
                preset_id=new_id,
                name=clean_name,
                description=clean_description,
            )
            if old_file != new_file and old_file.is_file():
                old_file.unlink()

            payload = load_preset_payload(new_file)
            payload.update(file=str(new_file), user=True, id=new_id)
            if new_id != old_id:
                del self._user_presets[old_id]
            self._user_presets[new_id] = payload

            for meta_key in ("favorites", "recent"):
                values = [
                    new_id if str(value) == old_id else str(value)
                    for value in self._preset_meta.get(meta_key, [])
                ]
                self._preset_meta[meta_key] = values

            categories = dict(self._preset_meta.get("categories", {}))
            categories.pop(old_id, None)
            if clean_category:
                categories[new_id] = clean_category
            else:
                categories.pop(new_id, None)
            self._preset_meta["categories"] = categories
            self._save_preset_meta()

            self.presetLibraryChanged.emit()
            self._refresh_user_preset_thumbnail(new_id)
            self._set_status(f"Saved preset: {clean_name}")
            return new_id
        except Exception as exc:
            self.errorOccurred.emit("Could not update preset", str(exc))
            return ""

    @Slot(str, str)
    def renamePresetInLibrary(self, preset_id: str, new_name: str) -> None:
        source = self._user_presets.get(str(preset_id))
        if source is None:
            return
        category = str(dict(self._preset_meta.get("categories", {})).get(str(preset_id), ""))
        self.updatePresetInLibrary(
            str(preset_id),
            str(new_name or ""),
            str(source.get("description", "")),
            category,
        )

    @Slot(str)
    def exportPresetPack(self, value: str) -> None:
        try:
            path = _local_path(value)
            if path.suffix.lower() != ".json": path = path.with_suffix(".json")
            presets = []
            for record in self._user_presets.values():
                payload = load_preset_payload(Path(str(record.get("file", ""))))
                presets.append(payload)
            document = {"schema": "rastermint-preset-pack", "version": 1, "presets": presets}
            path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self._set_status(f"Exported preset pack: {path.name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not export preset pack", str(exc))

    @Slot(str)
    def importPresetPack(self, value: str) -> None:
        try:
            path = _local_path(value)
            document = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(document, dict) or document.get("schema") != "rastermint-preset-pack":
                raise ValueError("Not a RasterMint preset pack.")
            folder = self._user_preset_folder(); folder.mkdir(parents=True, exist_ok=True)
            count = 0
            for payload in document.get("presets", []):
                if not isinstance(payload, dict): continue
                settings_payload = payload.get("settings") if isinstance(payload.get("settings"), dict) else payload
                settings = ProcessingSettings.from_dict(settings_payload)
                name = str(payload.get("name", "Imported Preset"))
                slug = slugify_preset_name(name); preset_id = f"user-{slug}"; target = folder / f"{slug}.json"
                save_preset(target, settings, preset_id=preset_id, name=name, description=str(payload.get("description", "")))
                loaded = load_preset_payload(target); loaded.update(file=str(target), user=True, id=preset_id)
                self._user_presets[preset_id] = loaded; count += 1
            self.presetLibraryChanged.emit(); self.refreshPresetThumbnails(); self._set_status(f"Imported {count} preset(s)")
        except Exception as exc:
            self.errorOccurred.emit("Could not import preset pack", str(exc))

    @Slot(str)
    def deletePresetFromLibrary(self, preset_id: str) -> None:
        record = self._user_presets.get(str(preset_id))
        if record is None:
            return
        try:
            file_path = Path(str(record.get("file", "")))
            if file_path.is_file():
                file_path.unlink()
            name = str(record.get("name") or "Preset")
            del self._user_presets[str(preset_id)]
            self._preset_meta["favorites"] = [v for v in self._preset_meta.get("favorites", []) if str(v) != str(preset_id)]
            self._preset_meta["recent"] = [v for v in self._preset_meta.get("recent", []) if str(v) != str(preset_id)]
            categories = dict(self._preset_meta.get("categories", {})); categories.pop(str(preset_id), None); self._preset_meta["categories"] = categories
            self._save_preset_meta()
            self.presetLibraryChanged.emit()
            self._set_status(f"Removed preset from library: {name}")
        except Exception as exc:
            self.errorOccurred.emit("Could not remove preset", str(exc))

    def _queue_preset_thumbnail(self, preset_id: str, settings: ProcessingSettings) -> None:
        source = self._active_source()
        if source is None:
            return
        source_revision = self._source_revision
        final_size = target_raster_size(source.size, settings)
        preview_source = make_preview_source(source, max_side=128, settings=settings)
        preview_settings = make_preview_settings(settings, final_size, preview_source.size)
        job = self._next_job()
        worker = ProcessingWorker(
            job,
            "preset-thumbnail",
            preview_source,
            preview_settings,
            {
                "preset_id": preset_id,
                "source_revision": source_revision,
                "thumbnail_revision": self._preset_thumbnail_revision,
            },
            display_mode="display",
            include_grid=False,
        )
        self._connect_worker(worker)
        self.thread_pool.start(worker, -1)

    def _refresh_user_preset_thumbnail(self, preset_id: str) -> None:
        record = self._user_presets.get(str(preset_id))
        if record is None or not self.hasSource:
            return
        try:
            settings = merge_preset_with_current_crop(
                load_preset(Path(str(record["file"]))),
                self.settings,
            )
            self._queue_preset_thumbnail(str(preset_id), settings)
        except Exception:
            pass

    @Slot()
    def refreshPresetThumbnails(self) -> None:
        super().refreshPresetThumbnails()
        if not self.hasSource:
            return
        for preset_id in list(self._user_presets):
            self._refresh_user_preset_thumbnail(preset_id)
