// SPDX-License-Identifier: AGPL-3.0-or-later
use docx_rs::*;
use serde_json::Value;
use std::{env, fs::File};

fn run(text: &str, font: &str, pt: usize) -> Run {
    Run::new().add_text(text).size(pt * 2)
        .fonts(RunFonts::new().ascii(font).hi_ansi(font).cs(font))
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    let data: Value = serde_json::from_reader(File::open(&args[1])?)?;
    let font = data["font"].as_str().ok_or("font")?;
    let body = data["body_pt"].as_u64().ok_or("body_pt")? as usize;
    let note = data["note_pt"].as_u64().ok_or("note_pt")? as usize;
    let mut doc = Docx::new().page_size(11906, 16838)
        .page_margin(PageMargin::new().top(1417).bottom(1417).left(1417).right(1984));
    let mut heading = Paragraph::new().align(AlignmentType::Center).add_run(
        run(data["heading"].as_str().ok_or("heading")?, font, data["heading_pt"].as_u64().ok_or("heading_pt")? as usize).bold());
    heading.property = heading.property.bidi(true);
    doc = doc.add_paragraph(heading);
    for item in data["paragraphs"].as_array().ok_or("paragraphs")? {
        let mut p = Paragraph::new().align(AlignmentType::Right)
            .page_break_before(item["break"].as_bool().unwrap_or(false));
        p.property = p.property.bidi(true);
        let segments = item["segments"].as_array().cloned().unwrap_or_else(|| vec![item.clone()]);
        for segment in segments {
            if let Some(text) = segment["text"].as_str() { p = p.add_run(run(text, font, body)); }
            if let Some(text) = segment["note"].as_str() {
                let mut n = Paragraph::new().align(AlignmentType::Right).add_run(run(text, font, note));
                n.property = n.property.bidi(true);
                p = p.add_run(Run::new().add_footnote_reference(Footnote::new().add_content(n)));
            }
        }
        doc = doc.add_paragraph(p);
    }
    doc.build().pack(File::create(&args[2])?)?;
    Ok(())
}
