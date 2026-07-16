# ClearCue 1.0.5 performance and reliability update

This update installs over ClearCue 1.0.0 using the same Windows application ID
and installation directory. Profiles, context, settings, history, logs and cached
speech models under `%LOCALAPPDATA%\ClearCue` are preserved.

## Reliability changes

- Microphone and meeting-audio workers contain backend failures instead of
  allowing them to escape into the application.
- A stale saved device automatically falls back to the current Windows default.
- The upgrade clears legacy saved audio IDs once so the first v1.0.5 session uses
  the live Windows defaults; devices can then be selected explicitly in Settings.
- Capture tries 48 kHz, 44.1 kHz and 16 kHz shared-mode formats and reconnects
  automatically after disconnects or device changes.
- Audio availability is shown inline as `CONNECTED`, `RETRYING` or `OFF`; capture
  failures no longer create repeated modal dialogs.
- Unhandled application and worker errors are written to the rotating diagnostic
  log at `%LOCALAPPDATA%\ClearCue\logs\clearcue.log`.

## Live-transcription changes

- The performance default is now `tiny.en` on CPU with `int8` compute. Existing
  installations using the old default `small.en` migrate automatically.
- The model begins loading as soon as listening starts.
- Audio capture uses 20 ms reads and speech is emitted after roughly 360 ms of
  ending silence instead of roughly 700 ms.
- The transcription queue is deliberately bounded. If the computer falls behind,
  old audio is discarded so the visible transcript catches up to live speech.
- CPU inference uses a bounded thread count, greedy decoding and text-only tokens.
- An unavailable CUDA configuration automatically falls back to CPU/int8.

## Interface changes

- The main window is a flat, two-pane transcript and answer workspace.
- The theme is opaque black with white, cyan, yellow and green high-contrast states.
- Rounded cards, translucent overlay composition and rich-text answer widgets were
  removed from the performance build.
- Transcript history in the live widget is capped to avoid gradual UI slowdown.

## Install

Close ClearCue and run `ClearCueUpdate_1.0.5.exe`. Windows may ask permission to
close the running application. Launch ClearCue normally after setup finishes.

The first listening session can download the smaller `tiny.en` model once. Keep
`tiny.en` for minimum latency, or choose `base.en` in Settings for more accuracy.
