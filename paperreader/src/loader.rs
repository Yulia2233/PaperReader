use crate::model::Artifact;
use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

#[derive(Debug, Clone)]
pub struct LoadedArtifact {
    pub path: PathBuf,
    pub artifact: Artifact,
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
            .filter(|candidate| candidate.to_string_lossy().ends_with(".paper.json"))
            .collect()
    } else {
        anyhow::bail!("input does not exist: {}", path.display());
    };

    let mut artifacts = Vec::new();
    for candidate in paths {
        let content = std::fs::read_to_string(&candidate)
            .with_context(|| format!("reading {}", candidate.display()))?;
        let artifact: Artifact = serde_json::from_str(&content)
            .with_context(|| format!("parsing {}", candidate.display()))?;
        if artifact.schema_version != "1.0" {
            anyhow::bail!(
                "{} uses unsupported schema {}",
                candidate.display(),
                artifact.schema_version
            );
        }
        validate_artifact(&artifact)
            .with_context(|| format!("validating {}", candidate.display()))?;
        artifacts.push(LoadedArtifact {
            path: candidate,
            artifact,
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
        anyhow::bail!("no .paper.json artifacts found in {}", path.display());
    }
    Ok(artifacts)
}

fn validate_artifact(artifact: &Artifact) -> Result<()> {
    if artifact.paper.title.trim().is_empty() {
        anyhow::bail!("paper.title is empty");
    }
    if !matches!(
        artifact.processing_status.as_str(),
        "complete" | "needs_fulltext"
    ) {
        anyhow::bail!("invalid processing_status");
    }
    for (expected, section) in artifact.sections.iter().enumerate() {
        if section.order != expected {
            anyhow::bail!("section order must start at zero and be contiguous");
        }
    }
    if artifact.processing_status == "needs_fulltext" && artifact.quality.missing_inputs.is_empty()
    {
        anyhow::bail!("needs_fulltext artifact has no missing_inputs");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_missing_path() {
        let error = load_path(Path::new("does-not-exist.paper.json")).unwrap_err();
        assert!(error.to_string().contains("does not exist"));
    }

    #[test]
    fn loads_fixture_and_preserves_section_order() {
        let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("fixtures/sample.paper.json");
        let papers = load_path(&path).unwrap();
        assert_eq!(papers.len(), 1);
        assert_eq!(papers[0].artifact.sections[0].order, 0);
        assert!(!papers[0].artifact.experiments.is_empty());
    }
}
