# SPDX-License-Identifier: AGPL-3.0-or-later
"""Isi catatan kaki lewat `rakit` dan Word asli: tiap catatan tetap berisi teksnya sendiri saat nomor diulang per
halaman, juga di potongan `--fasl` dan sesudah bukti yang tidak mencetak catatan. Runner tanpa Word melaporkan lewati.
Semua bahan tinggal di TEMP.
"""
import sys, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader

from bantu import bahts, salin_mesin, tanpa_word

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji catatan Word: " + alasan)
        return
    with tempfile.TemporaryDirectory(prefix="bahts-catatan-word-") as t:
        akar = Path(t)
        salin_mesin(akar, ("_meta", "11223"))
        f = akar / "uji"
        f.mkdir()
        teks = ("@judul: فحص الحواشي\n@bentuk: kitab\n@berkas: hasil\n"
                "@tanpa: pustaka, ayat, hadits, maudhuat\n@halaman_baru: B\n@rumuz: 11223=-\n"
                "#K المقدمة\nهذا تمهيد للفحص.\n#F الفصل الأول\nهذا فصل سابق[^OLD-FIRST-NOTE].\n"
                "#F الفصل الثاني\nهذا تمهيد للفصل الثاني.\n#B المبحث الأول\n"
                "توحيد الربوبية وهو إفراد الله تعالى بالخلق والملك والتدبير[^<<11223|-|5>>]\n"
                "هذا نص المبحث الأول[^EXPECTED-SECOND-NOTE].\n"
                "#B المبحث الثاني\nهذا نص المبحث الثاني[^EXPECTED-THIRD-NOTE].\n#K الخاتمة\nانتهى الفحص.\n")
        (f / "naskah.txt").write_text(teks, encoding="utf8")
        for args, nama, harus in (((), "hasil", ["OLD-FIRST-NOTE", "EXPECTED-SECOND-NOTE", "EXPECTED-THIRD-NOTE"]),
                                  (("--fasl", "2"), "hasil - الفصل الثاني والخاتمة", ["EXPECTED-SECOND-NOTE", "EXPECTED-THIRD-NOTE"])):
            r = bahts(akar, "rakit", "uji", *args, batas=1800)
            assert r.returncode == 0, r.stdout + r.stderr
            with zipfile.ZipFile(f / f"{nama}.docx") as z:
                tree = ET.fromstring(z.read("word/footnotes.xml"))
            catatan = ["".join(n.itertext()) for n in tree.findall("w:footnote", NS)
                       if int(n.attrib.get("{" + NS["w"] + "}id", "0")) > 0]
            assert len(catatan) == len(harus) and all(h in c for h, c in zip(harus, catatan)), catatan
            pdf = "\n".join(p.extract_text() or "" for p in PdfReader(f / f"{nama}.pdf").pages)
            assert all(h in pdf for h in harus), pdf
            print(f"lolos catatan Word {' '.join(args) or 'utuh'}: {len(catatan)} isi catatan DOCX dan PDF benar", flush=True)


if __name__ == "__main__":
    utama()
