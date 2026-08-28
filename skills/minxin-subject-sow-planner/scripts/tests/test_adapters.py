#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from planner_core import load_url_calendar, normalize_tabular_calendar, parse_csv_calendar, parse_ics_bytes, read_json  # noqa: E402
from sow_planner import calendar_from_pdf, run_node  # noqa: E402


class AdapterTests(unittest.TestCase):
    def test_csv_adapter_requires_title_and_date(self):
        with tempfile.TemporaryDirectory(prefix="minxin-csv-") as name:
            path = Path(name) / "calendar.csv"
            path.write_text("Title,Start Date,End Date\nHoliday,2026-10-01,2026-10-02\n", encoding="utf-8")
            result = parse_csv_calendar(path)
            self.assertEqual(len(result["events"]), 1)
            self.assertEqual(result["events"][0]["block_policy"], "REVIEW")

    def test_tabular_adapter_preserves_policy_scope_times_and_deduplicates(self):
        rows = [{"Title": "Oral assessment", "Start Date": "2026-10-02", "End Date": "2026-10-02", "Start Time": "10:00", "End Time": "10:45", "Type": "ASSESSMENT", "Policy": "BLOCK", "Scope": "COURSE", "Scope ID": "ENG-8A"}] * 2
        result = normalize_tabular_calendar(rows, "fixture.csv", "fixture-hash", "CSV")
        self.assertEqual(len(result["events"]), 1)
        event = result["events"][0]
        self.assertFalse(event["all_day"])
        self.assertEqual((event["event_type"], event["block_policy"]), ("ASSESSMENT", "BLOCK"))
        self.assertEqual((event["scope_type"], event["scope_id"]), ("COURSE", "ENG-8A"))

    def test_tabular_adapter_reports_invalid_or_missing_dates(self):
        rows = [
            {"Title": "Valid", "Start Date": "2026-10-02"},
            {"Title": "Non-ISO", "Start Date": "02/10/2026"},
            {"Title": "Inverted", "Start Date": "2026-10-03", "End Date": "2026-10-01"},
            {"Title": "Missing"},
        ]
        result = normalize_tabular_calendar(rows, "fixture.csv", "fixture-hash", "CSV")
        self.assertEqual([event["title"] for event in result["events"]], ["Valid"])
        self.assertEqual(len(result["import_warnings"]), 3)
        self.assertTrue(all("row " in warning for warning in result["import_warnings"]))

    def test_non_xlsx_calendar_cli_does_not_require_node(self):
        with tempfile.TemporaryDirectory(prefix="minxin-calendar-cli-") as name:
            directory = Path(name)
            source, output = directory / "calendar.csv", directory / "calendar.json"
            source.write_text("Title,Start Date\nHoliday,2026-10-01\n", encoding="utf-8")
            environment = dict(os.environ)
            environment["PATH"] = ""
            subprocess.run([sys.executable, str(ROOT / "scripts" / "sow_planner.py"), "calendar", "--source", str(source), "--out", str(output)], check=True, env=environment, capture_output=True, text=True)
            self.assertEqual(len(read_json(output)["events"]), 1)

    def test_pdf_adapter_is_review_first(self):
        source_value = os.environ.get("MINXIN_TEST_CALENDAR_PDF")
        if not source_value:
            self.skipTest("Set MINXIN_TEST_CALENDAR_PDF to an official calendar PDF")
        source = Path(source_value)
        if not source.exists():
            self.skipTest("MINXIN_TEST_CALENDAR_PDF does not exist")
        result = calendar_from_pdf(source)
        self.assertGreater(len(result["events"]), 20)
        self.assertTrue(all(event["block_policy"] == "REVIEW" for event in result["events"]))
        self.assertIn("import_warnings", result)
        self.assertFalse(any("Teaching Days" in warning for warning in result["import_warnings"]))
        self.assertTrue(all(event["start"] <= event["end_inclusive"] for event in result["events"]))
        events = {event["title"]: event for event in result["events"]}
        self.assertEqual(events["G12 (HKDSE) Pre-mock Assessment"]["start"], "2026-08-20")
        self.assertTrue(any("G12(GCE), G11 (IB) First Semester Assessment" in title for title in events))
        self.assertIn("HKDSE Examination (English Language - Speaking)", events)
        self.assertIn("IGCSE and GCE Examination", events)

    def test_url_adapter_keeps_address_out_of_normalized_events(self):
        with tempfile.TemporaryDirectory(prefix="minxin-url-") as name:
            directory = Path(name)
            ics = directory / "calendar.ics"
            ics.write_text("BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART;VALUE=DATE:20261001\nDTEND;VALUE=DATE:20261002\nSUMMARY:Fixture Holiday\nEND:VEVENT\nEND:VCALENDAR\n", encoding="utf-8")
            shortcut = directory / "calendar.url"
            shortcut.write_text(f"[InternetShortcut]\nURL={ics.as_uri()}\n", encoding="utf-8")
            data, label, source_hash = load_url_calendar(shortcut)
            payload = parse_ics_bytes(data, label, source_hash)
            self.assertEqual(len(payload["events"]), 1)
            self.assertNotIn(ics.as_uri(), str(payload))

    def test_xlsx_adapter_uses_artifact_runtime(self):
        node_value = os.environ.get("MINXIN_TEST_NODE")
        modules_value = os.environ.get("MINXIN_TEST_NODE_MODULES")
        if not node_value or not modules_value:
            self.skipTest("Set MINXIN_TEST_NODE and MINXIN_TEST_NODE_MODULES")
        node, modules = Path(node_value), Path(modules_value)
        with tempfile.TemporaryDirectory(prefix="minxin-xlsx-") as name:
            directory = Path(name)
            workbook, rows_path = directory / "calendar.xlsx", directory / "rows.json"
            run_node(Path(__file__).with_name("write_calendar_fixture.mjs"), ["--out", str(workbook)], node, modules)
            run_node(ROOT / "scripts" / "read_calendar_xlsx.mjs", ["--input", str(workbook), "--out", str(rows_path)], node, modules)
            rows = read_json(rows_path)["rows"]
            result = normalize_tabular_calendar(rows, workbook.name, "fixture-hash", "XLSX")
            self.assertEqual(len(result["events"]), 2)


if __name__ == "__main__":
    unittest.main()
