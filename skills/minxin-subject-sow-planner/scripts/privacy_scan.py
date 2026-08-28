#!/usr/bin/env python3
"""Scan Skill and release packages for credentials, unsafe Office features, and personal metadata."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile


PATTERNS = {
    "outlook_publication_url": re.compile(rb"https?://[^\s<\"]*(?:outlook\.office365\.com|outlook\.live\.com)/(?:owa/)?calendar/", re.I),
    "published_calendar_token": re.compile(rb"calendar/(?:published|[^\s/]{24,})/", re.I),
    "credential_assignment": re.compile(rb"(?:password|passwd|api[_-]?key|secret|token)\s*[:=]\s*[^\s]{8,}", re.I),
}


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def scan_package(path: Path) -> dict:
    findings = []
    external = 0
    try:
        with ZipFile(path) as archive:
            names = archive.namelist()
            content = []
            for name in names:
                if name.endswith((".xml", ".rels", ".txt", ".json")):
                    data = archive.read(name)
                    content.append(data)
                    if name.endswith(".rels"):
                        try:
                            root = ET.fromstring(data)
                            external += sum(1 for node in root if node.attrib.get("TargetMode") == "External")
                        except ET.ParseError:
                            findings.append(f"malformed_relationships:{name}")
            for label, pattern in PATTERNS.items():
                if any(pattern.search(data) for data in content):
                    findings.append(label)
            if any(name.lower().endswith("vbaproject.bin") for name in names):
                findings.append("macro_project")
            if any("comments" in name.lower() for name in names):
                findings.append("comments")
            if "docProps/core.xml" in names:
                root = ET.fromstring(archive.read("docProps/core.xml"))
                for node in root.iter():
                    if local(node.tag) in {"creator", "lastModifiedBy"} and (node.text or "").strip() not in {"", "MINXIN School"}:
                        findings.append(f"personal_property:{local(node.tag)}")
            if path.suffix.lower() == ".docx":
                stories = [archive.read(name) for name in names if name.startswith("word/") and name.endswith(".xml")]
                if any(re.search(rb"\bw:rsid[A-Za-z]*=", data) for data in stories):
                    findings.append("word_revision_session_ids")
    except (BadZipFile, FileNotFoundError):
        findings.append("missing_or_invalid_office_package")
    if external:
        findings.append(f"external_relationships:{external}")
    return {"file": str(path), "status": "PASS" if not findings else "FAIL", "findings": sorted(set(findings))}


def scan_tree(root: Path) -> dict:
    findings = []
    allowed_binary = {".docx", ".xlsx", ".jpeg", ".jpg", ".png"}
    for path in root.rglob("*"):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            findings.append(f"symlink:{relative}")
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            findings.append(f"python_cache:{relative}")
        if path.is_file() and (path.suffix.lower() in {".url", ".doc", ".pdf"} or path.name.startswith("~$")):
            findings.append(f"raw_or_temporary_source:{relative}")
        if path.is_file() and path.suffix.lower() not in allowed_binary:
            data = path.read_bytes()
            for label, pattern in PATTERNS.items():
                if pattern.search(data):
                    findings.append(f"{label}:{relative}")
    return {"root": str(root), "status": "PASS" if not findings else "FAIL", "findings": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, action="append", default=[])
    parser.add_argument("--skill-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    packages = [scan_package(path) for path in args.file]
    tree = scan_tree(args.skill_dir)
    failed = [item["file"] for item in packages if item["status"] != "PASS"]
    if tree["status"] != "PASS":
        failed.append("skill_tree")
    report = {"status": "PASS" if not failed else "FAIL", "failed_scopes": failed, "packages": packages, "skill_tree": tree}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
