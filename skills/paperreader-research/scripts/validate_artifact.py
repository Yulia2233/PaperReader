#!/usr/bin/env python3
"""Validate PaperReader v1.0 artifacts without third-party dependencies."""
from __future__ import annotations

import json
import sys
from pathlib import Path

STATUSES = {"complete", "needs_fulltext"}
REQUIRED_TOP = {"schema_version", "processing_status", "paper", "sections", "analysis", "experiments", "quality"}
REQUIRED_PAPER = {"title", "authors", "year", "venue", "venue_tier", "doi", "identifiers", "source_urls", "fulltext_source"}
REQUIRED_ANALYSIS = {"problem", "contributions", "innovations", "method_summary"}
REQUIRED_QUALITY = {"evidence_notes", "missing_inputs", "translation_status"}


def fail(message: str) -> None:
    raise ValueError(message)


def validate(path: Path) -> None:
    with path.open(encoding="utf-8") as handle:
        obj = json.load(handle)
    if not isinstance(obj, dict):
        fail("top level must be an object")
    missing = REQUIRED_TOP - obj.keys()
    if missing:
        fail(f"missing top-level fields: {sorted(missing)}")
    if obj["schema_version"] != "1.0":
        fail("schema_version must be 1.0")
    if obj["processing_status"] not in STATUSES:
        fail("processing_status must be complete or needs_fulltext")
    for name, required in (("paper", REQUIRED_PAPER), ("analysis", REQUIRED_ANALYSIS), ("quality", REQUIRED_QUALITY)):
        if not isinstance(obj[name], dict):
            fail(f"{name} must be an object")
        missing = required - obj[name].keys()
        if missing:
            fail(f"missing {name} fields: {sorted(missing)}")
    if not isinstance(obj["paper"]["title"], str) or not obj["paper"]["title"].strip():
        fail("paper.title must be non-empty")
    if not isinstance(obj["paper"]["authors"], list):
        fail("paper.authors must be a list")
    if not isinstance(obj["sections"], list):
        fail("sections must be a list")
    orders = []
    for section in obj["sections"]:
        required = {"id", "title", "order", "source_text", "translated_text"}
        if not isinstance(section, dict) or not required <= section.keys():
            fail("each section needs id, title, order, source_text, translated_text")
        orders.append(section["order"])
    if orders != list(range(len(orders))):
        fail("section order must be contiguous and start at zero")
    if not isinstance(obj["experiments"], list):
        fail("experiments must be a list")
    experiment_fields = {"name", "what_it_tests", "what_it_proves", "datasets", "baselines", "metrics", "result_summary"}
    for experiment in obj["experiments"]:
        if not isinstance(experiment, dict) or not experiment_fields <= experiment.keys():
            fail("each experiment needs the complete table fields")
    if obj["processing_status"] == "needs_fulltext" and not obj["quality"]["missing_inputs"]:
        fail("needs_fulltext artifacts must explain missing_inputs")


def main() -> int:
    if len(sys.argv) < 2:
        print(f"usage: {Path(sys.argv[0]).name} FILE...", file=sys.stderr)
        return 2
    failed = False
    for raw in sys.argv[1:]:
        path = Path(raw)
        try:
            validate(path)
            print(f"OK {path}")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            failed = True
            print(f"ERROR {path}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
