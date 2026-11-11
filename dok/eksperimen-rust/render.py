# SPDX-License-Identifier: AGPL-3.0-or-later
"""Real Word A/B timings and shared Arabic fixture for community renderers."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import runpy
import shutil
import statistics
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def fixture():
    fmt = json.loads((ROOT / "mesin/format.json").read_text(encoding="utf8"))["imam_ayat16"]
    prose = "هذا نص عربي تجريبي لفحص اتجاه الكتابة وموضع الحاشية وتوزيع الأسطر على الصفحة. "
    return {"font": fmt["huruf"], "body_pt": fmt["matan"], "note_pt": fmt["catatan"],
            "title": "اختبار صناعة الوثيقة العربية", "heading": "المقدمة", "heading_pt": fmt["judul"], "paragraphs": [
                {"text": f"PARA{i:02} " + prose * 3, "note": f"NOTE{i:02} هذه حاشية تجريبية لفحص ترتيب النص العربي ورقم الحاشية.", "break": i in (5, 9)}
                for i in range(1, 13)]}


def fixture_naskah(data):
    out = [f"@judul: {data['title']}", "@nama: اختبار آلي", "@berkas: hasil", "@format: imam_ayat16", "@bentuk: kitab",
           "@catatan_kaki: bersambung", "@tanpa: ayat, hadits, alam, maudhuat, pustaka", f"#K {data['heading']}"]
    for p in data["paragraphs"]:
        if p["break"]:
            out.append("#H")
        out.append(p["text"] + "[^" + p["note"] + "]")
    return "\n".join(out) + "\n"


def prepare(work, folders):
    if (work / "mesin").exists():
        raise RuntimeError("Use a fresh workspace")
    shutil.copytree(ROOT / "mesin", work / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__"))
    launcher = work / "dok/eksperimen-rust"
    launcher.mkdir(parents=True)
    shutil.copyfile(HERE / "jalankan.py", launcher / "jalankan.py")
    shutil.copytree(ROOT / "kitab/_meta", work / "kitab/_meta")
    source = work / "mesin/rakit.ps1"
    ps = source.read_text(encoding="utf-8-sig")
    old = '$CATATAN_WORD = "$dir\\_tmp\\rakit.word"'
    assert old in ps
    # Share existing Word ownership bookkeeping; no new cleanup mechanism.
    ps = ps.replace(old, "$CATATAN_WORD = Join-Path (Split-Path -Parent $Kunci) 'rakit.word'")
    source.write_text(ps, encoding="utf-8-sig", newline="\n")
    data = fixture()
    (work / "fixture").mkdir()
    (work / "fixture/naskah.txt").write_text(fixture_naskah(data), encoding="utf8", newline="\n")
    (work / "fixture.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8", newline="\n")
    jobs = ["fixture"]
    for i, folder in enumerate(folders, 1):
        target = work / f"manuscript-{i}"
        target.mkdir()
        text = (folder / "naskah.txt").read_text(encoding="utf-8-sig")
        text = re.sub(r"^@berkas:.*$", "@berkas: hasil", text, flags=re.M)
        if not re.search(r"^@berkas:", text, re.M):
            text = "@berkas: hasil\n" + text
        (target / "naskah.txt").write_text(text, encoding="utf8", newline="\n")
        for name in re.findall(r"^@templat:\s*(.+)$", text, re.M) + re.findall(r"<<luar\|([^|]+)\|", text):
            shutil.copyfile(folder / name, target / name)
        for sid in set(re.findall(r"<<(\d+)\|", text)):
            dest = work / "kitab" / sid
            if not dest.exists():
                shutil.copytree(ROOT / "kitab" / sid, dest)
        jobs.append(target.name)
    return jobs


def word_worker(job):
    work = Path(job["workspace"])
    sys.path.insert(0, str(work / "dok/eksperimen-rust"))
    from jalankan import pasang
    pasang(job["mode"], Path(job["library"]))
    sys.path.insert(0, str(work / "mesin"))
    import olah
    phases = {}
    periksa = olah.periksa
    def checked(*args, **kwargs):
        start = time.perf_counter()
        data = periksa(*args, **kwargs)
        phases["check_seconds"] = time.perf_counter() - start
        return data
    olah.periksa = checked
    run = subprocess.run
    def measured(command, *args, **kwargs):
        is_word = isinstance(command, list) and "-Build" in command and "-Kunci" in command
        if is_word:
            command = list(command)
            command[command.index("-Kunci") + 1] = str(ROOT / "mesin/_tmp/rakit.kunci")
        start = time.perf_counter()
        result = run(command, *args, **kwargs)
        if is_word:
            phases["powershell_word_seconds"] = time.perf_counter() - start
        return result
    subprocess.run = measured
    sys.argv = [str(work / "mesin/bahts.py"), "rakit", job["folder"]]
    start = time.perf_counter()
    runpy.run_path(sys.argv[0], run_name="__main__")
    phases["total_seconds"] = time.perf_counter() - start
    phases["other_seconds"] = phases["total_seconds"] - phases["check_seconds"] - phases["powershell_word_seconds"]
    from pypdf import PdfReader
    folder = work / job["folder"]
    pdf = PdfReader(folder / "hasil.pdf")
    text = [p.extract_text() for p in pdf.pages]
    with zipfile.ZipFile(folder / "hasil.docx") as z:
        xml = ET.fromstring(z.read("word/footnotes.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        notes = ["".join(x.itertext()) for x in xml.findall("w:footnote", ns) if int(x.attrib.get("{" + ns["w"] + "}id", "0")) > 0]
    print(json.dumps({"phases": phases, "pages": len(pdf.pages), "footnotes": len(notes),
                      "fingerprint": hashlib.sha256(json.dumps([text, notes], ensure_ascii=False).encode()).hexdigest()}), flush=True)


def word(args):
    work = args.out / "workspace"
    work.mkdir(parents=True)
    jobs = prepare(work, args.folder)
    sys.path.insert(0, str(ROOT / "mesin"))
    import bahts
    from berkas import kunci
    result = {"modes": ["python", "rust-cache"], "repeats": 3, "workloads": []}
    rng = random.Random(20261111)
    with kunci(bahts.RAKIT_PEKERJAAN, tunggu=bahts.RAKIT_ANTRE, apa="eksperimen Rust render"):
        for label in jobs:
            samples = {m: [] for m in result["modes"]}
            reference = None
            for repeat in range(3):
                order = list(samples)
                rng.shuffle(order)
                for mode in order:
                    bahts._tunggu_ps_yatim()
                    job = {"workspace": str(work), "folder": label, "mode": mode, "library": str(args.library.resolve())}
                    p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--word-worker"], input=json.dumps(job),
                                       capture_output=True, text=True, encoding="utf8")
                    (args.out / f"{label}-{mode}-{repeat}.log").write_text(p.stdout + p.stderr, encoding="utf8", newline="\n")
                    if p.returncode:
                        raise RuntimeError(f"Word failed; inspect {label}-{mode}-{repeat}.log")
                    data = json.loads(p.stdout.splitlines()[-1])
                    fingerprint = data.pop("fingerprint")
                    if reference is None:
                        reference = fingerprint
                    assert fingerprint == reference, f"Word PDF text/pages/notes differ for {label}"
                    samples[mode].append(data)
                    print(label, mode, repeat + 1, data, flush=True)
            entry = {"workload": label, "output_equal": True, "modes": {}}
            for mode, values in samples.items():
                entry["modes"][mode] = {"median_phases": {k: statistics.median(v["phases"][k] for v in values) for k in values[0]["phases"]},
                                         "pages": values[0]["pages"], "footnotes": values[0]["footnotes"], "samples": values}
            result["workloads"].append(entry)
            (args.out / "word.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8", newline="\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--library", type=Path, required=True)
    p.add_argument("--folder", type=Path, action="append", default=[])
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    word(args)


if __name__ == "__main__":
    if sys.argv[1:] == ["--word-worker"]:
        word_worker(json.loads(sys.stdin.read()))
    else:
        main()
