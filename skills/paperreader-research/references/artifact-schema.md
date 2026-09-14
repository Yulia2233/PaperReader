# PaperReader artifact schema v2.0

Each file is a ZIP archive with the `.paper` suffix. Its `manifest.json` is UTF-8 JSON and the archive is self-contained so the Rust viewer has no network dependency.

Required top-level fields:

- `schema_version`: exactly `"2.0"`; `artifact_type` is `"paperreader"`.
- `processing_status`: `complete`, `needs_fulltext`, or `needs_pdf_compile`.
- `paper`: title, authors, year, venue, venue tier, identifiers, source URLs, license, and PDF paths.
- `sections`: ordered section objects with `id`, `title`, zero-based `order`, and optional English/Chinese page mappings.
- `figures`: figure metadata, source page, captions, alt text, extraction status, and archive asset path.
- `analysis`: problem, contributions, innovations, and method summary.
- `experiments`: rows for the viewer table. `what_it_tests` and `what_it_proves` are required even for theoretical or survey papers.
- `quality`: evidence notes, missing inputs, and translation status.

The canonical object is:

```json
{
  "schema_version": "2.0",
  "artifact_type": "paperreader",
  "processing_status": "complete",
  "paper": {
    "title": "",
    "authors": [],
    "year": 0,
    "venue": "",
    "venue_tier": "tier_1",
    "doi": "",
    "identifiers": {},
    "source_urls": [],
    "fulltext_source": "",
    "english_pdf": "pdf/english.pdf",
    "chinese_pdf": "pdf/chinese.pdf"
  },
  "sections": [],
  "figures": [],
  "analysis": {
    "problem": "",
    "contributions": [],
    "innovations": [],
    "method_summary": ""
  },
  "experiments": [],
  "quality": {
    "evidence_notes": [],
    "missing_inputs": [],
    "translation_status": "complete"
  }
}
```

For unavailable full text, preserve metadata and set `processing_status` to `needs_fulltext`; put the requested file or URL in `quality.missing_inputs`. If LaTeX is unavailable, preserve `tex/chinese.tex` and set `processing_status` to `needs_pdf_compile`; do not create a fake PDF.
