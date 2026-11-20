# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pengujian rumus LaTeX (#E dan {E:…}) dan perhatian sub-bagian tunggal lewat pintu pemakai (`bahts.py cek`)
serta uji acak terikat benih (fuzzing) agar masukan LaTeX sebarang tidak pernah menjatuhkan pengurai."""
import json, os, random, subprocess, sys, tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "mesin"))
import olah, rumus
from bantu import salin_mesin
from dasar import TandaRusak

sys.stdout.reconfigure(encoding="utf8")

XML_WRAP = (
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">{}</w:document>'
)


def cek_xml(omml):
    """Pastikan fragmen OMML adalah XML utuh dan sah."""
    return ET.fromstring(XML_WRAP.format(omml))


def utama():
    # 1. Uji acak (fuzz) berbenih tetap: hanya boleh menghasilkan OMML XML sah atau TandaRusak (bukan galat lain)
    rng = random.Random(42)
    potongan = [
        "x", "y", "1", "0.5", "صافي", "{", "}", "^", "_", "(", ")", "[", "]", "&", "\\\\", "+", "-", "=", "'",
        "\\frac", "\\sqrt", "\\sum", "\\int", "\\lim", "\\text", "\\mathbb", "\\left(", "\\right)", "\\left.",
        "\\right|", "\\begin{pmatrix}", "\\end{pmatrix}", "\\begin{cases}", "\\end{cases}", "\\begin{aligned}",
        "\\end{aligned}", "\\tag{1}", "\\alpha", "\\beta", "\\times", "\\leq", "\\bar", "\\hat", "\\overbrace",
        "\\ngawur", "\\", " ",
    ]
    for _ in range(300):
        s = "".join(rng.choices(potongan, k=rng.randint(0, 18)))
        for disp in (False, True):
            try:
                omml, _ = rumus.konversi(s, display=disp)
            except TandaRusak:
                continue
            cek_xml(omml)

    # 1b. Regresi struktur OMML: n-ary sebelum ) / ], serta GAYA_MATH rekursif (\mathbf, \boldsymbol)
    ns = {"m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
    rad_xml = cek_xml(rumus.konversi(r"\sqrt[\sum_{i=1}^n a_i]{x}")[0])
    assert rad_xml.find(".//m:rad/m:deg/m:nary", ns) is not None, ET.tostring(rad_xml, encoding="unicode")
    sum_xml = cek_xml(rumus.konversi(r"(\sum_{i=1}^n x_i)^2")[0])
    nary_e = sum_xml.find(".//m:nary/m:e", ns)
    assert nary_e is not None and ")" not in "".join(nary_e.itertext()), ET.tostring(sum_xml, encoding="unicode")
    assert sum_xml.find(".//m:oMath/m:sSup", ns) is not None, ET.tostring(sum_xml, encoding="unicode")
    gaya_omml, _ = rumus.konversi(r"\mathbf{X_1} + \boldsymbol{\hat{\beta}}")
    gaya_xml = cek_xml(gaya_omml)
    assert gaya_xml.find(".//m:sSub", ns) is not None and gaya_xml.find(".//m:acc", ns) is not None, gaya_omml
    assert "_" not in gaya_omml and r"\hat" not in gaya_omml and "β" in gaya_omml, gaya_omml

    # 2. Uji lewat pintu pemakai (CLI `bahts.py cek`) dan isi bahan JSON
    with tempfile.TemporaryDirectory(prefix="bahts-uji-rumus-") as t:
        akar = Path(t)
        salin_mesin(akar, ("_meta", "11223"), huruf=False)
        f = akar / "uji"
        f.mkdir()
        dasar = (AKAR / "contoh" / "naskah.txt").read_text(encoding="utf8")
        (f / "riset.txt").write_text("tafsir 1:2\ncari الربوبية\n", encoding="utf8")

        def jalankan(nama, teks, gagal=False, pesan=""):
            (f / "naskah.txt").write_text(teks, encoding="utf8")
            r = subprocess.run(
                [sys.executable, str(akar / "mesin" / "bahts.py"), "cek", "uji"],
                cwd=akar, capture_output=True, encoding="utf8", timeout=60,
                env=dict(os.environ, PYTHONIOENCODING="utf8"),
            )
            out = r.stdout + r.stderr
            assert (r.returncode != 0) == gagal, (nama, out)
            assert "GALAT MESIN" not in out and "Traceback" not in out, (nama, out)
            if pesan:
                assert pesan in out, (nama, out)
            return out

        rumus_valid = (
            "بلغت التكلفة 100$ وارتفعت إلى 250$ بمستوى دلالة {E:\\alpha = 0.05} ومعامل {E:R^2 = 0.87} "
            "ونسبة {E:ROE = \\frac{\\text{صافي الربح}}{\\text{حقوق الملكية}} \\times 100\\%}[^شرح: حيث "
            "{E:\\beta_1 > 0} و{E:\\sqrt[3]{x} \\leq \\infty} والمجال {E:\\left[0, 1\\right)}.].\n"
            "#E NPV = \\sum_{t=1}^{n} \\frac{CF_t}{(1 + r)^t} - C_0 \\tag{1}\n"
            "#E \\sigma = \\sqrt{\\frac{1}{n-1}\\sum_{i=1}^{n}(x_i - \\bar{x})^2} \\tag{2}\n"
            "#E \\text{نسبة التداول} = \\frac{\\text{الأصول المتداولة}}{\\text{الخصوم المتداولة}}\n"
            "#E \\lim_{x \\to \\infty} \\left(1 + \\frac{1}{x}\\right)^x = e\n"
            "#E A = \\begin{pmatrix} a_{11} & a_{12} \\\\ a_{21} & a_{22} \\end{pmatrix}\n"
            "#E f(x) = \\begin{cases} x^2 & \\text{إذا كان } x \\ge 0 \\\\ -x & \\text{إذا كان } x < 0 \\end{cases}\n"
            "#E \\begin{aligned} Y_i &= \\beta_0 + \\beta_1 X_i + \\varepsilon_i \\\\ \\hat{Y}_i &= \\hat{\\beta}_0 + \\hat{\\beta}_1 X_i \\end{aligned}\n"
            "#E \\binom{n}{k} = \\frac{n!}{k!(n-k)!}, \\quad \\mathbb{R}, \\mathbf{X_1}, \\boldsymbol{\\hat{\\beta}}, \\overbrace{a+b}^{n}, \\int_0^1 x^2 dx\n"
            "#J المؤشر | الصيغة\n"
            "#J العائد على الأصول | {E:ROA = \\frac{\\text{صافي الربح}}{\\text{إجمالي الأصول}}}\n"
            "#J الاحتمال الشرطي | {E:P(A | B)}\n"
        )
        out = jalankan("rumus valid lengkap", dasar.replace("#K الخاتمة", rumus_valid + "#K الخاتمة"))
        assert "GAGAL: 0" in out, out
        # Periksa bahan JSON: tiap OMML XML sah, tag angka hindi (١، ٢), dan tanda $ tidak dianggap rumus
        bahan_path = akar / "mesin" / "_tmp" / olah.alamat_bahan(f).name
        bahan = json.loads(bahan_path.read_text(encoding="utf8"))
        blok_e = [b for b in bahan["blok"] if b["k"] == "E"]
        assert len(blok_e) == 8, len(blok_e)
        assert blok_e[0]["tag"] == "١" and blok_e[1]["tag"] == "٢", [b.get("tag") for b in blok_e[:2]]
        assert "tag" not in blok_e[2], blok_e[2]
        for b in blok_e:
            cek_xml(b["omml"])
        omml_sebaris = [
            r["omml"] for b in bahan["blok"] for runs in (b["sel"] if b["k"] == "J" else [b.get("runs", [])])
            for r in runs if "omml" in r
        ] + [r["omml"] for c in bahan["catatan"] for r in c["runs"] if "omml" in r]
        assert len(omml_sebaris) == 8, len(omml_sebaris)
        for o in omml_sebaris:
            cek_xml(o)
        assert "Traditional Arabic" in blok_e[2]["omml"], blok_e[2]["omml"]

        # @angka: latin menjaga angka tag tetap 0123; @format: dalil memakai Sakkal Majalla di \text{...}
        teks_dalil = dasar.replace("@format: imam_ayat16", "@format: dalil\n@angka: latin").replace(
            "#K الخاتمة", "#E \\text{الربح} = \\frac{1}{2} \\tag{1}\n#K الخاتمة"
        )
        jalankan("format dalil + angka latin", teks_dalil)
        bahan_d = json.loads(bahan_path.read_text(encoding="utf8"))
        e_d = [b for b in bahan_d["blok"] if b["k"] == "E"][0]
        assert e_d["tag"] == "1" and "Sakkal Majalla" in e_d["omml"], e_d

        # sidik_cetak berubah bila rumus #E berubah
        out1 = jalankan("sidik rumus 1", dasar.replace("#K الخاتمة", "#E x + 1\n#K الخاتمة"))
        out2 = jalankan("sidik rumus 2", dasar.replace("#K الخاتمة", "#E x + 2\n#K الخاتمة"))
        s1 = [x for x in out1.splitlines() if x.startswith("CETAK_SHA256=")][0]
        s2 = [x for x in out2.splitlines() if x.startswith("CETAK_SHA256=")][0]
        assert s1 != s2, (s1, s2)

        # Bentuk cetak lewat pintu pemakai: tiap rumus jadi satu #E, OMML-nya dibaca dari bahan `cek`.
        # Isi tiap <m:t> menurut urutan tulisnya = urutan cetak kiri-ke-kanan di Word.
        def cetak(*latex):
            jalankan("bentuk cetak", dasar.replace("#K الخاتمة", "".join(f"#E {x}\n" for x in latex) + "#K الخاتمة"))
            blok = [cek_xml(b["omml"]) for b in json.loads(bahan_path.read_text(encoding="utf8"))["blok"] if b["k"] == "E"]
            assert len(blok) == len(latex), (len(blok), latex)
            return blok

        def teks(xml):
            return [t.text for t in xml.iter(f"{{{ns['m']}}}t")]

        w = XML_WRAP.split('xmlns:w="')[1].split('"')[0]
        satu, limits, gaya, bilangan, arab, kurung, campur, relasi, angka, matriks = cetak(
            r"\frac12 + x^12", r"\sum\limits_{i=1}^{n} x_i", r"\mathcal{L} + \mathbb{R}", r"f(1, 2) + 1,250.75 + 2{,}5 + 0.05",
            r"\text{الربح} = (\text{الإيراد} - 2.5)^2 \div \text{المال}", r"\left[ \text{أ} - 3 \right)",
            r"ROE = \text{الإيراد} - \text{المصروف}", r"\text{الربح} > \text{التكلفة} \to \text{الدين} \leq \text{المال}",
            r"1\,250 - 1/2 = 2,5 \tag{a}", r"\begin{pmatrix} \text{أ} & \text{ب} \end{pmatrix}")
        # argumen tanpa kurung kurawal = satu angka; \limits sesudah operator; gaya huruf lewat m:scr
        assert teks(satu) == ["1", "2", "+", "x", "1", "2"], teks(satu)
        assert limits.find(".//m:nary/m:sub/m:r", ns) is not None
        assert [x.get(f"{{{ns['m']}}}val") for x in gaya.iter(f"{{{ns['m']}}}scr")] == ["script", "double-struck"]
        # satu bilangan = satu run (desimal, ribuan), dan tiap run rumus berbahasa en-US: tanpa itu Word menukar «.» dan
        # «,» saat mencetak di dokumen berangka ٠-٩
        assert teks(bilangan) == ["f", "(", "1", ",", "2", ")", "+", "1,250.75", "+", "2,5", "+", "0.05"], teks(bilangan)
        assert all(r.find(f"{{{w}}}rPr/{{{w}}}lang").get(f"{{{w}}}val") == "en-US" for r in bilangan.iter(f"{{{ns['m']}}}r"))
        # rumus tanpa huruf Latin tercetak kanan-ke-kiri: urutan dibalik, kurung dan tanda berarah dicerminkan, pangkat
        # di kiri (m:sPre), kolom pertama matriks di kanan; rumus yang memuat huruf Latin tetap kiri-ke-kanan
        assert teks(arab) == ["المال", "÷", "2", "(", "2.5", "−", "الإيراد", ")", "=", "الربح"], teks(arab)
        assert arab.find(".//m:sPre", ns) is not None
        assert [x.get(f"{{{ns['m']}}}val") for x in kurung.find(".//m:dPr", ns)] == ["(", "]"], teks(kurung)
        assert teks(campur) == ["R", "O", "E", "=", "الإيراد", "−", "المصروف"], teks(campur)
        assert teks(relasi) == ["المال", "≥", "الدين", "←", "التكلفة", "<", "الربح"], teks(relasi)
        # satu bilangan tetap utuh («1\,250», «1/2»), dan huruf di \tag bukan isi rumus
        assert teks(angka) == ["2,5", "=", "1/2", "−", "1\u2009250"], teks(angka)
        assert teks(matriks) == ["ب", "أ"], teks(matriks)

        # angka rumus di catatan kaki bukan juz/halaman rujukan
        pecahan = jalankan("pecahan di catatan kaki", dasar.replace("#K الخاتمة", "فقرة[^الكسر {E:3/4} هنا.].\n#K الخاتمة"))
        assert "rujukan kitab tanpa bukti" not in pecahan, pecahan

        # Kasus GAGAL sintaks LaTeX
        gagal_kasus = [
            ("rumus inline kosong", "فقرة {E:} هنا.", "rumus kosong"),
            ("rumus inline tak tertutup", "فقرة {E:\\frac{a}{b} هنا.", "tidak ditutup dengan }"),
            ("perintah tak dikenal", "#E \\fraac{a}{b}", "tidak dikenal di rumus"),
            ("frac kurang argumen", "#E \\frac{a}", "kekurangan argumen"),
            ("kurung berlebih", "#E a + b}", "berlebih tanpa «{»"),
            ("left tanpa right", "#E \\left( a + b", "\\left tidak ditutup dengan \\right"),
            ("right tanpa left", "#E a + b \\right)", "\\right tanpa \\left"),
            ("begin tak cocok end", "#E \\begin{pmatrix} a \\end{bmatrix}", "ditutup dengan \\end{bmatrix}"),
            ("begin tak ditutup", "#E \\begin{cases} x", "tidak ditutup dengan \\end{cases}"),
            ("tag di inline", "فقرة {E:x=1 \\tag{1}}.", "hanya boleh di persamaan baris sendiri"),
            ("tag ganda", "#E x = 1 \\tag{1} \\tag{2}", "disebut lebih dari sekali"),
            ("tag kosong", "#E x = 1 \\tag{}", "\\tag{} kosong"),
            ("kurung terlalu dalam", "#E " + "{" * 80 + "x" + "}" * 80, "terlalu dalam"),
            ("rantai sqrt terlalu dalam", "#E " + "\\sqrt" * 1200 + "x", "terlalu dalam"),
            ("rantai frac terlalu dalam", "#E " + "\\frac" * 1200 + "a", "terlalu dalam"),
            ("rantai hat terlalu dalam", "#E " + "\\hat" * 1200 + "x", "terlalu dalam"),
            ("rumus di judul", "#S المعادلة {E:x=1}", "judul tidak boleh memuat"),
            ("tanda dolar LaTeX", "#E $a = b$", "tanda «$» tidak dipakai"),
        ]
        for nama, baris_uji, pesan in gagal_kasus:
            jalankan(nama, dasar.replace("#K الخاتمة", baris_uji + "\n#K الخاتمة"), gagal=True, pesan=pesan)

        # 3. Sub-bagian tunggal (#B sendirian di bawah #F, #M sendirian di bawah #B)
        tunggal_b = dasar.replace(
            "#K الخاتمة",
            "#F الفصل الأول\nتمهيد الفصل.\n#B المبحث الأول\nنص المبحث.\n#K الخاتمة",
        )
        jalankan("sub-bagian tunggal #B", tunggal_b, gagal=False, pesan="sub-bagian tunggal «المبحث الأول»")

        tunggal_m = dasar.replace(
            "#K الخاتمة",
            "#F الفصل الأول\nتمهيد.\n#B المبحث الأول\nتمهيد.\n#M المطلب الأول\nنص.\n#B المبحث الثاني\nنص.\n#K الخاتمة",
        )
        jalankan("sub-bagian tunggal #M", tunggal_m, gagal=False, pesan="sub-bagian tunggal «المطلب الأول»")

        # Dua sub-bagian, تمهيد, dan @bentuk: kitab -> tidak kena perhatian sub-bagian tunggal
        berpasangan = dasar.replace(
            "#K الخاتمة",
            "#F الفصل الأول\nتمهيد.\n#B المبحث الأول\nنص.\n#B المبحث الثاني\nنص.\n#K الخاتمة",
        )
        assert "sub-bagian tunggal" not in jalankan("sub-bagian berpasangan", berpasangan)

        tamhid = dasar.replace(
            "#K الخاتمة",
            "#F الفصل الأول\n#B تمهيد\nنص التمهيد.\n#K الخاتمة",
        )
        assert "sub-bagian tunggal" not in jalankan("sub-bagian tunggal تمهيد", tamhid)
        # تمهيد bukan pasangan: فصل berisi تمهيد + satu مبحث tetap tunggal; «مدخلات» bukan «مدخل»
        tamhid_satu = dasar.replace(
            "#K الخاتمة",
            "#F الفصل الأول\nنص.\n#B تمهيد\nنص.\n#B المبحث الأول: مدخلات النظام\nنص.\n#K الخاتمة",
        )
        jalankan("تمهيد + satu مبحث", tamhid_satu, pesan="sub-bagian tunggal «المبحث الأول: مدخلات النظام»")
        assert "sub-bagian tunggal" not in jalankan("sub-bagian tunggal di kitab", "@bentuk: kitab\n" + tunggal_b)

    print("lolos uji rumus (fuzz 300x + CLI + sub-bagian tunggal)")


if __name__ == "__main__":
    utama()
