# prxmpt 1.0.20 hotfix

This hotfix repairs the missing lower-control text introduced by the v1.0.19
readability change.

## Fixed

- Removes `QGraphicsDropShadowEffect` from labels embedded in the scaled popup.
  Qt could clip those effected labels completely, hiding **LIVE**,
  **Auto answer** and **Stealth** in every skin.
- Replaces the effect with direct, low-cost label painting: bold white text with
  a very thin dark edge contained inside the label rectangle.
- Fixes the model badge font call that could interrupt its custom paint event,
  making the active model name disappear.
- Keeps the answer and live-transcript readability improvement from v1.0.19.
- Keeps the question reconstruction and résumé-grounding improvements unchanged.
- Moves the permanent PyInstaller specification and custom hook out of the
  generated `build` directory into `scripts`. Fresh source ZIPs, clean Git
  checkouts and projects moved to another directory can now build reliably.
- Corrects the permanent spec's project-root calculation so the bundled
  tiny.en files are found after a successful download.

## Build

Run `BUILD_INSTALLER.bat` or `BUILD_UPDATE_V1.0.20.bat`. The finished update is
created as `installer\output\prxmptUpdate_1.0.20.exe`.
