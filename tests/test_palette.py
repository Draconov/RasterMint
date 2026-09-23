# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from PIL import Image

from rastermint.core.palette import (
    BUILTIN_PALETTES,
    extract_palette,
    hex_to_rgb,
    rgb_to_hex,
)


def test_hex_roundtrip():
    assert hex_to_rgb("#12ABEF") == (0x12, 0xAB, 0xEF)
    assert rgb_to_hex((18, 171, 239)) == "#12ABEF"


def test_extract_palette_returns_requested_range():
    img = Image.new("RGB", (16, 16), "red")
    for x in range(8, 16):
        for y in range(16):
            img.putpixel((x, y), (0, 0, 255))
    colors = extract_palette(img, 4)
    assert 2 <= len(colors) <= 4


def test_builtin_palettes_have_colors():
    assert BUILTIN_PALETTES
    assert all(len(colors) >= 2 for colors in BUILTIN_PALETTES.values())


def test_palette_file_import_hex_gpl_and_jasc(tmp_path):
    from rastermint.core.palette import read_palette_file

    hex_file = tmp_path / "sample.hex"
    hex_file.write_text("112233\n#AABBCC\n", encoding="utf-8")
    assert read_palette_file(hex_file) == ["#112233", "#AABBCC"]

    gpl = tmp_path / "sample.gpl"
    gpl.write_text("GIMP Palette\nName: Sample\n255 0 0 Red\n0 255 0 Green\n", encoding="utf-8")
    assert read_palette_file(gpl) == ["#FF0000", "#00FF00"]

    pal = tmp_path / "sample.pal"
    pal.write_text("JASC-PAL\n0100\n2\n0 0 255\n255 255 255\n", encoding="utf-8")
    assert read_palette_file(pal) == ["#0000FF", "#FFFFFF"]


# ---- merged from test_lospec.py ----

import json

from rastermint.core.lospec import normalize_lospec_slug, palette_json_url, parse_lospec_palette


def test_lospec_slug_accepts_slug_and_full_url():
    assert normalize_lospec_slug("PICO-8") == "pico-8"
    assert normalize_lospec_slug("https://lospec.com/palette-list/greyt-bit/") == "greyt-bit"
    assert palette_json_url("greyt-bit").endswith("/greyt-bit.json")


def test_lospec_json_parser_preserves_attribution_and_colors():
    payload = json.dumps({
        "name": "Example Palette",
        "author": "Pixel Artist",
        "colors": ["000000", "abcdef", "FFFFFF"],
    })
    palette = parse_lospec_palette("example-palette", payload)
    assert palette.name == "Example Palette"
    assert palette.author == "Pixel Artist"
    assert palette.colors == ["#000000", "#ABCDEF", "#FFFFFF"]
    assert palette.source_url.endswith("/example-palette")


def test_user_content_backup_preserves_custom_libraries_and_metadata(tmp_path):
    import json
    from zipfile import ZipFile
    from rastermint.core.user_content_backup import export_user_content

    data_root = tmp_path / "app-data"
    (data_root / "palettes").mkdir(parents=True)
    (data_root / "presets").mkdir()
    (data_root / "cache").mkdir()
    (data_root / "palettes" / "custom.json").write_text('{"category":"My colours"}', encoding="utf-8")
    (data_root / "presets" / "custom.json").write_text('{"name":"My preset"}', encoding="utf-8")
    (data_root / "cache" / "preview.png").write_bytes(b"private cache")
    collections = {"presetLibraryMetaV1": {"categories": {"user-test": "My presets"}}}
    destination = tmp_path / "backups" / "my-content.zip"
    assert export_user_content(destination, data_root, collections) == 2

    with ZipFile(destination) as archive:
        names = set(archive.namelist())
        assert names == {"manifest.json", "palettes/custom.json", "presets/custom.json"}
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["format"] == "rastermint-user-content"
        assert manifest["collections"] == collections


def test_user_content_backup_does_not_follow_symlinks(tmp_path):
    from zipfile import ZipFile
    from rastermint.core.user_content_backup import export_user_content

    root = tmp_path / "app-data"
    folder = root / "palettes"
    folder.mkdir(parents=True)
    external = tmp_path / "private.json"
    external.write_text('{"secret":"outside"}', encoding="utf-8")
    (folder / "link.json").symlink_to(external)
    target = tmp_path / "backup.zip"
    assert export_user_content(target, root, {}) == 0
    with ZipFile(target) as archive:
        assert archive.namelist() == ["manifest.json"]


def test_user_content_backup_import_merge_and_replace(tmp_path):
    import json
    from zipfile import ZipFile
    from rastermint.core.user_content_backup import export_user_content, import_user_content

    source_root = tmp_path / "source-data"
    (source_root / "palettes").mkdir(parents=True)
    (source_root / "presets").mkdir()
    (source_root / "palettes" / "imported.json").write_text('{"name":"Imported palette"}', encoding="utf-8")
    (source_root / "presets" / "imported.json").write_text('{"name":"Imported preset"}', encoding="utf-8")
    backup_path = tmp_path / "content.zip"
    collections = {
        "presetLibraryMetaV1": {"categories": {"user-a": "Cool"}},
        "customDitherMatricesV1": [{"name": "Grid", "matrix": [[0, 1], [2, 3]]}],
    }
    export_user_content(backup_path, source_root, collections)

    target_root = tmp_path / "target-data"
    (target_root / "palettes").mkdir(parents=True)
    (target_root / "presets").mkdir()
    (target_root / "palettes" / "existing.json").write_text('{"name":"Existing palette"}', encoding="utf-8")
    (target_root / "presets" / "existing.json").write_text('{"name":"Existing preset"}', encoding="utf-8")

    count, imported = import_user_content(backup_path, target_root, mode="merge")
    assert count == 2
    assert imported == collections
    assert (target_root / "palettes" / "existing.json").is_file()
    assert (target_root / "palettes" / "imported.json").is_file()
    assert (target_root / "presets" / "existing.json").is_file()
    assert (target_root / "presets" / "imported.json").is_file()

    count, imported = import_user_content(backup_path, target_root, mode="replace")
    assert count == 2
    assert imported == collections
    assert not (target_root / "palettes" / "existing.json").exists()
    assert not (target_root / "presets" / "existing.json").exists()
    assert (target_root / "palettes" / "imported.json").is_file()
    assert (target_root / "presets" / "imported.json").is_file()


def test_user_content_backup_import_rejects_invalid_zip(tmp_path):
    from zipfile import ZipFile
    from rastermint.core.user_content_backup import import_user_content

    path = tmp_path / "bad.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", "{}")
    try:
        import_user_content(path, tmp_path, mode="merge")
    except ValueError as exc:
        assert "unsupported" in str(exc) or "missing" in str(exc)
    else:
        raise AssertionError("expected invalid backup to raise ValueError")
