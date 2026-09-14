use serde::Deserialize;
use std::collections::HashMap;

#[derive(Debug, Clone, Deserialize)]
pub struct Manifest {
    pub schema_version: String,
    pub artifact_type: String,
    pub processing_status: String,
    pub paper: Paper,
    #[serde(default)]
    pub sections: Vec<Section>,
    #[serde(default)]
    pub figures: Vec<Figure>,
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
    pub license: String,
    #[serde(default)]
    pub fulltext_source: String,
    pub english_pdf: String,
    pub chinese_pdf: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Section {
    pub id: String,
    pub title: String,
    pub order: usize,
    #[serde(default)]
    pub english_page_start: Option<usize>,
    #[serde(default)]
    pub english_page_end: Option<usize>,
    #[serde(default)]
    pub chinese_page_start: Option<usize>,
    #[serde(default)]
    pub chinese_page_end: Option<usize>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Figure {
    pub id: String,
    pub asset_path: String,
    #[serde(default)]
    pub source_page: Option<usize>,
    #[serde(default)]
    pub english_page: Option<usize>,
    #[serde(default)]
    pub chinese_page: Option<usize>,
    #[serde(default)]
    pub caption_en: String,
    #[serde(default)]
    pub caption_zh: String,
    #[serde(default)]
    pub alt_text_zh: String,
    #[serde(default)]
    pub status: String,
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
    pub missing_figures: Vec<String>,
    #[serde(default)]
    pub figure_extraction_status: String,
    #[serde(default)]
    pub figure_notes: Vec<String>,
    #[serde(default)]
    pub translation_status: String,
    #[serde(default)]
    pub pdf_status: String,
}
