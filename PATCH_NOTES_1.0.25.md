# PRXMPT next patch — intelligence foundation (in progress)

This is the first implementation patch after the 1.0.24 UI baseline. It is a
foundation patch, not a release-version bump yet.

## Included

- Added migration-safe SQLite state for ordered session turns.
- Added per-session rolling-context snapshots.
- Added confidence-scored interviewer profile storage for tone, pace, emotion
  and style signals.
- Added relevance decision and point-level novelty metadata fields to saved
  answers and turns.
- Added typed storage accessors for future follow-up, relevance, profile and
  answer-quality stages.
- Added storage migration, ordering, session-isolation and profile tests.
- Added a deterministic follow-up classifier for short and referential questions.
- Added a bounded rolling context window with explicit reset boundaries.
- Passed compact prior-turn context into answer prompt construction and local
  outline generation.
- Linked persisted follow-up turns to their parent turn and saved the context
  snapshot for the active session.

## Deliberately not included yet

- No relevance gate or answerability decision.
- No novelty filtering or answer buffering.
- No rich-answer UI or question header migration.

The 1.0.24 UI baseline remains authoritative until the complete intelligence
pipeline and its regression suite are finished.
