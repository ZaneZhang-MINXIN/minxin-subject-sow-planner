#!/usr/bin/env python3
"""Subject-neutral calendar, schedule, view, and QA core for MINXIN SOW planning."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


EDITABLE_SHEETS = [
    "Setup", "Course_Brief", "Calendar_Events", "Timetable_Slots",
    "Units", "Objectives", "Weekly_Plan",
]
GENERATED_SHEETS = ["Weeks", "SOW_View", "QA"]
ALL_SHEETS = EDITABLE_SHEETS + GENERATED_SHEETS
HONG_KONG_TZ = ZoneInfo("Asia/Hong_Kong")
REPETITION_PURPOSES = {"RETRIEVAL", "CONSOLIDATION", "SPIRAL", "TRANSFER", "ROUTINE"}
MAJOR_CONCERNS = {"MC1", "MC2", "MC3"}

HEADERS = {
    "Setup": ["key", "value", "notes"],
    "Course_Brief": [
        "course_id", "subject_name", "kla", "curriculum_framework", "key_stage",
        "grade_level", "course_level", "class_id", "output_language", "learner_context",
        "required_content", "assessment_pattern", "resource_constraints", "mc_focus",
        "authority_title", "authority_version", "authority_section", "authority_url",
        "authority_accessed", "alignment_status", "owner", "status", "notes",
    ],
    "Calendar_Events": [
        "event_id", "title", "start", "end_inclusive", "all_day", "start_time", "end_time",
        "event_type", "block_policy", "manual_override", "scope_type", "scope_id",
        "source_kind", "source_label", "source_sha256", "source_locator", "parse_status",
        "confidence", "notes",
    ],
    "Timetable_Slots": [
        "slot_id", "course_id", "class_id", "teacher_id", "room_id", "weekday",
        "period_no", "start_time", "end_time", "valid_from", "valid_to", "cycle_pattern", "active",
    ],
    "Units": [
        "unit_id", "course_id", "sequence_no", "title", "unit_type", "essential_question",
        "disciplinary_practice", "expected_evidence", "target_periods", "schedule_policy",
        "major_concern_refs", "major_concern_evidence", "source_ref", "status",
    ],
    "Objectives": [
        "objective_id", "course_id", "objective_text", "knowledge_type", "progression_level",
        "prerequisite_refs", "success_evidence", "standard_anchor", "source_ref",
        "alignment_status", "status",
    ],
    "Weekly_Plan": [
        "plan_id", "course_id", "week_id", "unit_id", "learning_unit", "prior_learning",
        "objective_refs", "knowledge_content", "disciplinary_practice", "activities", "evidence",
        "assessment_purpose", "feedback_revision", "resources", "values", "planned_periods",
        "available_periods", "repetition_purpose", "progression_delta", "context_delta",
        "evidence_delta", "independence_delta", "owner", "status",
    ],
    "Weeks": [
        "week_id", "year_id", "term", "week_no", "date_start", "date_end", "teaching_status",
        "working_days", "calendar_event_refs", "notes",
    ],
    "SOW_View": [
        "source_hash", "course_id", "plan_id", "week_id", "date_range", "week_label", "row_type",
        "unit_id", "module_unit", "learning_focus", "prior_learning", "objective_refs",
        "teaching_objectives", "knowledge_content", "disciplinary_practice", "periods", "resources",
        "values", "activities", "evidence", "assessment_purpose", "feedback_revision",
        "calendar_context", "status",
    ],
    "QA": [
        "qa_id", "severity", "scope", "code", "record_refs", "message", "owner", "status",
        "source_refs", "stop_condition",
    ],
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def split_refs(value: Any) -> list[str]:
    return [part.strip() for part in re.split(r"[;,]", str(value or "")) if part.strip()]


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(value or "").lower())).strip()


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active"}


def normalize_clock(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.search(r"(?:T|\s)?(\d{1,2}):(\d{2})", text)
    if match:
        return f"{int(match.group(1)):02d}:{match.group(2)}"
    if re.fullmatch(r"\d{3,4}", text):
        return f"{int(text[:-2]):02d}:{text[-2:]}"
    return text


def calendar_event_key(event: dict) -> str:
    parts = (
        normalize_text(event.get("title")), str(event.get("start", ""))[:10],
        str(event.get("end_inclusive", ""))[:10], str(truthy(event.get("all_day", True))),
        normalize_clock(event.get("start_time")), normalize_clock(event.get("end_time")),
        str(event.get("scope_type", "SCHOOL")).strip().upper(),
        str(event.get("scope_id", "ALL")).strip().upper(),
    )
    return "|".join(parts)


def dedupe_events(events: Iterable[dict]) -> list[dict]:
    unique: dict[str, dict] = {}
    for event in events:
        unique.setdefault(calendar_event_key(event), event)
    return list(unique.values())


def setup_dict(rows: list[dict]) -> dict:
    return {str(row.get("key", "")): row.get("value", "") for row in rows if row.get("key")}


def setup_rows(settings: dict) -> list[dict]:
    notes = {
        "school_weekdays": "Comma-separated ISO weekday numbers; 1=Monday.",
        "calendar_source_sha256": "Source fingerprint only; never store a publication URL.",
        "source_hash": "Generated lineage hash for editable curriculum data.",
    }
    return [{"key": key, "value": value, "notes": notes.get(key, "")} for key, value in settings.items()]


def generate_weeks(settings: dict, events: list[dict]) -> list[dict]:
    year_id = str(settings.get("year_id", "AY2026-27"))
    start = parse_date(settings.get("academic_start", "2026-09-01"))
    end = parse_date(settings.get("academic_end", "2027-07-03"))
    term_2 = parse_date(settings.get("term_2_start", "2027-02-15"))
    weekdays = {int(v) for v in str(settings.get("school_weekdays", "1,2,3,4,5")).split(",") if v.strip()}
    cursor = start
    number = 1
    weeks: list[dict] = []
    while cursor <= end:
        monday = cursor - timedelta(days=cursor.weekday())
        week_start = max(start, monday)
        friday = monday + timedelta(days=4)
        week_end = min(end, friday)
        school_dates = [week_start + timedelta(days=n) for n in range((week_end - week_start).days + 1)]
        school_dates = [day for day in school_dates if day.isoweekday() in weekdays]
        related = [event for event in events if parse_date(event["start"]) <= week_end and parse_date(event["end_inclusive"]) >= week_start]
        blocked_dates = set()
        for event in related:
            policy = str(event.get("manual_override") or event.get("block_policy", "")).upper()
            if (
                policy != "BLOCK"
                or str(event.get("scope_type", "SCHOOL")).upper() not in {"SCHOOL", "ALL"}
                or not truthy(event.get("all_day", True))
            ):
                continue
            event_start, event_end = parse_date(event["start"]), parse_date(event["end_inclusive"])
            blocked_dates.update(day for day in school_dates if event_start <= day <= event_end)
        available_days = max(0, len(school_dates) - len(blocked_dates))
        if not school_dates or available_days == 0:
            teaching_status = "BLOCKED"
        elif available_days < len(school_dates):
            teaching_status = "SHORT_WEEK"
        elif any(str(e.get("block_policy", "")).upper() == "REVIEW" for e in related):
            teaching_status = "REVIEW"
        else:
            teaching_status = "TEACHING"
        weeks.append({
            "week_id": f"{year_id}-W{number:02d}",
            "year_id": year_id,
            "term": "S2" if week_start >= term_2 else "S1",
            "week_no": number,
            "date_start": week_start.isoformat(),
            "date_end": week_end.isoformat(),
            "teaching_status": teaching_status,
            "working_days": available_days,
            "calendar_event_refs": ";".join(event["event_id"] for event in related),
            "notes": "; ".join(event["title"] for event in related),
        })
        number += 1
        cursor = monday + timedelta(days=7)
    return weeks


def grade_number(value: str) -> int | None:
    match = re.search(r"(?:^|\b)G(?:RADE\s*)?(\d{1,2})(?:\b|$)", str(value).upper())
    return int(match.group(1)) if match else None


def event_applies(event: dict, course: dict) -> bool:
    scope_type = str(event.get("scope_type", "SCHOOL")).upper()
    scope_id = str(event.get("scope_id", "ALL"))
    if scope_type in {"SCHOOL", "ALL"}:
        return True
    course_id = str(course.get("course_id", ""))
    grade = str(course.get("grade_level", ""))
    framework = str(course.get("curriculum_framework", ""))
    if scope_type == "COURSE":
        return scope_id.strip().casefold() == course_id.strip().casefold()
    if scope_type == "GRADE":
        scoped_grade, course_grade = grade_number(scope_id), grade_number(grade)
        if scoped_grade is not None and course_grade is not None:
            return scoped_grade == course_grade
        return normalize_text(scope_id) == normalize_text(grade) and bool(normalize_text(grade))
    if scope_type == "GRADE_RANGE":
        numbers = [int(v) for v in re.findall(r"G(\d{1,2})", scope_id.upper())]
        current = grade_number(grade)
        return current is not None and len(numbers) >= 2 and min(numbers) <= current <= max(numbers)
    if scope_type == "DIVISION":
        current = grade_number(grade)
        return current is not None and ((scope_id.upper() == "PRIMARY" and current <= 6) or (scope_id.upper() == "SECONDARY" and current >= 7))
    if scope_type == "COURSE_LIST":
        tokens = [token.strip().casefold() for token in re.split(r"[;,\n]", scope_id) if token.strip()]
        candidates = {course_id.strip().casefold(), grade.strip().casefold(), framework.strip().casefold()}
        return bool(candidates.intersection(tokens))
    if scope_type == "CLASS":
        return scope_id == str(course.get("class_id", ""))
    return False


def event_policy(event: dict) -> str:
    return str(event.get("manual_override") or event.get("block_policy") or "REVIEW").upper()


def cycle_overlaps(left: str, right: str) -> bool:
    left, right = (left or "ALL").upper(), (right or "ALL").upper()
    return left == "ALL" or right == "ALL" or left == right


def ranges_overlap(a_start: Any, a_end: Any, b_start: Any, b_end: Any) -> bool:
    return parse_date(a_start) <= parse_date(b_end) and parse_date(b_start) <= parse_date(a_end)


def time_overlaps(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    if not all([a_start, a_end, b_start, b_end]):
        return True
    return time.fromisoformat(a_start) < time.fromisoformat(b_end) and time.fromisoformat(b_start) < time.fromisoformat(a_end)


def relevant_events_for_week(week: dict, course: dict, events: list[dict]) -> list[dict]:
    return [
        event for event in events
        if ranges_overlap(week["date_start"], week["date_end"], event["start"], event["end_inclusive"])
        and event_applies(event, course)
    ]


def compute_available_periods(course: dict, week: dict, slots: list[dict], events: list[dict]) -> int | str:
    applicable = [slot for slot in slots if str(slot.get("course_id")) == str(course.get("course_id")) and truthy(slot.get("active", True))]
    if not applicable:
        return "UNCOMPUTED"
    start, end = parse_date(week["date_start"]), parse_date(week["date_end"])
    count = 0
    week_parity = "A" if int(week["week_no"]) % 2 else "B"
    for slot in applicable:
        valid_from = slot.get("valid_from") or start.isoformat()
        valid_to = slot.get("valid_to") or end.isoformat()
        if not ranges_overlap(start, end, valid_from, valid_to):
            continue
        cycle = str(slot.get("cycle_pattern") or "ALL").upper()
        if cycle not in {"ALL", week_parity}:
            continue
        weekday = int(slot.get("weekday") or 0)
        occurrence = start + timedelta(days=(weekday - start.isoweekday()) % 7)
        if occurrence > end or occurrence < parse_date(valid_from) or occurrence > parse_date(valid_to):
            continue
        blocked = False
        for event in events:
            if event_policy(event) != "BLOCK" or not event_applies(event, course):
                continue
            if not (parse_date(event["start"]) <= occurrence <= parse_date(event["end_inclusive"])):
                continue
            if truthy(event.get("all_day", True)) or time_overlaps(str(slot.get("start_time", "")), str(slot.get("end_time", "")), str(event.get("start_time", "")), str(event.get("end_time", ""))):
                blocked = True
                break
        if not blocked:
            count += 1
    return count


def editable_source_hash(tables: dict) -> str:
    normalized = {}
    for name in EDITABLE_SHEETS:
        rows = deepcopy(tables.get(name, []))
        if name == "Setup":
            rows = [row for row in rows if row.get("key") != "source_hash"]
        if name == "Weekly_Plan":
            for row in rows:
                row.pop("available_periods", None)
        normalized[name] = rows
    data = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(data)


def make_view(tables: dict, source_hash: str) -> list[dict]:
    courses = {row["course_id"]: row for row in tables["Course_Brief"]}
    weeks = {row["week_id"]: row for row in tables["Weeks"]}
    units = {row["unit_id"]: row for row in tables["Units"]}
    objectives = {row["objective_id"]: row for row in tables["Objectives"]}
    events = tables["Calendar_Events"]
    settings = setup_dict(tables.get("Setup", []))
    school_weekdays = {int(value) for value in str(settings.get("school_weekdays", "1,2,3,4,5")).split(",") if value.strip()}
    view = []

    def add_row(plan: dict, course: dict, week: dict, synthetic: bool = False) -> None:
        course = courses.get(plan.get("course_id"), {})
        week = weeks.get(plan.get("week_id"), {})
        unit = units.get(plan.get("unit_id"), {})
        related = relevant_events_for_week(week, course, events) if course and week else []
        blocked = [event for event in related if event_policy(event) == "BLOCK"]
        calendar_labels = list(dict.fromkeys(event["title"] for event in related))
        objective_texts = [objectives[ref]["objective_text"] for ref in split_refs(plan.get("objective_refs")) if ref in objectives]
        capacity = compute_available_periods(course, week, tables["Timetable_Slots"], events) if synthetic else plan.get("available_periods")
        fully_blocked = synthetic or (bool(blocked) and (capacity == 0 or str(capacity) == "0"))
        if capacity == "UNCOMPUTED" and week.get("teaching_status") == "BLOCKED":
            fully_blocked = bool(blocked)
        row_type = "CALENDAR_BLOCK" if fully_blocked else "INSTRUCTION"
        label = "; ".join(dict.fromkeys(event["title"] for event in blocked))
        view.append({
            "source_hash": source_hash,
            "course_id": plan.get("course_id", ""),
            "plan_id": plan.get("plan_id", ""),
            "week_id": plan.get("week_id", ""),
            "date_range": f"{week.get('date_start', '')} to {week.get('date_end', '')}",
            "week_label": f"Week {week.get('week_no', '')}",
            "row_type": row_type,
            "unit_id": plan.get("unit_id", ""),
            "module_unit": label if fully_blocked else unit.get("title", ""),
            "learning_focus": label if fully_blocked else plan.get("learning_unit", ""),
            "prior_learning": "" if fully_blocked else plan.get("prior_learning", ""),
            "objective_refs": "" if fully_blocked else plan.get("objective_refs", ""),
            "teaching_objectives": "No scheduled instruction" if fully_blocked else "\n".join(objective_texts),
            "knowledge_content": "" if fully_blocked else plan.get("knowledge_content", ""),
            "disciplinary_practice": "" if fully_blocked else plan.get("disciplinary_practice", ""),
            "periods": 0 if fully_blocked else plan.get("planned_periods", ""),
            "resources": "" if fully_blocked else plan.get("resources", ""),
            "values": "" if fully_blocked else plan.get("values", ""),
            "activities": "" if fully_blocked else plan.get("activities", ""),
            "evidence": "" if fully_blocked else plan.get("evidence", ""),
            "assessment_purpose": "" if fully_blocked else plan.get("assessment_purpose", ""),
            "feedback_revision": "" if fully_blocked else plan.get("feedback_revision", ""),
            "calendar_context": "; ".join(calendar_labels),
            "status": "CALENDAR_BLOCK" if fully_blocked else plan.get("status", ""),
        })

    plans = sorted(tables["Weekly_Plan"], key=lambda row: (str(row.get("course_id")), str(row.get("week_id"))))
    for plan in plans:
        add_row(plan, courses.get(plan.get("course_id"), {}), weeks.get(plan.get("week_id"), {}))

    planned_pairs = {(str(plan.get("course_id")), str(plan.get("week_id"))) for plan in plans}
    for course_id, course in courses.items():
        for week_id, week in weeks.items():
            if (str(course_id), str(week_id)) in planned_pairs:
                continue
            related = relevant_events_for_week(week, course, events)
            blocked = [event for event in related if event_policy(event) == "BLOCK"]
            if not blocked:
                continue
            capacity = compute_available_periods(course, week, tables["Timetable_Slots"], events)
            start, end = parse_date(week["date_start"]), parse_date(week["date_end"])
            school_dates = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
            school_dates = [day for day in school_dates if day.isoweekday() in school_weekdays]
            all_day_blocked = {
                day for day in school_dates
                if any(
                    truthy(event.get("all_day", True))
                    and parse_date(event["start"]) <= day <= parse_date(event["end_inclusive"])
                    for event in blocked
                )
            }
            fully_blocked = (capacity == 0 and capacity != "UNCOMPUTED") or (bool(school_dates) and len(all_day_blocked) == len(school_dates))
            if not fully_blocked:
                continue
            add_row({
                "course_id": course_id, "plan_id": f"CAL-{course_id}-{week_id}",
                "week_id": week_id, "unit_id": "", "available_periods": 0,
                "planned_periods": 0, "status": "CALENDAR_BLOCK",
            }, course, week, synthetic=True)
    return sorted(view, key=lambda row: (str(row.get("course_id")), str(row.get("week_id")), str(row.get("plan_id"))))


def qa_record(severity: str, scope: str, code: str, refs: str, message: str, owner: str = "Curriculum owner", source_refs: str = "", stop: str = "") -> dict:
    digest = hashlib.sha256(f"{scope}|{code}|{refs}|{message}".encode()).hexdigest()[:12].upper()
    return {
        "qa_id": f"QA-{digest}", "severity": severity, "scope": scope, "code": code,
        "record_refs": refs, "message": message, "owner": owner, "status": "OPEN",
        "source_refs": source_refs, "stop_condition": stop,
    }


def detect_timetable_conflicts(slots: list[dict]) -> list[dict]:
    issues = []
    active = [slot for slot in slots if truthy(slot.get("active", True))]
    for index, left in enumerate(active):
        for right in active[index + 1:]:
            if str(left.get("weekday")) != str(right.get("weekday")) or str(left.get("period_no")) != str(right.get("period_no")):
                continue
            if not cycle_overlaps(str(left.get("cycle_pattern", "ALL")), str(right.get("cycle_pattern", "ALL"))):
                continue
            if not ranges_overlap(left.get("valid_from", "1900-01-01"), left.get("valid_to", "2999-12-31"), right.get("valid_from", "1900-01-01"), right.get("valid_to", "2999-12-31")):
                continue
            shared = [field for field in ("class_id", "teacher_id", "room_id") if left.get(field) and left.get(field) == right.get(field)]
            if shared:
                refs = f"{left.get('slot_id')};{right.get('slot_id')}"
                issues.append(qa_record("HIGH", "Timetable_Slots", "TIMETABLE_CONFLICT", refs, f"Overlapping active slots share {', '.join(shared)}.", stop="Resolve the resource conflict or change validity/cycle."))
    return issues


def validate_tables(
    tables: dict,
    expected_view: list[dict] | None = None,
    expected_weeks: list[dict] | None = None,
    expected_qa: list[dict] | None = None,
    expected_source_hash: str | None = None,
) -> list[dict]:
    issues: list[dict] = []
    key_specs = {
        "Course_Brief": "course_id", "Calendar_Events": "event_id", "Timetable_Slots": "slot_id",
        "Weeks": "week_id", "Units": "unit_id", "Objectives": "objective_id", "Weekly_Plan": "plan_id",
    }
    for sheet, key in key_specs.items():
        values = [str(row.get(key, "")).strip() for row in tables.get(sheet, [])]
        for index, value in enumerate(values, 5):
            if not value:
                issues.append(qa_record("HIGH", sheet, "MISSING_PRIMARY_KEY", f"row {index}", f"{key} is required.", stop="Assign a stable ID."))
        for value, count in Counter(v for v in values if v).items():
            if count > 1:
                issues.append(qa_record("HIGH", sheet, "DUPLICATE_PRIMARY_KEY", value, f"{key} occurs {count} times.", stop="Make the stable ID unique."))

    courses = {row.get("course_id"): row for row in tables.get("Course_Brief", [])}
    weeks = {row.get("week_id"): row for row in tables.get("Weeks", [])}
    units = {row.get("unit_id"): row for row in tables.get("Units", [])}
    objectives = {row.get("objective_id"): row for row in tables.get("Objectives", [])}
    course_week = Counter((row.get("course_id"), row.get("week_id")) for row in tables.get("Weekly_Plan", []))
    slot_courses = {str(row.get("course_id")) for row in tables.get("Timetable_Slots", []) if truthy(row.get("active", True))}

    course_required = ("subject_name", "kla", "curriculum_framework", "key_stage", "grade_level", "output_language", "required_content", "assessment_pattern", "owner", "status")
    for course_id, course in courses.items():
        missing = [field for field in course_required if not str(course.get(field, "")).strip()]
        if missing:
            issues.append(qa_record("HIGH", "Course_Brief", "INCOMPLETE_COURSE_BRIEF", str(course_id), f"Required course fields are blank: {', '.join(missing)}.", stop="Complete the Course_Brief before release."))

    semantic_events: dict[str, list[str]] = defaultdict(list)
    for event in tables.get("Calendar_Events", []):
        semantic_events[calendar_event_key(event)].append(str(event.get("event_id", "")))
    for refs in semantic_events.values():
        if len(refs) > 1:
            issues.append(qa_record("MEDIUM", "Calendar_Events", "DUPLICATE_CALENDAR_EVENT", ";".join(refs), "Calendar rows describe the same scoped event and require deduplication or confirmation."))
    for course_id in courses:
        if str(course_id) not in slot_courses:
            issues.append(qa_record("HIGH", "Timetable_Slots", "CAPACITY_UNCOMPUTED", str(course_id), "No active timetable slots exist for this course; available periods remain UNCOMPUTED.", stop="Add the current official timetable before claiming timetable fit or release."))
    for pair, count in course_week.items():
        if count > 1:
            issues.append(qa_record("HIGH", "Weekly_Plan", "DUPLICATE_COURSE_WEEK", ";".join(map(str, pair)), f"Course/week combination occurs {count} times.", stop="Keep one authoritative row per course/week."))

    first_objective_week: dict[str, int] = {}
    valid_objective_refs: set[str] = set()
    for plan in tables.get("Weekly_Plan", []):
        plan_id, course_id = str(plan.get("plan_id", "")), plan.get("course_id")
        if course_id not in courses:
            issues.append(qa_record("HIGH", "Weekly_Plan", "INVALID_COURSE_REF", plan_id, f"Unknown course_id {course_id}.", stop="Link to a Course_Brief row."))
        if plan.get("week_id") not in weeks:
            issues.append(qa_record("HIGH", "Weekly_Plan", "INVALID_WEEK_REF", plan_id, f"Unknown week_id {plan.get('week_id')}.", stop="Use a generated Week ID."))
        unit = units.get(plan.get("unit_id"))
        if not unit:
            issues.append(qa_record("HIGH", "Weekly_Plan", "INVALID_UNIT_REF", plan_id, f"Unknown unit_id {plan.get('unit_id')}.", stop="Link to a Unit row."))
        elif unit.get("course_id") != course_id:
            issues.append(qa_record("HIGH", "Weekly_Plan", "CROSS_COURSE_UNIT_REF", plan_id, f"Unit {unit.get('unit_id')} belongs to {unit.get('course_id')}.", stop="Use a unit from the same course."))
        week_number = int(weeks.get(plan.get("week_id"), {}).get("week_no", 9999))
        is_calendar_or_assessment = str(plan.get("status", "")).upper() == "CALENDAR_BLOCK" or str((unit or {}).get("unit_type", "")).upper() == "ASSESSMENT"
        if not is_calendar_or_assessment:
            chain_fields = ("objective_refs", "knowledge_content", "disciplinary_practice", "activities", "evidence", "assessment_purpose", "feedback_revision")
            missing = [field for field in chain_fields if not str(plan.get(field, "")).strip()]
            if missing:
                issues.append(qa_record("HIGH", "Weekly_Plan", "INCOMPLETE_CURRICULUM_CHAIN", plan_id, f"Required weekly curriculum-chain fields are blank: {', '.join(missing)}.", stop="Complete the objective-to-evidence and feedback chain."))
        for ref in split_refs(plan.get("objective_refs")):
            objective = objectives.get(ref)
            if not objective:
                issues.append(qa_record("HIGH", "Weekly_Plan", "INVALID_OBJECTIVE_REF", f"{plan_id};{ref}", f"Unknown objective_id {ref}.", stop="Create or correct the objective."))
            elif objective.get("course_id") != course_id:
                issues.append(qa_record("HIGH", "Weekly_Plan", "CROSS_COURSE_OBJECTIVE_REF", f"{plan_id};{ref}", f"Objective {ref} belongs to {objective.get('course_id')}.", stop="Use an objective from the same course."))
            first_objective_week[ref] = min(first_objective_week.get(ref, week_number), week_number)
            available = plan.get("available_periods")
            if not is_calendar_or_assessment and available not in {0, "0"} and str(weeks.get(plan.get("week_id"), {}).get("teaching_status", "")).upper() != "BLOCKED":
                valid_objective_refs.add(ref)
        available = plan.get("available_periods")
        try:
            if available not in {"", None, "UNCOMPUTED"} and float(plan.get("planned_periods") or 0) > float(available):
                issues.append(qa_record("HIGH", "Weekly_Plan", "PERIOD_OVERLOAD", plan_id, f"Planned periods {plan.get('planned_periods')} exceed available periods {available}.", stop="Reschedule; do not compress required knowledge automatically."))
        except (TypeError, ValueError):
            issues.append(qa_record("HIGH", "Weekly_Plan", "INVALID_PERIOD_VALUE", plan_id, "Period values must be numeric or UNCOMPUTED.", stop="Correct the capacity field."))

        purpose = str(plan.get("repetition_purpose", "")).strip().upper()
        if purpose and purpose not in REPETITION_PURPOSES:
            issues.append(qa_record("HIGH", "Weekly_Plan", "INVALID_REPETITION_PURPOSE", plan_id, f"Unknown repetition purpose: {purpose}.", stop="Use the documented repetition-purpose list."))

    for objective in tables.get("Objectives", []):
        current = objective.get("objective_id")
        required = ("objective_text", "knowledge_type", "progression_level", "success_evidence", "alignment_status", "status")
        missing = [field for field in required if not str(objective.get(field, "")).strip()]
        if missing:
            issues.append(qa_record("HIGH", "Objectives", "INCOMPLETE_OBJECTIVE", str(current), f"Required objective fields are blank: {', '.join(missing)}.", stop="Complete the assessable objective record."))
        alignment = str(objective.get("alignment_status", "")).upper()
        anchors_complete = all(str(objective.get(field, "")).strip() for field in ("standard_anchor", "source_ref"))
        if alignment == "VERIFIED" and not anchors_complete:
            issues.append(qa_record("HIGH", "Objectives", "UNSUPPORTED_OBJECTIVE_ALIGNMENT", str(current), "VERIFIED objective alignment requires a standard anchor and source reference.", stop="Add the exact source anchor or change to INFORMED_BY."))
        elif alignment == "INFORMED_BY" and not anchors_complete:
            issues.append(qa_record("MEDIUM", "Objectives", "OBJECTIVE_AUTHORITY_PLANNING_REQUIRED", str(current), "INFORMED_BY objective is missing a standard anchor or source reference.", owner=str(courses.get(objective.get("course_id"), {}).get("owner") or "Curriculum owner"), stop="Record the source anchor before formal approval."))
        if current not in valid_objective_refs and str(objective.get("status", "")).upper() != "PLANNING_REQUIRED":
            issues.append(qa_record("HIGH", "Objectives", "UNSCHEDULED_OBJECTIVE", str(current), "Objective is not referenced in a valid instructional week.", stop="Schedule the objective before the applicable assessment or mark it PLANNING_REQUIRED."))
        for prerequisite in split_refs(objective.get("prerequisite_refs")):
            if prerequisite not in objectives:
                issues.append(qa_record("HIGH", "Objectives", "INVALID_PREREQUISITE", f"{current};{prerequisite}", "Prerequisite objective does not exist.", stop="Correct the prerequisite reference."))
            elif objectives[prerequisite].get("course_id") != objective.get("course_id"):
                issues.append(qa_record("HIGH", "Objectives", "CROSS_COURSE_PREREQUISITE", f"{current};{prerequisite}", "Prerequisite belongs to another course.", stop="Keep prerequisites course-scoped."))
            elif first_objective_week.get(prerequisite, -1) > first_objective_week.get(current, 9999):
                issues.append(qa_record("HIGH", "Objectives", "PREREQUISITE_ORDER", f"{current};{prerequisite}", "Prerequisite is first taught after the dependent objective.", stop="Restore the intended progression."))

    for unit in tables.get("Units", []):
        unit_id = str(unit.get("unit_id", ""))
        required = ["title", "unit_type", "schedule_policy", "status"]
        if str(unit.get("unit_type", "")).upper() != "ASSESSMENT":
            required.extend(["essential_question", "disciplinary_practice", "expected_evidence"])
        missing = [field for field in required if not str(unit.get(field, "")).strip()]
        if missing:
            issues.append(qa_record("HIGH", "Units", "INCOMPLETE_UNIT_DESIGN", unit_id, f"Required unit fields are blank: {', '.join(missing)}.", stop="Complete the subject-specific unit design."))
        concern_refs = [ref.upper() for ref in split_refs(unit.get("major_concern_refs"))]
        invalid_refs = [ref for ref in concern_refs if ref not in MAJOR_CONCERNS]
        if invalid_refs:
            issues.append(qa_record("HIGH", "Units", "INVALID_MAJOR_CONCERN_REF", unit_id, f"Unknown Major Concern references: {', '.join(invalid_refs)}.", stop="Use only MC1, MC2 and MC3."))
        if len(concern_refs) > 2:
            issues.append(qa_record("MEDIUM", "Units", "MAJOR_CONCERN_OVERMAPPING", unit_id, "A unit normally maps to one or two Major Concerns; confirm that every mapping changes student action or evidence."))
        if concern_refs and not str(unit.get("major_concern_evidence", "")).strip():
            issues.append(qa_record("MEDIUM", "Units", "MAJOR_CONCERN_WITHOUT_EVIDENCE", str(unit.get("unit_id")), "Major Concern mapping has no observable student action or evidence."))

    for course in tables.get("Course_Brief", []):
        status = str(course.get("alignment_status", "")).upper()
        authority_fields = ("authority_title", "authority_version", "authority_section", "authority_url", "authority_accessed")
        authority_complete = all(str(course.get(field, "")).strip() for field in authority_fields)
        if status == "VERIFIED" and not authority_complete:
            issues.append(qa_record("HIGH", "Course_Brief", "UNSUPPORTED_FORMAL_ALIGNMENT", str(course.get("course_id")), "VERIFIED alignment requires exact title, version, section, source URL, and access date.", stop="Complete the authority record or change to INFORMED_BY."))
        elif status == "INFORMED_BY" and not authority_complete:
            issues.append(qa_record("MEDIUM", "Course_Brief", "COURSE_AUTHORITY_PLANNING_REQUIRED", str(course.get("course_id")), "INFORMED_BY course authority is incomplete.", owner=str(course.get("owner") or "Curriculum owner"), stop="Record the missing authority metadata before formal approval."))

    objective_occurrences: dict[tuple[str, str], list[dict]] = defaultdict(list)
    signatures: dict[tuple[str, str], list[str]] = defaultdict(list)
    decorative = re.compile(r"\b(brainstorm|discussion|presentation|project|business analysis|commercial analysis|ai|group work)\b", re.I)
    for plan in tables.get("Weekly_Plan", []):
        for ref in split_refs(plan.get("objective_refs")):
            objective_occurrences[(str(plan.get("course_id")), ref)].append(plan)
        signature = (normalize_text(plan.get("activities")), normalize_text(plan.get("evidence")))
        if all(signature):
            signatures[signature].append(str(plan.get("plan_id")))
        if decorative.search(str(plan.get("activities", ""))) and not str(plan.get("evidence", "")).strip():
            issues.append(qa_record("MEDIUM", "Weekly_Plan", "ORNAMENTAL_ACTIVITY_RISK", str(plan.get("plan_id")), "A named strategy has no explicit evidence product or performance."))
        course = courses.get(plan.get("course_id"), {})
        if "mathematics" in str(course.get("kla", "")).lower() and decorative.search(str(plan.get("activities", ""))):
            rationale = " ".join(str(plan.get(field, "")) for field in ("disciplinary_practice", "evidence")).lower()
            if not re.search(r"reason|proof|represent|model|calculation|solution|error|conjecture|mathemat", rationale):
                issues.append(qa_record("MEDIUM", "Weekly_Plan", "SUBJECT_STRATEGY_REVIEW", str(plan.get("plan_id")), "Confirm that the named strategy produces objective-linked mathematical evidence rather than a generic project or presentation."))
        values_text = str(plan.get("values", ""))
        if len(values_text) > 140 or re.search(r"global engagement and innovation|high-quality teaching and academic excellence|holistic development and global outlook", values_text, re.I):
            issues.append(qa_record("MEDIUM", "Weekly_Plan", "VALUES_SLOGAN_RISK", str(plan.get("plan_id")), "Keep Values / National Education concise and place observable action in Activities or Evidence."))
        media_probe = " ".join(str(plan.get(field, "")) for field in ("learning_unit", "activities", "knowledge_content")).lower()
        rights_probe = " ".join(str(plan.get(field, "")) for field in ("resources", "evidence")).lower()
        if "arts education" in str(course.get("kla", "")).lower() and any(term in media_probe for term in ("collage", "sourced image", "ai-assisted", "authorship")):
            required_terms = ("source", "licence", "attribution", "access", "authorship")
            if not all(term in rights_probe for term in required_terms):
                issues.append(qa_record("MEDIUM", "Weekly_Plan", "RIGHTS_AUTHORSHIP_TRAIL_INCOMPLETE", str(plan.get("plan_id")), "Sourced/digital/AI-assisted arts work should record source, licence or permission, attribution, access date and student-authorship boundary in Resources/Evidence."))
    for (course_id, objective_id), plans in objective_occurrences.items():
        if len(plans) <= 1:
            continue
        ordered = sorted(plans, key=lambda plan: int(weeks.get(plan.get("week_id"), {}).get("week_no", 9999)))
        for plan in ordered[1:]:
            deltas = [plan.get(field) for field in ("progression_delta", "context_delta", "evidence_delta", "independence_delta")]
            if not plan.get("repetition_purpose") or not any(str(value or "").strip() for value in deltas):
                issues.append(qa_record("MEDIUM", "Weekly_Plan", "UNJUSTIFIED_OBJECTIVE_REPETITION", f"{course_id};{objective_id};{plan.get('plan_id')}", "Repeated objective lacks a purpose and progression/context/evidence/independence delta."))
    for signature, plan_ids in signatures.items():
        if len(plan_ids) > 1:
            issues.append(qa_record("MEDIUM", "Weekly_Plan", "DUPLICATE_ACTIVITY_EVIDENCE_SIGNATURE", ";".join(plan_ids), "Identical normalized Activities and Evidence combination requires human review."))

    for event in tables.get("Calendar_Events", []):
        if event_policy(event) == "REVIEW" or str(event.get("confidence", "")).upper() == "LOW":
            issues.append(qa_record("MEDIUM", "Calendar_Events", "CALENDAR_REVIEW_REQUIRED", str(event.get("event_id")), f"Confirm teaching impact for: {event.get('title')}", source_refs=str(event.get("source_locator", ""))))

    issues.extend(detect_timetable_conflicts(tables.get("Timetable_Slots", [])))

    def canonical(rows: list[dict], headers: list[str]) -> list[tuple]:
        return sorted((tuple(str(row.get(header, "")) for header in headers) for row in rows))

    if expected_view is not None:
        actual = tables.get("SOW_View", [])
        if canonical(actual, HEADERS["SOW_View"]) != canonical(expected_view, HEADERS["SOW_View"]):
            issues.append(qa_record("HIGH", "SOW_View", "STALE_GENERATED_VIEW", "SOW_View", "Generated view does not match editable source tables.", stop="Rebuild the workbook before export/release."))
    if expected_weeks is not None and canonical(tables.get("Weeks", []), HEADERS["Weeks"]) != canonical(expected_weeks, HEADERS["Weeks"]):
        issues.append(qa_record("HIGH", "Weeks", "STALE_GENERATED_WEEKS", "Weeks", "Generated Weeks rows do not match Setup and Calendar_Events.", stop="Rebuild the workbook before export/release."))
    if expected_qa is not None and canonical(tables.get("QA", []), HEADERS["QA"]) != canonical(expected_qa, HEADERS["QA"]):
        issues.append(qa_record("HIGH", "QA", "STALE_GENERATED_QA", "QA", "Generated QA rows do not match current source data.", stop="Rebuild the workbook before export/release."))
    if expected_source_hash is not None:
        actual_source_hash = str(setup_dict(tables.get("Setup", [])).get("source_hash", ""))
        view_hashes = {str(row.get("source_hash", "")) for row in tables.get("SOW_View", [])}
        if actual_source_hash != expected_source_hash or (view_hashes and view_hashes != {expected_source_hash}):
            issues.append(qa_record("HIGH", "Setup", "STALE_SOURCE_HASH", "source_hash", "Source lineage hash is missing or stale in Setup or SOW_View.", stop="Rebuild all generated outputs from the editable tables."))
    return issues


def build_planner_data(curriculum: dict, calendar: dict, settings_override: dict | None = None) -> dict:
    curriculum = deepcopy(curriculum)
    settings = {
        "year_id": calendar.get("year_id", "AY2026-27"),
        "academic_year": "2026-2027",
        "academic_start": calendar.get("academic_start", "2026-09-01"),
        "academic_end": calendar.get("academic_end", "2027-07-03"),
        "term_2_start": calendar.get("term_2_start", "2027-02-15"),
        "school_weekdays": "1,2,3,4,5",
        "default_language": "en-GB",
        "default_profile": "standard",
        "calendar_source_label": calendar.get("source", {}).get("source_label", "Uploaded calendar"),
        "calendar_source_sha256": calendar.get("source", {}).get("source_sha256", ""),
    }
    settings.update(curriculum.get("setup", {}))
    settings.update(settings_override or {})
    tables = {name: deepcopy(curriculum.get("tables", {}).get(name, [])) for name in EDITABLE_SHEETS}
    tables["Setup"] = setup_rows(settings)
    tables["Calendar_Events"] = deepcopy(calendar.get("events", []))
    tables["Weeks"] = generate_weeks(settings, tables["Calendar_Events"])
    courses = {row["course_id"]: row for row in tables["Course_Brief"]}
    weeks = {row["week_id"]: row for row in tables["Weeks"]}
    for plan in tables["Weekly_Plan"]:
        course, week = courses.get(plan.get("course_id")), weeks.get(plan.get("week_id"))
        plan["available_periods"] = compute_available_periods(course, week, tables["Timetable_Slots"], tables["Calendar_Events"]) if course and week else "UNCOMPUTED"
    source_hash = editable_source_hash(tables)
    settings["source_hash"] = source_hash
    tables["Setup"] = setup_rows(settings)
    tables["SOW_View"] = make_view(tables, source_hash)
    tables["QA"] = validate_tables(tables)
    return {"schema_version": "2.0", "headers": HEADERS, "tables": tables, "source_hash": source_hash}


def refresh_planner_payload(payload: dict) -> dict:
    """Recompute capacity, Weeks, SOW_View and QA after workbook edits."""
    tables = {name: deepcopy(payload.get("tables", {}).get(name, [])) for name in ALL_SHEETS}
    settings = setup_dict(tables["Setup"])
    tables["Weeks"] = generate_weeks(settings, tables["Calendar_Events"])
    courses = {row.get("course_id"): row for row in tables["Course_Brief"]}
    weeks = {row.get("week_id"): row for row in tables["Weeks"]}
    for plan in tables["Weekly_Plan"]:
        course, week = courses.get(plan.get("course_id")), weeks.get(plan.get("week_id"))
        plan["available_periods"] = compute_available_periods(course, week, tables["Timetable_Slots"], tables["Calendar_Events"]) if course and week else "UNCOMPUTED"
    source_hash = editable_source_hash(tables)
    settings["source_hash"] = source_hash
    tables["Setup"] = setup_rows(settings)
    tables["SOW_View"] = make_view(tables, source_hash)
    tables["QA"] = validate_tables(tables)
    return {"schema_version": "2.0", "headers": HEADERS, "tables": tables, "source_hash": source_hash}


def parse_ics_datetime(raw: str, property_key: str) -> tuple[datetime, str]:
    value = raw.strip()
    compact = value[:-1] if value.endswith("Z") else value
    format_code = "%Y%m%dT%H%M%S" if len(compact) >= 15 else "%Y%m%dT%H%M"
    parsed = datetime.strptime(compact, format_code)
    if value.endswith("Z"):
        return parsed.replace(tzinfo=timezone.utc).astimezone(HONG_KONG_TZ), "UTC"
    match = re.search(r"(?:^|;)TZID=([^;:]+)", property_key, re.I)
    tzid = match.group(1).strip('"') if match else "Asia/Hong_Kong"
    try:
        source_tz = ZoneInfo(tzid)
    except ZoneInfoNotFoundError:
        source_tz, tzid = HONG_KONG_TZ, f"UNRESOLVED:{tzid}"
    return parsed.replace(tzinfo=source_tz).astimezone(HONG_KONG_TZ), tzid


def parse_ics_bytes(data: bytes, source_label: str, source_hash: str | None = None) -> dict:
    text = data.decode("utf-8", errors="replace").replace("\r\n", "\n")
    unfolded = re.sub(r"\n[ \t]", "", text)
    blocks = re.findall(r"BEGIN:VEVENT\n(.*?)\nEND:VEVENT", unfolded, re.S)
    events = []
    for block in blocks:
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key] = value.replace("\\n", "\n").replace("\\,", ",")
        dtstart_key = next((key for key in fields if key.startswith("DTSTART")), "")
        dtend_key = next((key for key in fields if key.startswith("DTEND")), "")
        if not dtstart_key:
            continue
        raw_start, raw_end = fields[dtstart_key], fields.get(dtend_key, "")
        all_day = "VALUE=DATE" in dtstart_key or len(raw_start) == 8
        if all_day:
            start_dt = datetime.strptime(raw_start[:8], "%Y%m%d")
            end_exclusive = datetime.strptime(raw_end[:8], "%Y%m%d") if raw_end else start_dt + timedelta(days=1)
            end_dt = end_exclusive - timedelta(days=1)
            start_time, end_time = "", ""
        else:
            start_dt, start_zone = parse_ics_datetime(raw_start, dtstart_key)
            end_dt, end_zone = parse_ics_datetime(raw_end, dtend_key) if raw_end else (start_dt, start_zone)
            start_time, end_time = start_dt.time().isoformat(timespec="minutes"), end_dt.time().isoformat(timespec="minutes")
        title = fields.get("SUMMARY", "Untitled event")
        lowered = title.lower()
        if any(token in lowered for token in ("holiday", "vacation", "break")):
            event_type, policy = "HOLIDAY", "BLOCK"
        elif any(token in lowered for token in ("assessment", "exam", "mock")):
            event_type, policy = "ASSESSMENT", "REVIEW"
        elif any(token in lowered for token in ("week", "festival", "world book", "scholars")):
            event_type, policy = "OPPORTUNITY", "MILESTONE"
        else:
            event_type, policy = "SCHOOL_EVENT", "REVIEW"
        event = {
            "event_id": "", "title": title, "start": start_dt.date().isoformat(),
            "end_inclusive": end_dt.date().isoformat(), "all_day": all_day, "start_time": start_time,
            "end_time": end_time, "event_type": event_type, "block_policy": policy,
            "manual_override": "", "scope_type": "SCHOOL", "scope_id": "ALL", "source_kind": "ICS",
            "source_label": source_label, "source_sha256": source_hash or sha256_bytes(data),
            "source_locator": f"VEVENT {len(events)+1}", "parse_status": "REVIEW", "confidence": "MEDIUM",
            "notes": "Confirm scope and teaching impact after import." if all_day else f"Converted from {start_zone}/{end_zone} to Asia/Hong_Kong; confirm scope and teaching impact.",
        }
        identity = f"{source_hash or sha256_bytes(data)}|{calendar_event_key(event)}|{start_zone if not all_day else 'DATE'}|{end_zone if not all_day else 'DATE'}"
        event["event_id"] = f"EVT-{hashlib.sha256(identity.encode()).hexdigest()[:12].upper()}"
        events.append(event)
    return {"events": dedupe_events(events)}


def outlook_ics_url(publication_url: str) -> str:
    url = publication_url.strip()
    if "/owa/calendar/" in url and not url.rstrip("/").endswith("calendar.ics"):
        return url.rstrip("/") + "/calendar.ics"
    return url


def load_url_calendar(path: Path) -> tuple[bytes, str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^URL=(.+)$", text, re.M | re.I)
    if not match:
        raise ValueError(".url file does not contain a URL= line")
    url = outlook_ics_url(match.group(1))
    request = urllib.request.Request(url, headers={"User-Agent": "MINXIN-SOW-Planner/2.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    return data, path.stem, sha256_bytes(data)


def parse_csv_calendar(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return normalize_tabular_calendar(rows, path.name, sha256_file(path), "CSV")


def normalize_tabular_calendar(rows: Iterable[dict], label: str, source_hash: str, kind: str) -> dict:
    aliases = {
        "title": {"title", "event", "event_title", "name", "summary"},
        "start": {"start", "start_date", "date", "from"},
        "end_inclusive": {"end", "end_date", "end_inclusive", "to"},
        "all_day": {"all_day", "allday", "is_all_day"},
        "start_time": {"start_time", "time_start", "from_time"},
        "end_time": {"end_time", "time_end", "to_time"},
        "event_type": {"event_type", "type", "category"},
        "block_policy": {"block_policy", "policy", "teaching_policy"},
        "manual_override": {"manual_override", "override"},
        "scope_type": {"scope_type", "scope"},
        "scope_id": {"scope_id", "scope_value", "applies_to"},
        "parse_status": {"parse_status", "status"},
        "confidence": {"confidence", "parse_confidence"},
        "notes": {"notes", "note"},
    }
    normalized_rows = []
    for index, raw in enumerate(rows, 2):
        lowered = {re.sub(r"[\s-]+", "_", str(key).strip().lower()): value for key, value in raw.items()}
        picked = {}
        for canonical, names in aliases.items():
            match = next((lowered[name] for name in names if name in lowered and str(lowered[name]).strip()), "")
            picked[canonical] = str(match).strip()
        if not picked["title"] or not picked["start"]:
            continue
        try:
            start = parse_date(picked["start"]).isoformat()
            end = parse_date(picked["end_inclusive"] or start).isoformat()
            confidence, parse_status = "MEDIUM", "REVIEW"
        except ValueError:
            continue
        start_time, end_time = normalize_clock(picked.get("start_time")), normalize_clock(picked.get("end_time"))
        explicit_all_day = str(picked.get("all_day", "")).strip()
        all_day = truthy(explicit_all_day) if explicit_all_day else not (start_time or end_time)
        event = {
            "event_id": "", "title": picked["title"], "start": start, "end_inclusive": end,
            "all_day": all_day, "start_time": start_time, "end_time": end_time,
            "event_type": str(picked.get("event_type") or "SCHOOL_EVENT").strip().upper(),
            "block_policy": str(picked.get("block_policy") or "REVIEW").strip().upper(),
            "manual_override": str(picked.get("manual_override") or "").strip().upper(),
            "scope_type": str(picked.get("scope_type") or "SCHOOL").strip().upper(),
            "scope_id": str(picked.get("scope_id") or "ALL").strip(),
            "source_kind": kind, "source_label": label, "source_sha256": source_hash,
            "source_locator": f"row {index}", "parse_status": str(picked.get("parse_status") or parse_status).strip().upper(),
            "confidence": str(picked.get("confidence") or confidence).strip().upper(),
            "notes": str(picked.get("notes") or "Imported tabular event; confirm type, scope, and policy.").strip(),
        }
        identity = f"{source_hash}|{calendar_event_key(event)}"
        event["event_id"] = f"EVT-{hashlib.sha256(identity.encode()).hexdigest()[:12].upper()}"
        normalized_rows.append(event)
    return {"events": dedupe_events(normalized_rows)}
