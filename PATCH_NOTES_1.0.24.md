# PRXMPT 1.0.24 — consolidated UI baseline

Version 1.0.24 is the complete development baseline for the next stage of
PRXMPT. It consolidates the latest source, interface, assets, tests, installer
metadata and build workflow into one GitHub-ready repository.

## Confirmed latest changes

- Meeting-library hover focus: the hovered record stays fully visible while
  sibling records animate to 64% opacity, then restore on leave.
- Stronger logo glow: the centred PRXMPT logo keeps its exact artwork and
  position with a clearer 0.11-opacity hover glow.
- Rounded-corner correction: every outer popup surface, main content card,
  answer panel and meeting row now uses the approved 10 logical px radius in
  both paint styling and the actual window mask. Pill-shaped controls remain
  unchanged.
- Windows build fix: pytest now uses `build\pytest-temp`, avoiding the protected
  system `pytest-current` cleanup failure while preserving real test failures.
  The build also disables pytest's non-essential cache plugin, avoiding warnings
  from a protected legacy `.pytest_cache` folder.
- Baseline validation accepts harmless historical versioned builder launchers
  left behind when the complete repository is extracted over an existing clone;
  the current v1.0.24 launcher is still required.

## Authoritative UI baseline

- Establishes `docs\UI_BASELINE.md` as the single geometry and interaction
  contract for future UI development.
- Preserves the four approved 720 px reference-canvas surfaces and their
  adaptive/scaled runtime behaviour.
- Confirms that the logo is the show/hide control, the opacity button occupies
  the former eye position, and the top-bar profile shortcut remains absent.
- Locks the current microphone/speaker lamps, tactile controls, live transcript,
  feedback window, model dropdown, history layout and three supported skins.
- Corrects the installation guide's stale instruction referring to an eye
  button.

## Complete feature baseline

This repository includes all accumulated audio capture, bundled local speech
recognition, question detection, context retrieval, local/Gemini/OpenAI/Ollama
answers, credential-validated model selection, session history, profiles,
skins, system tray, shortcuts, updater, installer and GitHub Actions work through
version 1.0.24.

Historical patch notes remain as release history only. For current behaviour,
use `README.md`, `README_INSTALLATION.md` and `docs\UI_BASELINE.md`.
