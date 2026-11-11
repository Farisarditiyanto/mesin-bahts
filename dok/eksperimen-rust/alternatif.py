# SPDX-License-Identifier: AGPL-3.0-or-later
"""Compile the same public Arabic fixture with docx-rs and araby-book/Typst."""
import argparse
import json
from pathlib import Path
import re
import statistics
import subprocess
import time
import xml.etree.ElementTree as ET
import zipfile

from render import fixture


def model_from_bahan(data):
    """Content-only adapter: retain body/notes, not campus cover/indices/formatting."""
    fmt = data["format"]
    result = {"font": fmt["huruf"], "body_pt": fmt["matan"], "note_pt": fmt["catatan"],
              "heading_pt": fmt["judul"], "heading": "", "title": data["meta"]["judul"], "paragraphs": []}
    pending_break = False
    for block in data["blok"]:
        if block["k"] == "H":
            pending_break = True
            continue
        if block["k"] == "R":
            continue
        segments = []
        for run in block.get("runs", []):
            if "t" in run:
                segments.append({"text": run["t"]})
            if "fn" in run:
                note = ''.join(r.get("t", "") for r in data["catatan"][run["fn"]]["runs"])
                segments.append({"note": note})
        result["paragraphs"].append({"break": pending_break or block["k"] == "F", "segments": segments})
        pending_break = False
    return result


def typst_source(data, package):
    if package:
        lines = ['#import "@preview/araby-book:0.2.0": book',
                 '#show: book.with(title: ' + json.dumps(data["title"], ensure_ascii=False) + ', author: "اختبار آلي", paper: "a4", font: (' + json.dumps(data["font"]) + ',), font-size: ' + str(data["body_pt"]) + 'pt, footnote-size: ' + str(data["note_pt"]) + 'pt, show-toc: false)']
    else:
        lines = ['#set page(paper: "a4", numbering: "١")', '#set text(font: ' + json.dumps(data["font"]) + ', size: ' + str(data["body_pt"]) + 'pt, lang: "ar", dir: rtl)',
                 '#set footnote(numbering: "١")', '#show footnote.entry: set text(size: ' + str(data["note_pt"]) + 'pt)']
    lines += ['#set page(margin: (top: 2.5cm, bottom: 2.5cm, left: 2.5cm, right: 3.5cm))']
    if data["heading"]:
        lines += ['#align(center)[#text(size: ' + str(data["heading_pt"]) + 'pt, weight: "bold", ' + json.dumps(data["heading"], ensure_ascii=False) + ')]']
    for p in data["paragraphs"]:
        if p["break"]:
            lines.append('#pagebreak()')
        parts = []
        for segment in p.get("segments", [p]):
            if "text" in segment:
                parts.append('#text(' + json.dumps(segment["text"], ensure_ascii=False) + ')')
            if "note" in segment:
                parts.append('#footnote[#text(' + json.dumps(segment["note"], ensure_ascii=False) + ')]')
        lines += [''.join(parts), '']
    return '\n'.join(lines)


def pdf_info(path):
    from pypdf import PdfReader
    pdf = PdfReader(path)
    texts = [p.extract_text() for p in pdf.pages]
    return {"pages": len(pdf.pages), "a4_all_pages": all(abs(float(p.mediabox.width) - 595.276) < 2 and abs(float(p.mediabox.height) - 841.89) < 2 for p in pdf.pages),
            "paragraph_markers": len(re.findall(r"PARA", '\n'.join(texts))),
            "note_markers": len(re.findall(r"NOTE", '\n'.join(texts)))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--typst", type=Path, required=True)
    p.add_argument("--docx-bin", type=Path, required=True)
    p.add_argument("--bahan", type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    data = model_from_bahan(json.loads(args.bahan.read_text(encoding="utf8"))) if args.bahan else fixture()
    src = args.out / "fixture.json"
    src.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8", newline="\n")
    result = {"paragraphs": len(data["paragraphs"]), "scope": "body-and-notes-only" if args.bahan else "public-fixture", "renderers": {}}
    samples = []
    for _ in range(5):
        start = time.perf_counter()
        subprocess.run([str(args.docx_bin), str(src), str(args.out / "docx-rs.docx")], check=True)
        samples.append(time.perf_counter() - start)
    with zipfile.ZipFile(args.out / "docx-rs.docx") as z:
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        document = ET.fromstring(z.read("word/document.xml"))
        notes = ET.fromstring(z.read("word/footnotes.xml"))
        result["renderers"]["docx-rs"] = {"build_samples_seconds": samples, "median_build_seconds": statistics.median(samples),
            "rtl_paragraphs": len(document.findall(".//w:bidi", ns)),
            "footnote_references": len(document.findall(".//w:footnoteReference", ns)),
            "note_markers": ''.join(notes.itertext()).count("NOTE"), "pdf_requires_word": True}
    for name, package in (("araby-book", True), ("typst-core", False)):
        source, output = args.out / f"{name}.typ", args.out / f"{name}.pdf"
        source.write_text(typst_source(data, package), encoding="utf8", newline="\n")
        samples, diagnostics = [], []
        for _ in range(5):
            start = time.perf_counter()
            run = subprocess.run([str(args.typst), "compile", str(source), str(output)], capture_output=True, text=True, encoding="utf8")
            samples.append(time.perf_counter() - start)
            diagnostics.append(run.stderr)
            if run.returncode:
                raise RuntimeError(run.stderr)
        (args.out / f"{name}-diagnostics.txt").write_text('\n'.join(diagnostics), encoding="utf8", newline="\n")
        result["renderers"][name] = {"samples_seconds": samples, "median_seconds": statistics.median(samples),
                                     "warning_count": len(re.findall(r"(?m)^warning:", diagnostics[-1])), **pdf_info(output)}
    (args.out / "alternatif.json").write_text(json.dumps(result, indent=2) + '\n', encoding="utf8", newline="\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
