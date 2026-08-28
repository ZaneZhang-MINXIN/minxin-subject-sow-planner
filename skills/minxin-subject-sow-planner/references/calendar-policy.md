# Calendar normalization and scheduling policy

Use teacher-confirmed override → current official upload → bundled AY2026-27 snapshot → old SOW dates. Save source label, SHA-256, and locator. For Outlook `.url`, keep the publication address in memory only, convert to the OWA `/calendar.ics` route when needed, and never serialize the token or URL.

For ICS all-day events, `DTEND` is exclusive; subtract one day for `end_inclusive`. Preserve timed events and time zones. Deduplicate by normalized title, start, end, all-day semantics, scope, and source identity rather than trusting UID alone.

PDF text events retain page/line locators. Scanned or ambiguous rows remain `REVIEW` with low confidence. CSV/XLSX must expose recognizable date/title columns; do not guess column semantics.

## Event policy

- `HOLIDAY` or explicit closure: `BLOCK`, normally school-wide.
- `ASSESSMENT`: `BLOCK` only for the stated grade/course range; otherwise `NONBLOCK` or `REVIEW`.
- `SCHOOL_EVENT`: `REVIEW` unless the source explicitly states suspension or exact timing.
- `OPPORTUNITY`: non-blocking curriculum milestone. Suggest integration only when it serves the subject outcome.
- Timed events remove only intersecting timetable slots. An all-day `REVIEW` event removes none until confirmed.

Default school week is Monday–Friday. AY2026-27 Week 1 begins on Tuesday 2026-09-01 and is partial. Short weeks carry limited new content. Assessment aftermath uses subject-appropriate diagnosis, correction, revision, re-practice, reflection, and target adjustment.

`available_periods = active applicable timetable slots − confirmed blocked intersecting slots`

If there are no active slots for a course, return `UNCOMPUTED`. When planned periods exceed computed capacity, raise HIGH QA and suggest rescheduling; never compress required knowledge automatically.
