# prxmpt 1.0.17

This patch makes Azure Knight fully opaque by default and fixes the separate
saved window-opacity setting that could keep the skin transparent even after
editing its JSON file.

## Azure Knight opacity

- Azure Knight's deep-teal base now renders at 100% alpha.
- Existing Azure Knight users are migrated to 100% whole-window opacity once
  when this version first starts.
- Selecting Azure Knight from **Settings → Skins** resets the whole-window
  opacity to 100% before prxmpt restarts.
- The opacity slider remains available afterward, so the user can deliberately
  lower the entire popup cluster again.
- Midnight is unchanged.

## Build

Run `BUILD_INSTALLER.bat` or `BUILD_UPDATE_V1.0.17.bat`. The finished update is
created as `installer\output\prxmptUpdate_1.0.17.exe`.
