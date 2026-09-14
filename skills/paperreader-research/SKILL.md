---
name: paperreader-research
description: Discover and analyze computer-science papers for a topic, producing one validated bilingual .paper ZIP artifact per selected paper for the PaperReader viewer.
metadata:
  short-description: Generate bilingual paper reading artifacts
---

# PaperReader Research

Use this skill when the user provides a computer-science research topic and wants curated papers with source text, Simplified Chinese translation, and structured analysis for the PaperReader desktop viewer.

## Workflow

1. Clarify the topic only when it is too broad. Default to 10 papers; honor an explicit count.
2. Search authoritative metadata sources such as OpenAlex, Crossref, Semantic Scholar, arXiv, and DBLP. Prefer official venue pages and open-access full text when verifying claims.
3. Deduplicate by DOI, arXiv identifier, then normalized title plus first author. Rank by topic relevance, configured venue tier, recency/citation context, and full-text availability.
4. Use only legally available open full text or PDFs/HTML supplied by the user. Never bypass a paywall. A paper without full text still gets an artifact with `processing_status: "needs_fulltext"`.
5. Extract ordered sections, figures, and every source-paper table. Preserve the source English PDF, extract original figure pixels, translate section text, figure captions, and table captions into Simplified Chinese, and generate the Chinese PDF with the LaTeX helpers. Keep image-internal text, table headers, table cells, numbers, metric symbols, code identifiers, citations, and figure labels exactly as in the source; do not translate or redraw image/table content.
6. Treat the source paper's layout as a binding constraint for the Chinese PDF: preserve title/author order, abstract placement, section/subsection order, two-column profile when present, figure order, table order, figure captions, table structure, column order, row order, and page/section mappings. Do not produce a freeform summary PDF. Every translated section must correspond to exactly one source section; every extracted figure and table must have a source ID and an insertion point (`section_id` or `after_section_id`).
7. Summarize only evidence in the paper. Fill `analysis.problem`, `analysis.contributions`, `analysis.innovations`, and `analysis.method_summary`. Represent every reported experiment in `experiments`, with what it tests and what it proves. Do not invent experiments, numbers, citations, figure content, table rows, or alt text claims.
8. Package exactly one `<slug>.paper` ZIP per selected paper. It must contain `manifest.json`, `pdf/english.pdf`, `pdf/chinese.pdf`, `tex/chinese.tex`, and figure/table assets when available. Validate it with `scripts/validate_paper.py` before reporting completion.

## Artifact contract

Read [references/artifact-schema.md](references/artifact-schema.md) before writing artifacts. Use [references/venue-tiers.yaml](references/venue-tiers.yaml) for the editable venue ranking. Use `extract_figures.py`, `extract_tables.py`, `prepare_latex_assets.py`, `build_chinese_pdf.py`, and `package_paper.py` for deterministic figure/table/PDF/package steps. Keep uncertainty and missing material in `quality`; do not hide incomplete extraction.

## Inputs and outputs

Accept a topic, optional paper count, optional output directory, and optional user-provided PDF/HTML paths. Match supplied files to candidates by DOI, arXiv ID, or title. The output directory should contain only the selected artifacts unless the user asks for a report.

The viewer accepts a single `.paper` package or recursively scans a directory for `*.paper`.
