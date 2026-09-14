use crate::loader::LoadedArtifact;
use eframe::egui::{
    self, Align, Color32, FontData, FontDefinitions, FontFamily, Layout, RichText, ScrollArea,
    TextureHandle, TextureOptions,
};
use pdfium_render::prelude::*;
use std::collections::HashMap;
use std::path::PathBuf;

pub struct PaperReaderApp {
    papers: Vec<LoadedArtifact>,
    selected: usize,
    show_translation: bool,
    selected_section: Option<String>,
    current_page: usize,
    textures: HashMap<String, TextureHandle>,
    pdfium: Option<Pdfium>,
    pdf_error: Option<String>,
}

impl PaperReaderApp {
    pub fn new(papers: Vec<LoadedArtifact>, ctx: &egui::Context) -> Self {
        let mut fonts = FontDefinitions::default();
        fonts.font_data.insert(
            "noto_sans_sc".into(),
            FontData::from_owned(include_bytes!("../assets/fonts/NotoSansSC.ttf").to_vec()).into(),
        );
        fonts
            .families
            .get_mut(&FontFamily::Proportional)
            .unwrap()
            .insert(0, "noto_sans_sc".into());
        fonts
            .families
            .get_mut(&FontFamily::Monospace)
            .unwrap()
            .insert(0, "noto_sans_sc".into());
        ctx.set_fonts(fonts);
        let (pdfium, pdf_error) = bind_pdfium();
        Self {
            papers,
            selected: 0,
            show_translation: true,
            selected_section: None,
            current_page: 0,
            textures: HashMap::new(),
            pdfium,
            pdf_error,
        }
    }

    fn current(&self) -> &LoadedArtifact {
        &self.papers[self.selected]
    }
    fn current_page_number(&self) -> usize {
        self.current_page + 1
    }
    fn page_for_section(&self, section_id: &str) -> Option<usize> {
        self.current()
            .artifact
            .sections
            .iter()
            .find(|s| s.id == section_id)
            .and_then(|s| {
                if self.show_translation {
                    s.chinese_page_start
                } else {
                    s.english_page_start
                }
            })
            .map(|page| page.saturating_sub(1))
    }
    fn current_pdf(&self) -> Option<PathBuf> {
        self.current().pdf_path(self.show_translation)
    }

    fn list_panel(&mut self, ui: &mut egui::Ui) {
        ui.heading("论文库");
        ui.separator();
        for index in 0..self.papers.len() {
            let selected = index == self.selected;
            let title = self.papers[index].artifact.paper.title.clone();
            if ui.selectable_label(selected, title).clicked() {
                self.selected = index;
                self.current_page = 0;
                self.selected_section = None;
                self.textures.clear();
            }
        }
        ui.add_space(12.0);
        ui.label(RichText::new("章节").strong());
        let sections: Vec<(String, String)> = self
            .current()
            .artifact
            .sections
            .iter()
            .map(|s| (s.id.clone(), s.title.clone()))
            .collect();
        for (id, title) in sections {
            if ui
                .selectable_label(self.selected_section.as_deref() == Some(&id), title)
                .clicked()
            {
                self.selected_section = Some(id.clone());
                if let Some(page) = self.page_for_section(&id) {
                    self.current_page = page;
                }
            }
        }
    }

    fn render_page(&mut self, ctx: &egui::Context, page: usize) -> Option<TextureHandle> {
        let pdf_path = self.current_pdf()?;
        let key = format!("{}:{}:{}", self.selected, self.show_translation, page);
        if let Some(texture) = self.textures.get(&key) {
            return Some(texture.clone());
        }
        let pdfium = self.pdfium.as_ref()?;
        let document = match pdfium.load_pdf_from_file(&pdf_path, None) {
            Ok(document) => document,
            Err(error) => {
                self.pdf_error = Some(format!("打开 PDF 失败：{error}"));
                return None;
            }
        };
        let page_count = document.pages().len();
        if page >= page_count as usize {
            return None;
        }
        let rendered = match document.pages().get(page as i32) {
            Ok(page) => {
                match page.render_with_config(&PdfRenderConfig::new().set_target_width(1000)) {
                    Ok(bitmap) => match bitmap.as_image() {
                        Ok(image) => image.to_rgba8(),
                        Err(error) => {
                            self.pdf_error = Some(format!("渲染 PDF 页面失败：{error}"));
                            return None;
                        }
                    },
                    Err(error) => {
                        self.pdf_error = Some(format!("渲染 PDF 页面失败：{error}"));
                        return None;
                    }
                }
            }
            Err(error) => {
                self.pdf_error = Some(format!("读取 PDF 页面失败：{error}"));
                return None;
            }
        };
        let size = [rendered.width() as usize, rendered.height() as usize];
        let color_image = egui::ColorImage::from_rgba_unmultiplied(size, rendered.as_raw());
        let texture = ctx.load_texture(key.clone(), color_image, TextureOptions::LINEAR);
        self.textures.insert(key, texture.clone());
        Some(texture)
    }

