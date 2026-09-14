#!/usr/bin/env python3
"""Generate a publication-style, layout-preserving Chinese LaTeX PDF."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def latex_escape(value: str) -> str:
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "$": r"\$", "^": r"\textasciicircum{}", "~": r"\textasciitilde{}"}
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def normalize_table_text(value: str) -> str:
    """Render source LaTeX math markers as readable symbols without translating cells."""
    replacements = {
        r"\uparrow": "↑",
        r"\downarrow": "↓",
        r"\times": "×",
        "^{3}": "³",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def figure_block(figure: dict) -> str:
    path = (figure.get("latex_path") or figure.get("asset_path", "")).removeprefix("assets/")
    caption = latex_escape(figure.get("caption_zh", "") or figure.get("caption_en", ""))
    figure_id = latex_escape(figure.get("id", "figure"))
    if figure.get("status") == "missing" or not path:
        return "\\begin{figure}[tb]\n\\centering\n\\fbox{\\parbox{0.9\\columnwidth}{\\centering 图片 %s 无法提取}}\n\\caption{%s}\\label{fig:%s}\n\\end{figure}" % (figure_id, caption, figure_id)
    return "\\begin{figure}[tb]\n\\centering\n\\includegraphics[width=0.96\\columnwidth]{%s}\n\\caption{%s}\\label{fig:%s}\n\\end{figure}" % (path, caption, figure_id)


def experiment_table(experiments: list[dict]) -> str:
    if not experiments:
        return ""
    rows = []
    for experiment in experiments:
        values = [experiment.get("name", ""), experiment.get("what_it_tests", ""), experiment.get("what_it_proves", ""), experiment.get("result_summary", "")]
        rows.append(" & ".join(latex_escape(value.replace("\n", " ")) for value in values) + r" \\")
    return "\\clearpage\n\\onecolumn\n\\begin{table}[ht]\n\\centering\n\\caption{实验设置与结果摘要}\n\\label{tab:experiments}\n\\begin{tabularx}{0.98\\textwidth}{>{\\raggedright\\arraybackslash}p{0.16\\textwidth}>{\\raggedright\\arraybackslash}p{0.24\\textwidth}>{\\raggedright\\arraybackslash}p{0.25\\textwidth}X}\n\\toprule\n实验 & 验证什么 & 证明什么 & 结果 \\\\ \n\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabularx}\n\\end{table}"


def source_table_block(table: dict, two_column: bool) -> str:
    columns = table.get("columns", [])
    if not columns:
        return ""
    headers = [latex_escape(normalize_table_text(column.get("header_en", ""))) for column in columns]
    rows = []
    for row in table.get("rows", []):
        cells = row.get("cells_en", [])
        cells = list(cells) + [""] * (len(headers) - len(cells))
        rows.append(" & ".join(latex_escape(normalize_table_text(str(cell))) for cell in cells[:len(headers)]) + r" \\")
    column_spec = "X" * len(headers)
    environment = "table*" if two_column else "table"
    width = "0.98\\textwidth" if two_column else "0.98\\linewidth"
    return (
        f"\\begin{{{environment}}}[t]\n\\centering\n"
        f"\\caption{{{latex_escape(table.get('caption_zh') or table.get('caption_en', ''))}}}\n"
        f"\\label{{tab:{latex_escape(table.get('id', 'table'))}}}\n"
        f"\\begin{{tabularx}}{{{width}}}{{{column_spec}}}\n\\toprule\n"
        + " & ".join(headers)
        + r" \\ "
        + "\n\\midrule\n"
        + "\n".join(rows)
        + f"\n\\bottomrule\n\\end{{tabularx}}\n\\end{{{environment}}}"
    )


def compile_pdf(args: argparse.Namespace, tex_path: Path) -> int:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path, help="intermediate manifest with translated_text values")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--font", type=Path, help="bundled .ttf/.otf CJK font")
    parser.add_argument("--compiler", choices=["auto", "latexmk", "xelatex"], default="auto")
    parser.add_argument("--single-column", action="store_true", help="opt out of the source paper's two-column profile")
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tex_path = args.output_dir / "chinese.tex"
    font_line = ""
    if args.font:
        extension = args.font.suffix.lstrip(".") or "ttf"
        font_line = "\\setCJKmainfont[Path=%s/,Extension=.%s]{%s}\n" % (args.font.parent, extension, args.font.stem)

    figures_by_section: dict[str, list[dict]] = {}
    unassigned: list[dict] = []
    for figure in data.get("figures", []):
        section_id = figure.get("section_id") or figure.get("after_section_id")
        if section_id:
            figures_by_section.setdefault(section_id, []).append(figure)
        else:
            unassigned.append(figure)

    tables_by_section: dict[str, list[dict]] = {}
    unassigned_tables: list[dict] = []
    for table in data.get("tables", []):
        section_id = table.get("section_id")
        if section_id:
            tables_by_section.setdefault(section_id, []).append(table)
        else:
            unassigned_tables.append(table)

    body: list[str] = []
    sections = sorted(data.get("sections", []), key=lambda item: item.get("order", 0))
    for index, section in enumerate(sections):
        section_id = section.get("id", f"section-{index}")
        title = latex_escape(section.get("title", ""))
        translated = section.get("translated_text", "")
        if section_id == "abstract" or index == 0:
            body.append("\\begin{abstract}\n%s\n\\end{abstract}" % translated)
        elif section_id != "references":
            body.append("\\section{%s}\n%s" % (title, translated))
        else:
            body.append("\\section*{%s}\n%s" % (title, translated))
        body.extend(figure_block(figure) for figure in figures_by_section.get(section_id, []))
        body.extend(
            source_table_block(
                table,
                data.get("layout_profile", "two-column") == "two-column" and not args.single_column,
            )
            for table in tables_by_section.get(section_id, [])
        )
    if unassigned:
        body.append("\\section*{图表 / Figures}\n" + "\n".join(figure_block(figure) for figure in unassigned))
    if unassigned_tables:
        body.append(
            "\\section*{表格 / Tables}\n"
            + "\n".join(
                source_table_block(
                    table,
                    data.get("layout_profile", "two-column") == "two-column" and not args.single_column,
                )
                for table in unassigned_tables
            )
        )
    table = experiment_table(data.get("experiments", []))
    if table:
        body.append(table)

    two_column = not args.single_column and data.get("layout_profile", "two-column") == "two-column"
    document_class = "\\documentclass[a4paper,10pt]{ctexart}" if two_column else "\\documentclass[a4paper,11pt]{ctexart}"
    layout = "" if not two_column else "\\twocolumn"
    tex = r"""%% PaperReader generated source.
%% Layout constraints: preserve section order, figure order, captions, and the
%% source paper's two-column reading profile. Figures keep original pixels.
%% Text is translated; figure-internal labels are intentionally unchanged.
%s
%s
\usepackage[margin=1.75cm]{geometry}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{array}
\usepackage{caption}
\setlength{\columnsep}{0.65cm}
\hypersetup{hidelinks}
\title{%s}
\author{%s}
\date{%s}
\begin{document}
\maketitle
%s
\end{document}
""" % (document_class, font_line + layout, latex_escape(data["paper"]["title"]), latex_escape(", ".join(data["paper"].get("authors", []))), data["paper"].get("year", ""), "\n\n".join(body))
    tex_path.write_text(tex, encoding="utf-8")
    return compile_pdf(args, tex_path)


if __name__ == "__main__":
    raise SystemExit(main())
