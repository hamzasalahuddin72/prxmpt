# prxmpt 1.0.15

This patch implements the supplied live-transcript, answer-loading and updated
meeting-history designs.

## Live transcript and question emphasis

- The prompt strip now shows the complete transcript while listening instead
  of replacing it with only the latest detected question.
- The currently forming question-like sentence is bold. If the pause detector
  concludes that it was a normal remark, it returns to regular weight.
- Completed questions remain emphasized in the transcript and can trigger
  automatic answer generation after the listening pause.

## Answer generation surface

- A supplied rotating loading indicator appears in the answer surface as soon
  as answer generation starts.
- Streaming text replaces the loader without blocking the interface.
- Previous and next controls can browse earlier answers while a new answer is
  being generated, then return to the active result.

## Meeting history

- Every compact record now shows meeting title, local date and time, duration,
  AI model, and the existing transcript, notes and delete actions.
- The full history dialog shows the same metadata.
- Existing databases migrate automatically; no transcript data is removed.
- One-to-four-row expansion and smooth scrolling remain enabled.

## Visual correction

- Removes the unintended purple drop-shadow exported underneath the prxmpt
  logo while retaining the original blue and green artwork.
- Preserves the newly supplied live prompt, loading feedback and history SVGs
  as reference assets in the installer.

## Build

Run `BUILD_INSTALLER.bat` or `BUILD_UPDATE_V1.0.15.bat`. The finished update is
created as `installer\output\prxmptUpdate_1.0.15.exe`.
