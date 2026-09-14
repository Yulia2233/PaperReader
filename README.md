# PaperReader

PaperReader has two pieces:

- `skills/paperreader-research/` is a Codex skill that researches computer-science topics and produces one bilingual `<slug>.paper.json` artifact per paper.
- `paperreader/` is a Rust/egui desktop viewer for one artifact or a directory of artifacts.

## Run the viewer

```bash
cd paperreader
cargo run -- fixtures/sample.paper.json
# or load a collection
cargo run -- /path/to/paper-artifacts
```

The viewer embeds Noto Sans SC under the SIL Open Font License so Chinese text renders on machines without a CJK font. The UI has a paper/section navigator on the left, source/Chinese toggle in the document pane, and structured analysis plus an experiment table on the right.

## Install the skill locally

The tracked skill package can be copied into the Codex skill directory:

```bash
cp -R skills/paperreader-research ~/.codex/skills/paperreader-research
```

Use it with a topic, for example: `Use $paperreader-research to find papers about retrieval-augmented generation.` The skill uses open metadata/full text or user-supplied PDFs and never bypasses paywalls.

## Validate artifacts

```bash
python3 skills/paperreader-research/scripts/validate_artifact.py paperreader/fixtures/sample.paper.json
```

The JSON contract is documented in `skills/paperreader-research/references/artifact-schema.md`; venue tiers are editable in `venue-tiers.yaml`.
