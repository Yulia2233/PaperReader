#!/usr/bin/env python3
"""Validate a PaperReader v2 .paper ZIP artifact."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import PurePosixPath

STATUSES = {"complete", "needs_fulltext", "needs_pdf_compile"}
FIGURE_STATUSES = {"ready", "fallback_page_render", "missing"}


def fail(message: str) -> None:
    raise ValueError(message)


def safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def validate(path: str) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        unsafe = [name for name in names if not safe_member(name)]
        if unsafe:
            fail(f"unsafe ZIP paths: {unsafe}")
        if "manifest.json" not in names:
            fail("manifest.json is missing")
        manifest = json.loads(archive.read("manifest.json"))
        required = {"schema_version", "artifact_type", "processing_status", "layout_profile", "paper", "sections", "analysis", "experiments", "quality"}
        missing = required - manifest.keys()
        if missing:
            fail(f"missing manifest fields: {sorted(missing)}")
        if manifest["schema_version"] != "2.0" or manifest["artifact_type"] != "paperreader":
            fail("unsupported .paper schema")
        if manifest["processing_status"] not in STATUSES:
            fail("invalid processing_status")
        if manifest["layout_profile"] not in {"two-column", "single-column"}:
            fail("layout_profile must be two-column or single-column")
        paper = manifest["paper"]
        for key in ("title", "authors", "year", "venue", "venue_tier", "english_pdf", "chinese_pdf"):
            if key not in paper:
                fail(f"paper.{key} is missing")
        for key in ("english_pdf", "chinese_pdf"):
            pdf_path = paper[key]
            if pdf_path and pdf_path in names:
                if not archive.read(pdf_path).startswith(b"%PDF"):
                    fail(f"{pdf_path} is not a PDF")
            elif manifest["processing_status"] == "complete":
                fail(f"{pdf_path} is missing from a complete artifact")
        orders = []
        for section in manifest["sections"]:
            if not {"id", "title", "order"} <= section.keys():
                fail("each section needs id, title and order")
            orders.append(section["order"])
            for key in ("english_page_start", "english_page_end", "chinese_page_start", "chinese_page_end"):
                if key in section and section[key] is not None and (not isinstance(section[key], int) or section[key] < 1):
                    fail(f"invalid page mapping {key}")
        if orders != list(range(len(orders))):
            fail("section order must be contiguous and start at zero")
        quality = manifest["quality"]
        figures = manifest.get("figures", [])
        tables = manifest.get("tables", [])
        missing_figures = set(quality.get("missing_figures", []))
        for figure in figures:
            required_figure = {"id", "asset_path", "source_page", "caption_en", "caption_zh", "alt_text_zh", "status"}
            if not required_figure <= figure.keys():
                fail("each figure needs id, asset_path, captions, alt_text_zh and status")
            if figure["status"] not in FIGURE_STATUSES:
                fail(f"invalid figure status: {figure['status']}")
            if figure["source_page"] is not None and (not isinstance(figure["source_page"], int) or figure["source_page"] < 1):
                fail(f"invalid source page for {figure['id']}")
            asset = figure["asset_path"]
            if figure["status"] == "ready" and asset not in names:
                fail(f"missing figure asset: {asset}")
            if figure["status"] == "missing" and figure["id"] not in missing_figures:
                fail(f"missing figure {figure['id']} is not listed in quality.missing_figures")
        for table in tables:
            required_table = {"id", "caption_en", "caption_zh", "columns", "rows"}
            if not required_table <= table.keys():
                fail("each table needs id, captions, columns and rows")
            if not table["caption_zh"].strip():
                fail(f"table {table['id']} has no Chinese caption")
            if not table.get("section_id"):
                fail(f"table {table['id']} has no insertion section_id")
            for column in table["columns"]:
                if not column.get("header_zh", "").strip():
                    fail(f"table {table['id']} has an untranslated column header")
            width = len(table["columns"])
            for row in table["rows"]:
                cells = row.get("cells_zh", [])
                english_cells = row.get("cells_en", [])
                if len(cells) != width or any(str(en).strip() and not str(zh).strip() for en, zh in zip(english_cells, cells)):
                    fail(f"table {table['id']} has missing Chinese cells")
        if manifest["processing_status"] == "needs_pdf_compile" and "tex/chinese.tex" not in names:
            fail("needs_pdf_compile artifact must preserve tex/chinese.tex")


def main() -> int:
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} FILE...", file=sys.stderr)
        return 2
    failed = False
    for path in sys.argv[1:]:
        try:
            validate(path)
            print(f"OK {path}")
        except (OSError, KeyError, json.JSONDecodeError, ValueError, zipfile.BadZipFile) as exc:
            failed = True
            print(f"ERROR {path}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
