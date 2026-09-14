#!/usr/bin/env python3
"""Package manifest, PDFs, LaTeX source and figures into one .paper ZIP."""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--english-pdf", type=Path)
    parser.add_argument("--chinese-pdf", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    data.setdefault("schema_version", "2.0")
    data.setdefault("artifact_type", "paperreader")
    data.setdefault("quality", {})
    data["paper"]["english_pdf"] = "pdf/english.pdf"
    data["paper"]["chinese_pdf"] = "pdf/chinese.pdf"
    if not args.chinese_pdf or not args.chinese_pdf.exists():
        data["processing_status"] = "needs_pdf_compile"
        data["quality"]["pdf_status"] = "needs_pdf_compile"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        for source, target in ((args.english_pdf, "pdf/english.pdf"), (args.chinese_pdf, "pdf/chinese.pdf")):
            if source and source.exists():
                archive.write(source, target)
        for source in sorted(args.root.rglob("*")):
            if not source.is_file() or source.name == "manifest.json":
                continue
            relative = source.relative_to(args.root).as_posix()
            if relative.startswith("pdf/"):
                continue
            archive.write(source, relative)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
