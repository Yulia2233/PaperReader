mod loader;
mod model;
mod ui;

use anyhow::{Context, Result};
use eframe::egui;
use std::path::PathBuf;

fn main() -> Result<()> {
    let input = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .context("usage: paperreader <file-or-directory>")?;
    let papers = loader::load_path(&input)?;
    let title = if papers.len() == 1 {
        papers[0].artifact.paper.title.clone()
    } else {
        format!("PaperReader · {} 篇论文", papers.len())
    };
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1500.0, 920.0])
            .with_min_inner_size([900.0, 600.0]),
        ..Default::default()
    };
    eframe::run_native(
        &title,
        options,
        Box::new(move |cc| Ok(Box::new(ui::PaperReaderApp::new(papers, &cc.egui_ctx)))),
    )
    .map_err(|error| anyhow::anyhow!("failed to start PaperReader: {error}"))?;
    Ok(())
}
