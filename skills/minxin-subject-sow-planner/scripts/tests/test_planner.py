#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from planner_core import (  # noqa: E402
    build_planner_data, compute_available_periods, detect_timetable_conflicts,
    event_applies, generate_weeks, parse_ics_bytes, read_json, validate_tables,
)
from validate import release_blocking_issues  # noqa: E402


class PlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calendar = read_json(ROOT / "assets" / "ay2026-27-calendar.json")
        cls.fixture = read_json(ROOT / "scripts" / "tests" / "fixtures" / "multi-subject-fixture.json")

    def test_default_calendar_is_sanitized_and_fingerprinted(self):
        text = (ROOT / "assets" / "ay2026-27-calendar.json").read_text(encoding="utf-8")
        self.assertNotIn("outlook.office365.com", text)
        self.assertNotIn("[InternetShortcut]", text)
        self.assertEqual(self.calendar["source"]["source_sha256"], "a6a6b49390b855e0b8fa7c779ba56d6929591c993df03f91c5c4798bdf979161")

    def test_week_generation_partial_week_one_and_44_weeks(self):
        settings = {"year_id": "AY2026-27", "academic_start": "2026-09-01", "academic_end": "2027-07-03", "term_2_start": "2027-02-15", "school_weekdays": "1,2,3,4,5"}
        weeks = generate_weeks(settings, self.calendar["events"])
        self.assertEqual(len(weeks), 44)
        self.assertEqual((weeks[0]["date_start"], weeks[0]["date_end"]), ("2026-09-01", "2026-09-04"))
        self.assertEqual(weeks[-1]["week_id"], "AY2026-27-W44")

    def test_ics_exclusive_dtend_and_timed_event(self):
        data = b"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:a\r\nDTSTART;VALUE=DATE:20261001\r\nDTEND;VALUE=DATE:20261008\r\nSUMMARY:Holiday\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nUID:b\r\nDTSTART:20261009T090000\r\nDTEND:20261009T100000\r\nSUMMARY:Assembly\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
        events = parse_ics_bytes(data, "fixture")["events"]
        self.assertEqual(events[0]["end_inclusive"], "2026-10-07")
        self.assertFalse(events[1]["all_day"])
        self.assertEqual(events[1]["start_time"], "09:00")

    def test_ics_timezone_and_timed_deduplication(self):
        data = b"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nDTSTART:20261009T021500Z\r\nDTEND:20261009T030000Z\r\nSUMMARY:Checkpoint\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nDTSTART:20261009T031500Z\r\nDTEND:20261009T040000Z\r\nSUMMARY:Checkpoint\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nDTSTART:20261009T031500Z\r\nDTEND:20261009T040000Z\r\nSUMMARY:Checkpoint\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nDTSTART;TZID=Asia/Tokyo:20261009T100000\r\nDTEND;TZID=Asia/Tokyo:20261009T104500\r\nSUMMARY:Tokyo link\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
        events = parse_ics_bytes(data, "fixture")["events"]
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["start_time"], "10:15")
        self.assertEqual(events[1]["start_time"], "11:15")
        self.assertEqual(events[2]["start_time"], "09:00")

    def test_scope_matching_is_exact_and_grade_fallback_is_safe(self):
        course = {"course_id": "G8-ENG-8E-PSP-EXT", "grade_level": "Secondary 2"}
        self.assertFalse(event_applies({"scope_type": "COURSE", "scope_id": "G8-ENG-8E-PSP"}, course))
        self.assertFalse(event_applies({"scope_type": "GRADE", "scope_id": "Secondary 3"}, course))
        self.assertTrue(event_applies({"scope_type": "GRADE", "scope_id": "Secondary 2"}, course))

    def test_course_list_matches_grade_programme_composite(self):
        course = {
            "course_id": "MATHEMATICS-G10-CORE-A", "grade_level": "Grade 10",
            "curriculum_framework": "Cambridge IGCSE", "class_id": "G10A",
        }
        self.assertTrue(event_applies({"scope_type": "COURSE_LIST", "scope_id": "G10-IGCSE;G11-GCE"}, course))
        self.assertTrue(event_applies({"scope_type": "COURSE_LIST", "scope_id": "IGCSE;GCE"}, course))
        self.assertFalse(event_applies({"scope_type": "COURSE_LIST", "scope_id": "G11-IGCSE;G10-GCE"}, course))

    def test_capacity_requires_matching_class_id(self):
        settings = {"year_id": "X", "academic_start": "2026-09-07", "academic_end": "2026-09-11", "term_2_start": "2027-02-15", "school_weekdays": "1,2,3,4,5"}
        week = generate_weeks(settings, [])[0]
        course = {"course_id": "M", "class_id": "G8A", "grade_level": "G8"}
        slots = [
            {"slot_id": "A", "course_id": "M", "class_id": "G8A", "weekday": 1, "period_no": 1, "valid_from": "2026-09-01", "valid_to": "2026-09-30", "cycle_pattern": "ALL", "active": True},
            {"slot_id": "B", "course_id": "M", "class_id": "G8B", "weekday": 2, "period_no": 1, "valid_from": "2026-09-01", "valid_to": "2026-09-30", "cycle_pattern": "ALL", "active": True},
        ]
        self.assertEqual(compute_available_periods(course, week, slots, []), 1)

    def test_timed_block_does_not_reduce_working_days(self):
        settings = {"year_id": "X", "academic_start": "2026-09-07", "academic_end": "2026-09-11", "term_2_start": "2027-02-15", "school_weekdays": "1,2,3,4,5"}
        event = {"event_id": "E", "title": "Timed block", "start": "2026-09-08", "end_inclusive": "2026-09-08", "all_day": False, "start_time": "10:00", "end_time": "10:45", "block_policy": "BLOCK", "scope_type": "SCHOOL", "scope_id": "ALL"}
        week = generate_weeks(settings, [event])[0]
        self.assertEqual(week["working_days"], 5)
        self.assertNotEqual(week["teaching_status"], "SHORT_WEEK")

    def test_assessment_scope_does_not_freeze_other_grade(self):
        settings = {"year_id": "X", "academic_start": "2027-01-04", "academic_end": "2027-01-08", "term_2_start": "2027-02-15", "school_weekdays": "1,2,3,4,5"}
        week = generate_weeks(settings, self.calendar["events"])[0]
        slot = {"slot_id": "S", "course_id": "P6", "weekday": 1, "period_no": 1, "valid_from": "2027-01-01", "valid_to": "2027-01-31", "cycle_pattern": "ALL", "active": True}
        self.assertEqual(compute_available_periods({"course_id": "P6", "grade_level": "G6"}, week, [slot], self.calendar["events"]), 1)
        slot["course_id"] = "S7"
        self.assertEqual(compute_available_periods({"course_id": "S7", "grade_level": "G7"}, week, [slot], self.calendar["events"]), 0)

    def test_missing_timetable_is_uncomputed(self):
        settings = {"year_id": "X", "academic_start": "2026-09-01", "academic_end": "2026-09-04", "term_2_start": "2027-02-15", "school_weekdays": "1,2,3,4,5"}
        week = generate_weeks(settings, [])[0]
        self.assertEqual(compute_available_periods({"course_id": "M", "grade_level": "G8"}, week, [], []), "UNCOMPUTED")
        payload = build_planner_data({"tables": {"Course_Brief": [{"course_id": "M", "grade_level": "G8"}], "Timetable_Slots": [], "Units": [], "Objectives": [], "Weekly_Plan": []}}, {"year_id": "X", "academic_start": "2026-09-01", "academic_end": "2026-09-04", "term_2_start": "2027-02-15", "source": {}, "events": []})
        self.assertIn("CAPACITY_UNCOMPUTED", {issue["code"] for issue in payload["tables"]["QA"]})

    def test_ab_cycle_and_validity(self):
        settings = {"year_id": "X", "academic_start": "2026-09-01", "academic_end": "2026-09-18", "term_2_start": "2027-02-15", "school_weekdays": "1,2,3,4,5"}
        weeks = generate_weeks(settings, [])
        slots = [
            {"slot_id": "A", "course_id": "M", "weekday": 3, "period_no": 1, "valid_from": "2026-09-01", "valid_to": "2026-09-30", "cycle_pattern": "A", "active": True},
            {"slot_id": "B", "course_id": "M", "weekday": 3, "period_no": 2, "valid_from": "2026-09-01", "valid_to": "2026-09-30", "cycle_pattern": "B", "active": True},
        ]
        course = {"course_id": "M", "grade_level": "G8"}
        self.assertEqual(compute_available_periods(course, weeks[0], slots, []), 1)
        self.assertEqual(compute_available_periods(course, weeks[1], slots, []), 1)

    def test_timetable_conflict_understands_cycle(self):
        base = {"weekday": 1, "period_no": 1, "valid_from": "2026-09-01", "valid_to": "2027-07-03", "active": True, "teacher_id": "T"}
        left = {**base, "slot_id": "A", "course_id": "A", "cycle_pattern": "A"}
        right = {**base, "slot_id": "B", "course_id": "B", "cycle_pattern": "B"}
        self.assertEqual(detect_timetable_conflicts([left, right]), [])
        right["cycle_pattern"] = "ALL"
        self.assertEqual(len(detect_timetable_conflicts([left, right])), 1)

    def test_fixture_build_has_course_isolation_and_no_high_qa(self):
        payload = build_planner_data(self.fixture, self.calendar)
        self.assertEqual(len(payload["tables"]["Course_Brief"]), 3)
        self.assertEqual(len(payload["tables"]["Weeks"]), 44)
        self.assertEqual(len(payload["tables"]["Weekly_Plan"]), 132)
        self.assertFalse([issue for issue in payload["tables"]["QA"] if issue["severity"] == "HIGH"])
        self.assertFalse(any("Python" in json.dumps(row) for row in payload["tables"]["Course_Brief"]))

    def test_cross_course_objective_is_high(self):
        payload = build_planner_data(self.fixture, self.calendar)
        tables = payload["tables"]
        tables["Weekly_Plan"][0]["objective_refs"] = "MATHEMATICS-G8-CORE-B-U1-O1"
        issues = validate_tables(tables)
        self.assertIn("CROSS_COURSE_OBJECTIVE_REF", {issue["code"] for issue in issues})

    def test_unjustified_repetition_is_review_not_auto_delete(self):
        payload = build_planner_data(self.fixture, self.calendar)
        tables = payload["tables"]
        first, second = tables["Weekly_Plan"][0], tables["Weekly_Plan"][1]
        second["objective_refs"] = first["objective_refs"]
        for field in ("repetition_purpose", "progression_delta", "context_delta", "evidence_delta", "independence_delta"):
            second[field] = ""
        issues = validate_tables(tables)
        matching = [issue for issue in issues if issue["code"] == "UNJUSTIFIED_OBJECTIVE_REPETITION"]
        self.assertTrue(matching)
        self.assertTrue(all(issue["severity"] == "MEDIUM" for issue in matching))

    def test_blocked_week_without_plan_gets_calendar_view_row(self):
        curriculum = {"tables": {"Course_Brief": [{"course_id": "C", "subject_name": "Science", "kla": "Science Education", "curriculum_framework": "HK", "key_stage": "Key Stage 3", "grade_level": "G8", "output_language": "en-GB", "required_content": "Matter", "assessment_pattern": "Tasks", "owner": "Teacher", "status": "DRAFT"}], "Timetable_Slots": [{"slot_id": "S", "course_id": "C", "weekday": 1, "period_no": 1, "valid_from": "2026-09-01", "valid_to": "2026-09-30", "cycle_pattern": "ALL", "active": True}], "Units": [], "Objectives": [], "Weekly_Plan": []}}
        calendar = {"year_id": "X", "academic_start": "2026-09-07", "academic_end": "2026-09-11", "term_2_start": "2027-02-15", "source": {}, "events": [{"event_id": "E", "title": "Holiday", "start": "2026-09-07", "end_inclusive": "2026-09-11", "all_day": True, "start_time": "", "end_time": "", "block_policy": "BLOCK", "scope_type": "SCHOOL", "scope_id": "ALL"}]}
        payload = build_planner_data(curriculum, calendar)
        rows = payload["tables"]["SOW_View"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["row_type"], "CALENDAR_BLOCK")

    def test_major_concern_citation_is_selective_and_objective_linked(self):
        fixture = deepcopy(self.fixture)
        fixture["tables"]["Weekly_Plan"][0]["major_concern_refs"] = "MC2"
        payload = build_planner_data(fixture, self.calendar)
        english_rows = [row for row in payload["tables"]["SOW_View"] if row["course_id"] == "ENGLISH-G7-CORE-A"]
        first = next(row for row in english_rows if row["plan_id"] == "PLAN-ENGLISH-G7-CORE-A-W01")
        second = next(row for row in english_rows if row["plan_id"] == "PLAN-ENGLISH-G7-CORE-A-W02")
        self.assertEqual(first["major_concern_refs"], "MC2")
        self.assertIn("(M2)", first["teaching_objectives"])
        self.assertNotRegex(second["teaching_objectives"], r"\(M[123]")

    def test_curriculum_chain_authority_and_enums_are_checked(self):
        payload = build_planner_data(self.fixture, self.calendar)
        tables = payload["tables"]
        tables["Weekly_Plan"][0]["knowledge_content"] = ""
        tables["Weekly_Plan"][1]["repetition_purpose"] = "NOT_A_VALUE"
        tables["Weekly_Plan"][2]["major_concern_refs"] = "MC9"
        tables["Units"][0]["major_concern_refs"] = "MC9;MC1;MC2"
        target = tables["Objectives"][0]
        target["standard_anchor"] = ""
        target["alignment_status"] = "VERIFIED"
        target["objective_id"] = "UNSCHEDULED"
        issues = validate_tables(tables)
        codes = {issue["code"] for issue in issues}
        self.assertTrue({"INCOMPLETE_CURRICULUM_CHAIN", "INVALID_REPETITION_PURPOSE", "INVALID_MAJOR_CONCERN_REF", "INVALID_WEEKLY_MAJOR_CONCERN_REF", "UNSUPPORTED_OBJECTIVE_ALIGNMENT", "UNSCHEDULED_OBJECTIVE"} <= codes)

    def test_authority_placeholders_and_before_assessment_are_release_gates(self):
        payload = build_planner_data(self.fixture, self.calendar)
        tables = payload["tables"]
        course = tables["Course_Brief"][0]
        course["alignment_status"] = "VERIFIED"
        course["authority_section"] = "Exact chapter requires teacher confirmation"
        unit = next(row for row in tables["Units"] if row["course_id"] == course["course_id"] and row["schedule_policy"] == "BEFORE_ASSESSMENT")
        for plan in tables["Weekly_Plan"]:
            if plan["unit_id"] == unit["unit_id"]:
                plan["week_id"] = "AY2026-27-W19"
        issues = validate_tables(tables)
        codes = {issue["code"] for issue in issues}
        self.assertIn("UNSUPPORTED_FORMAL_ALIGNMENT", codes)
        self.assertIn("BEFORE_ASSESSMENT_TIMING", codes)
        self.assertTrue(release_blocking_issues(issues))

    def test_open_calendar_and_informed_by_qa_block_formal_release(self):
        payload = build_planner_data(self.fixture, self.calendar)
        blockers = release_blocking_issues(payload["tables"]["QA"])
        codes = {issue["code"] for issue in blockers}
        self.assertIn("CALENDAR_REVIEW_REQUIRED", codes)
        self.assertIn("COURSE_AUTHORITY_PLANNING_REQUIRED", codes)
        self.assertIn("OBJECTIVE_ALIGNMENT_NOT_VERIFIED", codes)

    def test_full_generated_view_comparison_detects_calendar_context_tamper(self):
        payload = build_planner_data(self.fixture, self.calendar)
        expected = deepcopy(payload["tables"]["SOW_View"])
        payload["tables"]["SOW_View"][0]["calendar_context"] = "tampered"
        issues = validate_tables(payload["tables"], expected_view=expected)
        self.assertIn("STALE_GENERATED_VIEW", {issue["code"] for issue in issues})

    def test_other_generated_tables_and_source_hash_are_compared(self):
        payload = build_planner_data(self.fixture, self.calendar)
        expected_weeks = deepcopy(payload["tables"]["Weeks"])
        expected_qa = deepcopy(payload["tables"]["QA"])
        payload["tables"]["Weeks"][0]["working_days"] = 99
        payload["tables"]["QA"] = []
        next(row for row in payload["tables"]["Setup"] if row["key"] == "source_hash")["value"] = "stale"
        issues = validate_tables(payload["tables"], expected_weeks=expected_weeks, expected_qa=expected_qa, expected_source_hash=payload["source_hash"])
        codes = {issue["code"] for issue in issues}
        self.assertTrue({"STALE_GENERATED_WEEKS", "STALE_GENERATED_QA", "STALE_SOURCE_HASH"} <= codes)


if __name__ == "__main__":
    unittest.main()
