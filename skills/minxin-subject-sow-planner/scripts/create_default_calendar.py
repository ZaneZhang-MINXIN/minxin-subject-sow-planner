#!/usr/bin/env python3
"""Create the sanitized AY2026-27 calendar snapshot bundled with this Skill."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


SOURCE_HASH = "a6a6b49390b855e0b8fa7c779ba56d6929591c993df03f91c5c4798bdf979161"

# start, end inclusive, title, event type, policy, scope type, scope id, page, confidence
EVENTS = [
    ("2026-08-20", "2026-09-04", "G12 (HKDSE) Pre-mock Assessment", "ASSESSMENT", "BLOCK", "GRADE", "G12", 1, "HIGH"),
    ("2026-09-01", "2026-09-02", "Commencement Ceremony & Beginning of the Year Affairs (SD)", "SCHOOL_EVENT", "REVIEW", "SCHOOL", "ALL", 1, "HIGH"),
    ("2026-09-01", "2026-09-03", "Commencement Ceremony & Beginning of the Year Affairs (PD)", "SCHOOL_EVENT", "REVIEW", "SCHOOL", "ALL", 1, "HIGH"),
    ("2026-09-10", "2026-09-10", "Teachers’ Day", "OPPORTUNITY", "NONBLOCK", "SCHOOL", "ALL", 1, "HIGH"),
    ("2026-09-25", "2026-09-25", "Mid-Autumn Festival", "OPPORTUNITY", "NONBLOCK", "SCHOOL", "ALL", 1, "HIGH"),
    ("2026-10-01", "2026-10-01", "National Day", "HOLIDAY", "BLOCK", "SCHOOL", "ALL", 1, "HIGH"),
    ("2026-10-01", "2026-10-07", "National Day Holiday", "HOLIDAY", "BLOCK", "SCHOOL", "ALL", 1, "HIGH"),
    ("2026-10-16", "2026-10-16", "G1 - G11 Parents’ Meeting", "SCHOOL_EVENT", "REVIEW", "GRADE_RANGE", "G1-G11", 1, "HIGH"),
    ("2026-10-21", "2026-10-23", "Reading Festival", "OPPORTUNITY", "MILESTONE", "SCHOOL", "ALL", 1, "HIGH"),
    ("2026-10-30", "2026-10-30", "G12 Parents’ Meeting", "SCHOOL_EVENT", "REVIEW", "GRADE", "G12", 1, "HIGH"),
    ("2026-11-13", "2026-11-13", "Sports Day (Primary Division)", "SCHOOL_EVENT", "REVIEW", "DIVISION", "PRIMARY", 1, "HIGH"),
    ("2026-11-20", "2026-11-20", "Sports Day (Secondary Division)", "SCHOOL_EVENT", "REVIEW", "DIVISION", "SECONDARY", 1, "HIGH"),
    ("2026-12-05", "2026-12-06", "Admissions Test", "SCHOOL_EVENT", "REVIEW", "SCHOOL", "ALL", 1, "HIGH"),
    ("2026-12-07", "2026-12-18", "G10 (IGCSE), G11 (GCE), G12 (GCE), G11 (IB) First Semester Assessment", "ASSESSMENT", "BLOCK", "COURSE_LIST", "G10-IGCSE;G11-GCE;G12-GCE;G11-IB", 1, "HIGH"),
    ("2026-12-11", "2026-12-11", "Minxin’s Got Talent", "OPPORTUNITY", "NONBLOCK", "SCHOOL", "ALL", 1, "HIGH"),
    ("2026-12-21", "2027-01-02", "Winter Break", "HOLIDAY", "BLOCK", "SCHOOL", "ALL", 1, "HIGH"),
    ("2027-01-01", "2027-01-01", "New Year’s Day", "HOLIDAY", "BLOCK", "SCHOOL", "ALL", 1, "HIGH"),
    ("2027-01-04", "2027-01-13", "G7 - G11 First Semester Assessment", "ASSESSMENT", "BLOCK", "GRADE_RANGE", "G7-G11", 1, "HIGH"),
    ("2027-01-04", "2027-01-19", "G12 (HKDSE) Mock Assessment", "ASSESSMENT", "BLOCK", "GRADE", "G12", 1, "HIGH"),
    ("2027-01-07", "2027-01-12", "G2 - G6 First Semester Assessment", "ASSESSMENT", "BLOCK", "GRADE_RANGE", "G2-G6", 1, "HIGH"),
    ("2027-01-22", "2027-01-22", "G10 IGCSE Parents’ Meeting", "SCHOOL_EVENT", "REVIEW", "COURSE", "G10-IGCSE", 1, "HIGH"),
    ("2027-01-29", "2027-01-29", "Chinese Culture Day", "OPPORTUNITY", "MILESTONE", "SCHOOL", "ALL", 1, "HIGH"),
    ("2027-02-01", "2027-02-13", "Lunar New Year Holiday", "HOLIDAY", "BLOCK", "SCHOOL", "ALL", 1, "HIGH"),
    ("2027-02-15", "2027-02-15", "First Day of the Second Semester", "MILESTONE", "NONBLOCK", "SCHOOL", "ALL", 1, "HIGH"),
    ("2027-02-19", "2027-02-19", "Around the World in a Day", "OPPORTUNITY", "MILESTONE", "SCHOOL", "ALL", 1, "HIGH"),
    ("2027-02-26", "2027-02-26", "Inter-house Academic Quiz Competition", "OPPORTUNITY", "NONBLOCK", "SCHOOL", "ALL", 1, "HIGH"),
    ("2027-03-01", "2027-03-16", "G10 (IGCSE), G11 (GCE) and G12 (GCE) Mock Assessment", "ASSESSMENT", "BLOCK", "COURSE_LIST", "G10-IGCSE;G11-GCE;G12-GCE", 2, "HIGH"),
    ("2027-03-05", "2027-03-06", "Parents’ Days", "SCHOOL_EVENT", "REVIEW", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-03-08", "2027-03-08", "The Day Following Parents’ Day", "SCHOOL_EVENT", "REVIEW", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-03-15", "2027-03-19", "AI & STEAM Week", "OPPORTUNITY", "MILESTONE", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-03-11", "2027-03-31", "HKDSE Examination (English Language - Speaking)", "ASSESSMENT", "REVIEW", "COURSE", "G12-HKDSE-ENGLISH", 2, "LOW"),
    ("2027-04-05", "2027-04-05", "Ching Ming Festival", "HOLIDAY", "BLOCK", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-04-06", "2027-05-04", "HKDSE Examination (Core & Elective Subjects)", "ASSESSMENT", "BLOCK", "GRADE", "G12", 2, "HIGH"),
    ("2027-04-08", "2027-04-08", "Online Briefing Session on G10 HKDSE Elective Subject Selection", "SCHOOL_EVENT", "REVIEW", "GRADE", "G10", 2, "HIGH"),
    ("2027-04-15", "2027-04-15", "National Security Education Day", "OPPORTUNITY", "NONBLOCK", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-04-15", "2027-04-15", "Online Briefing Session on Grade 9 Curriculum Pathways Selection", "SCHOOL_EVENT", "REVIEW", "GRADE", "G9", 2, "HIGH"),
    ("2027-04-19", "2027-04-23", "English Culture Week", "OPPORTUNITY", "MILESTONE", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-04-23", "2027-04-23", "World Book Day", "OPPORTUNITY", "MILESTONE", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-04-21", "2027-06-20", "IGCSE and GCE Examination", "ASSESSMENT", "REVIEW", "COURSE_LIST", "IGCSE;GCE", 2, "LOW"),
    ("2027-04-30", "2027-05-04", "Labour Day Holiday", "HOLIDAY", "BLOCK", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-05-01", "2027-05-01", "Labour Day", "HOLIDAY", "BLOCK", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-05-07", "2027-05-07", "Swimming Gala", "SCHOOL_EVENT", "REVIEW", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-05-15", "2027-05-15", "Graduation Ceremony", "SCHOOL_EVENT", "REVIEW", "GRADE", "G12", 2, "HIGH"),
    ("2027-05-21", "2027-05-21", "Young Scholars’ Day", "OPPORTUNITY", "MILESTONE", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-06-01", "2027-06-15", "G7 - G11 Second Semester Assessment", "ASSESSMENT", "BLOCK", "GRADE_RANGE", "G7-G11", 2, "HIGH"),
    ("2027-06-03", "2027-06-08", "G2 - G6 Second Semester Assessment", "ASSESSMENT", "BLOCK", "GRADE_RANGE", "G2-G6", 2, "HIGH"),
    ("2027-06-09", "2027-06-09", "Dragon Boat Festival", "HOLIDAY", "BLOCK", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-06-16", "2027-06-18", "G6 Life Education Camp", "SCHOOL_EVENT", "REVIEW", "GRADE", "G6", 2, "HIGH"),
    ("2027-07-03", "2027-07-03", "End of Year Ceremony & Parents’ Day", "SCHOOL_EVENT", "REVIEW", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-07-05", "2027-08-31", "Summer Vacation", "HOLIDAY", "BLOCK", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-07-14", "2027-07-14", "HKDSE Result Release (Tentative)", "MILESTONE", "NONBLOCK", "GRADE", "G12", 2, "HIGH"),
    ("2027-08-18", "2027-08-18", "IGCSE Result Release (Tentative)", "MILESTONE", "NONBLOCK", "COURSE_LIST", "IGCSE", 2, "HIGH"),
    ("2027-08-16", "2027-08-27", "Staff Induction, Development & Preparation Days", "STAFF_EVENT", "REVIEW", "SCHOOL", "ALL", 2, "HIGH"),
    ("2027-08-21", "2027-08-21", "Orientation Day", "SCHOOL_EVENT", "REVIEW", "SCHOOL", "ALL", 2, "HIGH"),
]


def event_id(start: str, end: str, title: str) -> str:
    digest = hashlib.sha256(f"{start}|{end}|{title}".encode()).hexdigest()[:12].upper()
    return f"EVT-{digest}"


def build() -> dict:
    events = []
    for start, end, title, event_type, policy, scope_type, scope_id, page, confidence in EVENTS:
        events.append({
            "event_id": event_id(start, end, title),
            "title": title,
            "start": start,
            "end_inclusive": end,
            "all_day": True,
            "start_time": "",
            "end_time": "",
            "event_type": event_type,
            "block_policy": policy,
            "manual_override": "",
            "scope_type": scope_type,
            "scope_id": scope_id,
            "source_kind": "PDF_SNAPSHOT",
            "source_label": "MINXIN School Calendar 2026-2027 — Final 260622",
            "source_sha256": SOURCE_HASH,
            "source_locator": f"page {page}",
            "parse_status": "REVIEW" if confidence == "LOW" else "VERIFIED_TRANSCRIPTION",
            "confidence": confidence,
            "notes": "Approximate range printed in source; confirm exact dates." if confidence == "LOW" else "Transcribed from the official two-page calendar.",
        })
    return {
        "schema_version": "2.0",
        "year_id": "AY2026-27",
        "academic_start": "2026-09-01",
        "academic_end": "2027-07-03",
        "term_2_start": "2027-02-15",
        "source": {
            "source_label": "MINXIN School Calendar 2026-2027 — Final 260622",
            "source_sha256": SOURCE_HASH,
            "source_pages": 2,
            "publication_url_stored": False,
            "original_file_packaged": False,
            "snapshot_created": "2026-08-28",
        },
        "events": events,
    }


def main() -> None:
    target = Path(__file__).resolve().parent.parent / "assets" / "ay2026-27-calendar.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
