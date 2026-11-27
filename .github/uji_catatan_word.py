# SPDX-License-Identifier: AGPL-3.0-or-later
"""Isi catatan kaki lewat `rakit` dan Word asli: tiap catatan tetap berisi teksnya sendiri saat nomor diulang per
halaman, juga di potongan `--fasl`. Runner tanpa Word melaporkan lewati.
Semua bahan tinggal di TEMP.
"""
import re, sys, tempfile, zipfile
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
        nomor_tiap_halaman(akar)


def nomor_halaman_pdf(pdf):
    """[[nomor catatan kaki tercetak, …] tiap halaman PDF]: «(n)» di bawah garis pemisah catatan kaki."""
    import pymupdf
    angka = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    hasil = []
    with pymupdf.open(pdf) as d:
        for p in d:
            garis = [g["rect"] for g in p.get_drawings()
                     if g["rect"].height < 2 and 60 < g["rect"].width < 260 and g["rect"].y0 > p.rect.height * 0.3]
            if not garis:
                hasil.append([])
                continue
            t = p.get_text(clip=pymupdf.Rect(0, max(g.y0 for g in garis), p.rect.width, p.rect.height))
            # angka di catatan kaki kanan-ke-kiri terbaca terbalik («(١٠)» -> «٠١»)
            hasil.append([int(n.translate(angka)[::-1]) for n in re.findall(r"\(([٠-٩0-9]+)\)", t)])
    return hasil


def nomor_tiap_halaman(akar):
    """Nomor catatan kaki tercetak di PDF: ulang = tiap halaman mulai (١) dan urut; bersambung = ١…N tanpa lompatan.
    Halaman penuh catatan kaki dengan judul #B/#M di tengah halaman: batas halaman yang bergeser sesudah nomor tetap
    (garis pemisah catatan kaki dipasang sesudah NomorCatatan) mencetak halaman yang mulai (٢)…(٧)."""
    kalimat = "وهذا كلام في بيان المسألة وتوضيح أطرافها وذكر ما قيل فيها من الأقوال والأدلة "
    hasyiyah = "حاشية لبيان المسألة وذكر من قال بها من أهل العلم وما استدلوا به "
    badan, n = [], 0
    for f in range(1, 4):
        badan.append(f"#F الفصل {['الأول', 'الثاني', 'الثالث'][f - 1]}")
        for b in range(1, 4):
            badan.append(f"#B المبحث {['الأول', 'الثاني', 'الثالث'][b - 1]}")
            for _ in range(4):
                n += 1
                isi = "".join(kalimat * (1 + (n * 7) % 4) + f"[^{hasyiyah * (1 + (n * 5 + c) % 4)}رقم {n}.]"
                              for c in range(1 + n % 3))
                badan.append(isi + "تم.")
            badan.append("#M مطلب في آخر المبحث")
            badan.append(kalimat * 2 + f"[^{hasyiyah}]تم.")
    for mode in ("ulang", "bersambung"):
        f = akar / f"nomor_{mode}"
        f.mkdir()
        (f / "naskah.txt").write_text(
            "@judul: فحص ترقيم الحواشي\n" + SAMPUL_UJI + f"@berkas: hasil\n@catatan_kaki: {mode}\n"
            "@tanpa: pustaka, ayat, hadits, maudhuat\n#K المقدمة\nتمهيد.\n" + "\n".join(badan)
            + "\n#K الخاتمة\nانتهى.\n", encoding="utf8")
        r = bahts(akar, "rakit", f.name, batas=1800)
        assert r.returncode == 0, r.stdout + r.stderr
        with zipfile.ZipFile(f / "hasil.docx") as z:
            jumlah = sum(1 for n in ET.fromstring(z.read("word/footnotes.xml")).findall("w:footnote", NS)
                         if int(n.attrib.get("{" + NS["w"] + "}id", "0")) > 0)
        halaman = nomor_halaman_pdf(f / "hasil.pdf")
        semua = [x for h in halaman for x in h]
        assert len(semua) == jumlah, f"{mode}: {len(semua)} nomor terbaca di PDF, {jumlah} catatan kaki di DOCX"
        if mode == "ulang":
            salah = [(i, h) for i, h in enumerate(halaman, 1) if h and h != list(range(1, len(h) + 1))]
            assert not salah, f"nomor ulang tiap halaman tidak mulai (١)/tidak urut di halaman PDF {salah}"
        else:
            assert semua == list(range(1, jumlah + 1)), f"nomor bersambung melompat: {halaman}"
        print(f"lolos nomor catatan kaki {mode}: {jumlah} catatan di {sum(1 for h in halaman if h)} halaman PDF",
              flush=True)


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
