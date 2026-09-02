# Workbook schema and lineage

The workbook contains exactly ten sheets.

## Editable sheets

- `Setup`: key/value settings for academic year, dates, weekdays, language, output profile, and calendar provenance.
- `Course_Brief`: `course_id, subject_name, kla, curriculum_framework, key_stage, grade_level, course_level, class_id, output_language, learner_context, required_content, assessment_pattern, resource_constraints, mc_focus, authority_title, authority_version, authority_section, authority_url, authority_accessed, alignment_status, owner, status, notes`.
- `Calendar_Events`: `event_id, title, start, end_inclusive, all_day, start_time, end_time, event_type, block_policy, manual_override, scope_type, scope_id, source_kind, source_label, source_sha256, source_locator, parse_status, confidence, notes`.
- `Timetable_Slots`: `slot_id, course_id, class_id, teacher_id, room_id, weekday, period_no, start_time, end_time, valid_from, valid_to, cycle_pattern, active`.
- `Units`: `unit_id, course_id, sequence_no, title, unit_type, essential_question, disciplinary_practice, expected_evidence, target_periods, schedule_policy, major_concern_refs, major_concern_evidence, source_ref, status`.
- `Objectives`: `objective_id, course_id, objective_text, knowledge_type, progression_level, prerequisite_refs, success_evidence, standard_anchor, source_ref, alignment_status, status`.
- `Weekly_Plan`: `plan_id, course_id, week_id, unit_id, learning_unit, prior_learning, objective_refs, major_concern_refs, knowledge_content, disciplinary_practice, activities, evidence, assessment_purpose, feedback_revision, resources, values, planned_periods, available_periods, repetition_purpose, progression_delta, context_delta, evidence_delta, independence_delta, owner, status`.

`available_periods` is generated when a timetable exists; a teacher should not invent it.

## Generated sheets

- `Weeks`: `week_id, year_id, term, week_no, date_start, date_end, teaching_status, working_days, calendar_event_refs, notes`.
- `SOW_View`: normalized course rows used for Word output, with source `plan_id`, `unit_id`, and `objective_refs` retained for lineage.
- `QA`: `qa_id, severity, scope, code, record_refs, message, owner, status, source_refs, stop_condition`.

Stable IDs are `year_id, course_id, event_id, slot_id, week_id, unit_id, objective_id, plan_id`. Never join on a title or row number.

- A plan's unit and objectives must belong to its `course_id`.
- `course_id + week_id` is unique in the generic single-track core.
- Prerequisites must exist in the same course and appear earlier in the progression.
- Timetable conflicts require overlapping weekday/period, validity dates, and A/B cycle.
- Generated rows store source lineage; a changed source makes downstream outputs stale until rebuilt.
- `Units.major_concern_refs` is the broad planning map. `Weekly_Plan.major_concern_refs` is the only source for visible `(M1–M3)` objective citations and must be blank unless the linked objective directly fits. The generated `SOW_View` retains this field for Word lineage.
