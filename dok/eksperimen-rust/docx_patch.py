# SPDX-License-Identifier: AGPL-3.0-or-later
"""Small OOXML adapter for missing run RTL and footnote-entry marks in this probe."""
import argparse
import json
from pathlib import Path
import statistics
import time
import zipfile

from lxml import etree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def adapt(source, target):
    counts = {}
    with zipfile.ZipFile(source) as z, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name in z.namelist():
            payload = z.read(name)
            if name in ("word/document.xml", "word/footnotes.xml"):
                root = ET.fromstring(payload)
                before = [x.text for x in root.iter(W + "t")]
                for run in root.iter(W + "r"):
                    prop = run.find(W + "rPr")
                    if prop is None:
                        prop = ET.Element(W + "rPr")
                        run.insert(0, prop)
                    if prop.find(W + "rtl") is None:
                        ET.SubElement(prop, W + "rtl")
                if name == "word/footnotes.xml":
                    for note in root.findall(W + "footnote"):
                        if int(note.get(W + "id", "0")) <= 0:
                            continue
                        if note.find(".//" + W + "footnoteRef") is None:
                            p = note.find(W + "p")
                            run = ET.Element(W + "r")
                            prop = ET.SubElement(run, W + "rPr")
                            ET.SubElement(prop, W + "rStyle").set(W + "val", "FootnoteReference")
                            ET.SubElement(prop, W + "rtl")
                            ET.SubElement(run, W + "footnoteRef")
                            p.insert(1 if p.find(W + "pPr") is not None else 0, run)
                    counts["footnote_head_markers"] = len(list(root.iter(W + "footnoteRef")))
                assert before == [x.text for x in root.iter(W + "t")], "Adapter changed actual text"
                payload = ET.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            out.writestr(name, payload)
    return counts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    args = p.parse_args()
    folder = args.folder
    times = []
    for _ in range(5):
        start = time.perf_counter()
        counts = adapt(folder / "docx-rs.docx", folder / "docx-rs-adapted.docx")
        times.append(time.perf_counter() - start)
    result = json.loads((folder / "alternatif.json").read_text(encoding="utf8"))
    raw = result["renderers"]["docx-rs"]
    result["renderers"]["docx-rs-adapted"] = {"median_build_seconds": raw["median_build_seconds"],
        "median_adapter_seconds": statistics.median(times), "adapter_samples_seconds": times, **counts,
        "actual_text_unchanged": True, "footnote_references": raw["footnote_references"]}
    (folder / "alternatif.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8", newline="\n")
    print(counts)


if __name__ == "__main__":
    main()
