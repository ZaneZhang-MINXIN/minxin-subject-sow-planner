#!/usr/bin/env python3
"""Public workflow for the MINXIN subject-neutral SOW Planner Skill."""

from __future__ import annotations

import argparse
from calendar import monthrange
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True

from planner_core import (
    build_planner_data,
    load_url_calendar,
    normalize_tabular_calendar,
    parse_csv_calendar,
    parse_ics_bytes,
    read_json,
    refresh_planner_payload,
    sha256_file,
    write_json,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_CALENDAR = SKILL_DIR / "assets" / "ay2026-27-calendar.json"
DEFAULT_CURRICULUM = SKILL_DIR / "assets" / "blank-curriculum.json"
DEFAULT_LOGO = SKILL_DIR / "assets" / "minxin-logo.jpeg"


def run(command: list[str]) -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(command, check=True, env=environment)


def run_status(command: list[str]) -> int:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(command, check=False, env=environment).returncode


def resolve_node(explicit: Path | None) -> Path:
    if explicit:
        return explicit.resolve()
    found = shutil.which("node")
    if found:
        return Path(found).resolve()
    raise SystemExit("Node.js is required; provide --node")


def resolve_node_modules(node: Path, explicit: Path | None) -> Path:
    if explicit:
        return explicit.resolve()
    candidate = node.parent.parent / "node_modules"
    if candidate.is_dir():
        return candidate
    raise SystemExit("Bundled node_modules is required; provide --node-modules")


def run_node(worker: Path, arguments: list[str], node: Path, node_modules: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="minxin-subject-sow-node-") as temp_name:
        temp = Path(temp_name)
        local = temp / worker.name
        shutil.copy2(worker, local)
        (temp / "node_modules").symlink_to(node_modules, target_is_directory=True)
        run([str(node), str(local), *arguments])


def add_node_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--node", type=Path)
    parser.add_argument("--node-modules", type=Path)


def sanitize_json(value):
    if isinstance(value, dict):
        return {key: sanitize_json(item) for key, item in value.items() if not any(token in key.lower() for token in ("url", "token", "publication_address"))}
    if isinstance(value, list):
        return [sanitize_json(item) for item in value]
    if isinstance(value, str) and re.search(r"https?://[^\s]*(?:outlook|calendar/published)", value, re.I):
        return "[REDACTED]"
    return value


def calendar_from_pdf(path: Path, academic_start: str = "2026-09-01", academic_end: str = "2027-07-03", term_2_start: str = "2027-02-15") -> dict:
    try:
        import pdfplumber
    except ModuleNotFoundError as error:
        raise SystemExit("PDF calendar import requires the bundled workspace Python runtime with pdfplumber") from error
    events, unparsed = [], []
    pattern = re.compile(r"(?P<d1>\d{1,2})/(?P<m1>\d{1,2})(?:\s*(?:-|–|&|to)\s*(?P<d2>\d{1,2})/(?P<m2>\d{1,2}))?\s*:\s*(?P<title>.+)", re.I)
    textual_pattern = re.compile(
        r"(?P<p1>early|mid|late)[ -](?P<m1>[A-Za-z]+)\s+to\s+"
        r"(?P<p2>early|mid|late)[ -](?P<m2>[A-Za-z]+)\s*:\s*(?P<title>.+)",
        re.I,
    )
    month_numbers = {
        name: number for number, name in enumerate(
            ("", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")
        ) if name
    }
    month_numbers.update({name[:3]: number for name, number in list(month_numbers.items())})
    source_hash = sha256_file(path)
    start_boundary, end_boundary = date.fromisoformat(academic_start), date.fromisoformat(academic_end)

    def inferred_year(month: int) -> int:
        return start_boundary.year if month >= start_boundary.month else end_boundary.year

    def bounded_day(position: str, year: int, month: int, boundary: str) -> int:
        if boundary == "start":
            return {"early": 1, "mid": 11, "late": 21}[position]
        return {"early": 10, "mid": 20, "late": monthrange(year, month)[1]}[position]

    def append_event(start: date, end: date, title: str, page_number: int, line_number: int, confidence: str, note: str) -> dict:
        event = {
            "event_id": "", "title": title.strip(), "start": start.isoformat(), "end_inclusive": end.isoformat(),
            "all_day": True, "start_time": "", "end_time": "", "event_type": "SCHOOL_EVENT", "block_policy": "REVIEW",
            "manual_override": "", "scope_type": "SCHOOL", "scope_id": "ALL", "source_kind": "PDF",
            "source_label": path.name, "source_sha256": source_hash, "source_locator": f"page {page_number}, line {line_number}",
            "parse_status": "REVIEW", "confidence": confidence, "notes": note,
        }
        events.append(event)
        return event

    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            last_event, last_raw_title = None, ""
            for line_number, line in enumerate((page.extract_text() or "").splitlines(), 1):
                match = pattern.search(line)
                if match:
                    d1, m1 = int(match.group("d1")), int(match.group("m1"))
                    d2, m2 = int(match.group("d2") or d1), int(match.group("m2") or m1)
                    year1, year2 = inferred_year(m1), inferred_year(m2)
                    start, end = date(year1, m1, d1), date(year2, m2, d2)
                    if end < start and m1 == 8 and m2 >= start_boundary.month:
                        start = date(start_boundary.year, m1, d1)
                    if end < start:
                        unparsed.append(f"page {page_number}, line {line_number}: inverted date range requires review: {line.strip()}")
                        last_event, last_raw_title = None, ""
                        continue
                    last_raw_title = match.group("title").strip()
                    last_event = append_event(start, end, last_raw_title, page_number, line_number, "MEDIUM", "PDF extraction draft; confirm type, scope, end date, and block policy.")
                    continue

                textual = textual_pattern.search(line)
                if textual:
                    m1 = month_numbers.get(textual.group("m1").lower())
                    m2 = month_numbers.get(textual.group("m2").lower())
                    if m1 and m2:
                        year1, year2 = inferred_year(m1), inferred_year(m2)
                        start = date(year1, m1, bounded_day(textual.group("p1").lower(), year1, m1, "start"))
                        end = date(year2, m2, bounded_day(textual.group("p2").lower(), year2, m2, "end"))
                        if end >= start:
                            last_raw_title = textual.group("title").strip()
                            last_event = append_event(start, end, last_raw_title, page_number, line_number, "LOW", "Textual PDF range converted to a bounded planning window; confirm exact dates, type, scope, and policy.")
                            continue

                stripped = line.strip()
                if last_event is not None and last_raw_title.endswith(",") and stripped and not stripped[0].isdigit():
                    last_event["title"] = f"{last_event['title']} {stripped}"
                    last_raw_title = stripped
                    continue
                lower_line = line.lower()
                if "teaching days" not in lower_line and ":" in line and any(term in lower_line for term in ("assessment", "examination", "exam", "mock", "holiday", "week", "festival", "ceremony", "day")):
                    unparsed.append(f"page {page_number}, line {line_number}: {line.strip()}")

    for event in events:
        identifier = __import__("hashlib").sha256(f"{event['start']}|{event['end_inclusive']}|{event['title']}".encode()).hexdigest()[:12].upper()
        event["event_id"] = f"EVT-{identifier}"
    return {
        "schema_version": "2.0", "year_id": "AY-UPLOADED", "academic_start": academic_start, "academic_end": academic_end,
        "term_2_start": term_2_start, "source": {"source_label": path.name, "source_sha256": source_hash, "publication_url_stored": False},
        "events": events, "import_warnings": unparsed,
    }


def normalized_calendar(source: Path, node: Path | None, node_modules: Path | None, academic_start: str = "2026-09-01", academic_end: str = "2027-07-03", term_2_start: str = "2027-02-15") -> dict:
    suffix = source.suffix.lower()
    if suffix == ".json":
        payload = sanitize_json(read_json(source))
        payload.setdefault("source", {})["publication_url_stored"] = False
        return payload
    if suffix == ".ics":
        data = source.read_bytes()
        parsed = parse_ics_bytes(data, source.name, sha256_file(source))
    elif suffix == ".url":
        data, label, source_hash = load_url_calendar(source)
        parsed = parse_ics_bytes(data, label, source_hash)
    elif suffix == ".csv":
        parsed = parse_csv_calendar(source)
    elif suffix == ".xlsx":
        if not node or not node_modules:
            raise SystemExit("XLSX calendar import requires --node and --node-modules")
        with tempfile.TemporaryDirectory(prefix="minxin-calendar-xlsx-") as temp_name:
            rows_path = Path(temp_name) / "rows.json"
            run_node(SCRIPT_DIR / "read_calendar_xlsx.mjs", ["--input", str(source), "--out", str(rows_path)], node, node_modules)
            rows = read_json(rows_path)["rows"]
        parsed = normalize_tabular_calendar(rows, source.name, sha256_file(source), "XLSX")
    elif suffix == ".pdf":
        return calendar_from_pdf(source, academic_start, academic_end, term_2_start)
    else:
        raise SystemExit(f"Unsupported calendar source: {suffix}")
    return {
        "schema_version": "2.0", "year_id": "AY-UPLOADED", "academic_start": academic_start, "academic_end": academic_end,
        "term_2_start": term_2_start, "source": {"source_label": source.stem, "source_sha256": parsed["events"][0]["source_sha256"] if parsed.get("events") else sha256_file(source), "publication_url_stored": False},
        "events": parsed.get("events", []), "import_warnings": parsed.get("import_warnings", []),
    }


def extract_workbook(workbook: Path, node: Path, node_modules: Path, out: Path, preview: Path | None = None, inspect: Path | None = None) -> None:
    arguments = ["--input", str(workbook), "--out", str(out)]
    if preview:
        arguments.extend(["--preview-dir", str(preview)])
    if inspect:
        arguments.extend(["--inspect-out", str(inspect)])
    run_node(SCRIPT_DIR / "read_planner.mjs", arguments, node, node_modules)


def load_timetable(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        payload = read_json(path)
        if isinstance(payload, list):
            return payload
        return payload.get("Timetable_Slots", payload.get("tables", {}).get("Timetable_Slots", []))
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    raise SystemExit("Timetable input must be JSON or CSV; use the workbook table for direct editing")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    learn = commands.add_parser("learn")
    learn.add_argument("--source", action="append", type=Path, required=True)
    learn.add_argument("--out-dir", type=Path, required=True)
    calendar = commands.add_parser("calendar")
    calendar.add_argument("--source", type=Path, default=DEFAULT_CALENDAR)
    calendar.add_argument("--out", type=Path, required=True)
    calendar.add_argument("--academic-start", default="2026-09-01")
    calendar.add_argument("--academic-end", default="2027-07-03")
    calendar.add_argument("--term-2-start", default="2027-02-15")
    add_node_args(calendar)
    build = commands.add_parser("build")
    build.add_argument("--curriculum", type=Path, default=DEFAULT_CURRICULUM)
    build.add_argument("--calendar", type=Path, default=DEFAULT_CALENDAR)
    build.add_argument("--timetable", type=Path)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--data-out", type=Path)
    build.add_argument("--preview-dir", type=Path)
    build.add_argument("--academic-start")
    build.add_argument("--academic-end")
    build.add_argument("--term-2-start")
    add_node_args(build)
    export = commands.add_parser("export")
    export.add_argument("--workbook", type=Path, required=True)
    export.add_argument("--course", default="all")
    export.add_argument("--out-dir", type=Path, required=True)
    export.add_argument("--profile", choices=["standard", "compact"], default="standard")
    export.add_argument("--language", choices=["en-GB", "zh-Hant-HK"])
    export.add_argument("--logo", type=Path, default=DEFAULT_LOGO)
    export.add_argument("--no-refresh-workbook", action="store_true")
    add_node_args(export)
    validate = commands.add_parser("validate")
    validate.add_argument("--workbook", type=Path, required=True)
    validate.add_argument("--word-dir", type=Path)
    validate.add_argument("--profile", choices=["standard", "compact"], default="standard")
    validate.add_argument("--language", choices=["en-GB", "zh-Hant-HK"])
    validate.add_argument("--report", type=Path, required=True)
    validate.add_argument("--release", action="store_true")
    validate.add_argument("--render-dir", type=Path)
    validate.add_argument("--preview-dir", type=Path)
    add_node_args(validate)
    render = commands.add_parser("render")
    render.add_argument("--word-dir", type=Path, required=True)
    render.add_argument("--output-dir", type=Path, required=True)
    render.add_argument("--renderer", type=Path)
    return parser


def renderer_path(explicit: Path | None) -> Path:
    if explicit:
        return explicit
    roots = sorted((Path.home() / ".codex/plugins/cache/openai-primary-runtime/documents").glob("*/skills/documents/render_docx.py"))
    if not roots:
        raise SystemExit("Provide --renderer with the documents Skill render_docx.py path")
    return roots[-1]


def main() -> int:
    args = build_parser().parse_args()
    python = Path(sys.executable)
    if args.command == "learn":
        command = [str(python), str(SCRIPT_DIR / "ingest_sow.py"), "--out-dir", str(args.out_dir)]
        for source in args.source:
            command.extend(["--source", str(source)])
        run(command)
        return 0
    if args.command == "render":
        documents = sorted(args.word_dir.glob("*.docx"))
        if not documents:
            raise SystemExit("No DOCX files found")
        run([str(python), str(SCRIPT_DIR / "render_sow.py"), *map(str, documents), "--renderer", str(renderer_path(args.renderer)), "--output-dir", str(args.output_dir)])
        return 0
    if args.command == "calendar":
        node = node_modules = None
        if args.source.suffix.lower() == ".xlsx":
            node = resolve_node(args.node)
            node_modules = resolve_node_modules(node, args.node_modules)
        write_json(args.out, normalized_calendar(args.source, node, node_modules, args.academic_start, args.academic_end, args.term_2_start))
        print(args.out)
        return 0
    node = resolve_node(args.node)
    node_modules = resolve_node_modules(node, args.node_modules)
    if args.command == "build":
        overrides = {key: value for key, value in {"academic_start": args.academic_start, "academic_end": args.academic_end, "term_2_start": args.term_2_start}.items() if value}
        curriculum = read_json(args.curriculum)
        if args.timetable:
            curriculum.setdefault("tables", {})["Timetable_Slots"] = load_timetable(args.timetable)
        payload = build_planner_data(curriculum, read_json(args.calendar), overrides)
        data_out = args.data_out or args.out.with_suffix(".planner.json")
        write_json(data_out, payload)
        arguments = ["--data", str(data_out), "--out", str(args.out)]
        if args.preview_dir:
            arguments.extend(["--preview-dir", str(args.preview_dir)])
        run_node(SCRIPT_DIR / "build_planner.mjs", arguments, node, node_modules)
        print(f"courses={len(payload['tables']['Course_Brief'])} weeks={len(payload['tables']['Weeks'])} plans={len(payload['tables']['Weekly_Plan'])}")
        return 0
    with tempfile.TemporaryDirectory(prefix="minxin-subject-sow-") as temp_name:
        temp = Path(temp_name)
        extracted = temp / "planner.json"
        inspect = (args.report.parent / "workbook-formula-scan.ndjson") if args.command == "validate" else None
        extract_workbook(args.workbook, node, node_modules, extracted, args.preview_dir if args.command == "validate" else None, inspect)
        if args.command == "export":
            refreshed = refresh_planner_payload(read_json(extracted))
            refreshed_json = temp / "refreshed.json"
            write_json(refreshed_json, refreshed)
            if not args.no_refresh_workbook:
                refreshed_book = temp / "refreshed.xlsx"
                run_node(SCRIPT_DIR / "build_planner.mjs", ["--data", str(refreshed_json), "--out", str(refreshed_book)], node, node_modules)
                shutil.copy2(refreshed_book, args.workbook)
            command = [str(python), str(SCRIPT_DIR / "export_sow.py"), "--planner-json", str(refreshed_json), "--out-dir", str(args.out_dir), "--course", args.course, "--profile", args.profile, "--logo", str(args.logo)]
            if args.language:
                command.extend(["--language", args.language])
            run(command)
            return 0
        command = [str(python), str(SCRIPT_DIR / "validate.py"), "--planner-json", str(extracted), "--report", str(args.report), "--profile", args.profile]
        if args.word_dir:
            command.extend(["--word-dir", str(args.word_dir)])
        if args.language:
            command.extend(["--language", args.language])
        if args.release:
            command.append("--release")
            if args.render_dir:
                command.extend(["--render-dir", str(args.render_dir)])
        validation_status = run_status(command)
        if args.release:
            privacy = args.report.parent / "privacy-scan.json"
            files = [args.workbook] + (sorted(args.word_dir.glob("*.docx")) if args.word_dir else [])
            privacy_command = [str(python), str(SCRIPT_DIR / "privacy_scan.py"), "--skill-dir", str(SKILL_DIR), "--report", str(privacy)]
            for file in files:
                privacy_command.extend(["--file", str(file)])
            run(privacy_command)
        return validation_status


if __name__ == "__main__":
    raise SystemExit(main())
