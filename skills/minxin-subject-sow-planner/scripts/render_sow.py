#!/usr/bin/env python3
"""Render every final SOW DOCX page using the canonical documents renderer."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def configure_fontconfig(environment: dict[str, str]) -> None:
    if sys.platform != "darwin" or environment.get("FONTCONFIG_FILE"):
        return
    executable = Path(sys.executable).resolve()
    try:
        dependencies = executable.parents[2]
    except IndexError:
        return
    candidate = dependencies / "native" / "libreoffice-headless" / "libreoffice" / "LibreOfficeDev.app" / "Contents" / "Resources" / "fontconfig" / "fonts.conf"
    if candidate.is_file():
        environment["FONTCONFIG_FILE"] = str(candidate)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("documents", nargs="+", type=Path)
    parser.add_argument("--renderer", type=Path, default=os.environ.get("CODEX_DOCX_RENDERER"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.renderer or not args.renderer.exists():
        parser.error("Provide the documents Skill render_docx.py path with --renderer")
    for document in args.documents:
        destination = args.output_dir / document.stem
        destination.mkdir(parents=True, exist_ok=True)
        environment = dict(os.environ)
        environment.setdefault("TMPDIR", "/private/tmp")
        configure_fontconfig(environment)
        subprocess.run([sys.executable, str(args.renderer), str(document), "--output_dir", str(destination), "--emit_pdf"], check=True, env=environment)
        pages = sorted(destination.glob("page-*.png"))
        if not pages:
            raise RuntimeError(f"Renderer produced no pages for {document}")
        print(f"{document.name}: pages={len(pages)} output={destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
