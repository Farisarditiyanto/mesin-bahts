# SPDX-License-Identifier: AGPL-3.0-or-later
"""Isi catatan kaki lewat `rakit` dan Word asli: tiap catatan tetap berisi teksnya sendiri saat nomor diulang per
halaman, juga di potongan `--fasl`. Runner tanpa Word melaporkan lewati.
Semua bahan tinggal di TEMP.
"""
import sys, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader

from bantu import SAMPUL_UJI, bahts, salin_mesin, tanpa_word

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji catatan Word: " + alasan)
        return
    with tempfile.TemporaryDirectory(prefix="bahts-catatan-word-") as t:
        akar = Path(t)
        salin_mesin(akar, ("_meta",))
        f = akar / "uji"
        f.mkdir()
        teks = ("@judul: فحص الحواشي\n" + SAMPUL_UJI + "@berkas: hasil\n"
                "@tanpa: pustaka, ayat, hadits, maudhuat\n@halaman_baru: B\n"
                "#K المقدمة\nهذا تمهيد للفحص.\n#F الفصل الأول\nهذا فصل سابق[^OLD-FIRST-NOTE].\n"
                "{X}خلاصة الفصل الأول.\n"
                "#F الفصل الثاني\nهذا تمهيد للفصل الثاني.\n#B المبحث الأول\n"
                "هذا نص المبحث الأول[^EXPECTED-SECOND-NOTE].\n"
                "{X}KHULASAHFASL2 خلاصة الفصل الثاني.\n"
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
            khulasah = f / f"{nama} - الخلاصات.pdf"
            assert khulasah.is_file(), f"PDF khulasah tidak dibuat untuk {' '.join(args) or 'utuh'}: {r.stdout}"
            pdf_k = "\n".join(p.extract_text() or "" for p in PdfReader(khulasah).pages)
            assert "KHULASAHFASL2" in pdf_k, pdf_k
            print(f"lolos catatan Word {' '.join(args) or 'utuh'}: {len(catatan)} isi catatan DOCX/PDF + khulasah benar", flush=True)
        format_catatan(akar)


def format_catatan(akar):
    f = akar / "format_fn"
    f.mkdir()
    teks = ("@judul: فحص تنسيق الحواشي\n" + SAMPUL_UJI + "@berkas: hasil\n@format: imam_ayat16\n"
            "@tanpa: pustaka, ayat, hadits, maudhuat\n"
            "#K المقدمة\n"
            "فقرة تمهيدية[^توضيح **توكيد** ونص عادي.].\n"
            "#J البند | البيان\n"
            "#J الأول | خلية[^حاشية الجدول الأولى.]\n"
            "#H\n"
            "فقرة الصفحة الثانية.\n"
            "#J البند | البيان\n"
            "#J الثاني | خلية[^حاشية الجدول الثانية.]\n"
            "#K الخاتمة\nانتهى.\n")
    (f / "naskah.txt").write_text(teks, encoding="utf8")
    r = bahts(akar, "rakit", "format_fn", batas=1800)
    assert r.returncode == 0, r.stdout + r.stderr
    with zipfile.ZipFile(f / "hasil.docx") as z:
        doc_xml = ET.fromstring(z.read("word/document.xml"))
        fn_xml = ET.fromstring(z.read("word/footnotes.xml"))
        gaya = ET.fromstring(z.read("word/styles.xml"))
    w = "{" + NS["w"] + "}"
    fns = {int(n.attrib[f"{w}id"]): n for n in fn_xml.findall("w:footnote", NS) if int(n.attrib.get(f"{w}id", "0")) > 0}
    fn1 = fns[min(fns)]
    runs = [("".join(rn.itertext()), rn.find("w:rPr", NS)) for rn in fn1.findall(".//w:r", NS)]
    bold_runs = [rpr for t, rpr in runs if "توكيد" in t]
    plain_runs = [rpr for t, rpr in runs if "عادي" in t]
    assert bold_runs and all((rpr.find("w:b", NS) is not None or rpr.find("w:bCs", NS) is not None) for rpr in bold_runs), runs
    assert plain_runs and all(rpr.find("w:b", NS) is None and rpr.find("w:bCs", NS) is None for rpr in plain_runs), runs
    # ukuran tercetak rujukan: szCs run, gaya karakternya, gaya paragrafnya (bawaan: gaya paragraf default), lalu
    # docDefaults. Word tidak menulis szCs run yang sama dengan gaya paragrafnya (Normal sampul qism = 16 pt)
    def sz(rpr):
        e = None if rpr is None else rpr.find("w:szCs", NS)
        return None if e is None else e.get(f"{w}val")

    def gaya_sz(jenis, sid):
        s = next((s for s in gaya.findall("w:style", NS) if s.get(f"{w}type") == jenis
                  and (s.get(f"{w}styleId") == sid if sid else s.get(f"{w}default") == "1")), None)
        return s is not None and sz(s.find("w:rPr", NS)) or None

    def ukuran(p, rn):
        rpr, ppr = rn.find("w:rPr", NS), p.find("w:pPr", NS)
        rs = None if rpr is None else rpr.find("w:rStyle", NS)
        ps = None if ppr is None else ppr.find("w:pStyle", NS)
        return (sz(rpr) or (rs is not None and gaya_sz("character", rs.get(f"{w}val")) or None)
                or gaya_sz("paragraph", None if ps is None else ps.get(f"{w}val"))
                or sz(gaya.find("w:docDefaults/w:rPrDefault/w:rPr", NS)))

    tc_refs = [ukuran(p, rn) for tc in doc_xml.findall(".//w:tc", NS) for p in tc.findall(".//w:p", NS)
               for rn in p.findall("w:r", NS) if rn.find("w:footnoteReference", NS) is not None]
    assert len(tc_refs) == 2 and tc_refs == ["32", "32"], f"ukuran rujukan catatan #J bukan 16 pt (32): {tc_refs}"
    luar_refs = [ukuran(p, rn) for p in doc_xml.findall("./w:body/w:p", NS)
                 for rn in p.findall(".//w:r", NS) if rn.find("w:footnoteReference", NS) is not None]
    assert luar_refs == ["36"], f"ukuran rujukan catatan matan bukan 18 pt (36): {luar_refs}"
    hal2 = PdfReader(f / "hasil.pdf").pages[2].extract_text() or ""  # halaman 1 = sampul, 2 = sebelum #H
    assert "حاشية" in hal2 and "الثانية" in hal2 and ("(١)" in hal2 or "(1)" in hal2), hal2
    print("lolos format catatan Word: **tebal** dan ukuran rujukan #J (16 pt) tetap sesudah NomorCatatan", flush=True)


if __name__ == "__main__":
    utama()
