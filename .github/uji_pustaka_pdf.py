# SPDX-License-Identifier: AGPL-3.0-or-later
"""Uji audit silang `#R`, generator `pustaka`, dan pemulihan teks PDF Arab visual-reversed
(`sumber_pdf` + `bukti`) lewat pintu pemakai (`bahts.py`)."""
import json, os, subprocess, sys, tempfile
from pathlib import Path
from bantu import salin_mesin

AKAR = Path(__file__).resolve().parent.parent
KETERANGAN_PDF = "Table identifier ZX19782 and edition 2019"
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
        p.insert_text((530, 450), KETERANGAN_PDF, rotate=90)
    doc.save(jalur)
    doc.close()


def utama():
    with tempfile.TemporaryDirectory(prefix="bahts-pustaka-pdf-") as t:
        akar = Path(t)
        salin_mesin(akar, ("_meta", "11223", "1082", "711", "1727"), huruf=False)
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

        # 1a. Baris #R yang tidak dirujuk catatan kaki mana pun = perhatian (أبو سليمان ص203-204); kitab berbukti
        #     yang hilang dari #R juga perhatian. Rinciannya lewat `pustaka`.
        hilang_r = dasar.replace(
            "رسالة في القضاء والقدر، محمد بن صالح بن محمد العثيمين، دار الوطن، 1423هـ.",
            "كتاب آخر غير مذكور في الحواشي، مؤلف وهمي، دار الفكر، 1430هـ.",
        )
        (f / "naskah.txt").write_text(hilang_r, encoding="utf8")
        kode, out = jalan("cek", "uji")
        assert kode == 0 and "): 2\n" in out and "tidak dirujuk di catatan kaki mana pun" in out, out
        assert "tidak ada di المصادر والمراجع" in out, out

        # 1b. Blok #R siap ditempel, dan status ditulis terpisah dari draf.
        kode, out_p = jalan("pustaka", "uji")
        assert kode == 0, out_p
        assert "#R المصادر والمراجع\nالقرآن الكريم.\nرسالة في القضاء والقدر" in out_p, out_p
        assert "11223: judul belum ditemukan di #R" in out_p, out_p
        assert "di luar padanan kitab berbukti" in out_p and "كتاب آخر غير مذكور" in out_p, out_p

        # 1c. `pustaka uji` dengan @pustaka_gaya: muallif memakai format **pengarang** dan __judul__
        (f / "naskah.txt").write_text("@pustaka_gaya: muallif\n" + dasar, encoding="utf8")
        kode, out_m = jalan("pustaka", "uji")
        assert kode == 0 and "**" in out_m and "__رسالة في القضاء والقدر__" in out_m, out_m

        # 1d. Satu entri data cetak hanya cukup untuk edisi yang cocok, walau ada dua bukti صحيح مسلم.
        dua_edisi = dasar.replace(
            "#K الخاتمة",
            "وفي الكتاب روايتان.[^انظر: صحيح مسلم، مسلم، 1/2. <<711|1|2|الحمد لله>>]"
            "[^انظر: صحيح مسلم، مسلم، 1/2. <<1727|1|2|الحمد لله>>]\n\n#K الخاتمة",
        )
        dua_edisi += ("صحيح مسلم، مسلم، تحقيق محمد فؤاد عبد الباقي [ت ١٣٨٨ هـ]، "
                      "مطبعة عيسى البابي الحلبي وشركاه، القاهرة، ١٣٧٤ هـ - ١٩٥٥ م.\n")
        (f / "naskah.txt").write_text(dua_edisi, encoding="utf8")
        kode, out_dua = jalan("pustaka", "uji")
        assert kode == 0 and "1727: data cetak cocok di #R" in out_dua, out_dua
        assert "711: judul ditemukan, edisi perlu dicek" in out_dua, out_dua
        (f / "naskah.txt").write_text(dua_edisi.replace("مطبعة عيسى البابي الحلبي وشركاه، القاهرة", "دار الطباعة العامرة"),
                                      encoding="utf8")
        kode, out_campur = jalan("pustaka", "uji")
        assert kode == 0 and "1727: judul ditemukan, edisi perlu dicek" in out_campur, out_campur
        assert "data cetak cocok" not in next(s for s in out_campur.splitlines() if "1727:" in s), out_campur

        # 1e. #R berangka Latin, bertahun wafat «(ت 261هـ)», dan nama pengarang lebih pendek dari kartu tetap edisi
        #     yang sama; yang dinilai muhaqqiq, penerbit, cetakan, dan tahun, dan yang beda disebut bidangnya.
        ringkas = dasar.replace(
            "#K الخاتمة", "وفي الكتاب رواية.[^انظر: صحيح مسلم، مسلم، 1/2. <<1727|1|2|الحمد لله>>]\n\n#K الخاتمة")
        ringkas += ("صحيح مسلم، مسلم بن الحجاج القشيري النيسابوري (ت 261هـ)، تحقيق: محمد فؤاد عبد الباقي، "
                    "مطبعة عيسى البابي الحلبي وشركاه، القاهرة، 1374هـ - 1955م.\n")
        (f / "naskah.txt").write_text(ringkas, encoding="utf8")
        kode, out_r = jalan("pustaka", "uji")
        assert kode == 0 and "1727: data cetak cocok di #R" in out_r, out_r
        # Penerbit tanpa kata badan usaha di depannya tetap penerbit yang sama.
        (f / "naskah.txt").write_text(ringkas.replace("مطبعة عيسى", "عيسى"), encoding="utf8")
        kode, out_r = jalan("pustaka", "uji")
        assert kode == 0 and "1727: data cetak cocok di #R" in out_r, out_r
        for salah, benar, bidang in (("1374هـ - 1955م", "1412هـ - 1991م", "tahun"), ("1955م", "1960م", "tahun"),
                                     ("محمد فؤاد عبد الباقي", "أحمد شاكر", "muhaqqiq"),
                                     ("مطبعة عيسى البابي الحلبي وشركاه، القاهرة", "دار إحياء التراث العربي، بيروت",
                                      "penerbit"),
                                     ("مطبعة عيسى البابي الحلبي وشركاه", "دار عيسى للنشر", "penerbit")):
            (f / "naskah.txt").write_text(ringkas.replace(salah, benar), encoding="utf8")
            kode, out_s = jalan("pustaka", "uji")
            baris_1727 = next(s for s in out_s.splitlines() if "1727:" in s)
            assert kode == 0 and "edisi perlu dicek" in baris_1727 and f"beda {bidang}" in baris_1727, (benar, out_s)

        # 1f. Draf #R tanpa gelar «د» bertitik atau tidak, tanpa kurung kosong sisa «[ت ١٤٢١ هـ]», dan muhaqqiq per
        #     baris sesudah label kosong ikut terbaca.
        meta_p = akar / "kitab" / "11223" / "book_metadata.json"
        meta = json.loads(meta_p.read_text(encoding="utf8"))
        meta["betaka_text"] = ("الكتاب: رسالة في القضاء والقدر\rالمؤلف: د محمد بن صالح بن محمد العثيمين "
                               "[ت ١٤٢١ هـ، خلافا لما على الغلاف: ١٤٢٠ هـ]\r"
                               "تحقيق وتعليق:\rأ د أحمد محمد شاكر (جـ ١)\rو د محمد فؤاد عبد الباقي (جـ ٢)\r"
                               "الناشر: دار الوطن\rالطبعة: ١٤٢٣هـ\rعام النشر:\rالجزء: ١ - الطبعة: ٠، ١٩٠٠\r"
                               "عدد الصفحات: ٢٩")
        meta_p.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf8")
        (f / "naskah.txt").write_text(dasar, encoding="utf8")
        kode, out_g = jalan("pustaka", "uji")
        baris_draf = next(s for s in out_g.splitlines() if s.startswith("رسالة في القضاء والقدر"))
        assert kode == 0 and "، محمد بن صالح بن محمد العثيمين، " in baris_draf, out_g
        assert "[" not in baris_draf and "]" not in baris_draf and "١٩٠٠" not in baris_draf, out_g
        assert "تحقيق: أحمد محمد شاكر (جـ ١)، ومحمد فؤاد عبد الباقي" in baris_draf, out_g
        (f / "naskah.txt").write_text("@pustaka_gaya: muallif\n" + dasar, encoding="utf8")
        kode, out_g = jalan("pustaka", "uji")
        assert kode == 0 and "**محمد بن صالح بن محمد العثيمين** (ت ١٤٢١هـ)" in out_g, out_g

        # 1g. Penerbit dinilai dari nama khasnya ke dua arah: kota yang ditempel di kartu dan «للنشر» boleh beda tempat,
        #     tetapi penerbit lain yang berawalan sama («دار الوطن العربي») atau jenis lain («مؤسسة») tetap beda.
        #     Muhaqqiq berlabel jilid dan «جماعة من العلماء بإشراف الناشر» dinilai dari namanya.
        meta["betaka_text"] = ("الكتاب: رسالة في القضاء والقدر\rالمؤلف: محمد بن صالح بن محمد العثيمين\r"
                               "المحقق: ضبطه وصححه جماعة من العلماء بإشراف الناشر\r"
                               "الناشر: دار الوطن للنشر بالرياض\rالطبعة: ١٤٢٣هـ")
        meta_p.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf8")
        asal_r = "رسالة في القضاء والقدر، محمد بن صالح بن محمد العثيمين، دار الوطن، 1423هـ."
        assert asal_r in dasar
        r_baru = "رسالة في القضاء والقدر، العثيمين، ضبطه وصححه جماعة من العلماء، دار الوطن- الرياض، 1423هـ."

        def status_11223(baris_r):
            (f / "naskah.txt").write_text(dasar.replace(asal_r, baris_r), encoding="utf8")
            kode, out = jalan("pustaka", "uji")
            assert kode == 0, out
            return next(s for s in out.splitlines() if "11223:" in s)
        assert "data cetak cocok" in status_11223(r_baru), r_baru
        for lain in ("دار الوطن العربي", "مؤسسة الوطن", "دار الفكر"):
            assert "beda penerbit" in status_11223(r_baru.replace("دار الوطن", lain)), lain
        meta["betaka_text"] = meta["betaka_text"].replace(
            "المحقق: ضبطه وصححه جماعة من العلماء بإشراف الناشر", "تحقيق:\rجزء ١، ٢: عبد الله التركي\rجزء ٣: شعيب الأرنؤوط")
        meta_p.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf8")
        assert "data cetak cocok" in status_11223(r_baru.replace("ضبطه وصححه جماعة من العلماء", "تحقيق: عبد الله التركي"))
        assert "beda muhaqqiq" in status_11223(r_baru.replace("ضبطه وصححه جماعة من العلماء", "تحقيق: أحمد شاكر"))

        # 1h. Draf dari kartu tanpa penerbit/cetakan/tahun menulis «د.ن، د.ط، د.ت», kartu tanpa pengarang «المؤلف مجهول»,
        #     dan kitab berpengumpul «جمع وترتيب: …» (أبو سليمان ص85-86، 136، 175)
        def draf_11223(betaka, pengarang):
            meta.update(betaka_text=betaka, main_author_name_ar=pengarang, death_year_hijri=None)
            meta_p.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf8")
            (f / "naskah.txt").write_text(dasar, encoding="utf8")
            kode, out = jalan("pustaka", "uji")
            assert kode == 0, out
            return next(s for s in out.splitlines() if s.startswith("رسالة في القضاء والقدر"))
        assert draf_11223("الكتاب: رسالة في القضاء والقدر\rالمؤلف: محمد بن صالح العثيمين\rالناشر: -", "") == \
            "رسالة في القضاء والقدر، محمد بن صالح العثيمين، د.ن، د.ط، د.ت."
        assert draf_11223("الكتاب: رسالة في القضاء والقدر\rالناشر: دار الوطن\rالطبعة: الأولى، ١٤٢٣هـ", "") == \
            "رسالة في القضاء والقدر، المؤلف مجهول، دار الوطن، الطبعة الأولى، ١٤٢٣هـ."
        assert draf_11223("الكتاب: رسالة في القضاء والقدر\rالمؤلف: محمد بن صالح العثيمين\rجمع وترتيب: فهد السليمان\r"
                          "طبع ونشر: دار الوطن", "") == \
            "رسالة في القضاء والقدر، محمد بن صالح العثيمين، جمع وترتيب: فهد السليمان، د.ط، د.ت."

        # 2. Regresi kartu `pustaka`: tahun wafat tanpa «ههـ» dobel, harakat «المتوفَّى», dan label ber-«：» + gelar
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
        # 2b. Kurung siku berisi tambahan judul («[العِبَر و] ديوان المبتدأ…») cocok dengan judul rapat («العبر وديوان المبتدأ…»),
        #     dan kurung pengarang yang memuat tahun wafat («[الظاهري، ت ٤٥٦ هـ]») tidak menyisakan koma menggantung.
        from cek_rujukan import bentuk_judul, judul_di_baris
        b_khaldun = bentuk_judul({
            "title_ar": "تاريخ ابن خلدون",
            "betaka_text": "الكتاب: [العِبَر و] ديوان المبتدأ والخبر في تاريخ العرب والبربر\n",
        })
        assert judul_di_baris(b_khaldun, "**ابن خلدون**. __العبر وديوان المبتدأ والخبر في تاريخ العرب والبربر__. دار الفكر."), b_khaldun
        kartu_hazm = pustaka._ekstrak_kartu({
            "betaka_text": "الكتاب: المحلى بالآثار\nالمؤلف: أبو محمد، علي بن أحمد بن حزم [الظاهري، ت ٤٥٦ هـ]\n",
            "title_ar": "المحلى بالآثار",
        })
        assert kartu_hazm["pengarang"].endswith("[الظاهري]") and "،]" not in kartu_hazm["pengarang"], kartu_hazm

        # 3. Pemulihan teks PDF Arab visual-reversed & ligatur Word (`sumber_pdf.pulihkan_arab` + end-to-end `bukti`)
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
            import pymupdf
        except ImportError:
            pymupdf = None
        if pymupdf is not None and (AKAR / "mesin" / "UthmanicHafs_V22.ttf").exists():
            # Uji end-to-end PDF nyata berisi teks Arab visual-reversed melalui `bahts.py bukti`
            pdf_p = f / "kajian.pdf"
            baris_terbalik = "ةٌيَّبِرَعَ ةٌغَلُ (٢٠٢١) روتسدلا يف ناسنإلا قوقح نع ةيملع ةسارد"
            _buat_pdf_arab(pdf_p, [baris_terbalik])
            naskah_pdf = dasar.replace(
                "#K الخاتمة",
                'وجاء في الدراسة: "حقوق الإنسان في الدستور"[^انظر: دراسة معاصرة، ص1. <<luar|kajian.pdf|1>>].\n\n#K الخاتمة',
            )
            (f / "naskah.txt").write_text(naskah_pdf, encoding="utf8")
            kode, out_b = jalan("bukti", "uji")
            assert kode == 0, out_b
            assert "sekitar kutipan" in out_b and "حقوق الإنسان في الدستور" in out_b, out_b
            assert "لُغَةٌ عَرَبِيَّةٌ" in out_b, out_b
            assert "(٢٠٢١)" in out_b, out_b
            assert KETERANGAN_PDF in out_b, out_b

            assert sumber_pdf.pulihkan_arab("ينغي ﻻو يداشرإ ليلدلا اذه") == "هذا الدليل إرشادي ولا يغني"
            assert sumber_pdf.pulihkan_arab("مﻻسﻹا يف") == "في الإسلام"
            assert sumber_pdf.pulihkan_arab("كتإ") == "كتإ"

        # 4. Pemeriksaan integritas struktur PDF (`cek` + `bukti`): bersih, sisa bait sesudah %%EOF, /Count tidak
        #    konsisten, dan tabel xref rusak yang memicu peringatan perbaikan pypdf.
        import io as _io
        from pypdf import PdfWriter

        buf = _io.BytesIO()
        w = PdfWriter()
        w.add_blank_page(width=200, height=200)
        w.write(buf)
        pdf_bersih = buf.getvalue()

        def uji_pdf_struktur(nama_pdf, data_pdf):
            (f / nama_pdf).write_bytes(data_pdf)
            naskah_s = dasar.replace(
                "#K الخاتمة",
                f"وفي الدراسة المعاصرة[^انظر: دراسة معاصرة، ص1. <<luar|{nama_pdf}|1>>].\n\n#K الخاتمة",
            )
            (f / "naskah.txt").write_text(naskah_s, encoding="utf8")
            k_cek, o_cek = jalan("cek", "uji")
            k_buk, o_buk = jalan("bukti", "uji")
            assert k_cek == 0 and k_buk == 0, (nama_pdf, k_cek, o_cek, k_buk, o_buk)
            return o_cek, o_buk

        o_cek, o_buk = uji_pdf_struktur("bersih.pdf", pdf_bersih)
        assert "struktur PDF" not in o_cek and "PERINGATAN struktur PDF" not in o_buk, (o_cek, o_buk)

        o_cek, o_buk = uji_pdf_struktur("eof_sisa.pdf", pdf_bersih + b"\nSAMPAH_SESUDAH_EOF")
        assert "struktur PDF" in o_cek and "%%EOF" in o_cek, o_cek
        assert "PERINGATAN struktur PDF" in o_buk and "%%EOF" in o_buk, o_buk

        pdf_count = pdf_bersih.replace(b"/Count 1", b"/Count 5", 1)
        assert pdf_count != pdf_bersih
        o_cek, o_buk = uji_pdf_struktur("count_salah.pdf", pdf_count)
        assert "struktur PDF" in o_cek and "jumlah halaman tidak konsisten" in o_cek, o_cek
        assert "PERINGATAN struktur PDF" in o_buk and "jumlah halaman tidak konsisten" in o_buk, o_buk

        # /Count sebagai indirect object harus tetap terdeteksi bila tidak cocok
        from pypdf.generic import NameObject, NumberObject
        w_ind = PdfWriter()
        w_ind.add_blank_page(width=200, height=200)
        ref_count = w_ind._add_object(NumberObject(99))
        w_ind._pages.get_object()[NameObject("/Count")] = ref_count
        buf_ind = _io.BytesIO()
        w_ind.write(buf_ind)
        o_cek, o_buk = uji_pdf_struktur("count_indirect.pdf", buf_ind.getvalue())
        assert "struktur PDF" in o_cek and "jumlah halaman tidak konsisten" in o_cek, o_cek
        assert "PERINGATAN struktur PDF" in o_buk and "jumlah halaman tidak konsisten" in o_buk, o_buk

        # Geser posisi xref agar pypdf memperbaikinya dengan peringatan tanpa gagal membaca halaman
        pdf_xref = pdf_bersih.replace(b"startxref\n", b"startxref\n999", 1)
        if pdf_xref == pdf_bersih:
            pdf_xref = pdf_bersih.replace(b"startxref\r\n", b"startxref\r\n999", 1)
        assert pdf_xref != pdf_bersih
        o_cek, o_buk = uji_pdf_struktur("xref_rusak.pdf", pdf_xref)
        assert "struktur PDF" in o_cek and "peringatan perbaikan PDF" in o_cek, o_cek
        assert "PERINGATAN struktur PDF" in o_buk and "peringatan perbaikan PDF" in o_buk, o_buk

        print("lolos uji pustaka, struktur PDF, dan pemulihan teks PDF Arab")


if __name__ == "__main__":
    utama()
