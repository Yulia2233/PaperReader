#!/usr/bin/env python3
"""Copy and validate figure assets for direct PDF rendering."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def valid_image(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 12:
        return False
    header = path.read_bytes()[:12]
    return (
        header.startswith(b"\x89PNG\r\n\x1a\n")
        or header.startswith(b"\xff\xd8\xff")
        or header.startswith(b"\x00\x00\x00\x0cjp2")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    figure_dir = args.output_root / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    for figure in data.get("figures", []):
        source = args.source_root / Path(figure.get("asset_path", ""))
        target = figure_dir / f"{figure['id']}{source.suffix.lower() or '.png'}"
        if valid_image(source):
            shutil.copyfile(source, target)
            figure["render_path"] = f"figures/{target.name}"
            figure["status"] = "ready"
            figure.pop("error", None)
        else:
            figure["status"] = "missing"
            figure["error"] = "image asset missing or has an unsupported format"
            missing.append(figure["id"])
    data.setdefault("quality", {})["missing_figures"] = missing
    args.manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
