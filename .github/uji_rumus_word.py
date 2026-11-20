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

from bantu import salin_mesin, tanpa_word


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
            "@bentuk: kitab\n@format: tatbiqi\n@judul: اختبار المعادلات المالية\n@berkas: uji\n"
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
        # 2 inline paragraf + 4 display #E + 2 inline di sel tabel #J = 8 di document.xml, + 2 di footnotes.xml
        assert len(omaths_doc) == 8, f"oMath di document.xml: {len(omaths_doc)}"
        assert len(omaths_para) >= 4, f"oMathPara di document.xml: {len(omaths_para)}"
        assert len(omaths_fn) == 2, f"oMath di footnotes.xml: {len(omaths_fn)}"
        # Pastikan teks sesudah {E:…} di sel tabel #J tetap di luar <m:oMath> (tidak tersedot masuk zona rumus)
        teks_math = "".join("".join(o.itertext()) for o in omaths_doc)
        assert "بعده" not in teks_math and "نهاية" not in teks_math, teks_math

        pdf_reader = PdfReader(folder / "uji.pdf")
        halaman = len(pdf_reader.pages)
        assert halaman >= 2, halaman
        # Pastikan #H sebelum #E \tag{2} benar-benar memindah persamaan (٢) ke halaman sesudah halaman pertama
        hal1_teks = unicodedata.normalize("NFKC", pdf_reader.pages[0].extract_text() or "")
        hal2_teks = unicodedata.normalize("NFKC", pdf_reader.pages[1].extract_text() or "")
        assert "NPV" in hal1_teks and "NPV" not in hal2_teks, (hal1_teks, hal2_teks)
        assert "(٢)" not in hal1_teks and "(٢)" in hal2_teks and "Yi" in hal2_teks, (hal1_teks, hal2_teks)
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
