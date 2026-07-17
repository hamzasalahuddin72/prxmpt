# prxmpt 1.0.18

This patch adds the third selectable popup skin from the supplied pink-theme
SVG while preserving the existing layout, icons and behavior.

## Rose Quartz skin

- Adds **Rose Quartz** under **Settings → Skins**.
- Uses the SVG's exact pale-rose `#EAC9C2` popup base at 100% opacity.
- Uses the exact muted-berry `#BE818D` panel and row color at 100% opacity.
- Starts the whole popup cluster at 100% opacity when selected.
- Retains the normal opacity control for deliberate adjustments afterward.
- Midnight and Azure Knight remain unchanged.

## Build

Run `BUILD_INSTALLER.bat` or `BUILD_UPDATE_V1.0.18.bat`. The finished update is
created as `installer\output\prxmptUpdate_1.0.18.exe`.
