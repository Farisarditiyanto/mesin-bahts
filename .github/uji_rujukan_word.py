# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regresi {P:} lewat `rakit` dan Word asli; cocokkan catatan kaki DOCX ke halaman target PDF.

Runner GitHub tidak menyediakan Word. Di sana tes dilewati secara terang; di PC yang punya Word tes wajib jalan.
Semua naskah dan hasil tinggal di TEMP. Tidak memakai layanan luar atau bahan pribadi.
"""
import os, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader

AKAR = Path(__file__).resolve().parent.parent
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if os.name != "nt":
        print("lewati uji rujukan Word: perlu Windows + Word asli")
        return
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            pass
    except FileNotFoundError:
        print("lewati uji rujukan Word: Microsoft Word tidak terpasang")
        return
    with tempfile.TemporaryDirectory(prefix="bahts-rujukan-word-") as t:
        akar = Path(t)
        shutil.copytree(AKAR / "mesin", akar / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__"))
        folder = akar / "uji"
        folder.mkdir()
        # Kunci panjang sah menurut `tanda`. Sebelum diisi, penanda memperpanjang catatan kaki beberapa baris;
        # sesudah diisi satu angka, target maju halaman. Nomor yang diisi sekali akan diam-diam menjadi salah.
        kunci = "target" * 35
        for mode in ("bersambung", "ulang"):
            teks = ("@bentuk: kitab\n@judul: اختبار\n@berkas: uji\n@angka: latin\n"
                    f"@catatan_kaki: {mode}\n@format: tatbiqi\n#K اختبار\n{{A:awal}}STARTMARK\n")
            for i in range(18):
                teks += ("هذا اختبار لترتيب الصفحات والتأكد من صحة الإحالة إلى موضع لاحق من الكتاب. " * 3
                         + f"[^REF{i} انظر الكلام المفصل عن هذه المسألة، ص{{P:{kunci}}}، "
                           f"وانظر ص{{P:awal}}، ثم ص{{P:{kunci}}}.]\n")
            teks += f"{{A:{kunci}}}TARGETMARK النص المقصود بالإحالة.\n"
            (folder / "naskah.txt").write_text(teks, encoding="utf8")
            r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), "rakit", "uji"], cwd=akar,
                               capture_output=True, encoding="utf8", timeout=1800)
            assert r.returncode == 0, r.stdout + r.stderr
            halaman = {}
            pdf = PdfReader(folder / "uji.pdf")
            for n, p in enumerate(pdf.pages, 1):
                for tanda in ("STARTMARK", "TARGETMARK"):
                    if tanda in p.extract_text():
                        halaman[tanda] = n
            assert set(halaman) == {"STARTMARK", "TARGETMARK"}, halaman
            with zipfile.ZipFile(folder / "uji.docx") as z:
                xml = ET.fromstring(z.read("word/footnotes.xml"))
                catatan = ["".join(n.itertext()) for n in xml.findall("w:footnote", NS)]
            catatan = [c for c in catatan if re.search(r"REF\d+", c)]
            assert len(catatan) == 18, catatan
            harus = [halaman["TARGETMARK"], halaman["STARTMARK"], halaman["TARGETMARK"]]
            for c in catatan:
                ada = [int(n) for n in re.findall(r"ص(\d+)", c)]
                assert ada == harus, f"{mode}: {c}; halaman PDF sebenarnya {harus}"
                assert "⟦" not in c, c
            print(f"lolos rujukan Word {mode}: {len(catatan)} catatan, 3 rujukan/catatan, target PDF {harus}", flush=True)


if __name__ == "__main__":
    utama()
