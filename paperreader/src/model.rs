use serde::Deserialize;
use std::collections::HashMap;

#[derive(Debug, Clone, Deserialize)]
pub struct Artifact {
    pub schema_version: String,
    pub processing_status: String,
    pub paper: Paper,
    #[serde(default)]
    pub sections: Vec<Section>,
    pub analysis: Analysis,
    #[serde(default)]
    pub experiments: Vec<Experiment>,
    pub quality: Quality,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Paper {
    pub title: String,
    #[serde(default)]
    pub authors: Vec<String>,
    pub year: i32,
    pub venue: String,
    pub venue_tier: String,
    #[serde(default)]
    pub doi: String,
    #[serde(default)]
    pub identifiers: HashMap<String, String>,
    #[serde(default)]
    pub source_urls: Vec<String>,
    #[serde(default)]
    pub fulltext_source: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Section {
    pub id: String,
    pub title: String,
    pub order: usize,
    #[serde(default)]
    pub source_text: String,
    #[serde(default)]
    pub translated_text: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Analysis {
    #[serde(default)]
    pub problem: String,
    #[serde(default)]
    pub contributions: Vec<String>,
    #[serde(default)]
    pub innovations: Vec<String>,
    #[serde(default)]
    pub method_summary: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Experiment {
    pub name: String,
    pub what_it_tests: String,
    pub what_it_proves: String,
    #[serde(default)]
    pub datasets: Vec<String>,
    #[serde(default)]
    pub baselines: Vec<String>,
    #[serde(default)]
    pub metrics: Vec<String>,
    pub result_summary: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Quality {
    #[serde(default)]
    pub evidence_notes: Vec<String>,
    #[serde(default)]
    pub missing_inputs: Vec<String>,
    #[serde(default)]
    pub translation_status: String,
}
