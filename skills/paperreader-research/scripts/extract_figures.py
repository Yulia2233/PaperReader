#!/usr/bin/env python3
"""Extract paper figures from HTML or PDF into a portable figure manifest."""
from __future__ import annotations

import argparse
import html
import json
import mimetypes
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


class FigureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.figures: list[dict[str, str]] = []
        self.current: dict[str, str] | None = None
        self.in_caption = False
        self.caption_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "figure":
            self.current = {"src": "", "caption_en": ""}
            self.caption_parts = []
        elif self.current is not None and tag == "img":
            self.current["src"] = data.get("src", "") or data.get("data-src", "")
            self.current["alt"] = data.get("alt", "")
        elif self.current is not None and tag == "figcaption":
            self.in_caption = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "figcaption":
            self.in_caption = False
        elif tag == "figure" and self.current is not None:
            self.current["caption_en"] = " ".join(self.caption_parts).strip()
            if self.current.get("src"):
                self.figures.append(self.current)
            self.current = None

    def handle_data(self, data: str) -> None:
        if self.in_caption:
            self.caption_parts.append(data)


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "PaperReader/0.2"})
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def safe_name(index: int, source: str, content_type: str | None = None) -> str:
    suffix = Path(urllib.parse.urlparse(source).path).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".jp2", ".webp"}:
        suffix = ".png" if content_type == "image/png" else ".jpg"
    return f"fig-{index:03d}{suffix}"


def extract_html(input_path: Path, output_dir: Path, base_url: str | None) -> list[dict]:
    parser = FigureParser()
    parser.feed(input_path.read_text(encoding="utf-8"))
    records = []
    for index, item in enumerate(parser.figures, 1):
        source = urllib.parse.urljoin(base_url or input_path.as_uri(), html.unescape(item["src"]))
        name = safe_name(index, source)
        destination = output_dir / name
        try:
            if urllib.parse.urlparse(source).scheme in {"http", "https"}:
                download(source, destination)
            else:
                shutil.copyfile(Path(urllib.parse.urlparse(source).path), destination)
            status = "ready"
        except (OSError, urllib.error.URLError) as exc:
            status = "missing"
            destination.write_bytes(b"")
            item["error"] = str(exc)
        records.append({
            "id": f"fig-{index:03d}",
            "asset_path": f"assets/figures/{name}",
            "source_page": None,
            "source_kind": "html",
            "caption_en": item.get("caption_en", ""),
            "caption_zh": "",
            "alt_text_zh": "",
            "status": status,
            "source_url": source,
            "error": item.get("error", ""),
        })
    return records


def extract_pdf(input_path: Path, output_dir: Path) -> list[dict]:
    prefix = output_dir / "pdf-figure"
    command = ["pdfimages", "-j", "-png", str(input_path), str(prefix)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        return [{"id": "fig-001", "asset_path": "", "source_page": None, "source_kind": "pdf", "caption_en": "", "caption_zh": "", "alt_text_zh": "", "status": "missing", "error": f"pdfimages failed: {exc}"}]
    candidates = sorted(output_dir.glob("pdf-figure-*"))
    records = []
    for index, source in enumerate(candidates, 1):
        suffix = source.suffix.lower() or ".png"
        destination = output_dir / f"fig-{index:03d}{suffix}"
        source.rename(destination)
        records.append({
            "id": f"fig-{index:03d}",
            "asset_path": f"assets/figures/{destination.name}",
            "source_page": None,
            "source_kind": "pdfimages",
            "caption_en": "",
            "caption_zh": "",
            "alt_text_zh": "",
            "status": "ready",
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="assets/figures output directory")
    parser.add_argument("--kind", choices=["html", "pdf"], required=True)
    parser.add_argument("--base-url", help="base URL for relative HTML image links")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    records = extract_html(args.input, args.out, args.base_url) if args.kind == "html" else extract_pdf(args.input, args.out)
    manifest = args.out.parent / "figure-manifest.json"
    manifest.write_text(json.dumps({"figures": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest)
    return 0 if all(item["status"] != "missing" for item in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
