# Application Icons

RasterMint ships platform-specific application icons generated from the project artwork under:

```text
src/rastermint/data/icons/
```

## Included assets

| Asset | Purpose |
| --- | --- |
| `rastermint.ico` | Windows executable icon |
| `rastermint.icns` | macOS application bundle icon |
| `rastermint.png` | Runtime/window icon and Linux fallback |
| `rastermint-16.png` … `rastermint-1024.png` | Size-specific PNG variants |

The documentation copy used by the README lives at `docs/assets/rastermint-icon.png`.

## Runtime behavior

`rastermint.app` loads `data/icons/rastermint.png` through package resources and sets it as the Qt application/window icon when available.

## Packaging

`build/rastermint.spec` uses:

- `.ico` for the Windows PyInstaller executable;
- `.icns` for the macOS bundle.

Linux desktop environments use the runtime PNG unless a distribution package supplies additional desktop metadata.

## Updating the icon

When replacing the application artwork:

1. regenerate all platform/PNG variants from the same source artwork;
2. preserve the existing filenames unless the spec/runtime loader is updated too;
3. verify transparency and edge quality at 16/24/32 px;
4. verify Windows and macOS packaged artifacts, not only the development window;
5. run the icon asset test.
