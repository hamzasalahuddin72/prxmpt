# prxmpt 1.0.19

This patch improves popup readability and makes automatic answers more reliable
when interview audio contains repeated, incomplete or noisy transcription.

## Readability

- Uses slightly heavier white text in the transcript, answer, model, toggle and
  meeting-history surfaces.
- Adds a very thin dark text edge to the transcript and answer without changing
  the approved font, sizing or layout.
- Adds a subtle dark shadow to the small lower labels and a compact outline to
  the model badge so Rose Quartz remains readable.

## Question and answer quality

- Finds the strongest complete question anywhere in a noisy utterance instead
  of losing it when remarks such as “thank you” follow it.
- Reconstructs important premises and trade-offs around the detected question.
- Rejects unfinished fragments ending in connectors such as “and” or “about”.
- Keeps the full raw transcript visible while bolding only the detected question
  span; later non-question remarks return to regular weight.
- Increases the completion pause to 1.15 seconds to reduce premature answers.
- Expands retrieval for common motivation, background, career-change and
  behavioural questions, with a small résumé/profile fallback for sparse
  keyword matches.
- Prevents cloud prompts from returning placeholders, templates, coaching
  commentary or “I need more information” responses.
- Gives hypothetical choice questions a direct decision-and-commitment frame.

## Build

Run `BUILD_INSTALLER.bat` or `BUILD_UPDATE_V1.0.19.bat`. The finished update is
created as `installer\output\prxmptUpdate_1.0.19.exe`.
