# SPDX-License-Identifier: AGPL-3.0-or-later
"""Uji audit silang `#R`, generator `pustaka`, audit bahasa/keseimbangan (`cek_gaya`), dan pemulihan teks PDF Arab
visual-reversed (`sumber_pdf` + `bukti`) lewat pintu pemakai (`bahts.py`)."""
import os, subprocess, sys, tempfile
from pathlib import Path
from bantu import salin_mesin

AKAR = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf8")
sys.stderr.reconfigure(encoding="utf8")


def _buat_pdf_arab(jalur, teks_halaman):
    """Buat PDF nyata berisi teks Unicode Arab memakai pymupdf + font Arab di mesin/."""
    import pymupdf
    font_p = AKAR / "mesin" / "UthmanicHafs_V22.ttf"
    doc = pymupdf.open()
    for teks in teks_halaman:
        p = doc.new_page()
        if font_p.exists():
            p.insert_font(fontname="ar", fontfile=str(font_p))
            p.insert_text((50, 100), teks, fontname="ar", fontsize=14)
        else:
            p.insert_textbox(pymupdf.Rect(50, 50, 540, 750), teks, fontsize=12)
    doc.save(jalur)
    doc.close()


def utama():
    with tempfile.TemporaryDirectory(prefix="bahts-pustaka-gaya-") as t:
        akar = Path(t)
        salin_mesin(akar, ("_meta", "11223", "1082", "1727"), huruf=False)
        f = akar / "uji"
        f.mkdir()
        dasar = (AKAR / "contoh" / "naskah.txt").read_text(encoding="utf8")
        (f / "riset.txt").write_text("tafsir 1:2\ncari توحيد الربوبية | uji\n", encoding="utf8")

        def jalan(*args):
            r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), *args], cwd=akar,
                               capture_output=True, text=True, encoding="utf8", timeout=60,
                               env=dict(os.environ, PYTHONIOENCODING="utf8"))
            out = r.stdout + r.stderr
            assert "GALAT MESIN" not in out and "Traceback" not in out, (args, out)
            return r.returncode, out

        # 1. Audit silang #R: contoh asli harus 0 perhatian
        (f / "naskah.txt").write_text(dasar, encoding="utf8")
        kode, out = jalan("cek", "uji")
        assert kode == 0 and "): 0\n" in out, out

        # 1a. Kitab berbukti di catatan kaki hilang dari #R -> perhatian
        hilang_r = dasar.replace(
            "رسالة في القضاء والقدر، محمد بن صالح بن محمد العثيمين، دار الوطن، 1423هـ.",
            "كتاب آخر غير مذكور في الحواشي، مؤلف وهمي، دار الفكر، 1430هـ.",
        )
        (f / "naskah.txt").write_text(hilang_r, encoding="utf8")
        kode, out = jalan("cek", "uji")
        assert kode == 0, out
        assert "المصادر والمراجع belum memuat «رسالة في القضاء والقدر» (kitab 11223)" in out, out
        assert "tetapi tidak dirujuk di catatan kaki mana pun" in out, out

        # 1b. Perintah `pustaka uji` menghasilkan draf siap tempel, menandai [BELUM DI #R], dan melaporkan sisa #R
        kode, out_p = jalan("pustaka", "uji")
        assert kode == 0, out_p
        assert "[SUDAH DI #R] القرآن الكريم." in out_p, out_p
        assert "[BELUM DI #R] رسالة في القضاء والقدر" in out_p and "# kitab 11223" in out_p, out_p
        assert "tidak terhubung ke bukti Shamela/Waqfeya" in out_p and "كتاب آخر غير مذكور" in out_p, out_p

        # 1c. `pustaka uji` dengan @pustaka_gaya: muallif memakai format **pengarang** dan __judul__
        (f / "naskah.txt").write_text("@pustaka_gaya: muallif\n" + dasar, encoding="utf8")
        kode, out_m = jalan("pustaka", "uji")
        assert kode == 0 and "**" in out_m and "__رسالة في القضاء والقدر__" in out_m, out_m

        # 1d. `#R` hanya berisi القرآن الكريم. tetap melaporkan kitab berbukti yang hilang, dan jalur berspasi dikutip
        mushaf_saja = dasar.replace(
            "رسالة في القضاء والقدر، محمد بن صالح بن محمد العثيمين، دار الوطن، 1423هـ.\n", "",
        )
        f_spasi = akar / "bahts" / "ahmad" / "naskah uji"
        f_spasi.mkdir(parents=True)
        (f_spasi / "riset.txt").write_text("tafsir 1:2\ncari توحيد الربوبية | uji\n", encoding="utf8")
        (f_spasi / "naskah.txt").write_text(mushaf_saja, encoding="utf8")
        kode, out_ms = jalan("cek", "bahts/ahmad/naskah uji")
        assert kode == 0, out_ms
        assert "المصادر والمراجع belum memuat «رسالة في القضاء والقدر» (kitab 11223)" in out_ms, out_ms
        assert 'pustaka "bahts/ahmad/naskah uji"' in out_ms, out_ms

        # 2. Audit gaya bahasa akademik (`cek_gaya`)
        gaya_salah = dasar.replace(
            "#K الخاتمة",
            "بصفتي نموذج ذكاء اصطناعي لا أستطيع الجزم بذلك.\n"
            "أقول إن هذا القول معتبر في الفقه.\n"
            "أنا أرجح هذا القول في المسألة.\n"
            "قلت: هذه المسألة واضحة في الشرع.\n"
            "هذا الحكمُ, وهو ظاهر في المعاملات.\n"
            "وهذا أصلٌ; وينبني عليه فروع.\n"
            "هل هذا جائزٌ? وهل يصح العقد ?\n"
            "و الفقه الإسلامي واسع في أبوابه.\n"
            "في عالم اليوم يلعب دوراً محورياً في الدراسة.\n"
            "#K الخاتمة",
        )
        (f / "naskah.txt").write_text(gaya_salah, encoding="utf8")
        kode, out_g = jalan("cek", "uji")
        assert kode == 0, out_g
        assert "ungkapan sistem AI" in out_g, out_g
        assert "kata ganti orang pertama «أقول»" in out_g, out_g
        assert "kata ganti orang pertama «أنا أرجح»" in out_g, out_g
        assert "kata ganti orang pertama «قلت:»" in out_g, out_g
        assert "tanda baca Latin «,»" in out_g, out_g
        assert "tanda baca Latin «;»" in out_g, out_g
        assert "tanda baca Latin «?»" in out_g, out_g
        assert "huruf sambung «و» terpisah spasi" in out_g, out_g
        assert "ungkapan klise/terjemahan harfiah" in out_g, out_g

        # 2b. Bukan false positive: isim tafdhil fiqih («أرجح القولين/ما قيل/هذه الأقوال/أن»), fi'il «قلت غلتها»,
        #     serta «و» yang menempel pada kutipan/ayat («و«…»», «و"…"», «و{Q:…}»)
        gaya_aman = dasar.replace(
            "#K الخاتمة",
            "وإذا تعارضت مفسدة ومصلحة أرجح منها قُدّمت المصلحة، كما إذا قلت غلتها أو تعطلت منافعها.\n"
            "وهو أرجح القولين عند أهل العلم، وهذا أرجح ما قيل في هذه المسألة، وهو أرجح الرأيين وأرجح المذهبين، "
            "فهو أرجح هذه الأقوال، وكان أرجح أن يحمل اللفظ على العموم.\n"
            'قال بعضهم: «الربوبية» و«الألوهية» هما أصل التوحيد، كما يجمع بين "العقل" و"النقل" في الفهم، '
            'ونحو قوله تعالى: {Q:1:2} و{Q:1:2} في السورة[^سورة الفاتحة، آية: 2.][^سورة الفاتحة، آية: 2.].\n'
            "#K الخاتمة",
        )
        (f / "naskah.txt").write_text(gaya_aman, encoding="utf8")
        kode, out_a = jalan("cek", "uji")
        assert kode == 0 and "): 0\n" in out_a, out_a

        # 2c. Keseimbangan panjang bagian: #F 600 kata vs #F 50 kata -> perhatian;
        #     #F التمهيد dan #F المبحث التمهيدي tidak dinilai; #B setingkat di bawah satu #F tetap dinilai
        panjang_600 = "وهذا بيان مفصل لمسألة التوحيد " * 120
        pendek_50 = "وهذا بيان موجز جدا " * 12
        timpang = dasar.replace(
            "#K الخاتمة",
            f"{panjang_600}\n\n#F التمهيد: مدخل عام\n{pendek_50}\n\n#F المبحث التمهيدي: التعريف بالمسألة\n{pendek_50}\n\n"
            f"#F المبحث الثاني: تفاصيل الحكم\n{pendek_50}\n\n#K الخاتمة",
        )
        (f / "riset.txt").write_text("tafsir 1:2\ncari التوحيد | uji\ncari مدخل | uji\ncari التعريف | uji\ncari الحكم | uji\n", encoding="utf8")
        (f / "naskah.txt").write_text(timpang, encoding="utf8")
        kode, out_t = jalan("cek", "uji")
        assert kode == 0, out_t
        baris_timpang = [b for b in out_t.splitlines() if "sangat timpang dibanding" in b]
        assert len(baris_timpang) == 1 and "المبحث الثاني" in baris_timpang[0], out_t
        assert "التمهيد" not in baris_timpang[0] and "التمهيدي" not in baris_timpang[0], out_t

        # #B setingkat di bawah satu #F tetap dinilai (sedangkan #B di bawah #K المقدمة tidak dinilai)
        timpang_b = dasar.replace(
            "#K الخاتمة",
            f"\n#B المبحث الأول: تفاصيل موسعة\n{panjang_600}\n\n#B المبحث الثاني: تفاصيل الحكم\n{pendek_50}\n\n#K الخاتمة",
        )
        (f / "naskah.txt").write_text(timpang_b, encoding="utf8")
        kode, out_tb = jalan("cek", "uji")
        assert kode == 0 and "sangat timpang dibanding" in out_tb and "المبحث الثاني" in out_tb, out_tb

        # 3. Regresi kartu `pustaka`: tahun wafat tanpa «ههـ» dobel, harakat «المتوفَّى», dan label ber-«：» + gelar
        sys.path.insert(0, str(akar / "mesin"))
        import pustaka
        import sumber_pdf
        kartu_uji = pustaka._ekstrak_kartu({
            "betaka_text": "الكتاب： الفقه الإسلامي: دراسة مقارنة\n"
                           "المؤلف： الشيخ أحمد بن تيمية (المتوفَّى: ٧٢٨ هـ)\n"
                           "المحقق： الدكتور عبد الله التركي\n",
            "title_ar": "الفقه الإسلامي",
        })
        assert kartu_uji["judul"] == "الفقه الإسلامي: دراسة مقارنة", kartu_uji
        assert kartu_uji["wafat"] == "٧٢٨هـ" and "ههـ" not in kartu_uji["wafat"], kartu_uji
        assert "المتوف" not in kartu_uji["pengarang"] and "الشيخ" not in kartu_uji["pengarang"], kartu_uji
        assert kartu_uji["muhaqqiq"] == "عبد الله التركي", kartu_uji

        # 4. Pemulihan teks PDF Arab visual-reversed & ligatur Word (`sumber_pdf.pulihkan_arab` + end-to-end `bukti`)
        assert sumber_pdf.pulihkan_arab("(٢٠٠٥) روتسدلا يف ناسنإلا قوقح") == "حقوق الإنسان في الدستور (٢٠٠٥)"
        assert sumber_pdf.pulihkan_arab("(125-140 .ص) ثحبلا عجرم") == "مرجع البحث (ص. 125-140)"
        assert sumber_pdf.pulihkan_arab("ةيبرعلا ةغللا (IFRS 17)") == "(IFRS 17) اللغة العربية"
        assert sumber_pdf.pulihkan_arab("(Ali, Hassan) ةساردلا يف") == "في الدراسة (Ali, Hassan)"
        assert sumber_pdf.pulihkan_arab("(2020, 2021) ةساردلا يف") == "في الدراسة (2020, 2021)"
        assert sumber_pdf.pulihkan_arab("user@example.com ةيبرعلا ةغللا") == "اللغة العربية user@example.com"
        assert sumber_pdf.pulihkan_arab("https://example.com/path/ ةيبرعلا ةغللا") == "اللغة العربية https://example.com/path/"
        assert sumber_pdf.pulihkan_arab("https://example.com/a#sec ةيبرعلا ةغللا") == "اللغة العربية https://example.com/a#sec"
        assert sumber_pdf.pulihkan_arab("بسم هللا الرحمن الرحيم في اإلسلام واألحكام واآليات") == "بسم الله الرحمن الرحيم في الإسلام والأحكام والآيات"
        # Teks normal (termasuk baris pendek penuh kata manshub berakhiran «لا») tidak boleh dibalik!
        for normal in ("وهذا مثال واضح، قليلا ما نجد مثله، مثلا في كتب الفقه المعاصر (2024).", "مثلا قليلا طويلا جميلا"):
            assert sumber_pdf.pulihkan_arab(normal) == normal, normal

        try:
            import pymupdf  # noqa: F401
        except ImportError:
            pymupdf = None
        if pymupdf is not None and (AKAR / "mesin" / "UthmanicHafs_V22.ttf").exists():
            # Uji end-to-end PDF nyata berisi teks Arab visual-reversed melalui `bahts.py bukti`
            pdf_p = f / "kajian.pdf"
            baris_terbalik = "(٢٠٢١) روتسدلا يف ناسنإلا قوقح نع ةيملع ةسارد"
            _buat_pdf_arab(pdf_p, [baris_terbalik])
            naskah_pdf = dasar.replace(
                "#K الخاتمة",
                'وجاء في الدراسة: "حقوق الإنسان في الدستور"[^انظر: دراسة معاصرة، ص1. <<luar|kajian.pdf|1>>].\n\n#K الخاتمة',
            )
            (f / "naskah.txt").write_text(naskah_pdf, encoding="utf8")
            kode, out_b = jalan("bukti", "uji")
            assert kode == 0, out_b
            assert "sekitar kutipan" in out_b and "حقوق الإنسان في الدستور" in out_b, out_b

        print("lolos uji pustaka, cek_gaya, keseimbangan bagian, dan pemulihan teks PDF Arab")


if __name__ == "__main__":
    utama()
