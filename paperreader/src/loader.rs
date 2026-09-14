use crate::model::Manifest;
use anyhow::{Context, Result};
use std::io::{Cursor, Read};
use std::path::{Path, PathBuf};
use tempfile::TempDir;
use walkdir::WalkDir;
use zip::ZipArchive;

#[derive(Debug)]
pub struct LoadedArtifact {
    pub path: PathBuf,
    pub artifact: Manifest,
    extracted_root: TempDir,
}

impl LoadedArtifact {
    pub fn pdf_path(&self, chinese: bool) -> Option<PathBuf> {
        let relative = if chinese {
            &self.artifact.paper.chinese_pdf
        } else {
            &self.artifact.paper.english_pdf
        };
        let path = self.extracted_root.path().join(relative);
        path.is_file().then_some(path)
    }
}

pub fn load_path(path: &Path) -> Result<Vec<LoadedArtifact>> {
    let paths = if path.is_file() {
        vec![path.to_path_buf()]
    } else if path.is_dir() {
        WalkDir::new(path)
            .into_iter()
            .filter_map(|entry| entry.ok())
            .filter(|entry| entry.file_type().is_file())
            .map(|entry| entry.into_path())
            .filter(|candidate| candidate.extension().is_some_and(|ext| ext == "paper"))
            .collect()
    } else {
        anyhow::bail!("input does not exist: {}", path.display());
    };

    let mut artifacts = Vec::new();
    for candidate in paths {
        let content = std::fs::read(&candidate)
            .with_context(|| format!("reading {}", candidate.display()))?;
        let (artifact, extracted_root) =
            read_package(&content).with_context(|| format!("loading {}", candidate.display()))?;
        artifacts.push(LoadedArtifact {
            path: candidate,
            artifact,
            extracted_root,
        });
    }
    artifacts.sort_by(|left, right| {
        left.artifact
            .paper
            .title
            .to_lowercase()
            .cmp(&right.artifact.paper.title.to_lowercase())
    });
    if artifacts.is_empty() {
        anyhow::bail!("no .paper packages found in {}", path.display());
    }
    Ok(artifacts)
}

fn read_package(content: &[u8]) -> Result<(Manifest, TempDir)> {
    let mut archive = ZipArchive::new(Cursor::new(content)).context("opening .paper ZIP")?;
    let mut manifest_text = String::new();
    for index in 0..archive.len() {
        let mut entry = archive.by_index(index).context("reading ZIP entry")?;
        let name = entry.name().replace('\\', "/");
        if !is_safe_member(&name) {
            anyhow::bail!("unsafe ZIP member: {name}");
        }
        if name == "manifest.json" {
            entry
                .read_to_string(&mut manifest_text)
                .context("reading manifest.json")?;
        }
    }
    if manifest_text.is_empty() {
        anyhow::bail!("manifest.json is missing");
    }
    let artifact: Manifest =
        serde_json::from_str(&manifest_text).context("parsing manifest.json")?;
    validate_artifact(&artifact)?;
    let root = tempfile::tempdir().context("creating package cache")?;
    let mut archive = ZipArchive::new(Cursor::new(content)).context("reopening .paper ZIP")?;
    for index in 0..archive.len() {
        let mut entry = archive.by_index(index).context("reading ZIP entry")?;
        let name = entry.name().replace('\\', "/");
        if !is_safe_member(&name) || entry.is_dir() {
            continue;
        }
        let target = root.path().join(&name);
        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let mut output = std::fs::File::create(target)?;
        std::io::copy(&mut entry, &mut output)?;
    }
    if artifact.processing_status == "complete" {
        for pdf in [&artifact.paper.english_pdf, &artifact.paper.chinese_pdf] {
            if !root.path().join(pdf).is_file() {
                anyhow::bail!("required PDF is missing: {pdf}");
            }
        }
    }
    Ok((artifact, root))
}

fn is_safe_member(name: &str) -> bool {
    let path = Path::new(name);
    !path.is_absolute() && !name.split('/').any(|part| part == "..")
}

fn validate_artifact(artifact: &Manifest) -> Result<()> {
    if artifact.schema_version != "2.0" || artifact.artifact_type != "paperreader" {
        anyhow::bail!("unsupported .paper schema");
    }
    if !matches!(
        artifact.processing_status.as_str(),
        "complete" | "needs_fulltext" | "needs_pdf_compile"
    ) {
        anyhow::bail!("invalid processing_status");
    }
    if artifact.paper.title.trim().is_empty() {
        anyhow::bail!("paper.title is empty");
    }
    for (expected, section) in artifact.sections.iter().enumerate() {
        if section.order != expected {
            anyhow::bail!("section order must start at zero and be contiguous");
        }
        for page in [
            section.english_page_start,
            section.english_page_end,
            section.chinese_page_start,
            section.chinese_page_end,
        ]
        .into_iter()
        .flatten()
        {
            if page == 0 {
                anyhow::bail!("page mappings must start at one");
            }
        }
    }
    for figure in &artifact.figures {
        if !matches!(
            figure.status.as_str(),
            "ready" | "fallback_page_render" | "missing"
        ) {
            anyhow::bail!("invalid figure status: {}", figure.status);
        }
        if let Some(page) = figure.source_page {
            if page == 0 {
                anyhow::bail!("figure source pages start at one");
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_missing_path() {
        let error = load_path(Path::new("does-not-exist.paper")).unwrap_err();
        assert!(error.to_string().contains("does not exist"));
    }

    #[test]
    fn rejects_unsafe_member_name() {
        assert!(!is_safe_member("../manifest.json"));
        assert!(!is_safe_member("/tmp/file"));
        assert!(is_safe_member("pdf/english.pdf"));
    }

    #[test]
    fn loads_fixture_and_exposes_both_pdfs() {
        let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("fixtures/sample.paper");
        let papers = load_path(&path).unwrap();
        assert_eq!(papers.len(), 1);
        assert!(papers[0].pdf_path(false).is_some());
        assert!(papers[0].pdf_path(true).is_some());
    }
}
