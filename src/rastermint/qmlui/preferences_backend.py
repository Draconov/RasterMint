# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QStandardPaths, QUrl, Signal, Slot

from rastermint.core import builtin_presets, palette_library
from rastermint.core.history import UndoHistory
from rastermint.core.palette_json import load_palette_json, slugify_palette_name, write_palette_json
from rastermint.core.presets import load_preset, load_preset_payload, save_preset, slugify_preset_name
from rastermint.core.settings import ProcessingSettings
from rastermint.qmlui.backend import RasterMintBackend as BaseRasterMintBackend
from rastermint.qmlui.workers import ProcessingWorker


DEFAULT_HISTORY_LIMIT = 50
MIN_HISTORY_LIMIT = 10
MAX_HISTORY_LIMIT = 200


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
    userPaletteLibraryChanged = Signal()
    presetLibraryChanged = Signal()

    def __init__(self, image_provider, parent=None) -> None:
        super().__init__(image_provider, parent)
        self._history_limit = _clamp_history_limit(
            self.app_settings.value("historyLimitQml", DEFAULT_HISTORY_LIMIT)
        )
        # The base backend creates history during construction, before any user
        # edits can exist. Recreate it with the persisted depth immediately.
        self._history = UndoHistory(limit=self._history_limit)

        self._user_palettes: dict[str, dict[str, object]] = {}
        self._user_presets: dict[str, dict[str, object]] = {}
        self._load_user_palettes()
        self._load_user_presets()

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

    @Slot()
    def resetSettings(self) -> None:
        super().resetSettings()
        changed = self._history_limit != DEFAULT_HISTORY_LIMIT
        self._history_limit = DEFAULT_HISTORY_LIMIT
        self._history.set_limit(DEFAULT_HISTORY_LIMIT)
        self.app_settings.setValue("historyLimitQml", DEFAULT_HISTORY_LIMIT)
        if changed:
            self.historyLimitChanged.emit()

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
        users = [
            {
                "id": str(item["id"]),
                "name": str(item.get("name") or Path(str(item.get("file", "preset"))).stem),
                "description": str(item.get("description", "")),
                "user": True,
            }
            for item in self._user_presets.values()
        ]
        users.sort(key=lambda item: str(item["name"]).casefold())
        return builtins + users

    @Slot(str)
    def applyPreset(self, preset_id: str) -> None:
        record = self._user_presets.get(str(preset_id))
        if record is None:
            super().applyBuiltinPreset(preset_id)
            return
        try:
            path = Path(str(record.get("file", "")))
            self._replace_settings(
                load_preset(path),
                action=f"Applied preset: {record.get('name') or path.stem}",
            )
        except Exception as exc:
            self.errorOccurred.emit("Could not apply preset", str(exc))

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
            {"preset_id": preset_id, "source_revision": source_revision},
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
            self._queue_preset_thumbnail(str(preset_id), load_preset(Path(str(record["file"]))))
        except Exception:
            pass

    @Slot()
    def refreshPresetThumbnails(self) -> None:
        super().refreshPresetThumbnails()
        if not self.hasSource:
            return
        for preset_id in list(self._user_presets):
            self._refresh_user_preset_thumbnail(preset_id)
