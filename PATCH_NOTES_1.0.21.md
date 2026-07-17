# prxmpt 1.0.21

This patch moves day-to-day answer-model switching onto the answer popup while
keeping API-key management in Settings.

## Model dropdown

- Clicking the model badge now opens the model dropdown instead of opening the
  Settings window.
- Google Gemini models are shown only after the saved Gemini key successfully
  lists models that support text generation.
- OpenAI models are shown only after the saved OpenAI key successfully lists
  compatible answer models.
- Ollama shows only models installed in the currently running local service.
- The offline grounded-outline provider remains available without a key.
- Models are grouped by provider, and the current selection is check-marked.
- Selecting a model is saved immediately and applies to the next answer without
  restarting prxmpt.

## Privacy and performance

- Discovery runs on a background worker so startup and popup interaction remain
  responsive.
- Discovery uses model-list requests only. It sends no transcript, question,
  résumé/context or microphone audio and does not make a generation request.
- Providers with missing, rejected or unreachable credentials are omitted from
  the dropdown rather than displayed as unusable choices.
- The dropdown includes manual refresh and a shortcut to API-key configuration.

## Build reliability

- Includes both v1.0.20 build corrections: the permanent PyInstaller spec is
  outside the generated build directory and resolves the project root correctly
  when the source folder is moved.
