---
name: paperreader-research
description: Read, translate, and analyze computer-science papers for PaperReader. Use when the user invokes `$paperreader-research` or clearly asks to use the 阅读论文 skill, 论文阅读 skill, PaperReader skill, or this paper-reading skill to process a supplied paper or research topic. Do not trigger for generic PDF, translation, or paper questions that do not name or clearly refer to the skill.
metadata:
  short-description: Generate bilingual paper reading artifacts
---

# PaperReader Research

Use this skill when the user provides a computer-science research topic and wants curated papers with source text, Simplified Chinese translation, and structured analysis for the PaperReader desktop viewer.

Activate this skill when the current user message either invokes `$paperreader-research` or clearly asks to use the 阅读论文 skill, 论文阅读 skill, PaperReader skill, or “这个阅读论文 skill” for the paper or topic at hand. Phrases such as “使用阅读论文 skill 对这个论文进行处理”, “用论文阅读 skill 翻译这篇论文”, and “用 PaperReader skill 阅读这个 PDF” count as intentional activation. Do not activate merely because a request happens to involve a paper, PDF, translation, summary, or literature search without naming or clearly referring to this skill.

## Workflow

1. Clarify the topic only when it is too broad. Default to 10 papers; honor an explicit count.
2. Search authoritative metadata sources such as OpenAlex, Crossref, Semantic Scholar, arXiv, and DBLP. Prefer official venue pages and open-access full text when verifying claims.
3. Deduplicate by DOI, arXiv identifier, then normalized title plus first author. Rank by topic relevance, configured venue tier, recency/citation context, and full-text availability.
4. Use only legally available open full text or PDFs/HTML supplied by the user. Never bypass a paywall. A paper without full text still gets an artifact with `processing_status: "needs_fulltext"`.
5. Extract ordered sections, figures, and every source-paper table. Preserve the source English PDF, extract original figure pixels, translate section text, figure captions, and table captions into Simplified Chinese, and generate the Chinese PDF with `scripts/build_chinese_pdf.py`. The default ReportLab renderer uses the bundled CJK font and does not require LaTeX. Keep image-internal text, table headers, table cells, numbers, metric symbols, code identifiers, citations, and figure labels exactly as in the source; do not translate or redraw image/table content.
6. Treat the source paper's layout as a binding constraint for the Chinese PDF: preserve title/author order, abstract placement, section/subsection order, two-column profile when present, figure order, table order, figure captions, table structure, column order, row order, and page/section mappings. Do not produce a freeform summary PDF. Every translated section must correspond to exactly one source section; every extracted figure and table must have a source ID and an insertion point (`section_id` or `after_section_id`).
7. Summarize only evidence in the paper. Fill `analysis.problem`, `analysis.contributions`, `analysis.innovations`, and `analysis.method_summary`. Represent every reported experiment in `experiments`, with what it tests and what it proves. Do not invent experiments, numbers, citations, figure content, table rows, or alt text claims.
8. Package exactly one `<slug>.paper` ZIP per selected paper. It must contain `manifest.json`, `pdf/english.pdf`, `pdf/chinese.pdf`, and figure/table assets when available. Validate it with `scripts/validate_paper.py` before reporting completion.
9. After validation, run `scripts/organize_paper_output.py` to create a new per-paper directory. Copy the source PDF, translated PDF, and validated `.paper` package into that directory. Never move or delete the user's source PDF, and never overwrite an existing paper directory.

## Artifact contract

Read [references/artifact-schema.md](references/artifact-schema.md) before writing artifacts. Use [references/venue-tiers.yaml](references/venue-tiers.yaml) for the editable venue ranking. Use `extract_figures.py`, `extract_tables.py`, `prepare_pdf_assets.py`, `build_chinese_pdf.py`, `package_paper.py`, and `organize_paper_output.py` for deterministic figure/table/PDF/package/output steps. `build_chinese_pdf.py` defaults to ReportLab; use `--renderer latex` only for legacy compatibility. Install the renderer dependency from `requirements.txt`; PDF figure extraction additionally requires the `pdfimages` command from Poppler. Keep uncertainty and missing material in `quality`; do not hide incomplete extraction.

## Inputs and outputs

Accept a topic, optional paper count, optional output root, and optional user-provided PDF/HTML paths. Match supplied files to candidates by DOI, arXiv ID, or title. Default the output root to `~/Downloads/论文` unless the user supplies another directory.

Create one new directory per paper under the output root, preferably named `<year>-<short-title-or-slug>`. Inside it, place exactly these user-facing deliverables:

- `论文原文.pdf`: a copy of the source PDF.
- `中文翻译.pdf`: the generated Chinese PDF.
- `<slug>.paper`: the validated PaperReader package.

If the target directory already exists, append `-2`, `-3`, and so on. Do not overwrite an earlier result. Temporary extraction and build files must stay outside the final paper directory.

The viewer accepts a single `.paper` package or recursively scans a directory for `*.paper`.
