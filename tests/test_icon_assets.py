from importlib import resources


def test_icon_assets_present():
    base = resources.files("rastermint").joinpath("data/icons")
    for name in ["rastermint.png", "rastermint.ico", "rastermint.icns"]:
        path = base.joinpath(name)
        assert path.is_file(), f"missing icon asset: {name}"
