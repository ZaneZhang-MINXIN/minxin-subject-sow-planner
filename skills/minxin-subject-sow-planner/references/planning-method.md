# Bounded teacher interview and curriculum design

## `grill-me` state machine

1. `INSPECT`: read the available sources and populate known facts.
2. `RANK`: order open decisions by effect on authority, required content, assessment, safety/resources, and schedule.
3. `ASK_ONE`: ask only the highest-impact question.
4. `RECORD`: write the answer, source, status, owner, and implication into `Course_Brief`.
5. `RE-RANK`: stop when the design is decision-complete or after five questions by default.

If a high-impact answer is refused or contradictory, record `PLANNING_REQUIRED` and the release stop condition. If only a reversible presentation preference is missing, use a documented assumption and continue.

## Bounded brainstorming

Create three alternatives only for decisions that materially affect curriculum structure. Each alternative must differ in learning architecture, not just title.

Compare:

- curriculum/qualification alignment;
- validity of intended evidence;
- learner readiness, diversity, and accessibility;
- calendar and timetable capacity;
- teacher preparation and marking load;
- resource, safety, privacy, and rights feasibility;
- Major Concern contribution with observable evidence.

Keep a teacher-selected option as `CONFIRMED`; keep an unselected recommendation as `PROPOSED_DESIGN`.

## Curriculum chain

Every planned week must be traceable through:

`aim → target → unit outcome → weekly objective → knowledge/practice → action → evidence → feedback/revision → transfer or assessment`

An activity is appropriate only when it elicits the intended disciplinary practice and evidence. Brainstorming generates and categorises hypotheses or criteria; discussion elicits reasoning or comparison; commercial analysis belongs where market evidence changes a disciplinary decision; presentation belongs where audience communication is an outcome; AI belongs where students can improve and verify subject inquiry, analysis, creation, or feedback. Sourced or AI-assisted media also requires a visible rights/authorship trail: source, licence or permission, attribution, access date, transformation boundary, and the student's own contribution.

## Repetition and progression

Use `repetition_purpose` values `RETRIEVAL`, `CONSOLIDATION`, `SPIRAL`, `TRANSFER`, or `ROUTINE`. Repetition is purposeful only if at least one delta is recorded: `progression_delta`, `context_delta`, `evidence_delta`, or `independence_delta`.

Exact normalized activity/evidence combinations without a purpose are QA warnings, never auto-deleted.
