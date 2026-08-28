#!/usr/bin/env python3
"""Create the clean reusable MINXIN subject SOW Word template."""

from __future__ import annotations

import argparse
from pathlib import Path

from export_sow import create_sow


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--logo", type=Path)
    args = parser.parse_args()
    planner = {
        "source_hash": "TEMPLATE",
        "tables": {"Setup": [{"key": "academic_year", "value": "20XX-20XX"}]},
    }
    course = {"course_id": "SUBJECT-GRADE-LEVEL-CLASS", "subject_name": "Subject", "grade_level": "Grade", "course_level": "Level", "class_id": "Class"}
    row = {
        "date_range": "YYYY-MM-DD to YYYY-MM-DD", "week_label": "Week N", "row_type": "INSTRUCTION",
        "module_unit": "Unit title", "learning_focus": "Specific learning focus", "prior_learning": "Relevant prior learning",
        "teaching_objectives": "Assessable learning objective", "periods": "—", "resources": "Purposeful resources",
        "values": "Concise value", "activities": "Subject-appropriate student action",
        "evidence": "Observable evidence", "assessment_purpose": "Assessment for/as/of learning",
        "feedback_revision": "Feedback and revision action",
    }
    create_sow(planner, course, [row], args.out, "standard", "en-GB", args.logo)
    print(args.out)


if __name__ == "__main__":
    main()
