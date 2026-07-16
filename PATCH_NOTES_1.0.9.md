# prxmpt 1.0.9 fixed-layout and Designer workflow update

## Fixed approved geometry

- Replaces the incorrect layout stretch ratios that caused the top bar to grow
  into a large empty panel.
- Locks the normal popup to the approved `551 × 827` logical canvas.
- Uses the exact SVG panel bounds: `515 × 64` header, `166 × 178` audio card,
  `350 × 178` question card, `532 × 393` answer card and `537 × 132` history.
- Keeps the complete canvas proportional when it must scale down for a smaller
  Windows work area.
- Preserves always-on-top, drag lock, collapse and minimize-to-tray behaviour.
- Clamps the collapsed corner radius and applies a rounded native window mask,
  preventing the hidden title bar from showing a square black outline.

## Manually editable interface

- Adds `src\clearcue\assets\prxmpt-main.ui` as the authoritative popup layout.
- Loads the form directly with PySide6 `QUiLoader`; saved Designer changes are
  visible on the next source launch without regenerating Python.
- Keeps dynamic controls, audio state, transcription, answers and meeting
  history connected in Python.
- Adds `docs\EDIT_UI_WITH_QT_DESIGNER.md` with setup, preview and safe-editing
  instructions.

## Packaging

- Packages the `.ui` source in both editable Python installs and the PyInstaller
  application.
- Changes the normal update filename to `prxmptUpdate_1.0.9.exe` now that the
  one-time ClearCue-to-prxmpt transition release is complete.
- Retains the bundled `tiny.en` speech model and existing update verification.

## Build

Run `BUILD_UPDATE_V1.0.9.bat` or `BUILD_INSTALLER.bat`. The finished installer is:

`installer\output\prxmptUpdate_1.0.9.exe`
