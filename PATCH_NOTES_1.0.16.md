# prxmpt 1.0.16

This patch adds a deliberately simple skin system based on the two palette
changes in the supplied blue-theme SVG.

## Included skins

- **Midnight** preserves the current popup appearance exactly: black popup
  base and the existing translucent lavender panel tint.
- **Azure Knight** uses the approved deep-teal `#1C4345` base at 42% opacity
  and cyan `#85F7FF` panel tint at 34% opacity.
- Each skin is stored in its own small JSON file. Layouts, icons, sizing and
  application behavior are shared and are not duplicated.

## Skin selection

- Open the top-bar Settings menu and choose **Skins**.
- The active skin has a check mark.
- Clicking another skin displays a restart warning, saves the choice and
  relaunches prxmpt automatically.
- If relaunch cannot start, prxmpt restores the previous skin instead of
  leaving a broken selection.

## Build

Run `BUILD_INSTALLER.bat` or `BUILD_UPDATE_V1.0.16.bat`. The finished update is
created as `installer\output\prxmptUpdate_1.0.16.exe`.
