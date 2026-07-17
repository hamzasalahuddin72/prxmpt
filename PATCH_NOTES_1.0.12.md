# prxmpt 1.0.12

## Four-surface interface rebuild

- Replaces the previous five-popup cluster with the four revised 657 px-wide
  component specifications supplied for this patch:
  - 657 × 46 top bar
  - 657 × 166 prompt screen
  - 657 × 275 feedback window
  - 657 × 164 history popup
- Keeps only the top bar visible at startup.
- The eye control shows or hides the prompt screen and any open child surface.
- Plot opens the feedback window and History opens the meeting list; the two
  lower surfaces remain mutually exclusive.
- Keeps the entire cluster always on top, draggable when unlocked, clamped to
  the active Windows work area and uniformly scaled on smaller screens.

## Revised controls and assets

- Moves microphone, meeting-audio and live-session controls into the top bar.
- Moves Answer, Clear, transcription activity, Plot and History into the prompt
  screen at the exact supplied coordinates.
- Uses the revised prxmpt logo and original embedded PNG bytes for settings,
  audio, lock, hide, exit, loading, switches and all meeting actions.
- Rebuilds the feedback surface with the approved cyan radial glow, model badge,
  Auto answer and placeholder Stealth switch.
- Rebuilds saved meetings as four compact 625 × 34 rounded rows with transcript,
  answer/notes and delete actions aligned to the SVG.
- Retains tactile hover, focus, selected and pressed feedback through the shared
  lightweight native glass-button renderer.

## Editing and verification

- Adds editable `prxmpt-prompt-screen.ui` and
  `prxmpt-feedback-window.ui` forms and updates the top-bar and history forms.
- Preserves all four supplied SVGs byte-for-byte and verifies that their embedded
  icons match the packaged runtime assets.
- Updates fixed-geometry, popup-state, scaling and asset-integrity tests.
- Produces `installer\output\prxmptUpdate_1.0.12.exe` through
  `BUILD_INSTALLER.bat` or `BUILD_UPDATE_V1.0.12.bat`.
