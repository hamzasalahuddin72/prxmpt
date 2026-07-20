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

## Deliberately not included yet

- No provider prompt changes.
- No relevance gate or follow-up classifier.
- No novelty filtering or answer buffering.
- No rich-answer UI or question header migration.

The 1.0.24 UI baseline remains authoritative until the complete intelligence
pipeline and its regression suite are finished.
