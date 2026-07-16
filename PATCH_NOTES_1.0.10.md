# prxmpt 1.0.10 five-popup interface update

This patch replaces the previous monolithic popup with five coordinated,
fixed-size Designer surfaces based on the approved SVG components.

## Interface changes

- Starts with only the 516 × 46 top bar visible.
- The eye button shows or hides the audio handler and activity buttons.
- Plot and History open in one mutually exclusive content position.
- Clicking the active Plot or History button closes that content surface.
- Dragging the unlocked top bar moves the complete visible cluster together.
- Every surface has its own translucent rounded native window region.
- Restoring from the system tray always returns to the top-bar-only state.
- The complete cluster scales uniformly when the Windows work area is smaller
  than the 516 × 642 maximum reference layout.

## Preserved functionality

- Microphone and meeting-audio source toggles
- Clickable listening-status dot
- Question detection, transcription indicator and manual/automatic answers
- Scrollable meeting history with transcript, notes and delete actions
- Settings, profiles, updater, global shortcuts and system tray integration
- Bundled `tiny.en` speech model build validation

## Designer files

The editable forms are in `src\clearcue\assets`:

- `prxmpt-top-bar.ui`
- `prxmpt-audio-handler.ui`
- `prxmpt-activity-buttons.ui`
- `prxmpt-plot-popup.ui`
- `prxmpt-history-popup.ui`

The five supplied SVG files are retained byte-for-byte beside the forms and
verified during tests. Their embedded icons match the packaged PNG controls.

## Build

Run `BUILD_UPDATE_V1.0.10.bat` or `BUILD_INSTALLER.bat`. The finished installer
is `installer\output\prxmptUpdate_1.0.10.exe`.
