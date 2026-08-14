# Application icon

RasterMint now includes a bundled application icon derived from the project
artwork under `src/rastermint/data/icons/`.

Included files:

- `rastermint.ico` — Windows executable icon
- `rastermint.icns` — macOS app bundle icon
- `rastermint.png` / size variants — runtime/Linux/README assets

The PyInstaller spec uses the `.ico` file for Windows builds and the `.icns`
file for macOS app bundles. The Qt application sets the runtime window icon
from `rastermint.png`, which is also used by Linux desktop environments that
show the window icon.
