#!/usr/bin/env python3
"""Copy one completed paper's deliverables into a unique library directory."""
from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path


def safe_name(value: str) -> str:
    """Return a filesystem-safe macOS folder or file stem."""
    value = re.sub(r"[/:\x00-\x1f]", "-", value).strip(" .")
    value = re.sub(r"\s+", "-", value)
    if not value:
        raise ValueError("name must contain at least one usable character")
    return value


def require_pdf(path: Path, label: str) -> Path:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    if not path.read_bytes()[:5] == b"%PDF-":
        raise ValueError(f"{label} is not a PDF: {path}")
    return path


def require_paper(path: Path) -> Path:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f".paper package does not exist: {path}")
    try:
        with zipfile.ZipFile(path) as archive:
            required = {"manifest.json", "pdf/english.pdf", "pdf/chinese.pdf"}
            missing = required.difference(archive.namelist())
    except zipfile.BadZipFile as exc:
        raise ValueError(f"invalid .paper ZIP: {path}") from exc
    if missing:
        raise ValueError(f".paper package is missing: {', '.join(sorted(missing))}")
    return path


def unique_directory(root: Path, folder_name: str) -> Path:
    candidate = root / folder_name
    suffix = 2
    while candidate.exists():
        candidate = root / f"{folder_name}-{suffix}"
        suffix += 1
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create one non-overwriting paper folder with original, translation, and .paper files."
    )
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--translated-pdf", type=Path, required=True)
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--folder-name", required=True)
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()

    source_pdf = require_pdf(args.source_pdf, "source PDF")
    translated_pdf = require_pdf(args.translated_pdf, "translated PDF")
    paper = require_paper(args.paper)
    root = args.output_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = unique_directory(root, safe_name(args.folder_name))
    destination.mkdir()

    try:
        shutil.copy2(source_pdf, destination / "论文原文.pdf")
        shutil.copy2(translated_pdf, destination / "中文翻译.pdf")
        shutil.copy2(paper, destination / f"{safe_name(args.slug)}.paper")
    except Exception:
        shutil.rmtree(destination)
        raise

    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
