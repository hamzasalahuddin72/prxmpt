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
- Added a provider-neutral conversation-quality gate before answer generation.
- Expanded follow-up matching to recognise short detail requests such as role,
  outcome, process, database, technology and implementation questions.
- Added topic locks so an accepted follow-up uses only its parent topic's
  rolling context and verified retrieval results.
- Added conservative ambiguity detection: fragmented questions now produce a
  clarification state and do not call an answer provider.
- Added high-confidence, active-topic ASR repair for common technical phrases;
  repairs are recorded with their confidence and reason.
- Persisted gate status, scores, topic-lock identifiers and repair reasoning in
  each ordered session turn for later tuning and audit.
- Added regression coverage from real mock-interview transcripts, including the
  role/outcome continuation and “text tag” → “tech stack” correction.

## Patch 3.1 — locked-topic evidence boundary

- Replaced prompt-only topic locking with a hard evidence boundary before any
  provider is called.
- Locked follow-ups now retrieve only source chunks containing distinctive
  anchors from the locked conversation topic; broad lexical matches such as
  "team", "PHP", "JavaScript" or "database" cannot admit a similar but
  unrelated project.
- Focused matched source chunks to anchor-bearing sentences where a chunk spans
  more than one subject, reducing cross-project fact leakage further.
- Moved the locked turn facts ahead of source evidence in every provider prompt
  and explicitly marks the lock as authoritative.
- Added a realistic multi-project resume regression: a six-person sneaker-site
  follow-up can retrieve the RapidAPI/Git project evidence but cannot retrieve
  the Rizka Travel invoicing evidence.
- Added a conservative no-anchor regression: when the lock cannot be grounded
  in an uploaded source, no broad fallback context is sent to the provider.

## Patch 3.1.1 — rolling-context prompt hand-off

- Fixed a prompt-construction omission: the compact saved session window is now
  rendered for ordinary, non-locked follow-ups as `ROLLING SESSION CONTEXT`.
- Preserved the stricter `ACTIVE TOPIC LOCK — HARD EVIDENCE BOUNDARY` route for
  locked follow-ups; it continues to take priority over the general context
  window.
- This makes the existing follow-up regression for “Why did you choose it?”
  pass without broadening the evidence available to a locked topic.

## Deliberately not included yet

- No point-level novelty filtering or answer buffering.
- No rich-answer UI or question header migration.

The 1.0.24 UI baseline remains authoritative until the complete intelligence
pipeline and its regression suite are finished.