    fn document_panel(&mut self, ctx: &egui::Context, ui: &mut egui::Ui) {
        let paper = &self.current().artifact.paper;
        let title = paper.title.clone();
        let authors = paper.authors.join(", ");
        let venue = paper.venue.clone();
        let year = paper.year;
        ui.horizontal(|ui| {
            ui.heading(title);
            ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                if ui.selectable_label(self.show_translation, "中文").clicked() {
                    self.show_translation = true;
                    self.current_page = self
                        .page_for_section(self.selected_section.as_deref().unwrap_or(""))
                        .unwrap_or(self.current_page);
                    self.textures.clear();
                }
                if ui
                    .selectable_label(!self.show_translation, "English")
                    .clicked()
                {
                    self.show_translation = false;
                    self.current_page = self
                        .page_for_section(self.selected_section.as_deref().unwrap_or(""))
                        .unwrap_or(self.current_page);
                    self.textures.clear();
                }
            });
        });
        ui.label(format!(
            "{} · {} · {} · 第 {} 页",
            authors,
            venue,
            year,
            self.current_page_number()
        ));
        ui.separator();
        ui.horizontal(|ui| {
            if ui.button("上一页").clicked() && self.current_page > 0 {
                self.current_page -= 1;
            }
            if ui.button("下一页").clicked() {
                self.current_page += 1;
            }
            ui.label(if self.show_translation {
                "中文 PDF"
            } else {
                "English PDF"
            });
        });
        if let Some(error) = &self.pdf_error {
            ui.colored_label(Color32::RED, error);
        }
        if self.current_pdf().is_none() {
            ui.colored_label(
                Color32::YELLOW,
                if self.show_translation {
                    "中文 PDF 尚未生成，请先运行 LaTeX 编译。"
                } else {
                    "英文 PDF 缺失，请补充开放全文或用户提供的 PDF。"
                },
            );
            return;
        }
        if self.pdfium.is_none() {
            ui.colored_label(Color32::YELLOW, "未找到 PDFium。请把对应平台的 PDFium 动态库放到 resources/pdfium，或设置 PAPERREADER_PDFIUM_DIR。");
            return;
        }
        ScrollArea::vertical()
            .auto_shrink([false, false])
            .show(ui, |ui| {
                if let Some(texture) = self.render_page(ctx, self.current_page) {
                    let max_width = ui.available_width().max(300.0);
                    let scale = (max_width / texture.size_vec2().x).min(1.0);
                    ui.image((texture.id(), texture.size_vec2() * scale));
                }
            });
    }

    fn summary_panel(&self, ui: &mut egui::Ui) {
        let artifact = &self.current().artifact;
        let paper = &artifact.paper;
        ui.heading("论文信息与分析");
        ui.label(format!("Venue: {} ({})", paper.venue, paper.venue_tier));
        ui.small(format!("文件：{}", self.current().path.display()));
        if !paper.license.is_empty() {
            ui.small(format!("许可证：{}", paper.license));
        }
        if !paper.fulltext_source.is_empty() {
            ui.small(format!("全文来源：{}", paper.fulltext_source));
        }
        if !paper.doi.is_empty() {
            ui.hyperlink_to(
                format!("DOI: {}", paper.doi),
                format!("https://doi.org/{}", paper.doi),
            );
        }
        for url in &paper.source_urls {
            ui.hyperlink(url);
        }
        for (kind, value) in &paper.identifiers {
            ui.small(format!("{}: {}", kind, value));
        }
        if artifact.processing_status != "complete" {
            ui.colored_label(
                Color32::YELLOW,
                format!("状态：{}", artifact.processing_status),
            );
        }
        if !artifact.quality.missing_inputs.is_empty() {
            for item in &artifact.quality.missing_inputs {
                ui.label(format!("• 缺少输入：{}", item));
            }
        }
        if !artifact.quality.figure_extraction_status.is_empty() {
            ui.small(format!(
                "图片提取：{}",
                artifact.quality.figure_extraction_status
            ));
        }
        if !artifact.quality.translation_status.is_empty() {
            ui.small(format!("翻译：{}", artifact.quality.translation_status));
        }
        if !artifact.quality.pdf_status.is_empty() {
            ui.small(format!("PDF：{}", artifact.quality.pdf_status));
        }
        if !artifact.quality.missing_figures.is_empty() {
            ui.colored_label(
                Color32::YELLOW,
                format!("缺失图片：{}", artifact.quality.missing_figures.join(", ")),
            );
        }
        for note in &artifact.quality.evidence_notes {
            ui.label(format!("• {}", note));
        }
        for note in &artifact.quality.figure_notes {
            ui.label(format!("• 图片：{}", note));
        }
        if !artifact.figures.is_empty() {
            ui.label(RichText::new("图片").strong());
            for figure in &artifact.figures {
                let caption = if self.show_translation && !figure.caption_zh.is_empty() {
                    &figure.caption_zh
                } else {
                    &figure.caption_en
                };
                let page = if self.show_translation {
                    figure.chinese_page
                } else {
                    figure.english_page
                };
                let response = ui.label(format!(
                    "{} [{}] {}{}",
                    figure.id,
                    figure.status,
                    caption,
                    page.map(|p| format!(" · 第 {} 页", p)).unwrap_or_default()
                ));
                response.on_hover_text(format!(
                    "资源：{}\n{}",
                    figure.asset_path, figure.alt_text_zh
                ));
            }
        }
        ui.separator();
        Self::block(ui, "解决什么问题", &artifact.analysis.problem);
        Self::bullets(ui, "贡献", &artifact.analysis.contributions);
        Self::bullets(ui, "创新点", &artifact.analysis.innovations);
        Self::block(ui, "方法简述", &artifact.analysis.method_summary);
        ui.separator();
        ui.heading(format!("实验（{} 组）", artifact.experiments.len()));
        ScrollArea::horizontal().show(ui, |ui| {
            egui::Grid::new("experiments")
                .striped(true)
                .min_col_width(120.0)
                .spacing([12.0, 8.0])
                .show(ui, |ui| {
                    for label in [
                        "实验",
                        "验证什么",
                        "证明什么",
                        "数据集",
                        "基线",
                        "指标",
                        "结果",
                    ] {
                        ui.strong(label);
                    }
                    ui.end_row();
                    for experiment in &artifact.experiments {
                        for value in [
                            &experiment.name,
                            &experiment.what_it_tests,
                            &experiment.what_it_proves,
                            &experiment.datasets.join(", "),
                            &experiment.baselines.join(", "),
                            &experiment.metrics.join(", "),
                            &experiment.result_summary,
                        ] {
                            ui.label(value);
                        }
                        ui.end_row();
                    }
                });
        });
    }

    fn block(ui: &mut egui::Ui, title: &str, text: &str) {
        ui.label(RichText::new(title).strong());
        ui.label(text);
        ui.add_space(8.0);
    }
    fn bullets(ui: &mut egui::Ui, title: &str, values: &[String]) {
        ui.label(RichText::new(title).strong());
        for value in values {
            ui.label(format!("• {}", value));
        }
        ui.add_space(8.0);
    }
}

