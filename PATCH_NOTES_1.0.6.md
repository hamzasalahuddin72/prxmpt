# ClearCue 1.0.6 reliability and updater patch

This is the final update that must be installed manually. Starting with 1.0.6,
ClearCue automatically detects newer stable GitHub Releases and can install a
verified update from inside the application.

## Microphone reliability

- Microphone capture now uses python-sounddevice/PortAudio instead of the
  SoundCard Windows recorder that rejected some USB, headset and virtual audio
  formats with a bare `AssertionError`.
- Meeting/system audio keeps the existing SoundCard WASAPI loopback path that
  was working correctly.
- The first 1.0.6 launch clears the incompatible saved microphone endpoint and
  selects the current Windows default. The saved loopback selection is retained.
- A stale PortAudio microphone index falls back to the current Windows default.
- Reconnection continues automatically, but repeated failures are summarized
  at most once every 30 seconds instead of flooding the diagnostic log.

## Transcription recovery

- Existing 1.0.5 configurations migrate once to `CPU` + `int8` for a reliable
  default.
- If a user later selects CUDA and CTranslate2 only discovers missing CUDA DLLs
  during inference, ClearCue reloads the model on CPU/int8 and retries the
  interrupted audio segment once.
- CPU settings reject incompatible float16 compute selections.

## In-app updates

- ClearCue checks the public GitHub latest-release endpoint after startup and
  every six hours without requiring a GitHub account or token.
- A visible high-contrast banner provides release notes, Later, and Download
  and install controls.
- Downloads run in the background with progress and must match GitHub's
  SHA-256 release-asset digest before execution.
- The installer updates the same per-user application directory, preserves all
  application data, and relaunches ClearCue after a successful silent update.
- Network, parsing, download or integrity failures are contained and reported;
  they never prevent ClearCue from starting.

## Build and release pipeline

- Version tags such as `v1.0.6` build and publish a permanent GitHub Release.
- Manual workflow runs continue to produce a downloadable Actions artifact.
- The Windows builder no longer tries to open Explorer on a GitHub Actions runner.

## Install

Close ClearCue and run `ClearCueUpdate_1.0.6.exe`, or allow setup to close it.
This update preserves `%LOCALAPPDATA%\ClearCue` and installs without administrator
rights. Future published patches can be installed through ClearCue's update banner.
