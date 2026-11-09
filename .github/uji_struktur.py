# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regresi struktur lewat CLI asli di salinan TEMP, memakai contoh dan kitab asli.
Tidak menjalankan Word: naskah yang kehilangan isi harus ditolak sebelum perakit dipanggil.
"""
import json, os, random, re, shutil, subprocess, sys, tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf8")


def utama():
    with tempfile.TemporaryDirectory(prefix="bahts-struktur-") as t:
        akar = Path(t)
        shutil.copytree(AKAR / "mesin", akar / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__", "*.ttf"))
        for sid in ("_meta", "11223", "1681", "2348", "1726", "1082"):
            shutil.copytree(AKAR / "kitab" / sid, akar / "kitab" / sid)
        f = akar / "uji"
        f.mkdir()
        dasar = (AKAR / "contoh" / "naskah.txt").read_text(encoding="utf8")
        hasil = []

        def cek(nama, teks, gagal=False, pesan="", cmd="cek"):
            (f / "naskah.txt").write_text(teks, encoding="utf8")
            r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), cmd, "uji"],
                               cwd=akar, capture_output=True, encoding="utf8", timeout=60,
                               env=dict(os.environ, PYTHONIOENCODING="utf8"))
            out = r.stdout + r.stderr
            assert (r.returncode != 0) == gagal, (nama, out)
            assert "GALAT MESIN" not in out and "Traceback" not in out, (nama, out)
            assert pesan in out, (nama, out)
            hasil.append(nama)
            return out

        perkiraan = re.compile(r"perkiraan halaman isi [^±]*±(\d+)")  # ± pertama = isi; sesudahnya «seluruh PDF: ±N»
        isi_asli = perkiraan.search(cek("contoh asli", dasar)).group(1)
        # #K sebelum المقدمة (الملخص dst.) bukan halaman isi, juga tanpa @nomor (HALAMAN_ISI rakit.ps1 sama)
        mulakhas = dasar.replace("#K المقدمة", "#K الملخص\n" + "كلمة " * 600 + "\n#K المقدمة", 1)
        isi = perkiraan.search(cek("الملخص panjang sebelum المقدمة", mulakhas)).group(1)
        assert isi == isi_asli, f"perkiraan halaman isi ikut menghitung الملخص: ±{isi}, contoh ±{isi_asli}"
        # riset.txt: jejak langkah connector hanya pernah jadi perhatian, apa pun isinya (cek_seluruh.periksa_riset)
        riset = f / "riset.txt"
        for nama, isi, pesan in (
                ("tanpa riset.txt", None, "tafsir belum tercatat di riset.txt untuk 1 ayat: 1:2 →"),
                ("riset tercatat", "﻿tafsir 1:2\r\n# catatan\r\n", "perhatian (lolos, tetapi lihat sendiri): 0"),
                ("riset rentang", "tafsir 1:1-7\n", "perhatian (lolos, tetapi lihat sendiri): 0"),
                ("riset langkah asing", "ngaco 1:2\ntafsir 1:2\n", "riset.txt baris 1: «ngaco 1:2» tidak dikenal"),
                ("riset belum tanpa alasan", "belum tafsir 1:2\n", "tulis alasannya sesudah objek"),
                ("riset belum beralasan", "belum tafsir 1:2 connector mati\n", "perhatian (lolos, tetapi lihat sendiri): 0"),
                ("riset ayat tidak ada", "tafsir 1:8\n", "tafsir «1:8»: surat/ayat itu tidak ada"),
                ("riset rentang terbalik", "tafsir 1:5-2\n", "tafsir «1:5-2»: rentang ayat harus dari kecil ke besar"),
                ("riset rentang raksasa", "tafsir 2:1-999999999999\n", "surat/ayat itu tidak ada"),
                ("riset kunci tak dipakai", "tafsir 1:2\ntakhrij8 tidakada\n", "takhrij8 «tidakada»: tidak ada {H:…|tidakada}")):
            if isi is None:
                riset.unlink(missing_ok=True)
            else:
                riset.write_text(isi, encoding="utf8", newline="")
            cek(nama, dasar, pesan=pesan)
        riset.write_bytes("tafsir 1:2".encode("utf-16"))
        cek("riset bukan UTF-8", dasar, pesan="riset.txt bukan UTF-8")
        riset.write_text("tafsir 1:" + "9" * 5000 + "\n", encoding="utf8")
        cek("riset angka melampaui batas konversi", dasar, pesan="surat/ayat itu tidak ada")
        riset.write_text("tafsir 1:2\n", encoding="utf8")
        out = cek("riset melewati rentang ayat yang ditolak", dasar.replace("{Q:1:2}", "{Q:1:1-10000}"),
                  True, "surat/ayat itu tidak ada")
        assert "belum tercatat" not in out, out
        riset.unlink()
        out = cek("khilaf dua masalah", dasar.replace("#K الخاتمة", "#B مسألة\nالقول الأول: يجوز.\n#B مسألة أخرى\n"
                                                      "القَوْلُ الأوَّلُ: يجوز.\n#K الخاتمة"))
        assert "untuk 2 masalah khilaf («القول الأول»): ke-1, ke-2 →" in out, out
        riset.write_text("tafsir 1:2\nkhilaf مسألة\n", encoding="utf8")
        out = cek("khilaf satu tercatat", dasar.replace("#K الخاتمة", "#B مسألة\nالقول الأول: يجوز.\n#B مسألة أخرى\n"
                                                        "الرأي الأول: يجوز.\n#K الخاتمة"))
        assert "untuk 1 masalah khilaf («القول الأول»): ke-2 →" in out, out
        riset.unlink()
        # di tengah kalimat (المناقشة, nukilan) bukan masalah baru; «#S القول الأول» lalu «#B أدلة القول الأول» = satu
        out = cek("khilaf bukan masalah baru", dasar.replace("#K الخاتمة", "#S القول الأول\nيجوز.\n#B أدلة القول الأول ومناقشتها\n"
                                                             "اختار القول الأول جماعة، ثم قال: \"والصحيح هو القول الأول\".\n"
                                                             "#K الخاتمة"))
        assert "untuk 1 masalah khilaf («القول الأول»): ke-1 →" in out, out
        # فصل/مبحث yang langsung disusul مبحث/مطلب-nya tanpa تمهيد = perhatian; dengan paragraf pengantar = tidak
        out = cek("judul bertumpuk", dasar.replace("#K الخاتمة", "#F الفصل الثاني\n#B المبحث الأول\n#M المطلب الأول\nنص.\n#K الخاتمة"))
        assert out.count("langsung disusul judul") == 2 and "وفيه مبحثان" in out, out
        # bahts pendek: #F = مبحث, isinya مطلب (contoh pesan mengikuti kata di judul, bukan huruf tandanya)
        out = cek("judul bertumpuk pendek", dasar.replace("#K الخاتمة", "#F المبحث الثاني\n#B المطلب الأول\nنص.\n#K الخاتمة"))
        assert "وفيه مطلبان" in out and "وفيه مبحثان" not in out, out
        out = cek("judul berpengantar", dasar.replace("#K الخاتمة", "#F الفصل الثاني\nوفيه مبحث.\n#B المبحث الأول\n"
                                                      "وفيه مطلب.\n#M المطلب الأول\nنص.\n#K الخاتمة"))
        assert "langsung disusul judul" not in out, out
        # «#B تمهيد» di bawah فصل adalah pengantarnya sendiri
        for tamhid in ("تمهيد", "المبحث التمهيدي"):
            out = cek("judul " + tamhid, dasar.replace("#K الخاتمة", f"#F الفصل الثاني\n#B {tamhid}\nهذا تمهيد الفصل، وفيه مبحثان.\n#K الخاتمة"))
            assert "langsung disusul judul" not in out, out
        # bagian kosong (judul tanpa paragraf isi sebelum judul setingkat/lebih tinggi; #H bukan isi) = satu perhatian per
        # judul, menggantikan «tercetak sendirian»; judul yang membawahi judul lebih rendah bukan kosong; kitab tidak diperiksa
        kosong = dasar.replace("#K المقدمة", "#K الإهداء\n#K المقدمة").replace(
            "#K الخاتمة", "#B المبحث الأول\n#S الأول\n#S الثاني\nنص.\n#M المطلب\n#H\n#B المبحث الثاني\nنص.\n#K الخاتمة")
        out = cek("bagian kosong", kosong)
        assert re.findall(r"bagian «(.+?)» masih kosong", out) == ["الإهداء", "الأول", "المطلب"], out
        assert "tercetak sendirian" not in out, out
        out = cek("bagian kosong di kitab", "@bentuk: kitab\n" + kosong)
        assert "masih kosong" not in out, out
        out = cek("riset {Q:} di bawah #R", dasar + "مرجع {Q:1:1}.\n")
        assert "{Q:1:1}" not in out, out
        for tanda in ("#K", "#F", "#B", "#M", "#S", "#T", "#R", "#H"):
            akhir = tanda + ("" if tanda == "#H" else " نص إضافي")
            cek("isi sesudah pustaka " + tanda, dasar + "\n" + akhir + "\n", True, "sesudah #R")
        # Perintah rakit harus berhenti pada cek; sumber dan generasi hasil lama tetap utuh.
        lama = {"uji.docx": b"DOCX-LAMA", "uji.pdf": b"PDF-LAMA", "laporan.txt": b"LAPORAN-LAMA"}
        for nama, data in lama.items():
            (f / nama).write_bytes(data)
        cek("rakit menolak isi yang akan hilang", dasar + "\n#T نص إضافي\n", True, "Belum dirakit", "rakit")
        assert all((f / nama).read_bytes() == data for nama, data in lama.items())
        assert not list(f.glob(".rakit-*"))

        for salah, benar in (("fromat", "format"), ("angka_ayta", "angka_ayat"), ("halaman_bru", "halaman_baru")):
            cek("salah ketik " + salah, f"@{salah}: latin\n" + dasar, True, "maksudnya @" + benar)
        cek("@pustaka nilai salah", "@pustaka: awal\n" + dasar, True, "@pustaka: «awal» tidak dikenal")
        cek("@pustaka: akhir diterima", "@pustaka: akhir\n" + dasar)
        # «000000000» dulu ada di contoh/naskah.txt, tersalin ke bahts nyata, lalu tercetak di sampul sebagai nomor mahasiswa
        for nol in ("000000000", "٠٠٠٠٠٠٠٠٠"):
            cek("@nim nol " + nol, dasar.replace("@nim: -", "@nim: " + nol), True, "tercetak di sampul sebagai nomor mahasiswa")
        cek("@nim asli diterima", dasar.replace("@nim: -", "@nim: 123456789"))

        # @catatan_kaki/@spasi menimpa satu nilai profil @format di bahan yang dibaca rakit.ps1; profil lain tetap
        sys.path.insert(0, str(akar / "mesin"))
        from berkas import bahan
        profil = json.loads((akar / "mesin" / "format.json").read_text(encoding="utf8"))
        format_bahan = lambda: json.loads(bahan(f).read_text(encoding="utf8"))["format"]
        dengan = lambda baris: dasar.replace("@format: imam_ayat16\n", baris)
        cek("@catatan_kaki dan @spasi menimpa profil", dengan("@format: tatbiqi\n@catatan_kaki: bersambung\n@spasi: 1.5\n"))
        assert format_bahan() == {**profil["tatbiqi"], "catatan_ulang_tiap_halaman": False, "spasi": 1.5}, format_bahan()
        cek("@catatan_kaki: ulang", dengan("@format: imam_ayat16_bersambung\n@catatan_kaki: ulang\n"))
        assert format_bahan() == {**profil["imam_ayat16_bersambung"], "catatan_ulang_tiap_halaman": True}, format_bahan()
        cek("@spasi: 1", dengan("@format: tatbiqi_15\n@spasi: 1\n"))
        assert format_bahan() == {**profil["tatbiqi_15"], "spasi": 1}, format_bahan()
        cek("profil tanpa kunci timpa", dengan("@format: tatbiqi_15\n"))
        assert format_bahan() == profil["tatbiqi_15"], format_bahan()
        cek("@catatan_kaki nilai salah", dengan("@format: tatbiqi\n@catatan_kaki: bersambng\n"), True,
            "@catatan_kaki: «bersambng» tidak dikenal (yang ada: bersambung, ulang)")
        cek("@spasi nilai salah", dengan("@format: tatbiqi\n@spasi: 1,5\n"), True, "@spasi: «1,5» tidak dikenal (yang ada: 1, 1.5)")
        cek("salah ketik catatan_kaki", "@catatan_kaky: bersambung\n" + dasar, True, "maksudnya @catatan_kaki")

        kutipan = '«توحيد الربوبية وهو إفراد الله تعالى بالخلق والملك والتدبير»'
        catatan = '[^رسالة في القضاء والقدر، ابن عثيمين، ص5. <<11223|-|5>>]'
        teks = "قال الشيخ: " + kutipan + catatan
        sisip = lambda s: dasar.replace("#K الخاتمة", s + "\n#K الخاتمة")
        cek("catatan penjelasan berurutan", sisip(teks + '[^حاشية توضيحية.].'))
        cek("kutipan melintasi catatan penjelasan", sisip(
            'قال الشيخ: «توحيد الربوبية[^حاشية توضيحية.] وهو إفراد الله تعالى بالخلق والملك والتدبير»' + catatan + '.'))
        cek("catatan kedua sesudah tanda baca", sisip(teks + '، [^حاشية توضيحية.].'))
        cek("dua sumber untuk satu nukilan", sisip(teks + catatan + '.'))
        cek("kutipan baru tetap perlu bukti", sisip(teks + ' ثم قال: «هذا كلام لم يقله المؤلف»[^توضيح.].'), True, "tanpa bukti")
        cek("kutipan kedua berbukti tetap dicek", sisip(teks + ' ثم قال: ' + kutipan + catatan + '.'))
        for halaman, gagal in ((170, True), (171, False)):
            cek("kepala hadits Bukhari " + str(halaman), sisip(
                f"هذا موضع الحديث[^أخرجه البخاري، رقم الحديث (856)، 1/{halaman}. <<1681|1|{halaman}|#856>>]."), gagal)
        cek("lanjutan hadits tetap sah", sisip("هذا موضع الحديث[^رياض الصالحين، النووي، ص10. <<2348|-|10|#2>>]."))
        # takhrij beberapa bukti: kutipan dicek ke tiap bukti tanpa potongan. Bukti kitab lain yang tidak memuatnya tetap
        # GAGAL, tetapi pesannya menunjuk bukti yang memuatnya dan bentuk berpotongan untuk bukti derajat/takhrij lain
        takhrij = ('قال: «نهى رسول الله ﷺ عن بيع العربان»[^أخرجه أبو داود، كتاب البيوع، باب في العربان، رقم الحديث (3502)، '
                   '3/283، وهو حديث ضعيف، وانظر: سبل السلام، 5/41. <<1726|3|283>> <<1082|5|41{}>>].')
        cek("bukti derajat tanpa potongan", sisip(takhrij.format("")), True,
            "kutipan sebelum catatan kaki ada di <<1726|3|283>>, tetapi tidak di <<1082|5|41>>")
        out = cek("bukti derajat tanpa potongan: bentuk yang ditunjuk", sisip(takhrij.format("|واختلف الفقهاء في جواز هذا البيع")))
        assert "| GAGAL: 0" in out, out
        # lafaz riwayat lain («teks berbeda», bukan «TIDAK KETEMU»), kutipannya terbukti di bukti berpotongan #nomor
        cek("riwayat berlafaz lain sesudah bukti #nomor", sisip(
            'قال ﷺ: «فمن كانت هجرته إلى دنيا يصيبها، أو إلى امرأة ينكحها، فهجرته إلى ما هاجر إليه»[^أخرجه البخاري، '
            'رقم الحديث (1)، 1/6، وأبو داود، رقم الحديث (2201)، 2/262. <<1681|1|6|#1>> <<1726|2|262>>].'), True,
            "kutipan sebelum catatan kaki ada di <<1681|1|6>>, tetapi tidak di <<1726|2|262>> (teks berbeda")
        cek("kutipan palsu tetap GAGAL walau dua bukti", sisip(takhrij.replace("العربان»", "الكلب»").format("")), True,
            "teks berbeda dengan kitab 1726")

        for akhir in (",", ";", ":", "]", "…", "）", "\u200f,\u200f", ". اهـ,", " انتهى كلامه؛"):
            cek("kutipan palsu dengan tanda baca " + repr(akhir), sisip(
                'قال الشيخ: «القدر سر مكشوف»' + akhir +
                '[^رسالة في القضاء والقدر، ابن عثيمين، ص5. <<11223|-|5|توحيد الربوبية وهو إفراد الله>>].'),
                True, "kutipan sebelum catatan kaki: teks TIDAK KETEMU")
            cek("kutipan sah dengan tanda baca " + repr(akhir), sisip('قال الشيخ: ' + kutipan + akhir + catatan + '.'))

        # Beban besar dengan teks/rujukan asli, tanpa jaringan atau Word.
        out = cek("2000 nukilan dan 4000 catatan kaki", sisip((teks + '[^حاشية توضيحية.].\n') * 2000))
        assert "catatan kaki=4002" in out and "| GAGAL: 0" in out
        out = cek("500 data salah ketik", "@fromat: imam_ayat16\n" * 500 + dasar, True)
        assert "| GAGAL: 500" in out

        def bahts(*argumen):
            return subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), *argumen], cwd=akar, capture_output=True,
                                  encoding="utf8", timeout=60, env=dict(os.environ, PYTHONIOENCODING="utf8"))

        r = bahts("baru", "bahts/ahmad/ikhlas", "الإخلاص")
        assert r.returncode == 0 and (akar / "bahts" / "ahmad" / "ikhlas" / "naskah.txt").exists(), r.stdout + r.stderr
        (akar / "bahts" / "ahmad" / "ikhlas" / "naskah.txt").write_text(dasar, encoding="utf8")
        assert bahts("cek", "bahts/ahmad/ikhlas").returncode == 0
        assert "Folder ikhlas sudah ada" in bahts("baru", "bahts/ahmad/Ikhlas", "الإخلاص").stderr
        assert "bahts/ahmad/ikhlas" in bahts("cek", "ikhlas").stderr  # nama pendek menunjuk tempatnya
        assert bahts("baru", "mesin/ikhlas", "الإخلاص").returncode != 0 and not (akar / "mesin" / "ikhlas").exists()
        hasil.append("bahts bersarang per orang")
        # sub-judul « - …» tercetak di sampul: `baru` mengingatkan supaya tidak ditambah sendiri
        assert "Sub-judul" not in r.stdout, r.stdout
        r = bahts("baru", "bahts/ahmad/sub", "الإخلاص - دراسة موضوعية")
        assert r.returncode == 0 and "Sub-judul sampul «دراسة موضوعية»" in r.stdout, r.stdout + r.stderr
        hasil.append("peringatan sub-judul di baru")
        # sampul_saya.txt = data pemilik repo: tidak boleh tercetak di sampul bahts/<orang lain>/…
        saya = akar / "sampul_saya.txt"
        saya.write_text("@nama: صاحب المستودع\n@nim: 111\n@thalibah: ya\n@sampul: mahad\n@angka: latin\n", encoding="utf8")
        r = bahts("baru", "bahts/umar/a", "الإخلاص")
        isi = (akar / "bahts" / "umar" / "a" / "naskah.txt").read_text(encoding="utf8")
        assert r.returncode == 0 and "صاحب" not in isi and "@nim: 111" not in isi and "thalibah" not in isi, isi
        assert "mahad" not in isi and "@angka: latin" in isi and "tidak diambil dari sampul_saya.txt" in r.stdout, isi + r.stdout
        assert "Tanyakan ke «umar»" in r.stdout and "boleh ditulis sekali" not in r.stdout, r.stdout
        r = bahts("baru", "Bahts/zaid/a", "الإخلاص")  # huruf besar: di Windows folder yang sama
        assert "صاحب" not in (akar / "Bahts" / "zaid" / "a" / "naskah.txt").read_text(encoding="utf8"), r.stdout
        (akar / "bahts" / "umar" / "a" / "naskah.txt").write_text(isi.replace("@nama:", "@nama: عمر", 1), encoding="utf8")
        r = bahts("baru", "bahts/umar/b", "الإخلاص")
        isi = (akar / "bahts" / "umar" / "b" / "naskah.txt").read_text(encoding="utf8")
        assert "@nama: عمر" in isi and "bahts/umar/a/naskah.txt" in r.stdout, isi + r.stdout
        r = bahts("baru", "milikku", "الإخلاص")
        assert "@nama: صاحب المستودع" in (akar / "milikku" / "naskah.txt").read_text(encoding="utf8"), r.stdout
        saya.unlink()
        hasil.append("data diri sampul_saya.txt tidak ke bahts orang lain")

        # Label wajib punya isi, dan harus satu kata utuh; catatan kaki bukan isi label di matan.
        studi = "بحث باحث، 2020م. وجه الاتفاق: الموضوع. وجه الاختلاف: النطاق. التقويم: محدود."
        def dirasat(teks):
            return cek("label الدراسات السابقة", sisip("#S الدراسات السابقة\n" + teks))

        for nama in ("وجه الاتفاق:", "وجه الاختلاف:", "التقويم:"):
            isi_label = {"وجه الاتفاق:": "الموضوع.", "وجه الاختلاف:": "النطاق.", "التقويم:": "محدود."}[nama]
            out = dirasat(studi.replace(isi_label, "..."))
            assert f"«{nama}» masih kosong" in out, out
            out = dirasat(studi.replace(nama, "عدم" + nama))
            assert f"belum ada «{nama}»" in out, out
        out = dirasat("بحث باحث، 2020م. وجه الاتفاق: وجه الاختلاف: التقويم:")
        assert out.count("masih kosong") == 3, out
        out = dirasat(studi.replace("الموضوع.", "[^توضيح من المحقق.]"))
        assert "«وجه الاتفاق:» masih kosong" in out, out
        out = dirasat(studi.replace("وجه الاتفاق:", "وأوجه الاتفاق:").replace("وجه الاختلاف:", "وأوجه الافتراق:"))
        assert "belum ada «" not in out and "masih kosong" not in out, out
        # awalan ف seperti و: label tetap dikenali (pola sebelum #153 juga menerimanya)
        out = dirasat(studi.replace("وجه الاتفاق:", "فوجه الاتفاق:").replace("التقويم:", "فالتقويم:"))
        assert "belum ada «" not in out and "masih kosong" not in out, out
        out = dirasat(studi.replace("وجه الاتفاق:", "اوجه الاتفاق:").replace("وجه الاختلاف:", "وإوجه الاختلاف:"))
        assert "belum ada «" not in out and "masih kosong" not in out, out
        for tanda in ("#K", "#F", "#B", "#M", "#S"):
            out = cek("tingkat الدراسات السابقة", sisip(tanda + " الدِّرَاسَاتُ السَّابِقَةُ\n" + studi))
            assert "الدراسات السابقة: PDF-nya belum dibaca" in out, out
        out = dirasat(studi + "\n#S قسم آخر\nبحث باحث، 2021م.")
        assert out.count("الدراسات السابقة:") == 1, out
        rng = random.Random(148)
        for _ in range(36):
            nama = rng.choice(("وجه الاتفاق:", "وجه الاختلاف:", "التقويم:"))
            isi_label = {"وجه الاتفاق:": "الموضوع.", "وجه الاختلاف:": "النطاق.", "التقويم:": "محدود."}[nama]
            # Properti: tanda baca dan angka berapa pun tidak mengisi pembahasan yang diwajibkan label.
            kosong = "".join(rng.choices(" .،؛:-_0123456789٠١٢٣", k=rng.randrange(1, 60)))
            out = dirasat(studi.replace(isi_label, kosong))
            assert f"«{nama}» masih kosong" in out, out
        hasil.append("label الدراسات السابقة utuh dan berisi, di tiap tingkat judul")

        # Salinan PDF: tanpa keluaran_saya.txt tidak ada apa-apa; dengan berkas itu tersalin per orang.
        salin = ("import sys; sys.argv=['bahts']; import bahts\n"
                 "f = bahts.AKAR / 'bahts' / 'ahmad' / 'ikhlas'\n"
                 "(f / 'hasil.pdf').write_bytes(b'PDF')\n"
                 "bahts.salin_keluaran(f, 'hasil')")
        jalan = lambda: subprocess.run([sys.executable, "-c", salin], cwd=akar / "mesin", capture_output=True, encoding="utf8", timeout=60)
        assert jalan().returncode == 0
        (akar / "keluaran_saya.txt").write_text(str(akar / "keluar") + "\n", encoding="utf8")
        r = jalan()
        assert (akar / "keluar" / "ahmad" / "hasil.pdf").read_bytes() == b"PDF", r.stdout + r.stderr
        hasil.append("salinan PDF per orang")

        # `tahap`: keadaan dibaca ulang dari barang aslinya. Yang diam-diam menyesatkan: PDF lama dilaporkan TERKINI sesudah
        # naskah diubah, folder .rakit-* tanpa penanda disuruh/dibiarkan dibuang, atau rakit yang jalan tidak terlihat.
        ikhlas = akar / "bahts" / "ahmad" / "ikhlas"
        (ikhlas / "riset.txt").write_text("tafsir 1:2\n", encoding="utf8")

        def tahap():
            r = bahts("tahap", "bahts/ahmad/ikhlas")
            assert r.returncode == 0 and "Traceback" not in r.stderr, r.stdout + r.stderr
            return r.stdout

        out = tahap()
        assert "NASKAH=LOLOS" in out and "HASIL=BELUM" in out and 'rakit "bahts/ahmad/ikhlas"' in out, out
        sidik = __import__("hashlib").sha256((ikhlas / "naskah.txt").read_bytes()).hexdigest()
        (ikhlas / "ikhlas.pdf").write_bytes(b"%PDF")
        (ikhlas / "laporan.txt").write_text(f"NASKAH_SHA256={sidik}\nHALAMAN=1\n", encoding="utf8")
        out = tahap()
        assert "HASIL=TERKINI" in out and 'bukti "bahts/ahmad/ikhlas"' in out, out
        (ikhlas / "laporan-fasl1.txt").write_text(f"POTONGAN=--fasl 1: المقدمة\nNASKAH_SHA256={sidik}\n", encoding="utf8")
        (ikhlas / "ikhlas - المقدمة.pdf").write_bytes(b"%PDF")
        assert "HASIL fasl1=TERKINI" in tahap()
        (ikhlas / "naskah.txt").write_text(dasar + "\n", encoding="utf8")
        out = tahap()
        assert "HASIL=USANG" in out and "HASIL fasl1=USANG" in out and "rakit ulang" in out, out
        assert 'rakit "bahts/ahmad/ikhlas" --fasl 1\n' in out, out  # yang terakhir dirakit = potongan itu
        os.utime(ikhlas / "laporan-fasl1.txt", (1, 1))
        assert 'rakit "bahts/ahmad/ikhlas"\n' in tahap()  # seluruh naskah dirakit sesudahnya: itu yang menentukan
        (ikhlas / "riset.txt").unlink()  # perhatian yang bertahan: perintahnya tetap `rakit`, bukan `cek` berulang
        out = tahap()
        assert "NASKAH=PERHATIAN" in out and "HASIL=USANG" in out and '-> ' in out, out
        assert out.rstrip().endswith('rakit "bahts/ahmad/ikhlas"'), out
        (ikhlas / "riset.txt").write_text("tafsir 1:2\n", encoding="utf8")
        (ikhlas / "naskah.txt").write_text("@fromat: imam\n" + dasar, encoding="utf8")
        out = tahap()
        assert "NASKAH=GAGAL" in out and 'cek "bahts/ahmad/ikhlas"' in out and "HASIL=USANG" in out, out
        (ikhlas / "naskah.txt").write_text(dasar, encoding="utf8")
        for nama, penanda, harus in ((".rakit-lama", None, "=ASING"), (".rakit-simpan", "JANGAN_DIHAPUS.txt", "=SIMPAN"),
                                     (".rakit-sisa", "rakit.sementara", "=SEMENTARA")):
            (ikhlas / nama).mkdir()
            if penanda:
                (ikhlas / nama / penanda).write_text("")
        out = tahap()
        assert "FOLDER_KERJA .rakit-lama=ASING" in out and "FOLDER_KERJA .rakit-simpan=SIMPAN" in out, out
        assert "FOLDER_KERJA .rakit-sisa=SEMENTARA" in out, out
        assert "PERLU PEMAKAI: .rakit-lama, .rakit-simpan " in out and all((ikhlas / n).is_dir() for n in
                                                                          (".rakit-lama", ".rakit-simpan", ".rakit-sisa")), out
        (ikhlas / "_arsip" / "rakit-x").mkdir(parents=True)
        out = tahap()
        assert "ARSIP _arsip/rakit-x" in out and "_arsip/rakit-x tidak pernah dibuang" in out, out
        for nama in (".rakit-lama", ".rakit-simpan", ".rakit-sisa", "_arsip"):
            shutil.rmtree(ikhlas / nama)

        def pegang_rakit(apa, naskah_):  # rakit yang sedang jalan = proses yang memegang kunci rakit
            (ikhlas / "naskah.txt").write_text(naskah_, encoding="utf8")
            p = subprocess.Popen([sys.executable, "-c", "import sys, time; from pathlib import Path; import berkas\n"
                                  f"with berkas.kunci(Path('_tmp/rakit.pekerjaan'), apa='{apa}'):\n"
                                  "    print('pegang', flush=True); time.sleep(60)"],
                                 cwd=akar / "mesin", stdout=subprocess.PIPE, encoding="utf8")
            try:
                assert p.stdout.readline().strip() == "pegang"
                return tahap()
            finally:
                p.kill()
                p.wait()
        out = pegang_rakit("bahts/ahmad/ikhlas", dasar)
        assert "RAKIT=JALAN: bahts/ahmad/ikhlas, proses" in out and "BERIKUTNYA: rakit bahts ini sedang jalan" in out, out
        # rakit bahts lain tidak menahan membetulkan naskah ini
        out = pegang_rakit("bahts/umar/a", "@fromat: imam\n" + dasar)
        assert "RAKIT=JALAN: bahts/umar/a" in out and 'BERIKUTNYA: betulkan' in out, out
        (ikhlas / "naskah.txt").write_text(dasar, encoding="utf8")
        assert "RAKIT=BEBAS" in tahap()
        # perhatian yang tidak bisa dibereskan tidak menahan: PDF TERKINI -> pemeriksa, bukan rakit lagi
        (ikhlas / "riset.txt").unlink()
        (ikhlas / "laporan.txt").write_text(f"NASKAH_SHA256={sidik}\n", encoding="utf8")
        out = tahap()
        assert "NASKAH=PERHATIAN" in out and "HASIL=TERKINI" in out and 'bukti "bahts/ahmad/ikhlas"' in out, out
        # laporan versi lama tanpa NASKAH_SHA256: tidak diketahui, bukan «naskah diubah»
        (ikhlas / "riset.txt").write_text("tafsir 1:2\n", encoding="utf8")
        (ikhlas / "laporan.txt").write_text("HALAMAN=1\n", encoding="utf8")
        out = tahap()
        assert "HASIL=TIDAK_DIKETAHUI" in out and "naskah diubah" not in out.split("HASIL fasl")[0], out
        # bertahap per فصل: potongan terakhir yang dirakit menentukan; potongan lama yang USANG tidak disuruh rakit
        (ikhlas / "laporan.txt").unlink()
        (ikhlas / "laporan-fasl1.txt").write_text(f"POTONGAN=--fasl 1: المقدمة\nNASKAH_SHA256=lama\n", encoding="utf8")
        (ikhlas / "laporan-fasl2.txt").write_text(f"POTONGAN=--fasl 2: الفصل\nNASKAH_SHA256={sidik}\n", encoding="utf8")
        (ikhlas / "ikhlas - الفصل.pdf").write_bytes(b"%PDF")
        (ikhlas / "laporan-fasl10.txt").write_text("HALAMAN=1\n", encoding="utf8")  # tanpa baris POTONGAN
        os.utime(ikhlas / "laporan-fasl1.txt", (1, 1))
        os.utime(ikhlas / "laporan-fasl10.txt", (2, 2))
        out = tahap()
        assert "HASIL fasl1=USANG" in out and "HASIL fasl2=TERKINI" in out and "HASIL fasl10=TIDAK_DIKETAHUI" in out, out
        assert out.index("fasl2=") < out.index("fasl10="), out
        assert 'bukti "bahts/ahmad/ikhlas"' in out, out
        # folder kerja yang gagal dibuang sebagian tetap SEMENTARA (dicoba lagi), tidak jadi ASING
        sys.path.insert(0, str(akar / "mesin"))
        import berkas as berkas_
        sisa = ikhlas / ".rakit-sebagian"
        (sisa / "word").mkdir(parents=True)
        (sisa / "rakit.sementara").write_text("")
        (sisa / "buka.txt").write_text("")
        with open(sisa / "buka.txt") as _terbuka:  # Windows: berkas yang terbuka tidak bisa dihapus
            hilang = berkas_.FolderKerja(sisa).buang()
            assert not hilang or os.name != "nt", "berkas terbuka ikut terhapus"
            if not hilang:
                assert berkas_.FolderKerja(sisa).keadaan() is berkas_.FolderKerja.Keadaan.SEMENTARA, list(sisa.iterdir())
        if sisa.exists():
            assert berkas_.FolderKerja(sisa).buang() and not sisa.exists()
        hasil.append("tahap: naskah, hasil (juga --fasl dan laporan lama), perhatian tidak menahan, folder .rakit-*, "
                     "_arsip, rakit bahts ini dan bahts lain; folder kerja setengah terbuang tetap SEMENTARA")
        print(f"uji struktur: {len(hasil)} skenario sesuai, termasuk beban 2000 nukilan/4000 catatan kaki dan 500 data salah ketik")


if __name__ == "__main__":
    utama()