fn bind_pdfium() -> (Option<Pdfium>, Option<String>) {
    let mut candidates = Vec::new();
    if let Ok(path) = std::env::var("PAPERREADER_PDFIUM_DIR") {
        candidates.push(PathBuf::from(path));
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            candidates.push(parent.join("resources/pdfium"));
        }
    }
    if let Ok(current_dir) = std::env::current_dir() {
        candidates.push(current_dir.join("resources/pdfium"));
    }
    for directory in candidates {
        let library = Pdfium::pdfium_platform_library_name_at_path(&directory);
        if let Ok(bindings) = Pdfium::bind_to_library(library) {
            return (Some(Pdfium::new(bindings)), None);
        }
    }
    match Pdfium::bind_to_system_library() {
        Ok(bindings) => (Some(Pdfium::new(bindings)), None),
        Err(error) => (None, Some(error.to_string())),
    }
}

impl eframe::App for PaperReaderApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::SidePanel::left("papers")
            .resizable(true)
            .default_width(230.0)
            .show(ctx, |ui| self.list_panel(ui));
        egui::SidePanel::right("summary")
            .resizable(true)
            .default_width(460.0)
            .show(ctx, |ui| {
                ScrollArea::vertical().show(ui, |ui| self.summary_panel(ui))
            });
        egui::CentralPanel::default().show(ctx, |ui| self.document_panel(ctx, ui));
    }
}
