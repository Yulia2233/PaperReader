# PaperReader

PaperReader has two pieces:

- `skills/paperreader-research/` is a Codex skill that researches computer-science topics and produces one bilingual `<slug>.paper` ZIP package per paper.
- `paperreader/` is a Rust/egui desktop viewer for one package or a directory of packages. It renders the embedded English/Chinese PDFs with PDFium.

## Run the viewer

```bash
cd paperreader
cargo run -- fixtures/sample.paper
# or load a collection
cargo run -- /path/to/paper-artifacts
```

The viewer embeds Noto Sans SC under the SIL Open Font License so Chinese UI text renders on machines without a CJK font. The UI has a paper/section navigator on the left, an English/中文 PDF toggle in the document pane, and structured analysis plus an experiment table on the right. Release bundles must include the matching PDFium library under `resources/pdfium`.

For local development, place the matching PDFium library in `paperreader/resources/pdfium` or set `PAPERREADER_PDFIUM_DIR`; the expected names and release source are documented in `paperreader/resources/pdfium/README.md`.

## Install the skill locally

The tracked skill package can be copied into the Codex skill directory:

```bash
cp -R skills/paperreader-research ~/.codex/skills/paperreader-research
```

Use it with a topic, for example: `Use $paperreader-research to find papers about retrieval-augmented generation.` The skill uses open metadata/full text or user-supplied PDFs, extracts figures, translates captions, compiles the Chinese LaTeX PDF, and never bypasses paywalls.

## Validate artifacts

```bash
python3 skills/paperreader-research/scripts/validate_paper.py paperreader/fixtures/sample.paper
```

The ZIP/manifest contract is documented in `skills/paperreader-research/references/artifact-schema.md`; venue tiers are editable in `venue-tiers.yaml`. Figure extraction helpers live in `skills/paperreader-research/scripts/`.
