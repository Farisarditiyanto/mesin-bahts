# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regresi tabel #J lewat `rakit` dan Word asli: tabel 2 sampai 6 kolom harus terakit.

Lebar kolom tabel ≥3 kolom = 82 / (kolom - 1) persen; untuk 4 kolom itu pecahan (27.33) yang dulu ditolak Word
(«Specified cast is not valid», rakit.ps1). Runner tanpa Word melaporkan lewati. Semua bahan tinggal di TEMP.
"""
import os, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

AKAR = Path(__file__).resolve().parent.parent
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if os.name != "nt":
        print("lewati uji tabel Word: perlu Windows + Word asli")
        return
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            pass
    except FileNotFoundError:
        print("lewati uji tabel Word: Microsoft Word tidak terpasang")
        return
    kolom = range(2, 7)
    with tempfile.TemporaryDirectory(prefix="bahts-tabel-word-") as t:
        akar = Path(t)
        shutil.copytree(AKAR / "mesin", akar / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__"))
        folder = akar / "uji"
        folder.mkdir()
        teks = "@bentuk: kitab\n@judul: اختبار\n@berkas: uji\n#K اختبار الجداول\n"
        for n in kolom:
            teks += f"جدول من {n} أعمدة:\n"
            for r in range(3):
                teks += "#J " + " | ".join(f"خلية{r}{c}" for c in range(n)) + "\n"
            teks += "فقرة بعد الجدول.\n"
        (folder / "naskah.txt").write_text(teks, encoding="utf8")
        r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), "rakit", "uji"], cwd=akar,
                           capture_output=True, encoding="utf8", timeout=1800)
        assert r.returncode == 0 and (folder / "uji.pdf").is_file(), r.stdout + r.stderr
        with zipfile.ZipFile(folder / "uji.docx") as z:
            xml = ET.fromstring(z.read("word/document.xml"))
        tabel = xml.findall(".//w:tbl", NS)
        lebar = [len(tb.find("w:tr", NS).findall("w:tc", NS)) for tb in tabel]
        # tabel #J naskah lebih dulu; sesudahnya bisa ada tabel فهرس buatan rakit sendiri
        assert lebar[:len(kolom)] == list(kolom), f"jumlah kolom tabel di DOCX {lebar}, harus diawali {list(kolom)}"
        print(f"lolos tabel Word: {len(tabel)} tabel, kolom {lebar}", flush=True)


if __name__ == "__main__":
    utama()
