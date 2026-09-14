use crate::loader::LoadedArtifact;
use eframe::egui::{
    self, Align, Color32, FontData, FontDefinitions, FontFamily, Layout, RichText, ScrollArea,
    TextStyle,
};

pub struct PaperReaderApp {
    papers: Vec<LoadedArtifact>,
    selected: usize,
    show_translation: bool,
    selected_section: Option<String>,
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
        Self {
            papers,
            selected: 0,
            show_translation: true,
            selected_section: None,
        }
    }

    fn current(&self) -> &LoadedArtifact {
        &self.papers[self.selected]
    }

    fn section_text<'a>(&self, section: &'a crate::model::Section) -> &'a str {
        if self.show_translation && !section.translated_text.trim().is_empty() {
            &section.translated_text
        } else {
            &section.source_text
        }
    }

    fn list_panel(&mut self, ui: &mut egui::Ui) {
        ui.heading("论文库");
        ui.separator();
        for (index, paper) in self.papers.iter().enumerate() {
            let selected = index == self.selected;
            if ui
                .selectable_label(selected, &paper.artifact.paper.title)
                .clicked()
            {
                self.selected = index;
                self.selected_section = None;
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
                self.selected_section = Some(id);
            }
        }
    }

    fn document_panel(&mut self, ui: &mut egui::Ui) {
        let paper = &self.current().artifact.paper;
        let title = paper.title.clone();
        let authors = paper.authors.join(", ");
        let venue = paper.venue.clone();
        let year = paper.year;
        ui.horizontal(|ui| {
            ui.heading(title);
            ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                ui.selectable_value(&mut self.show_translation, true, "中文");
                ui.selectable_value(&mut self.show_translation, false, "原文");
            });
        });
        ui.label(format!("{} · {} · {}", authors, venue, year));
        ui.separator();
        let selected = self.selected_section.clone();
        ScrollArea::vertical()
            .auto_shrink([false, false])
            .show(ui, |ui| {
                for section in &self.current().artifact.sections {
                    if selected.as_deref().is_some_and(|id| id != section.id) {
                        continue;
                    }
                    ui.add_space(8.0);
                    ui.label(RichText::new(&section.title).text_style(TextStyle::Heading));
                    ui.label(self.section_text(section));
                }
                if self.current().artifact.sections.is_empty() {
                    ui.colored_label(
                        Color32::YELLOW,
                        "暂无全文章节，请补充 PDF/HTML 后重新生成此 artifact。",
                    );
                }
            });
    }

    fn summary_panel(&self, ui: &mut egui::Ui) {
        let artifact = &self.current().artifact;
        let paper = &artifact.paper;
        ui.heading("论文信息与分析");
        ui.label(format!("Venue: {} ({})", paper.venue, paper.venue_tier));
        ui.small(format!("文件：{}", self.current().path.display()));
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
            ui.colored_label(Color32::YELLOW, "状态：需要补充全文");
            for item in &artifact.quality.missing_inputs {
                ui.label(format!("• {}", item));
            }
        }
        if !artifact.quality.evidence_notes.is_empty() {
            ui.label(RichText::new("证据与质量备注").strong());
            for note in &artifact.quality.evidence_notes {
                ui.label(format!("• {}", note));
            }
        }
        if !artifact.quality.translation_status.is_empty() {
            ui.small(format!("翻译状态：{}", artifact.quality.translation_status));
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
        egui::CentralPanel::default().show(ctx, |ui| self.document_panel(ui));
    }
}
