# PRXMPT UI baseline

Status: authoritative from version 1.0.24
Baseline date: 20 July 2026
Reference width: 720 logical pixels

This document is the single interface contract for continued PRXMPT
development. Historical patch notes record how the app reached this state, but
they do not override the geometry, controls or behaviour defined here.

## Surface model

PRXMPT uses four independent frameless PySide6 surfaces. They scale uniformly
on smaller Windows work areas; their logical geometry remains fixed.

| Surface | Logical size | Behaviour |
| --- | ---: | --- |
| Top bar | 720 × 58 | Always-on-top owner window and startup state |
| Prompt screen | 720 × 35 | Live transcript, question editing and actions |
| Feedback window | 720 × 261 | Generated answer, model and answer controls |
| History popup | 720 × 164 maximum | Adaptive one-to-four-row meeting library |

The top bar and prompt screen have a 6 px logical gap. The prompt screen and
the active lower surface have another 6 px gap. Feedback and History share the
same anchor and are mutually exclusive.

## Top-bar baseline

| Control | Geometry | Baseline behaviour |
| --- | --- | --- |
| Drag lock | x=16, y=20, 25 × 25 | Locks or unlocks full-cluster movement |
| Microphone | x=87, y=20, 25 × 25 | Enables or disables microphone capture |
| Microphone lamp | x=110, y=23, 18 × 18 | Red, driven by live microphone level |
| Speaker | x=145, y=20, 25 × 25 | Enables or disables meeting-audio capture |
| Speaker lamp | x=168, y=23, 18 × 18 | Blue, driven by live loopback level |
| Live control | x=209, y=21, 57 × 25 | Starts or stops a listening session |
| PRXMPT logo | x=308, y=8, 104 × 56 | Shows/hides controls; drag handle when unlocked |
| Settings | x=603, y=20, 25 × 25 | Opens settings, context, skins and updates |
| Opacity | x=640, y=20, 25 × 25 | Opens whole-cluster opacity control |
| Close | x=677, y=20, 25 × 25 | Minimises to the system tray |

There is no profile shortcut and no separate eye/show-hide button. The former
profile position remains empty. The opacity control occupies the former eye
position. Profiles and context remain available through Settings.

### Logo interaction

- The canonical `prxmpt-logo.png` artwork, 104 × 56 size and x=308/y=8 position
  are unchanged.
- Hover uses an artwork-only glow at 0.11 maximum opacity with 1.6 px cardinal
  offsets. It must not draw an outline or button surface.
- Pressing applies a restrained 1.8% squeeze.
- When dragging is unlocked, dragging the logo moves the complete popup cluster
  and suppresses the show/hide click after real movement begins.

### Audio-lamp interaction

- Microphone and speaker lamps receive the actual live RMS level rather than a
  binary state.
- Their nonlinear curve keeps quiet speech visible and avoids immediate
  saturation on loud speech.
- Attack is 48 ms and decay is 155 ms.

## Prompt-screen baseline

| Control | Geometry |
| --- | --- |
| History toggle | x=15, y=4, 25 × 27 |
| Ghost Writer / Plot toggle | x=42, y=4, 25 × 27 |
| Live transcript and question | x=70, y=7, 580 × 20 |
| Transcribing indicator | x=618, y=8, 26 × 18 |
| Clear | x=650, y=4, 24 × 27 |
| Answer | x=676, y=4, 29 × 27 |

The transcript stays visible while listening. Probable questions are bold. The
three-dot indicator appears only while transcription is active.

## Feedback-window baseline

| Control | Geometry |
| --- | --- |
| Answer view | x=6, y=7, 708 × 215 |
| Loading spinner | x=349, y=104, 22 × 22 |
| Validated model dropdown | x=14, y=227, 100 × 25 |
| Previous answer | x=326, y=228, 25 × 25 |
| Next answer | x=369, y=228, 25 × 25 |
| Auto answer | x=607, y=227, 25 × 25 |
| Stealth placeholder | x=677, y=227, 25 × 25 |

The model menu lists only cloud models whose credentials validate and local
models that are currently installed. The Stealth control remains an explicit
non-functional placeholder.

## History-popup baseline

- Each meeting record is 34 px high with a 4 px gap.
- Popup heights are 50, 88, 126 and 164 px for one, two, three and four-or-more
  records respectively.
- Additional records remain available through smooth wheel or trackpad
  scrolling.
- Every record shows meeting number, local date/time, duration and model, plus
  transcript, notes and delete actions.
- Hovering a record keeps it at full opacity while every sibling animates to
  64% opacity over 120 ms with an OutCubic easing curve.
- Leaving the focused record restores all rows to full opacity. Actions remain
  visible and clickable throughout the transition.

## Popup states

| State | Visible surfaces |
| --- | --- |
| Startup / top only | Top bar |
| Controls | Top bar + prompt screen |
| Plot | Top bar + prompt screen + feedback window |
| History | Top bar + prompt screen + history popup |

Clicking the centred logo toggles between top-only and controls. Plot and
History replace one another and return to Controls when toggled closed.

## Visual system

- All outer popup surfaces and main content cards use a 10 logical px corner radius.
  This includes the visible top-bar backdrop and outer mask, Prompt,
  Feedback and History cards and masks, Answer view, and every meeting row.
- Switches, audio lamps and the model badge remain deliberately pill-shaped or
  circular. Small controls retain their component-specific radii.
- Canonical PNG and SVG artwork is hash-locked by the asset manifests.
- Midnight, Azure Knight and Rose Quartz are the supported skins.
- Azure Knight remains fully opaque; the other skins keep their configured
  translucency.
- Tactile icon feedback stays fill-only, without hover or focus outlines around
  supplied artwork.
- The whole popup cluster shares one user-controlled opacity value.
- Dormant `profile.png` and `collapse.png` source artwork is retained only for
  asset-history compatibility; no Designer form or runtime control references
  either file.

## Functional baseline included in this repository

- Local microphone and Windows WASAPI loopback capture.
- Live level lamps, local faster-whisper transcription and question detection.
- Full live transcript, provisional bold questions and manual question editing.
- Local grounded outlines, Gemini, OpenAI and installed Ollama models.
- Credential-validated main-popup model selection.
- PDF, DOCX, TXT and Markdown context ingestion with local retrieval.
- SQLite profiles, documents, transcripts, generated answers and meeting
  metadata.
- System tray, global shortcuts, skins, update checks and verified in-place
  update handoff.
- Reproducible PyInstaller/Inno Setup and GitHub Actions Windows builds.
- Project-local pytest temporary storage to avoid protected Windows Temp links.

The internal Python package remains named `clearcue` for upgrade and data-path
compatibility. The installed product, executable, installer and user-facing
identity are PRXMPT.

## Baseline change rule

Future UI work must update the relevant Designer form or Python control, this
document and the baseline tests in the same commit. Geometry changes must also
update popup masks and scaling helpers. A release is not a new baseline until
those checks pass and the baseline version is advanced deliberately.
