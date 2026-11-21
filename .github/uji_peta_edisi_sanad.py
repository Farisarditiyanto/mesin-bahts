# SPDX-License-Identifier: AGPL-3.0-or-later
"""Uji `peta <folder>`, `edisi <kueri|id|w…>`, dan posisi rawi yang belum dikenal lewat pintu pemakai (`bahts.py`),
100% offline dengan subset kitab CI."""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path
from bantu import salin_mesin

AKAR = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf8")
sys.stderr.reconfigure(encoding="utf8")


def utama():
    with tempfile.TemporaryDirectory(prefix="bahts-peta-edisi-") as t:
        akar = Path(t)
        salin_mesin(akar, ("_meta", "11223", "1681", "1727", "711", "654", "1726", "1082", "10649", "7283"), huruf=False)
        # Salin dok/mutamad.md agar peta menandai kitab mu'tamad secara nyata
        (akar / "dok").mkdir(exist_ok=True)
        shutil.copy(AKAR / "dok" / "mutamad.md", akar / "dok" / "mutamad.md")

        def jalan(*args):
            r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), *args], cwd=akar,
                               capture_output=True, text=True, encoding="utf8", timeout=60,
                               env=dict(os.environ, PYTHONIOENCODING="utf8"))
            out = r.stdout + r.stderr
            assert "GALAT MESIN" not in out and "Traceback" not in out, (args, out)
            return r.returncode, out

        # 1. `peta contoh`: dasar offline
        shutil.copytree(AKAR / "contoh", akar / "contoh", ignore=shutil.ignore_patterns("*.docx", "*.pdf", "laporan.txt", "jebakan"))
        kode, out = jalan("peta", "contoh")
        assert kode == 0, out
        for harus in ("PETA BAHTS:", "[1] Struktur & Cakupan", "[2] Sijil Sumber", "11223]", "[3] Busur Argumen"):
            assert harus in out, (harus, out)

        # 2. `peta` pada uji_pemeriksa/khiyar: cakupan mazhab kosong, kontradiksi tarjih vs khatimah, {H:}, `terima`
        shutil.copytree(AKAR / ".github" / "uji_pemeriksa" / "khiyar", akar / "khiyar")
        kode, out_k = jalan("peta", "khiyar")
        assert kode == 0, out_k
        assert "الحنفية: 0 bukti (KOSONG!)" in out_k, out_k
        assert "المالكية: 0 bukti (KOSONG!)" in out_k, out_k
        assert "الشافعية: 0 bukti (KOSONG!)" in out_k, out_k
        assert "رجحان القول الأول" in out_k and "أن الراجح عدم ثبوت خيار المجلس" in out_k, out_k
        assert "[4] Hadits bertanda {H:…}" in out_k, out_k
        # Pastikan baris hadits memuat nomor baris nyata (bukan L?), nama rawi, dan ringkasan takhrij
        assert "L?" not in out_k and "ابن عمر" in out_k and "إذا تبايع الرجلان" in out_k, out_k
        assert "[5] Perhatian Diterima" in out_k and "367514" in out_k, out_k

        # Dua {H:} yang berbeda dapat ditulis pada satu baris, masing-masing dengan bukti sendiri.
        khiyar = akar / "khiyar" / "naskah.txt"
        teks = khiyar.read_text(encoding="utf8")
        h1, h2, *_ = [s for s in teks.splitlines() if "{H:" in s]
        khiyar.write_text(teks.replace(h1, h1 + " " + h2).replace("\n" + h2 + "\n", "\n"), encoding="utf8")
        kode, out_h = jalan("peta", "khiyar")
        hadits = out_h.split("[4] Hadits bertanda", 1)[1].split("[5]", 1)[0].splitlines()
        assert kode == 0, out_h
        assert any("ابن عمر" in s and "1681|3|64" in s for s in hadits), hadits
        assert any("أبو هريرة" in s and "1726|3|304" in s and "1681|3|64" not in s for s in hadits), hadits
        khiyar.write_text(teks.replace("#K الخاتمة", "وفي دراسة معاصرة تفصيل.[^بحث معاصر. <<luar>>]\n#K الخاتمة"), encoding="utf8")
        kode, out_l = jalan("peta", "khiyar")
        assert kode == 0 and "<<luar>> 1" in out_l, out_l

        # 2b. `peta` menandai bagian isi >=80 kata tanpa catatan kaki, ketimpangan panjang antar-#F,
        # `#K الملخص` tidak ikut jadi [متن], dan `#F مقدمة في …` tetap dinilai [متن] (bukan [مقدمة])
        uji_f = akar / "uji_peta"
        uji_f.mkdir()
        dasar = (AKAR / "contoh" / "naskah.txt").read_text(encoding="utf8")
        panjang = "وهذا بيان مفصل لمسألة التوحيد " * 120
        pendek = "وهذا بيان موجز جدا " * 25  # 100 kata tanpa catatan kaki
        naskah_u = dasar.replace(
            "#K المقدمة",
            "#K الملخص\nيهدف هذا البحث إلى خلاصة سريعة ويرجح الكاتب فيها قولا مجملا.\n\n#K المقدمة",
        ).replace(
            "#K الخاتمة",
            f"{panjang}\n\n#F مقدمة في أصول المسألة\nوالراجح في هذه المسألة ما دل عليه النص الصريح.\n\n"
            f"#F المبحث الثاني: مسألة فرعية\n{pendek}\n\n#K الخاتمة",
        )
        (uji_f / "naskah.txt").write_text(naskah_u, encoding="utf8")
        kode, out_p = jalan("peta", "uji_peta")
        assert kode == 0, out_p
        assert "<-- 0 catatan kaki!" in out_p, out_p
        assert "ketimpangan panjang:" in out_p and "المبحث الثاني" in out_p, out_p
        assert "خلاصة سريعة" not in out_p, out_p
        assert "[متن   L" in out_p and "والراجح في هذه المسألة" in out_p, out_p

        # 3. `edisi` 100% offline: `edisi w…` sebelum waqfeya.tsv ada harus menolak secara ramah tanpa mengunduh
        (akar / "kitab" / "_meta" / "waqfeya.tsv").unlink(missing_ok=True)
        kode_off, out_off = jalan("edisi", "w01234567")
        assert kode_off != 0 and "Katalog Waqfeya belum diunduh" in out_off, (kode_off, out_off)
        assert not (akar / "kitab" / "_meta" / "waqfeya.tsv").exists()

        # 3a. `edisi` lintas katalog Shamela & Waqfeya + jebakan pengarang/karya terkait
        kolom = ("title", "author", "category", "pages", "pdf_paths", "txt_paths")
        baris_wq = [
            ("صحيح مسلم (ط. دار طيبة)", "مسلم بن الحجاج القشيري النيسابوري", "الحديث الشريف", "1500", "['./m1/1.pdf']", "['./m1/1.txt']"),
            ("مختصر صحيح مسلم (ت_ الألباني)", "عبد العظيم بن عبد القوي المنذري", "الحديث الشريف", "600", "['./m2/1.pdf']", "['./m2/1.txt']"),
            ("تفسير القرآن العظيم (تفسير ابن كثير) (ط. ابن حزم)", "إسماعيل بن عمر بن كثير القرشي", "التفسير", "2000", "['./ik/1.pdf']", "['./ik/1.txt']"),
            ("السنن الصغرى (المجتبى)", "أحمد بن شعيب النسائي", "الحديث الشريف", "900", "['./ns/1.pdf']", "['./ns/1.txt']"),
        ]
        (akar / "kitab" / "_meta" / "waqfeya.tsv").write_text(
            "\n".join("\t".join(b) for b in (kolom, *baris_wq)) + "\n", encoding="utf8",
        )

        # 3a. `edisi 1727` menampilkan 1727 + 711 (group_id sama), mencocokkan صحيح مسلم Waqfeya, memisahkan مختصر sebagai karya terkait
        kode, out_e1 = jalan("edisi", "1727")
        assert kode == 0, out_e1
        assert "Shamela 1727" in out_e1 and "Shamela 711" in out_e1, out_e1
        assert "صحيح مسلم (ط. دار طيبة)" in out_e1, out_e1
        bag_sama, _, bag_terkait = out_e1.partition("Karya terkait")
        assert "مختصر صحيح مسلم" not in bag_sama and "مختصر صحيح مسلم" in bag_terkait, out_e1

        # 3b. `edisi` dengan nomor Waqfeya (تفسير ابن كثير di dalam kurung) menemukan Shamela تفسير ابن كثير
        sys.path.insert(0, str(akar / "mesin"))
        import edisi, waqfeya
        wid_ik = next(w for w, b in waqfeya.katalog().items() if "ابن كثير" in b["judul"])
        kode, out_e2 = jalan("edisi", wid_ik)
        assert kode == 0, out_e2
        assert "Shamela 1503" in out_e2 or "Shamela 1509" in out_e2 or "Shamela 8473" in out_e2, out_e2

        # 3c. `edisi` pencarian judul + filter pengarang
        kode, out_e3 = jalan("edisi", "تفسير القرطبي")
        assert kode == 0 and "Shamela 20855" in out_e3, out_e3
        kode, out_e4 = jalan("edisi", "رسالة في القضاء والقدر", "العثيمين")
        assert kode == 0 and "[ADA] Shamela 11223" in out_e4, out_e4

        # 3d. Uji unit jebakan rekonsiliasi pengarang & judul (arabic-bib / turath-match)
        assert edisi.cocok_pengarang("ابن حجر العسقلاني", "ابن حجر الهيتمي") == "beda"
        assert edisi.cocok_pengarang("سبط ابن الجوزي", "ابن الجوزي") == "beda"
        assert edisi.cocok_pengarang("ابن أبي حاتم", "أبو حاتم الرازي") == "beda"
        assert edisi.cocok_pengarang("أبو بكر بن أبي شيبة", "ابن أبي شيبة") == "sama"
        assert edisi.cocok_pengarang("أبو نعيم الأصفهاني", "أبو نعيم الأصبهاني") == "sama"
        assert edisi.cocok_pengarang("ابن أبي العز", "صالح الفوزان") == "beda"
        assert not edisi._pengarang_terima("ابن أبي العز", "صالح آل الشيخ")  # dua pengarang terisi tidak boleh lolos via `ragu`
        assert edisi.cocok_pengarang("ابن حزم", "ابن باز") == "beda"
        assert not edisi._pengarang_terima("محمد بن أحمد", "صالح الفوزان")  # dua pengarang terisi tidak boleh lolos via `ragu`
        assert edisi.cocok_pengarang("أحمد بن عبد الحليم بن تيمية الحراني", "ابن تيمية") == "sama"
        assert edisi.hubungan_judul("السنن الكبرى", "السنن الصغرى") == "beda"
        assert edisi.hubungan_judul("صحيح مسلم", "مختصر صحيح مسلم") == "terkait"
        assert edisi.hubungan_judul("صحيح مسلم", "صحيح مسلم بشرح النووي") == "terkait"
        assert edisi.hubungan_judul("فيض القدير", "فيض القدير شرح الجامع الصغير") == "sama"
        assert edisi.hubungan_judul("الجامع لأحكام القرآن", "الجامع لأحكام القرآن") == "sama"

        # 4. Riwayat lain satu karya tidak ditempatkan bersama cetakan riwayat yang sedang dibuka.
        kode, out_e5 = jalan("edisi", "1699")
        bag_cetak, _, riwayat = out_e5.partition("Riwayat lain di Shamela")
        assert kode == 0 and "Shamela 28107" in bag_cetak, out_e5
        for sid in ("8140", "16050"):
            assert f"Shamela {sid}" not in bag_cetak and f"Shamela {sid}" in riwayat, out_e5

        # 5. `rawi` menyajikan sumber penilaian sebagaimana tercatat.
        kode, out_r1 = jalan("rawi", "1681", "1", "31")
        assert kode == 0, out_r1
        assert "#84: البخاري (#5495) > إسماعيل بن أبي أويس (#676) > مالك بن أنس بن مالك (#5361)" in out_r1, out_r1
        assert "وقيل: إنه تغير بآخره" in out_r1 and "terendah:" not in out_r1 and "اختلط في السند" not in out_r1, out_r1
        kode, out_r2 = jalan("rawi", "1580")
        assert kode == 0 and "إلا أنه ربما دلس" in out_r2 and "peringkat" not in out_r2, out_r2
        kode, out_r3 = jalan("rawi", "1681", "1", "72")
        assert kode == 0 and "(#1562) > [rawi tanpa nomor] > #1" in out_r3, out_r3

        print("lolos uji peta, edisi lintas-katalog, dan tampilan sanad rawi")


if __name__ == "__main__":
    utama()
