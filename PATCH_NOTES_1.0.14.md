# prxmpt 1.0.14

This is the full horizontal UI reconstruction based on the supplied SVG
canvases and canonical PNG artwork.

## Exact reference surfaces

- Top bar: `720 × 58`
- Prompt strip: `720 × 35`
- Answer/feedback surface: `720 × 261`
- History surface: `720 × 164`
- Only the top bar opens at startup.
- The eye toggles the prompt strip, while Ghost Writer and History switch the
  lower surface mutually exclusively.
- The entire cluster scales uniformly only when the Windows work area is too
  small for the reference geometry.

## Canonical visual assets

- Replaces every visible UI control with the newly supplied source artwork.
- Preserves the four uploaded SVG specifications byte-for-byte in the package.
- Extracts the prxmpt logo directly from the supplied top-bar vector group.
- Locks asset and SVG hashes in regression tests so later patches cannot
  silently substitute or alter approved artwork.

## Interaction and responsiveness

- Adds native Qt hover glow, press compression, soft focus feedback and smooth
  short-duration easing without a browser engine or continuous animation loop.
- Removes every popup-button outline. Interaction feedback is now limited to a
  faint translucent hover wash, a subtle icon lift and short click compression.
- Removes supporting-dialog button strokes and replaces them with restrained
  fill changes on hover and press.
- Adds the top-bar opacity button and a live 45–100% opacity slider.
- Adds functional previous/next navigation for generated answers.
- Keeps transcription dots hidden unless active transcription is occurring.
- Uses a single-line low-latency question field and scrollable four-row meeting
  history with the exact supplied transcript, notes and delete icons.
- Auto-sizes History to one, two, three or four populated rows, eliminating the
  empty black area when only one meeting exists.
- Animates History expansion and contraction with a short native Qt easing
  curve, then smoothly scrolls additional meetings beyond the four-row limit.

## Build

Run `BUILD_INSTALLER.bat` or `BUILD_UPDATE_V1.0.14.bat`. The finished update is
created as `installer\output\prxmptUpdate_1.0.14.exe`.
