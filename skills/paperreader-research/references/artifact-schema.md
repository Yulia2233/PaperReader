# PaperReader artifact schema v1.0

Each file is UTF-8 JSON with the `.paper.json` suffix. It is self-contained so the Rust viewer has no network dependency.

Required top-level fields:

- `schema_version`: exactly `"1.0"`.
- `processing_status`: `complete` or `needs_fulltext`.
- `paper`: title, authors, year, venue, venue tier, identifiers, source URLs, and full-text source.
- `sections`: ordered section objects with `id`, `title`, zero-based `order`, `source_text`, and `translated_text`.
- `analysis`: problem, contributions, innovations, and method summary.
- `experiments`: rows for the viewer table. `what_it_tests` and `what_it_proves` are required even for theoretical or survey papers.
- `quality`: evidence notes, missing inputs, and translation status.

The canonical object is:

```json
{
  "schema_version": "1.0",
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
    "fulltext_source": ""
  },
  "sections": [],
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

For unavailable full text, preserve metadata and set `processing_status` to `needs_fulltext`; put the requested file or URL in `quality.missing_inputs`.
