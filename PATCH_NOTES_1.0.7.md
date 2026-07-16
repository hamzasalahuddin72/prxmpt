# ClearCue 1.0.7 compact popup update

This update installs over earlier ClearCue versions using the same Windows
application ID and installation directory. Profiles, context, settings, model
files, history and logs under `%LOCALAPPDATA%\ClearCue` are preserved.

## New popup interface

- ClearCue now opens directly as one frameless 520×760 popup centred at the top
  of the current Windows work area.
- The popup is always on top by default and scales down proportionally when the
  available display area is smaller.
- The separate dashboard and overlay workflow has been replaced by this single
  compact question-and-answer surface.
- The header provides profile/settings access, a lockable drag control, a
  collapse-to-header control and a close-to-tray button.
- `Ctrl+Alt+O` shows or hides the popup.

## Live controls

- The circular microphone and speaker buttons independently enable or disable
  their audio sources, including while a session is running.
- The centre three-dot pill starts and stops listening and changes to `LIVE`
  while capture is active.
- Consent confirmation is requested on first listening use instead of occupying
  permanent space in the popup.
- The Auto answer switch is live. The Stealth switch is a visual placeholder for
  a later feature and currently changes no application behaviour.

## Meeting history

- The four most recent local sessions appear in the bottom meeting list.
- Each row can open its transcript, open generated answers/notes, or delete the
  complete local meeting.
- Generated answers and their context-source names are now stored with the
  active session when transcript history is enabled.

## Model reliability

- If a Whisper cache contains metadata but is missing `model.bin`, ClearCue
  removes only that incomplete model cache and retries the download once.
- CUDA inference fallback, PortAudio microphone capture and bounded live
  transcription from 1.0.6 remain enabled.

## Install

Close ClearCue from its tray menu, then run `ClearCueUpdate_1.0.7.exe`. The
installer preserves local data and can relaunch the popup after an in-app update.
