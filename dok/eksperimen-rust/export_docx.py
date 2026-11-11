# SPDX-License-Identifier: AGPL-3.0-or-later
"""Complete the docx-rs-to-PDF measurement through Word, serializing with Bahts."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

from alternatif import pdf_info
from render import ROOT


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--variant", choices=("docx-rs", "docx-rs-adapted"), default="docx-rs")
    args = p.parse_args()
    sys.path.insert(0, str(ROOT / "mesin"))
    import bahts
    import teks_pdf
    from berkas import kunci
    folder = args.folder.resolve()
    source = folder / f"{args.variant}.docx"
    output = folder / f"{args.variant}.pdf"
    samples = []
    word_samples = []
    with kunci(bahts.RAKIT_PEKERJAAN, tunggu=bahts.RAKIT_ANTRE, apa="eksperimen docx-rs PDF"):
        bahts._tunggu_ps_yatim()
        for _ in range(3):
            start = time.perf_counter()
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                            str(Path(__file__).with_name("docx_export.ps1")), "-InputDocx", str(source),
                            "-OutputPdf", str(output), "-Kunci", str(bahts.RAKIT_PS_KUNCI)], check=True)
            word_samples.append(time.perf_counter() - start)
            teks_pdf.betulkan(output)
            samples.append(time.perf_counter() - start)
    report = json.loads((folder / "alternatif.json").read_text(encoding="utf8"))
    report["renderers"][args.variant].update(export_samples_seconds=samples, word_only_samples_seconds=word_samples,
                                         export_includes_pdf_text_correction=True, median_export_seconds=statistics.median(samples), **pdf_info(output))
    record = report["renderers"][args.variant]
    record["sum_stage_medians_seconds"] = record["median_build_seconds"] + record.get("median_adapter_seconds", 0) + statistics.median(samples)
    (folder / "alternatif.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8", newline="\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
