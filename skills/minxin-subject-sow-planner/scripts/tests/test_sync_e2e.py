#!/usr/bin/env python3

from __future__ import annotations

import sys
import tempfile
import unittest
import os
import zipfile
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from export_sow import create_sow  # noqa: E402
from planner_core import build_planner_data, read_json, write_json  # noqa: E402
from sow_planner import run_node  # noqa: E402


class SyncEndToEndTests(unittest.TestCase):
    def test_exported_workbook_persists_freeze_rows(self):
        node_value = os.environ.get("MINXIN_TEST_NODE")
        modules_value = os.environ.get("MINXIN_TEST_NODE_MODULES")
        if not node_value or not modules_value:
            self.skipTest("Set MINXIN_TEST_NODE and MINXIN_TEST_NODE_MODULES")
        calendar = read_json(ROOT / "assets" / "ay2026-27-calendar.json")
        fixture = read_json(ROOT / "scripts" / "tests" / "fixtures" / "multi-subject-fixture.json")
        payload = build_planner_data(fixture, calendar)
        with tempfile.TemporaryDirectory(prefix="minxin-freeze-e2e-") as name:
            directory = Path(name)
            data, workbook = directory / "planner.json", directory / "planner.xlsx"
            write_json(data, payload)
            run_node(ROOT / "scripts" / "build_planner.mjs", ["--data", str(data), "--out", str(workbook)], Path(node_value), Path(modules_value))
            roundtrip = directory / "roundtrip.json"
            run_node(ROOT / "scripts" / "read_planner.mjs", ["--input", str(workbook), "--out", str(roundtrip)], Path(node_value), Path(modules_value))
            self.assertEqual(read_json(roundtrip)["source_hash"], payload["source_hash"])
            with zipfile.ZipFile(workbook) as archive:
                sheets = [member for member in archive.namelist() if member.startswith("xl/worksheets/sheet") and member.endswith(".xml")]
                self.assertEqual(len(sheets), 10)
                self.assertTrue(all(b'ySplit="4"' in archive.read(member) and b'state="frozen"' in archive.read(member) for member in sheets))

    def test_one_objective_change_updates_only_linked_course_and_both_profiles(self):
        calendar = read_json(ROOT / "assets" / "ay2026-27-calendar.json")
        fixture = read_json(ROOT / "scripts" / "tests" / "fixtures" / "multi-subject-fixture.json")
        baseline = build_planner_data(fixture, calendar)
        marker = "SYNC-MARKER: cites two precise details and explains their combined effect."
        target = next(row for row in fixture["tables"]["Objectives"] if row["objective_id"] == "ENGLISH-G7-CORE-A-U1-O1")
        target["objective_text"] = marker
        updated = build_planner_data(fixture, calendar)
        self.assertNotEqual(baseline["source_hash"], updated["source_hash"])
        english_rows = [row for row in updated["tables"]["SOW_View"] if row["course_id"] == "ENGLISH-G7-CORE-A"]
        other_rows = [row for row in updated["tables"]["SOW_View"] if row["course_id"] != "ENGLISH-G7-CORE-A"]
        self.assertTrue(any(marker in row["teaching_objectives"] for row in english_rows))
        self.assertFalse(any(marker in row["teaching_objectives"] for row in other_rows))
        course = next(row for row in updated["tables"]["Course_Brief"] if row["course_id"] == "ENGLISH-G7-CORE-A")
        with tempfile.TemporaryDirectory(prefix="minxin-sync-e2e-") as name:
            directory = Path(name)
            standard = directory / "standard.docx"
            compact = directory / "compact.docx"
            create_sow(updated, course, english_rows, standard, "standard", "en-GB", ROOT / "assets" / "minxin-logo.jpeg")
            create_sow(updated, course, english_rows, compact, "compact", "en-GB", ROOT / "assets" / "minxin-logo.jpeg")
            standard_doc, compact_doc = Document(standard), Document(compact)
            self.assertTrue(any(len(table.columns) == 11 for table in standard_doc.tables))
            self.assertTrue(any(len(table.columns) == 10 for table in compact_doc.tables))
            text = "\n".join(cell.text for table in standard_doc.tables for row in table.rows for cell in row.cells)
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
