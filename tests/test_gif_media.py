from __future__ import annotations

from pathlib import Path

from PIL import Image

from rastermint.core.media import export_processed_gif, probe_video, read_video_frame
from rastermint.core.settings import ProcessingSettings


def make_gif(path: Path) -> None:
    frames = []
    for index, color in enumerate(((255, 0, 0), (0, 255, 0), (0, 0, 255))):
        frame = Image.new("RGB", (12, 8), "black")
        for x in range(index * 4, index * 4 + 4):
            for y in range(8):
                frame.putpixel((x, y), color)
        frames.append(frame)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=[80, 120, 160], loop=0, disposal=2)


def test_gif_probe_and_time_decode(tmp_path):
    path = tmp_path / "input.gif"
    make_gif(path)
    info = probe_video(path)
    assert info.frames == 3
    assert info.width == 12 and info.height == 8
    a = read_video_frame(path, 0.01)
    b = read_video_frame(path, 0.11)
    assert a.getpixel((0, 0)) != b.getpixel((0, 0))


def test_gif_processing_preserves_animation(tmp_path):
    source = tmp_path / "input.gif"
    output = tmp_path / "output.gif"
    make_gif(source)
    settings = ProcessingSettings(palette=["#000000", "#FF0000", "#00FF00", "#0000FF", "#FFFFFF"], algorithm="Nearest Palette")
    export_processed_gif(source, settings, output)
    with Image.open(output) as result:
        assert getattr(result, "n_frames", 1) == 3
