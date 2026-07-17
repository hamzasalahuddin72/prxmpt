# prxmpt 1.0.11

This patch upgrades the five-popup interface and adds an optional Google Gemini
answer provider. Existing profiles, context, transcripts, settings and meeting
history are preserved by the in-place installer.

## Interface

- Applies the revised fixed 516 × 393 Plot popup reference.
- Reproduces the approved `#00C3D0` cyan-blue radial glow behind live answer text.
- Uses the approved 63%-opaque outer Plot card and 58 px corner radius.
- Makes the live answer editor transparent so it no longer hides the artwork.
- Introduces one native `GlassButton` renderer for consistent rounded, glossy,
  hover, pressed, selected, focus and disabled states.
- Normalizes Answer/Clear and Plot/History heights to 22 px.
- Normalizes microphone/speaker hit surfaces to 45 × 45 px, top-bar hit surfaces
  to 28 × 28 px, and meeting actions to 28 × 28 px.
- Preserves the five fixed component sizes and smaller-screen cluster scaling.

## Gemini answers

- Adds Google Gemini as an optional provider using the official `google-genai`
  package and stateless Interactions API.
- Provides Quality (`gemini-3.5-flash`) and Fast
  (`gemini-3.1-flash-lite`) choices.
- Streams answer text into the Plot popup as it arrives.
- Cancels the visible request when Clear is pressed so late output is ignored.
- Stores the Gemini key in Windows Credential Manager, never `settings.json`.
- Includes a Google AI Studio key link, Test Connection action and Clear Key
  action in Settings.
- Handles invalid keys, quota/429 responses, missing dependencies and timeouts
  with actionable messages while retaining Local mode.
- Sends only the question, instructions and retrieved text context. Audio remains
  in the local `tiny.en` transcription pipeline.

## Build and verification

- Updates the Windows installer, GitHub Actions artifact and release metadata to
  `prxmptUpdate_1.0.11.exe`.
- Keeps the bundled and validated `tiny.en` model requirement.
- Expands automated coverage for Gemini streaming, quota handling, configuration
  migration, answer cancellation and consistent fixed control geometry.

## Free-tier notice

Gemini free-tier availability and quotas are controlled by Google and can change.
Google states that free-tier content may be used to improve its products. Review
the current Google AI Studio terms before sending sensitive meeting content.
