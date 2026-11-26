# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regresi rumus LaTeX (#E dan {E:…}) lewat `rakit` dan Microsoft Word asli, plus `pratinjau`.

Memastikan:
- {E:…} sebaris (di paragraf, sel tabel #J, dan catatan kaki [^…]) dan #E baris sendiri (dengan dan tanpa \\tag)
  menjadi objek OMML asli (<m:oMath> / <m:oMathPara>) di word/document.xml dan tercetak di PDF tanpa peringatan.
- `pratinjau` menghasilkan gambar grid 2×2 PNG dari PDF hasil rakit.
Runner tanpa Word melaporkan lewati. Semua bahan tinggal di TEMP.
"""
import subprocess, sys, tempfile, unicodedata, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader

from bantu import SAMPUL_UJI, salin_mesin, tanpa_word


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji rumus Word: " + alasan)
        return
    with tempfile.TemporaryDirectory(prefix="bahts-rumus-word-") as t:
        akar = Path(t)
        salin_mesin(akar)
        folder = akar / "uji"
        folder.mkdir()
        teks = (
            SAMPUL_UJI + "@tanpa: pustaka\n@format: tatbiqi\n@judul: اختبار المعادلات المالية\n@berkas: uji\n"
            "#K المقدمة\n"
            "تُحسب نسبة العائد على حقوق الملكية بالصيغة {E:ROE = \\frac{\\text{صافي الربح}}{\\text{حقوق الملكية}}} "
            "بمستوى دلالة {E:\\alpha = 0.05}[^حيث {E:p < 0.05} والمجال {E:\\left[0, 1\\right)} دليل على المعنوية الإحصائية.].\n"
            "ويُحسب صافي القيمة الحالية بالمعادلة الآتية:\n"
            "#E NPV = \\sum_{t=1}^{n} \\frac{CF_t}{(1 + r)^t} - C_0 \\tag{1}\n"
            "أما نسبة التداول العربية الخالصة فتُحسب بالصيغة الآتية:\n"
            "#E \\frac{\\text{الأصول المتداولة}}{\\text{الخصوم المتداولة}}\n"
            "#H\n"
            "#E Y_i = \\beta_0 + \\beta_1 X_{1i} + \\varepsilon_i \\tag{2}\n"
            "#J المؤشر المالي | المعادلة الرياضية | الدلالة\n"
            "#J العائد على الأصول | {E:ROA > 0} نص بعده و{E:P(A | B)} نهاية. | كفاءة الأصول\n"
            "وتُحسب الدرجة المعيارية بالمعادلة الآتية:\n"
            "#E Z = \\frac{\\bar{X} - \\mu}{\\sigma / \\sqrt{n}} \\tag{3}\n"
            "ويُحسب الوعاء الزكوي للسهم بالمعادلة العربية الطويلة الآتية:\n"
            "#E \\text{وعاء السهم الزكوي} = \\frac{\\text{الأصول المتداولة الزكوية} - \\text{الالتزامات المتداولة الحالة}}{\\text{إجمالي الأسهم المصدرة}} \\tag{4}\n"
            "#K الخاتمة\n"
            "أهم النتائج: نجح تركيب المعادلات الرياضية بنجاح.\n"
        )
        (folder / "naskah.txt").write_text(teks, encoding="utf8")
        r = subprocess.run(
            [sys.executable, str(akar / "mesin" / "bahts.py"), "rakit", "uji"],
            cwd=akar, capture_output=True, encoding="utf8", timeout=1800,
        )
        assert r.returncode == 0 and (folder / "uji.pdf").is_file(), r.stdout + r.stderr
        assert "PERINGATAN" not in r.stdout, r.stdout

        with zipfile.ZipFile(folder / "uji.docx") as z:
            doc_xml = ET.fromstring(z.read("word/document.xml"))
            fn_xml = ET.fromstring(z.read("word/footnotes.xml"))
        ns = {"m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
        omaths_doc = doc_xml.findall(".//m:oMath", ns)
        omaths_para = doc_xml.findall(".//m:oMathPara", ns)
        omaths_fn = fn_xml.findall(".//m:oMath", ns)
        # 2 inline paragraf + 5 display #E + 2 inline di sel tabel #J = 9 di document.xml, + 2 di footnotes.xml
        assert len(omaths_doc) == 9, f"oMath di document.xml: {len(omaths_doc)}"
        assert len(omaths_para) >= 5, f"oMathPara di document.xml: {len(omaths_para)}"
        assert len(omaths_fn) == 2, f"oMath di footnotes.xml: {len(omaths_fn)}"
        # Pastikan teks sesudah {E:…} di sel tabel #J tetap di luar <m:oMath> (tidak tersedot masuk zona rumus)
        teks_math = "".join("".join(o.itertext()) for o in omaths_doc)
        assert "بعده" not in teks_math and "نهاية" not in teks_math, teks_math
        # Run angka rumus tetap berbahasa en-US sesudah disimpan Word: tanpa itu «0.05» tercetak «0,05» di dokumen
        # berangka ٠-٩ (lapisan teks PDF tetap «0.05», jadi yang bisa dijaga dari sini hanya penandanya)
        w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        angka = [r for o in omaths_doc + omaths_fn for r in o.iter(f"{{{ns['m']}}}r") if "0.05" in "".join(r.itertext())]
        assert len(angka) == 2 and all(r.find(f"{w}rPr/{w}lang").get(f"{w}val") == "en-US" for r in angka), len(angka)

        pdf_reader = PdfReader(folder / "uji.pdf")
        halaman = len(pdf_reader.pages)
        assert halaman >= 3, halaman
        # Pastikan #H sebelum #E \tag{2} benar-benar memindah persamaan (٢) ke halaman sesudah halaman isi pertama
        # (halaman PDF 1 = sampul)
        hal1_teks = unicodedata.normalize("NFKC", pdf_reader.pages[1].extract_text() or "")
        hal2_teks = unicodedata.normalize("NFKC", pdf_reader.pages[2].extract_text() or "")
        assert "NPV" in hal1_teks and "NPV" not in hal2_teks, (hal1_teks, hal2_teks)
        assert "(٢)" not in hal1_teks and "(٢)" in hal2_teks and "Yi" in hal2_teks, (hal1_teks, hal2_teks)
        # Rumus pecahan Arab panjang pada @format: imam_ayat16 (matan 18 pt) tidak boleh terlipat lalu dibalik
        # huruf-per-huruf oleh Word («ةردصملا» alih-alih «المصدرة»); rumus yang lebih lebar lagi otomatis diperkecil
        # sampai muat satu baris
        arab_p = akar / "arab"
        arab_p.mkdir()
        (arab_p / "naskah.txt").write_text(
            SAMPUL_UJI + "@tanpa: pustaka\n@format: imam_ayat16\n@judul: اختبار\n@berkas: arab\n#K المقدمة\n"
            "وتُصاغ المعادلة العربية كما يأتي:\n"
            "#E \\text{وعاء السهم الزكوي} = \\frac{\\text{الأصول المتداولة الزكوية} - \\text{الالتزامات المتداولة الحالة}}{\\text{إجمالي الأسهم المصدرة}} \\tag{1}\n"
            "#E \\text{الوعاء الزكوي للسهم} = \\frac{\\text{النقدية} + \\text{المدينون} + \\text{المخزون السلعي} + \\text{الاستثمارات المتداولة} - \\text{الالتزامات الحالية}}{\\text{عدد الأسهم المصدرة}} \\tag{2}\n"
            "#K الخاتمة\nأهم النتائج: نجح.\n", encoding="utf8")
        ra = subprocess.run(
            [sys.executable, str(akar / "mesin" / "bahts.py"), "rakit", "arab"],
            cwd=akar, capture_output=True, encoding="utf8", timeout=1800,
        )
        assert ra.returncode == 0 and "PERINGATAN" not in ra.stdout, ra.stdout + ra.stderr
        arab_teks = unicodedata.normalize("NFKC", "".join(p.extract_text() or "" for p in PdfReader(arab_p / "arab.pdf").pages))
        assert "ةردصم" not in arab_teks and "ةيوكز" not in arab_teks and "ةيلاح" not in arab_teks, arab_teks
        assert "السهم الزكوي" in arab_teks and "النقدية" in arab_teks and "صدرة" in arab_teks, arab_teks
        with zipfile.ZipFile(arab_p / "arab.docx") as za:
            arab_xml = ET.fromstring(za.read("word/document.xml"))
        omaths_arab = arab_xml.findall(".//m:oMath", ns)
        assert len(omaths_arab) == 2, len(omaths_arab)
        sz_eq2 = {
            int(el.get(f"{w}val"))
            for tag in (f"{w}szCs", f"{w}sz")
            for el in omaths_arab[1].iter(tag)
            if el.get(f"{w}val")
        }
        assert sz_eq2 and max(sz_eq2) < 36, f"rumus panjang tidak diperkecil: {sz_eq2}"
        # Pecahan Arab di catatan kaki bukan rumus #E yang menyusul matan: pengantar berakhir «:» di ujung halaman
        # tetap diperingatkan
        ujung = akar / "ujung"
        ujung.mkdir()
        (ujung / "naskah.txt").write_text(
            SAMPUL_UJI + "@tanpa: pustaka\n@format: tatbiqi\n@judul: اختبار\n@berkas: ujung\n#K المقدمة\n"
            "نص فيه حاشية[^النسبة {E:\\frac{\\text{صافي الربح}}{\\text{المبيعات}}} هنا.] وينتهي بتمهيد منفصل عن محتواه كما يأتي:\n"
            "#H\nالمحتوى في الصفحة التالية.\n#K الخاتمة\nأهم النتائج: نجح.\n", encoding="utf8")
        ru = subprocess.run(
            [sys.executable, str(akar / "mesin" / "bahts.py"), "rakit", "ujung"],
            cwd=akar, capture_output=True, encoding="utf8", timeout=1800,
        )
        assert ru.returncode == 0 and "berakhir «:»" in ru.stdout, ru.stdout + ru.stderr
        # Uji `pratinjau` pada PDF hasil rakit
        rp = subprocess.run(
            [sys.executable, str(akar / "mesin" / "bahts.py"), "pratinjau", "uji", "1"],
            cwd=akar, capture_output=True, encoding="utf8", timeout=60,
        )
        assert rp.returncode == 0 and "hal 1:" in rp.stdout, rp.stdout + rp.stderr
        png_path = Path(rp.stdout.strip().split(": ", 1)[1])
        assert png_path.is_file() and png_path.stat().st_size > 1000, png_path
        print(
            f"lolos rumus Word: {len(omaths_doc)} oMath + {len(omaths_fn)} fn oMath, "
            f"{halaman} hal, pratinjau {png_path.name}",
            flush=True,
        )


if __name__ == "__main__":
    utama()
