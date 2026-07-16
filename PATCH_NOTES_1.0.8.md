# prxmpt 1.0.8 rename, interface and bundled-speech update

This release installs over ClearCue 1.0.7 with the same Windows application ID.
The installed application, executable, shortcuts, tray menu and Windows Apps
entry are renamed to **prxmpt**. The release asset remains named
`ClearCueUpdate_1.0.8.exe` once so existing 1.0.7 clients can detect it.

## Final approved interface

- Uses the approved `551 × 827` popup body and scales down on smaller work areas.
- Displays the new `prxmpt` logo and exact image assets extracted from the final
  SVG without emoji or icon substitution.
- Keeps the frameless popup top-centred, always on top and transparent outside
  its rounded body.
- Moves the model badge to the answer footer and keeps the dummy Stealth toggle.
- Uses `START`/`LIVE` beside the microphone and meeting-audio controls.
- Shows the three-dot indicator only during active speech-model inference.
- Keeps the red X as minimize-to-tray and the lock icon as the drag lock.
- Keeps transcript, answer/notes and delete controls for each recent meeting.

## Speech reliability and latency

- Bundles the `Systran/faster-whisper-tiny.en` model in the Windows application.
- Validates `config.json`, `tokenizer.json` and a complete `model.bin` during the
  build, so an incomplete installer fails before release.
- Loads the packaged model before consulting the user model cache.
- Uses CPU/`int8` as the migrated default and keeps CUDA-to-CPU recovery.
- Reduces end-of-utterance silence to approximately 280 ms.
- Collects adjacent interviewer transcript fragments and waits for an 850 ms
  question pause before one automatic answer is generated.
- Reports transcription activity separately from the listening-session state.

## Upgrade preservation

- Copies existing settings and SQLite history from `%LOCALAPPDATA%\ClearCue` to
  `%LOCALAPPDATA%\prxmpt` without deleting the previous data.
- Migrates the existing OpenAI credential from the legacy Windows Credential
  Manager service on first read.
- Keeps the existing Inno Setup AppId for an in-place update.

## Building

Run `BUILD_UPDATE_V1.0.8.bat` or `BUILD_INSTALLER.bat`. The first build downloads
the speech snapshot into `build\models\faster-whisper-tiny.en`; subsequent local
builds reuse it. The result is:

`installer\output\ClearCueUpdate_1.0.8.exe`
