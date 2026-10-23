"""Portable RasterMint .rastermint projects and translation integrity."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from PIL import Image

from rastermint.core.project import load_project_file, save_project_file


def test_project_embeds_source_and_custom_sprite_and_restores_without_originals(tmp_path):
    source = tmp_path / 'photo.png'
    sprite = tmp_path / 'sprite.png'
    Image.new('RGB', (16, 12), '#223344').save(source)
    Image.new('RGBA', (5, 5), '#aabbcc').save(sprite)
    settings = {'effect_stack': [
        {'kind': 'Pixel Material', 'params': {'sprite_path': str(sprite)}}
    ]}
    project = save_project_file(tmp_path / 'portable.rastermint', {
        'source': {'path': str(source), 'kind': 'image'},
        'settings': settings,
    }, package_assets=True)
    serialized = json.loads(project.read_text('utf-8'))
    assert len(serialized['embedded_assets']) == 2
    assert serialized['source']['path'].startswith('asset://')
    assert serialized['settings']['effect_stack'][0]['params']['sprite_path'].startswith('asset://')
    source.unlink()
    sprite.unlink()
    restored = load_project_file(project, extract_assets_to=tmp_path / 'restored')
    assert Path(restored['source']['path']).is_file()
    with Image.open(restored['settings']['effect_stack'][0]['params']['sprite_path']) as image:
        assert image.size == (5, 5)
    with Image.open(restored['source']['path']) as image:
        assert image.size == (16, 12)
    # After reopening an embedded project, saving again still preserves assets.
    second = save_project_file(tmp_path / 'resaved.rastermint', restored, package_assets=True)
    assert len(load_project_file(second)['embedded_assets']) == 2


def test_project_embeds_reference_image_and_font(tmp_path):
    font = tmp_path / 'custom.ttf'
    font.write_bytes(b'font-content-for-serialization')
    ref = tmp_path / 'reference.jpg'
    Image.new('RGB', (3, 4), 'red').save(ref)
    target = save_project_file(tmp_path / 'references.rastermint', {
        'ui': {'reference_path': str(ref)},
        'settings': {'effect_stack': [{'params': {'font_path': str(font)}}]},
    }, package_assets=True)
    restored = load_project_file(target, extract_assets_to=tmp_path / 'cache')
    assert Path(restored['ui']['reference_path']).read_bytes() == ref.read_bytes()
    assert Path(restored['settings']['effect_stack'][0]['params']['font_path']).read_bytes() == font.read_bytes()


def test_reject_modified_embedded_asset(tmp_path):
    image = tmp_path / 'image.png'
    Image.new('RGB', (5, 5), 'black').save(image)
    project = save_project_file(tmp_path / 'altered.rastermint', {'source': {'path': str(image)}}, package_assets=True)
    content = json.loads(project.read_text('utf-8'))
    entry = next(iter(content['embedded_assets'].values()))
    entry['sha256'] = '0' * 64
    project.write_text(json.dumps(content), encoding='utf-8')
    with pytest.raises(ValueError, match='metadata'):
        load_project_file(project, extract_assets_to=tmp_path / 'extracted')


def test_legacy_project_remains_readable(tmp_path):
    project = save_project_file(tmp_path / 'legacy.rastermint', {'settings': {'effect_stack': []}})
    assert 'embedded_assets' not in load_project_file(project)
    assert load_project_file(project, extract_assets_to=tmp_path / 'cache')['settings'] == {'effect_stack': []}


def test_all_qml_literal_translations_are_present_and_placeholders_match():
    root = Path(__file__).resolve().parents[1] / 'src' / 'rastermint'
    sources: set[str] = set()
    for qml_file in (root / 'qml').rglob('*.qml'):
        sources.update(re.findall(r'qsTr\("((?:[^"\\]|\\.)*)"\)', qml_file.read_text(encoding='utf-8')))
    assert sources
    translation_files = sorted((root / 'data' / 'translations').glob('*.json'))
    assert len(translation_files) == 21
    for translation_file in translation_files:
        payload = json.loads(translation_file.read_text(encoding='utf-8'))
        messages = payload['messages']
        missing = sources - set(messages)
        assert not missing, f'{translation_file.name}: missing {sorted(missing)}'
        for source, translated in messages.items():
            assert isinstance(translated, str) and translated.strip(), (translation_file.name, source)
            assert sorted(re.findall(r'%\d+', source)) == sorted(re.findall(r'%\d+', translated)), (translation_file.name, source)
