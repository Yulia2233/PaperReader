#!/usr/bin/env python3
"""Generate a Chinese LaTeX paper and compile it with a preinstalled XeLaTeX."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def latex_escape(value: str) -> str:
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "$": r"\$"}
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path, help="JSON containing paper, sections and figures")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--font", type=Path, help="bundled .ttf/.otf CJK font")
    parser.add_argument("--compiler", choices=["auto", "latexmk", "xelatex"], default="auto")
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tex_path = args.output_dir / "chinese.tex"
    font_line = ""
    if args.font:
        font_line = "\\setCJKmainfont[Path=%s/,Extension=.ttf]{%s}\n" % (args.font.parent, args.font.stem)
    body = []
    for section in sorted(data.get("sections", []), key=lambda item: item.get("order", 0)):
        body.append("\\section{%s}\n%s" % (latex_escape(section.get("title", "")), latex_escape(section.get("translated_text", ""))))
    figure_tex = args.output_dir / "figures.tex"
    if figure_tex.exists():
        body.append("\\input{figures.tex}")
    tex = """\\documentclass[a4paper,11pt]{ctexart}
\\usepackage[margin=2.2cm]{geometry}
\\usepackage{graphicx}
\\usepackage{hyperref}
\\usepackage{longtable}
\\usepackage{booktabs}
\\hypersetup{hidelinks}
%% PaperReader generated source. Figures preserve original pixels; captions are translated.
%s
\\title{%s}
\\author{%s}
\\date{%s}
\\begin{document}
\\maketitle
%s
\\end{document}
""" % (font_line, latex_escape(data["paper"]["title"]), latex_escape(", ".join(data["paper"].get("authors", []))), data["paper"].get("year", ""), "\n\n".join(body))
    tex_path.write_text(tex, encoding="utf-8")
    compiler = shutil.which("latexmk") if args.compiler in {"auto", "latexmk"} else None
    command = [compiler, "-xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name] if compiler else None
    if command is None:
        compiler = shutil.which("xelatex")
        command = [compiler, "-interaction=nonstopmode", "-halt-on-error", tex_path.name] if compiler else None
    if command is None:
        print(f"LaTeX compiler not found; source saved at {tex_path}")
        return 2
    result = subprocess.run(command, cwd=args.output_dir, capture_output=True, text=True, timeout=300)
    if result.returncode:
        print(result.stdout[-4000:])
        print(result.stderr[-4000:])
        return result.returncode
    print(args.output_dir / "chinese.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
