#!/usr/bin/env python3
"""Generate a publication-style, layout-preserving Chinese PDF."""
from __future__ import annotations

import argparse
import html
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


def _reportlab_font_path(args: argparse.Namespace) -> Path | None:
    candidates = [
        args.font,
        Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NotoSansSC.ttf",
        Path(__file__).resolve().parents[3] / "paperreader" / "assets" / "fonts" / "NotoSansSC.ttf",
    ]
    return next((path.resolve() for path in candidates if path and path.is_file()), None)


def _reportlab_image_path(args: argparse.Namespace, figure: dict) -> Path | None:
    relative_paths = [figure.get("render_path"), figure.get("latex_path"), figure.get("asset_path")]
    roots = [args.output_dir, args.manifest.resolve().parent]
    for relative in relative_paths:
        if not relative:
            continue
        path = Path(relative)
        if path.is_absolute() and path.is_file():
            return path
        for root in roots:
            candidate = root / path
            if candidate.is_file():
                return candidate
            if path.parts and path.parts[0] == "assets":
                candidate = root / Path(*path.parts[1:])
                if candidate.is_file():
                    return candidate
    return None


def build_reportlab_pdf(args: argparse.Namespace, data: dict) -> int:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            BaseDocTemplate,
            Frame,
            FrameBreak,
            Image,
            KeepTogether,
            LongTable,
            NextPageTemplate,
            PageBreak,
            PageTemplate,
            Paragraph,
            Spacer,
            TableStyle,
        )
    except ImportError:
        print("ReportLab is required: python3 -m pip install --user 'reportlab>=4,<5'")
        return 2

    font_path = _reportlab_font_path(args)
    if font_path is None:
        print("CJK font not found; pass --font or bundle assets/fonts/NotoSansSC.ttf")
        return 2

    font_name = "PaperReaderNotoSansSC"
    pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    pdfmetrics.registerFontFamily(
        font_name,
        normal=font_name,
        bold=font_name,
        italic=font_name,
        boldItalic=font_name,
    )

    page_width, page_height = A4
    left_margin = right_margin = 1.35 * cm
    top_margin = 1.25 * cm
    bottom_margin = 1.35 * cm
    column_gap = 0.55 * cm
    body_width = page_width - left_margin - right_margin
    column_width = (body_width - column_gap) / 2
    two_column = not args.single_column and data.get("layout_profile", "two-column") == "two-column"

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "ChineseBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=8.6 if two_column else 10.2,
        leading=13.2 if two_column else 15.8,
        spaceAfter=6,
        wordWrap="CJK",
        textColor=colors.HexColor("#222222"),
    )
    abstract_style = ParagraphStyle(
        "AbstractBody",
        parent=body_style,
        fontSize=8.4 if two_column else 10,
        leading=12.8 if two_column else 15.4,
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=13 if two_column else 15,
        leading=17,
        spaceBefore=10,
        spaceAfter=7,
        keepWithNext=True,
        wordWrap="CJK",
        textColor=colors.HexColor("#111111"),
    )
    title_style = ParagraphStyle(
        "PaperTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=16,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=10,
        wordWrap="CJK",
    )
    author_style = ParagraphStyle(
        "Authors",
        parent=body_style,
        fontSize=9.5,
        leading=13,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    caption_style = ParagraphStyle(
        "Caption",
        parent=body_style,
        fontSize=7.4,
        leading=10.2,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#444444"),
        spaceBefore=3,
        spaceAfter=8,
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=body_style,
        fontSize=6.7,
        leading=8.4,
        spaceAfter=0,
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=table_cell_style,
        alignment=TA_CENTER,
        textColor=colors.white,
    )

    def markup(value: object) -> str:
        return html.escape(str(value or "")).replace("\n", "<br/>")

    def add_text(story: list, value: str, style: ParagraphStyle = body_style) -> None:
        for paragraph in (part.strip() for part in value.split("\n\n")):
            if paragraph:
                story.append(Paragraph(markup(paragraph), style))

    def figure_flowables(figure: dict, full_width: bool = False) -> list:
        caption = figure.get("caption_zh") or figure.get("caption_en") or figure.get("id", "figure")
        image_path = _reportlab_image_path(args, figure)
        if figure.get("status") == "missing" or image_path is None:
            placeholder = Paragraph(
                markup(f"图片 {figure.get('id', 'figure')} 无法提取"),
                ParagraphStyle("MissingFigure", parent=caption_style, borderWidth=0.5, borderPadding=12),
            )
            return [placeholder, Paragraph(markup(caption), caption_style)]
        image = Image(str(image_path))
        max_width = body_width if full_width or not two_column else column_width
        max_height = 10.5 * cm if full_width or not two_column else 6.2 * cm
        scale = min(max_width / image.imageWidth, max_height / image.imageHeight, 1.0)
        image.drawWidth = image.imageWidth * scale
        image.drawHeight = image.imageHeight * scale
        image.hAlign = "CENTER"
        return [image, Paragraph(markup(caption), caption_style)]

    def table_flowable(table: dict, experiments: bool = False) -> LongTable:
        if experiments:
            headers = ["实验", "验证什么", "证明什么", "结果"]
            rows = [
                [
                    experiment.get("name", ""),
                    experiment.get("what_it_tests", ""),
                    experiment.get("what_it_proves", ""),
                    experiment.get("result_summary", ""),
                ]
                for experiment in table
            ]
            weights = [1.15, 2.0, 2.0, 2.35]
        else:
            columns = table.get("columns", [])
            headers = [normalize_table_text(column.get("header_en", "")) for column in columns]
            rows = [
                [normalize_table_text(cell) for cell in row.get("cells_en", [])]
                for row in table.get("rows", [])
            ]
            weights = [1.0] * max(1, len(headers))
        total_weight = sum(weights)
        widths = [body_width * weight / total_weight for weight in weights]
        wrapped = [[Paragraph(markup(cell), table_header_style) for cell in headers]]
        wrapped.extend([[Paragraph(markup(cell), table_cell_style) for cell in row] for row in rows])
        result = LongTable(wrapped, colWidths=widths, repeatRows=1, hAlign="CENTER", splitByRow=1)
        result.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#94a3b8")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return result

    output_path = args.output_dir / "chinese.pdf"
    document = BaseDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
        title=data.get("paper", {}).get("title", ""),
        author=", ".join(data.get("paper", {}).get("authors", [])),
    )

    def draw_page_number(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(font_name, 7.5)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawCentredString(page_width / 2, 0.65 * cm, str(doc.page))
        canvas.restoreState()

    body_height = page_height - top_margin - bottom_margin
    full_frame = Frame(left_margin, bottom_margin, body_width, body_height, id="full", showBoundary=0)
    if two_column:
        title_height = 4.4 * cm
        column_height = body_height - title_height - 0.25 * cm
        first_frames = [
            Frame(left_margin, page_height - top_margin - title_height, body_width, title_height, id="title", showBoundary=0),
            Frame(left_margin, bottom_margin, column_width, column_height, id="first-left", showBoundary=0),
            Frame(left_margin + column_width + column_gap, bottom_margin, column_width, column_height, id="first-right", showBoundary=0),
        ]
        column_frames = [
            Frame(left_margin, bottom_margin, column_width, body_height, id="left", showBoundary=0),
            Frame(left_margin + column_width + column_gap, bottom_margin, column_width, body_height, id="right", showBoundary=0),
        ]
        document.addPageTemplates(
            [
                PageTemplate("first", first_frames, onPage=draw_page_number, autoNextPageTemplate="two"),
                PageTemplate("two", column_frames, onPage=draw_page_number),
                PageTemplate("full", [full_frame], onPage=draw_page_number),
            ]
        )
        body_template = "two"
    else:
        document.addPageTemplates([PageTemplate("full", [full_frame], onPage=draw_page_number)])
        body_template = "full"

    story: list = []
    paper = data.get("paper", {})
    story.append(Paragraph(markup(paper.get("title_zh") or paper.get("title", "")), title_style))
    story.append(Paragraph(markup(", ".join(paper.get("authors", []))), author_style))
    story.append(Paragraph(markup(paper.get("year", "")), author_style))
    if two_column:
        story.append(FrameBreak())

    figures_by_section: dict[str, list[dict]] = {}
    unassigned_figures: list[dict] = []
    for figure in data.get("figures", []):
        section_id = figure.get("section_id") or figure.get("after_section_id")
        if section_id:
            figures_by_section.setdefault(section_id, []).append(figure)
        else:
            unassigned_figures.append(figure)
    tables_by_section: dict[str, list[dict]] = {}
    unassigned_tables: list[dict] = []
    for table in data.get("tables", []):
        section_id = table.get("section_id")
        if section_id:
            tables_by_section.setdefault(section_id, []).append(table)
        else:
            unassigned_tables.append(table)

    def add_full_width_tables(
        blocks: list[tuple[str, LongTable]],
        *,
        start_new_page: bool = True,
    ) -> None:
        if not blocks:
            return
        if two_column and start_new_page:
            story.extend([NextPageTemplate("full"), PageBreak()])
        for index, (caption, table) in enumerate(blocks):
            story.extend([Paragraph(markup(caption), caption_style), table])
            if index + 1 < len(blocks):
                story.append(Spacer(1, 14))
        if two_column:
            story.extend([NextPageTemplate(body_template), PageBreak()])
        else:
            story.append(Spacer(1, 10))

    def add_full_width_figures(figures: list[dict], *, resume_body: bool = True) -> None:
        if not figures:
            return
        if two_column:
            story.extend([NextPageTemplate("full"), PageBreak()])
        for figure in figures:
            story.append(KeepTogether(figure_flowables(figure, full_width=True)))
        if two_column and resume_body:
            story.extend([NextPageTemplate(body_template), PageBreak()])
        else:
            story.append(Spacer(1, 10))

    sections = sorted(data.get("sections", []), key=lambda item: item.get("order", 0))
    for index, section in enumerate(sections):
        section_id = section.get("id", f"section-{index}")
        if section_id == "abstract" or index == 0:
            story.append(Paragraph("摘要", section_style))
            add_text(story, section.get("translated_text", ""), abstract_style)
        else:
            story.append(Paragraph(markup(section.get("title", "")), section_style))
            add_text(story, section.get("translated_text", ""))
        section_figures = figures_by_section.get(section_id, [])
        for figure in (item for item in section_figures if not item.get("full_width")):
            story.append(KeepTogether(figure_flowables(figure)))
        section_tables = tables_by_section.get(section_id, [])
        full_width_figures = [item for item in section_figures if item.get("full_width")]
        add_full_width_figures(full_width_figures, resume_body=not section_tables)
        add_full_width_tables(
            [
                (table.get("caption_zh") or table.get("caption_en", ""), table_flowable(table))
                for table in section_tables
            ],
            start_new_page=not full_width_figures,
        )

    if unassigned_figures:
        story.append(Paragraph("图表 / Figures", section_style))
        for figure in unassigned_figures:
            story.append(KeepTogether(figure_flowables(figure, full_width=bool(figure.get("full_width")))))
    add_full_width_tables(
        [
            (table.get("caption_zh") or table.get("caption_en", ""), table_flowable(table))
            for table in unassigned_tables
        ]
    )
    if data.get("experiments"):
        add_full_width_tables(
            [("实验设置与结果摘要", table_flowable(data["experiments"], experiments=True))]
        )

    try:
        document.build(story)
    except Exception as exc:
        print(f"ReportLab PDF generation failed: {exc}")
        return 1
    print(output_path)
    return 0


def compile_pdf(args: argparse.Namespace, tex_path: Path) -> int:
    compiler_name = args.compiler
    if compiler_name == "auto":
        compiler_name = next(
            (name for name in ("latexmk", "xelatex", "tectonic") if shutil.which(name)),
            None,
        )
    compiler = shutil.which(compiler_name) if compiler_name else None
    if compiler is None:
        requested = "latexmk, xelatex, or tectonic" if args.compiler == "auto" else args.compiler
        print(f"LaTeX compiler not found ({requested}); source saved at {tex_path}")
        return 2
    if compiler_name == "latexmk":
        command = [compiler, "-xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
    elif compiler_name == "xelatex":
        command = [compiler, "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
    else:
        command = [compiler, "--keep-logs", "--outdir", str(args.output_dir), tex_path.name]
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
    parser.add_argument("--renderer", choices=["reportlab", "latex"], default="reportlab")
    parser.add_argument("--compiler", choices=["auto", "latexmk", "xelatex", "tectonic"], default="auto", help="compiler for the optional LaTeX renderer")
    parser.add_argument("--single-column", action="store_true", help="opt out of the source paper's two-column profile")
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.renderer == "reportlab":
        return build_reportlab_pdf(args, data)
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
