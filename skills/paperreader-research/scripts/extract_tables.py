#!/usr/bin/env python3
"""Extract HTML tables into an English/Chinese-aligned translation manifest.

The script never invents Chinese text. It emits ``*_zh`` fields as empty
placeholders for the research agent to translate before LaTeX compilation.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[dict] = []
        self.current: dict | None = None
        self.section_id: str | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None
        self.caption: list[str] = []
        self.in_caption = False
        self.math_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "section":
            self.section_id = data.get("id")
        elif tag == "figure" and "ltx_table" in (data.get("class") or ""):
            self.current = {"id": data.get("id", ""), "rows": [], "source_section_id": self.section_id}
            self.caption = []
        elif self.current is not None and tag == "tr":
            self.row = []
        elif self.current is not None and tag in {"td", "th"} and self.row is not None:
            self.cell = []
        elif self.current is not None and tag == "figcaption":
            self.in_caption = True
        elif self.current is not None and tag == "math" and self.cell is not None:
            self.math_depth = 1
            alttext = data.get("alttext")
            if alttext:
                self.cell.append(alttext)

    def handle_endtag(self, tag: str) -> None:
        if tag == "math" and self.math_depth:
            self.math_depth = 0
        elif self.current is not None and tag in {"td", "th"} and self.cell is not None and self.row is not None:
            self.row.append(clean(" ".join(self.cell)))
            self.cell = None
        elif self.current is not None and tag == "tr" and self.row is not None:
            if self.row:
                self.current["rows"].append(self.row)
            self.row = None
        elif tag == "figcaption":
            self.in_caption = False
        elif tag == "figure" and self.current is not None:
            rows = self.current.pop("rows")
            if rows:
                table_number = re.search(r"(?:T|table)(\d+)", self.current["id"], re.I)
                table_id = f"table-{table_number.group(1)}" if table_number else f"table-{len(self.tables) + 1}"
                width = max(len(row) for row in rows)
                if len(rows) > 1 and len(rows[0]) < width and len(rows[1]) == width:
                    header = rows[1]
                    data_rows = rows[2:]
                else:
                    header = list(rows[0]) + [""] * (width - len(rows[0]))
                    data_rows = rows[1:]
                self.tables.append({
                    "id": table_id,
                    "source_id": self.current["id"],
                    "source_section_id": self.current.get("source_section_id"),
                    "caption_en": clean(" ".join(self.caption)),
                    "caption_zh": "",
                    "section_id": "",
                    "source_page": None,
                    "columns": [{"header_en": cell, "header_zh": ""} for cell in header],
                    "rows": [
                        {
                            "cells_en": (([""] + list(row)) if len(row) == width - 1 else list(row) + [""] * (width - len(row))),
                            "cells_zh": ["" for _ in range(width)],
                        }
                        for row in data_rows
                    ],
                })
            self.current = None

    def handle_data(self, data: str) -> None:
        if self.current is None:
            return
        if self.in_caption:
            self.caption.append(data)
        elif self.cell is not None and not self.math_depth:
            self.cell.append(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    parser_obj = TableParser()
    parser_obj.feed(args.input.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"tables": parser_obj.tables}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.out}: {len(parser_obj.tables)} tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
