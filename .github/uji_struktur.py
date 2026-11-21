# SPDX-License-Identifier: AGPL-3.0-or-later
"""Putusan `cek` atas @data, susunan judul, riset.txt, dan الدراسات السابقة, serta `baru` dan `tahap`, lewat CLI asli
di salinan TEMP dengan contoh dan kitab asli. Tidak menjalankan Word: naskah yang kehilangan isi harus ditolak
sebelum perakit dipanggil.
"""
import json, os, random, re, shutil, struct, subprocess, sys, tempfile, zipfile
from pathlib import Path
from bantu import salin_mesin

AKAR = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf8")


def utama():
    with tempfile.TemporaryDirectory(prefix="bahts-struktur-") as t:
        akar = Path(t)
        salin_mesin(akar, ("_meta", "11223", "1681", "2348", "1726", "1082"), huruf=False)
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
        asli = cek("contoh asli", dasar)
        isi_asli = perkiraan.search(asli).group(1)
        for nama in ("NUL", "con", "COM1", "LPT9.txt", "COM¹", "AUX .data", "hasil\x01baru"):
            cek("nama hasil terlarang Windows", "@berkas: " + nama + "\n" + dasar, True, "@berkas:")
        for nama in ("CON sesuai", "NUL catatan.txt", "COM10", "بحث علمي"):
            cek("nama hasil sah bukan perangkat", "@berkas: " + nama + "\n" + dasar)
        gambar_asli = (AKAR / "contoh/jebakan/gambar.png").read_bytes()
        for isi in (gambar_asli[:24], gambar_asli[:16] + b"\0" * 4 + gambar_asli[20:],
                    gambar_asli[:20] + b"\0" * 4 + gambar_asli[24:], gambar_asli[:-12]):
            (f / "rusak.png").write_bytes(isi)
            cek("gambar terpotong atau dimensi nol", dasar.replace("#K الخاتمة", "#G rusak.png | صورة\n#K الخاتمة"),
                True, "bukan PNG/JPG yang terbaca")
        for isi in (gambar_asli + b"\0" * 10, gambar_asli + b"\r\n", gambar_asli[:-1]):  # byte sesudah IEND = PNG utuh
            (f / "lebih.png").write_bytes(isi)
            teks = dasar.replace("#K الخاتمة", "#G lebih.png | صورة\n#K الخاتمة")
            if isi == gambar_asli[:-1]:  # CRC IEND terpotong satu byte: terpotong
                cek("PNG kurang satu byte", teks, True, "bukan PNG/JPG yang terbaca")
            else:
                cek("PNG utuh berbyte tambahan sesudah IEND", teks)
        # @minimal_halaman: bawaan 25 halaman seluruh PDF (perkiraan); contoh menulis 0 karena ±8 halaman
        assert "kurang dari" not in asli and "@minimal_halaman: 0\n" in dasar, asli
        # @logo: berwarna = rakit.ps1 menukar word/media/image2.png sampul_qism.docx dengan milik sampul_jakarta.docx
        cek("logo berwarna di sampul qism", "@logo: berwarna\n" + dasar)
        cek("logo tidak dikenal", "@logo: biru\n" + dasar, True, "@logo: «biru» tidak dikenal")
        for sampul, pesan in (("@sampul: jakarta", "@sampul: jakarta memakai logonya sendiri"),
                              ("@sampul: mahad", "@sampul: mahad memakai logonya sendiri")):
            cek("logo berwarna bukan di sampul qism", f"@logo: berwarna\n{sampul}\n" + dasar, True, pesan)
        logo = {n: zipfile.ZipFile(AKAR / "mesin" / f"sampul_{n}.docx").read("word/media/image2.png") for n in ("qism", "jakarta")}
        assert logo["qism"] != logo["jakarta"], "logo sampul qism dan jakarta sama: @logo: berwarna tidak mengubah apa pun"
        for n, b in logo.items():  # logo tegak (tinggi > lebar); gambar kop sampul melebar: urutan gambar templat tidak bergeser
            lebar, tinggi = struct.unpack(">II", b[16:24])
            assert b[1:4] == b"PNG" and tinggi > lebar, f"word/media/image2.png sampul_{n}.docx bukan logo tegak"
        tanpa_batas = dasar.replace("@minimal_halaman: 0\n", "")
        cek("halaman kurang dari bawaan", tanpa_batas, pesan="halaman, kurang dari 25 (bawaan 25)")
        cek("batas halaman dari dosen, angka hindi", dasar.replace("@minimal_halaman: 0", "@minimal_halaman: ٩"),
            pesan="kurang dari 9 («@minimal_halaman: ٩»)")
        out = cek("batas halaman terpenuhi", dasar.replace("@minimal_halaman: 0", "@minimal_halaman: 2"))
        assert "kurang dari" not in out, out
        cek("@minimal_halaman kosong", dasar.replace("@minimal_halaman: 0", "@minimal_halaman:"), True, "@minimal_halaman: kosong")
        cek("@minimal_halaman bukan bilangan", dasar.replace("@minimal_halaman: 0", "@minimal_halaman: banyak"), True,
            "bukan bilangan bulat")
        out = cek("@bentuk: kitab tidak dinilai halamannya", tanpa_batas.replace("@format:", "@bentuk: kitab\n@format:", 1))
        assert "halaman, kurang dari" not in out, out
        # @minimal_kitab: bawaan tidak dinilai (contoh asli di atas: tanpa «kurang dari»); hanya kalau dosen menulis batasnya
        dua = dasar.replace("@minimal_halaman: 0", "@minimal_halaman: 0\n@minimal_kitab: 2")
        cek("kitab kurang dari batas dosen", dua, pesan="baru 1 kitab (selain القرآن الكريم), kurang dari 2 («@minimal_kitab: 2»)")
        cek("batas kitab angka hindi", dua.replace("@minimal_kitab: 2", "@minimal_kitab: ٢"),
            pesan="kurang dari 2 («@minimal_kitab: ٢»)")
        for nama, nilai in (("batas kitab nol", "0"), ("batas kitab terpenuhi", "1")):
            out = cek(nama, dua.replace("@minimal_kitab: 2", f"@minimal_kitab: {nilai}"))
            assert "baru 1 kitab" not in out, (nama, out)
        cek("batas kitab bukan bilangan", dua.replace("@minimal_kitab: 2", "@minimal_kitab: dua puluh"), True, "bukan bilangan bulat")
        out = cek("@tanpa: pustaka tidak dihitung", dua.replace("@minimal_kitab: 2\n", "@minimal_kitab: 2\n@tanpa: pustaka\n").split("#R")[0])
        assert "baru 0 kitab" not in out and "baru 1 kitab" not in out, out
        cek("@minimal_kitab kosong", dua.replace("@minimal_kitab: 2", "@minimal_kitab:"), True, "@minimal_kitab: kosong")
        # mushaf ditulis lain tetap bukan kitab; kitab berjudul «القرآن …» tetap kitab; baris kembar dihitung sekali
        kitab = "رسالة في القضاء والقدر، محمد بن صالح بن محمد العثيمين، دار الوطن، 1423هـ.\n"
        for nama, ganti, kurang in (
                ("القران tanpa madda bukan kitab", ("القرآن الكريم.\n", "القُرَانُ الكَريم، رواية حفص.\n"), True),
                ("المصحف bukan kitab", ("القرآن الكريم.\n", "المصحف الشريف برواية حفص.\n"), True),
                ("kitab berjudul القرآن tetap kitab", (kitab, kitab + "القرآن والسنة في مواجهة البدع، فلان، 1430هـ.\n"), False),
                ("#R kembar dihitung sekali", (kitab, kitab + "**رسالة في القضاء والقدر**، محمد بن صالح بن محمد العثيمين، دار الوطن، 1423هـ\n"), True)):
            kembar = nama.startswith("#R kembar")  # selalu bisa dibereskan: GAGAL
            out = cek(nama, dua.replace(*ganti), kembar, "baris kembar (dihitung sekali)" if kembar else "")
            assert ("baru 1 kitab" in out) == kurang, (nama, out)
        # kitab berbukti di catatan kaki harus ada di #R (cek_rujukan.kitab_tanpa_pustaka): judul katalog, judul kartu,
        # judul seperti di catatan kaki, atau judul #R yang disingkat; @pustaka_gaya: muallif = judul di __…__
        hilang = "«رسالة في القضاء والقدر» (<<11223|…>>) dirujuk di catatan kaki tetapi tidak ada di المصادر والمراجع (#R)"
        lain = "الأصول من علم الأصول، محمد بن صالح العثيمين، دار ابن الجوزي، 1426هـ.\n"
        out = cek("kitab berbukti tidak ada di #R", dasar.replace(kitab, lain), pesan=hilang)
        assert "pustaka <folder>" in out, out
        for nama, ganti in (("judul #R disingkat", "رسالة في القضاء، محمد بن صالح العثيمين، دار الوطن، 1423هـ.\n"),
                            ("judul #R gaya muallif", "**العثيمين، محمد بن صالح** (ت 1421هـ). __رسالة في القضاء والقدر__. دار الوطن، 1423هـ.\n"),
                            ("judul #R dengan pengarang tempelan", "رسالة في القضاء والقدر للعثيمين، دار الوطن، 1423هـ.\n")):
            out = cek(nama, dasar.replace(kitab, ganti + lain))
            assert "(#R)" not in out, (nama, out)
        # satu catatan kaki, dua sumber dipisah «؛»: judul dan pengarang bagian pertama bukan milik kitab kedua
        dua_sumber = dasar.replace("#K الخاتمة", "نص للاختبار.[^انظر: رسالة في القضاء والقدر، ابن عثيمين، ص5؛ صحيح "
                                   "البخاري، البخاري، 1/6. <<11223|-|5|توحيد الربوبية وهو إفراد الله>> "
                                   "<<1681|1|6|إنما الأعمال بالنيات>>]\n#K الخاتمة", 1)
        bukhari = "صحيح البخاري، محمد بن إسماعيل البخاري، الطبعة السلطانية، بولاق، 1311هـ.\n"
        out = cek("dua sumber «؛» semuanya di #R", dua_sumber.replace(kitab, kitab + bukhari))
        assert "(#R)" not in out, out
        out = cek("dua sumber «؛», sumber kedua tidak di #R", dua_sumber, pesan="(<<1681|…>>) dirujuk di catatan kaki tetapi tidak ada")
        assert "<<11223|…>>) dirujuk" not in out, out
        out = cek("dua sumber «؛», sumber pertama tidak di #R", dua_sumber.replace(kitab, bukhari), pesan=hilang)
        assert "<<1681|…>>) dirujuk" not in out, out
        out = cek("@tanpa: pustaka tidak menilai #R",dasar.replace("@minimal_halaman: 0\n", "@minimal_halaman: 0\n@tanpa: pustaka\n").split("#R")[0])
        assert "(#R)" not in out, out
        # #K sebelum المقدمة (الملخص dst.) bukan halaman isi, juga tanpa @nomor (HALAMAN_ISI rakit.ps1 sama)
        mulakhas = dasar.replace("#K المقدمة", "#K الملخص\n" + "كلمة " * 600 + "\n#K المقدمة", 1)
        isi = perkiraan.search(cek("الملخص panjang sebelum المقدمة", mulakhas)).group(1)
        assert isi == isi_asli, f"perkiraan halaman isi ikut menghitung الملخص: ±{isi}, contoh ±{isi_asli}"
        # «#L **Abstract**» sesudah isi الملخص = halaman sendiri; langsung di bawah judul #K tetap sehalaman dengan judulnya
        for nama, sisip, n in (("Abstract sesudah الملخص beda halaman", "#K الملخص\nنص عربي.\n#L **Abstract**\n#L English text.\n", 2),
                               ("Abstract langsung di bawah #K sehalaman", "#K الملخص\n#L **Abstract**\n#L English text.\n", 1)):
            out = cek(nama, dasar.replace("#K المقدمة", sisip + "#K المقدمة", 1))
            assert f"sebelum المقدمة {n}," in out, (nama, out)
        # riset.txt: jejak langkah connector hanya pernah jadi perhatian, apa pun isinya (cek_seluruh.periksa_riset)
        riset = f / "riset.txt"
        for nama, isi, pesan in (
                ("tanpa riset.txt", None, "tafsir belum tercatat di riset.txt untuk 1 ayat: 1:2 →"),
                ("riset tercatat", "﻿tafsir 1:2\r\n# catatan\r\ncari الربوبية\r\n", "): 0\ncatatan kaki tanpa bukti"),
                ("riset rentang", "tafsir 1:1-7\ncari توحيد الربوبية | 3052 halaman\n", "): 0\ncatatan kaki tanpa bukti"),
                ("riset langkah asing", "ngaco 1:2\ntafsir 1:2\n", "riset.txt baris 1: «ngaco 1:2» tidak dikenal"),
                ("riset belum tanpa alasan", "belum tafsir 1:2\n", "tulis alasannya sesudah objek"),
                ("riset belum beralasan", "belum tafsir 1:2 connector mati\nbelum cari توحيد الربوبية | kuota habis\n",
                 "): 0\ncatatan kaki tanpa bukti"),
                ("riset cari belum tanpa alasan", "tafsir 1:2\nbelum cari توحيد الربوبية\n", "tulis alasannya sesudah «|»"),
                ("riset cari tanpa istilah Arab", "tafsir 1:2\ncari | catatan\n", "tulis istilah huruf Arab yang dicari"),
                # istilah yang tidak tertulis di bagian itu tidak menutupnya, juga yang hanya ada di catatan kaki
                # (judul kitab rujukan) atau di kata urutan judul («المبحث الأول:»)
                ("riset cari istilah lain", "tafsir 1:2\ncari الاستصحاب\n",
                 "cari belum tercatat di riset.txt untuk 1 مبحث: «المبحث الأول: تعريف توحيد الربوبية»"),
                ("riset cari istilah catatan kaki", "tafsir 1:2\ncari القضاء\ncari المبحث\n",
                 "cari belum tercatat di riset.txt untuk 1 مبحث: «المبحث الأول: تعريف توحيد الربوبية»"),
                ("riset ayat tidak ada", "tafsir 1:8\n", "tafsir «1:8»: surat/ayat itu tidak ada"),
                ("riset rentang terbalik", "tafsir 1:5-2\n", "tafsir «1:5-2»: rentang ayat harus dari kecil ke besar"),
                ("riset rentang raksasa", "tafsir 2:1-999999999999\n", "surat/ayat itu tidak ada"),
                ("riset kunci tak dipakai", "tafsir 1:2\ntakhrij8 tidakada\n", "takhrij8 «tidakada»: tidak ada {H:…|tidakada}")):
            if isi is None:
                riset.unlink(missing_ok=True)
            else:
                riset.write_text(isi, encoding="utf8", newline="")
            cek(nama, dasar, pesan=pesan)
        # bahts berفصل: tiap #B wajib, #F berisi #B tidak, #F tanpa #B (التمهيد) wajib
        riset.write_text("tafsir 1:2\ncari الربوبية\n", encoding="utf8")
        out = cek("riset cari berفصل", dasar.replace("#F المبحث الأول: تعريف توحيد الربوبية", "#F التمهيد\nنص التمهيد.\n"
                                                     "#F الفصل الأول: التوحيد\nوفيه مبحث.\n#B المبحث الأول: تعريف توحيد الربوبية"))
        assert "cari belum tercatat di riset.txt untuk 1 مبحث: «التمهيد»" in out, out
        out = cek("riset cari berفصل tercatat", dasar.replace("#F المبحث الأول: تعريف توحيد الربوبية", "#F الفصل الأول: التوحيد\n"
                                                              "وفيه مبحث.\n#B المبحث الأول: تعريف توحيد الربوبية"))
        assert "cari belum tercatat" not in out, out
        # bahts tanpa فصل: isi مطلب (#B) termasuk مبحث (#F) induknya; «#B المبحث» = tingkat مبحث walau #F bukan «الفصل»
        riset.write_text("tafsir 1:2\ncari الاستصحاب\n", encoding="utf8")
        out = cek("riset cari isi مطلب", dasar.replace("#K الخاتمة", "#B المطلب الأول: حجيته\nويظهر للباحث أن الاستصحاب حجة.\n"
                                                       "#K الخاتمة"))
        assert "cari belum tercatat" not in out, out
        out = cek("riset cari #B مبحث", dasar.replace("#F المبحث الأول: تعريف توحيد الربوبية", "#F فصل أول: التوحيد\nوفيه مبحث.\n"
                                                      "#B المبحث الأول: تعريف توحيد الربوبية"))
        assert "untuk 1 مبحث: «المبحث الأول: تعريف توحيد الربوبية»" in out, out
        # kata urutan judul berharakat tidak menutup bagian; istilah sebelum «:» di judul tetap dihitung
        berharakat = dasar.replace("#F المبحث الأول: تعريف توحيد الربوبية", "#F المَبْحَثُ الأَوَّلُ في تعريف الربوبية: لغة")
        for isi, ada in (("cari المبحث\ncari الأول\n", True), ("cari الربوبية\n", False)):
            riset.write_text("tafsir 1:2\n" + isi, encoding="utf8")
            out = cek("riset cari judul berharakat " + isi.split()[1], berharakat)
            assert ("cari belum tercatat" in out) == ada, out
        riset.write_bytes("tafsir 1:2".encode("utf-16"))
        cek("riset bukan UTF-8", dasar, pesan="riset.txt bukan UTF-8")
        cek("riset kitab bukan UTF-8 tetap dilaporkan", "@bentuk: kitab\n" + dasar, pesan="riset.txt bukan UTF-8")
        riset.write_text("tafsir 1:" + "9" * 5000 + "\n", encoding="utf8")
        cek("riset angka melampaui batas konversi", dasar, pesan="surat/ayat itu tidak ada")
        riset.write_text("tafsir 1:2\ncari الربوبية\n", encoding="utf8")
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
        assert "tafsir belum tercatat di riset.txt untuk 1 ayat: 1:2 →" in out, out
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
        # nomor mahasiswa isian nol tercetak di sampul apa adanya
        for nol in ("000000000", "٠٠٠٠٠٠٠٠٠"):
            cek("@nim nol " + nol, dasar.replace("@nim: -", "@nim: " + nol), True, "tercetak di sampul sebagai nomor mahasiswa")
        cek("@nim asli diterima", dasar.replace("@nim: -", "@nim: 123456789"))

        # @catatan_kaki/@spasi menimpa satu nilai profil @format di bahan yang dibaca rakit.ps1; profil lain tetap
        sys.path.insert(0, str(akar / "mesin"))
        from olah import alamat_bahan as bahan
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

        def sidik_naskah(keluaran_cek):
            return re.search(r"^NASKAH_SHA256=(\w+)$", keluaran_cek, re.M)[1]

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
        # awalan ف seperti و: label tetap dikenali
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

        # أبو سليمان، كتابة البحث العلمي: الخاتمة memuat النتائج (ص198); المقدمة رسالة memuat isinya (ص196-197), بحث صفي tidak dinilai
        khatimah = re.search(r"#K الخاتمة\n([^\n]*)\n", dasar)[1]
        out = cek("الخاتمة tanpa النتائج", dasar.replace(khatimah, "هذا آخر ما كتبته في هذا البحث."))
        assert "الخاتمة belum menyebut النتائج" in out, out
        assert "الخاتمة belum" not in cek("الخاتمة dengan النتائج", dasar)
        # «#F الفصل الخامس: الخاتمة» juga الخاتمة
        out = cek("الخاتمة di #F", dasar.replace(khatimah, "هذا آخر ما كتبته في هذا البحث.").replace(
            "#K الخاتمة", "#F الفصل الثاني: الخاتمة"))
        assert "الخاتمة belum menyebut النتائج" in out, out
        out = cek("المقدمة رسالة", dasar.replace("@jenis: مثال تجريبي", "@jenis: رسالة ماجستير"))
        assert "المقدمة belum menyebut: " in out and "قيمة البحث وأهميته" in out, out
        lengkap = dasar.replace("#K المقدمة\n", "#K المقدمة\nموضوع البحث وأهميته وأسباب اختياره وحدوده وإجراءاته ومنهجه "
                                "ومصطلحاته وآفاقه والدراسات السابقة وخطته.\n", 1)
        assert "\n#K المقدمة\n" in dasar and "المقدمة belum" not in cek(
            "المقدمة رسالة lengkap", lengkap.replace("@jenis: مثال تجريبي", "@jenis: رسالة ماجستير"))
        assert "المقدمة belum" not in cek("المقدمة بحث صفي", dasar)
        # bab isi yang judulnya memuat kata itu bukan المقدمة/الخاتمة: «المقدمات اللغوية», «الخاتم في اللغة»
        bab = lengkap.replace("@jenis: مثال تجريبي", "@jenis: رسالة ماجستير").replace(
            "#K المقدمة\n", "#F الفصل الأول: المقدمات اللغوية\nكلام في اللغة.\n#F الفصل الثاني: الخاتم في اللغة\n"
            "كلام آخر في اللغة.\n#K المقدمة\n", 1)
        out = cek("bab isi bernama mirip", bab)
        assert "المقدمة belum" not in out and "الخاتمة belum" not in out, out
        # urutan المصادر gaya muallif: «ابن/أبو» tidak dihitung, «ابن كثير» di ك sesudah «الترمذي» (ص204)
        gaya = dasar.replace("@format: imam_ayat16", "@format: imam_ayat16\n@pustaka_gaya: muallif").replace(
            "رسالة في القضاء والقدر، محمد بن صالح بن محمد العثيمين، دار الوطن، 1423هـ.",
            "**ابن كثير، إسماعيل بن عمر**. __تفسير القرآن العظيم__.\n**أبو داود، سليمان بن الأشعث**. __السنن__.\n"
            "**الترمذي، محمد بن عيسى**. __السنن__.\n**العثيمين، محمد بن صالح**. __رسالة في القضاء والقدر__. دار الوطن، 1423هـ.")
        cek("urutan pustaka muallif", gaya)
        urut = [p.split("،")[0].strip("*") for p in json.loads(bahan(f).read_text(encoding="utf8"))["pustaka"]]
        assert urut == ["القرآن الكريم.", "الترمذي", "أبو داود", "العثيمين", "ابن كثير"], urut
        hasil.append("standar أبو سليمان: الخاتمة, المقدمة رسالة, urutan pustaka muallif")

        # `tahap`: keadaan dibaca ulang dari barang aslinya. Yang diam-diam menyesatkan: PDF lama dilaporkan TERKINI sesudah
        # naskah diubah, folder .rakit-* tanpa penanda disuruh/dibiarkan dibuang, atau rakit yang jalan tidak terlihat.
        ikhlas = akar / "bahts" / "ahmad" / "ikhlas"
        (ikhlas / "riset.txt").write_text("tafsir 1:2\ncari الربوبية\n", encoding="utf8")

        def tahap():
            r = bahts("tahap", "bahts/ahmad/ikhlas")
            assert r.returncode == 0 and "Traceback" not in r.stderr, r.stdout + r.stderr
            return r.stdout

        out = tahap()
        assert "NASKAH=LOLOS" in out and "HASIL=BELUM" in out and 'rakit "bahts/ahmad/ikhlas"' in out, out
        sidik = sidik_naskah(bahts("cek", "bahts/ahmad/ikhlas").stdout)
        (ikhlas / "ikhlas.pdf").write_bytes(b"%PDF")
        (ikhlas / "laporan.txt").write_text(f"NASKAH_SHA256={sidik}\nHALAMAN=1\n", encoding="utf8")
        out = tahap()
        assert "HASIL=TERKINI" in out and 'bukti "bahts/ahmad/ikhlas"' in out, out
        (ikhlas / "laporan-fasl1.txt").write_text(f"POTONGAN=--fasl 1: المقدمة\nNASKAH_SHA256={sidik}\n", encoding="utf8")
        (ikhlas / "ikhlas - المقدمة.pdf").write_bytes(b"%PDF")
        assert "HASIL fasl1=TERKINI" in tahap()
        # CETAK_SHA256: naskah yang hanya berubah di yang tidak tercetak (@minimal_*, baris kosong) tetap TERKINI;
        # satu kata tercetak berubah = USANG. Laporan tanpa CETAK_SHA256 (atas) tetap dinilai dari naskah saja.
        cetak = re.search(r"^CETAK_SHA256=(\w+)$", bahts("cek", "bahts/ahmad/ikhlas").stdout, re.M)[1]
        (ikhlas / "laporan.txt").write_text(f"CETAK_SHA256={cetak}\nNASKAH_SHA256={sidik}\nHALAMAN=1\n", encoding="utf8")
        (ikhlas / "naskah.txt").write_text(dasar.replace("@minimal_halaman: 0", "@minimal_halaman: 3\n"), encoding="utf8")
        assert "HASIL=TERKINI" in tahap(), "setelan cek saja yang berubah: PDF tetap TERKINI"
        (ikhlas / "naskah.txt").write_text(dasar.replace("الحمد لله", "الحمدُ لله", 1), encoding="utf8")
        assert "HASIL=USANG" in tahap(), "kata tercetak berubah: PDF harus USANG"
        (ikhlas / "naskah.txt").write_text(dasar, encoding="utf8")
        (ikhlas / "laporan.txt").write_text(f"NASKAH_SHA256={sidik}\nHALAMAN=1\n", encoding="utf8")
        lalu = (ikhlas / "laporan-fasl1.txt").stat().st_mtime - 10  # potongan tetap yang terakhir dirakit
        os.utime(ikhlas / "laporan.txt", (lalu, lalu))
        (ikhlas / "naskah.txt").write_text(dasar + "\n", encoding="utf8")
        out = tahap()
        assert "HASIL=USANG" in out and "HASIL fasl1=USANG" in out and "rakit ulang" in out, out
        assert 'rakit "bahts/ahmad/ikhlas" --fasl 1\n' in out, out  # yang terakhir dirakit = potongan itu
        os.utime(ikhlas / "laporan-fasl1.txt", (1, 1))
        assert 'rakit "bahts/ahmad/ikhlas"\n' in tahap()  # seluruh naskah dirakit sesudahnya: itu yang menentukan
        (ikhlas / "riset.txt").unlink()  # perhatian belum ditangani menahan rakit-ulang juga: tangani dulu, lalu rakit
        out = tahap()
        assert "NASKAH=PERHATIAN" in out and "HASIL=USANG" in out and "lalu rakit" in out, out
        assert out.rstrip().endswith('cek "bahts/ahmad/ikhlas"'), out
        (ikhlas / "riset.txt").write_text("tafsir 1:2\ncari الربوبية\n", encoding="utf8")
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
            p = subprocess.Popen([sys.executable, "-c", "import sys, time; from pathlib import Path; import rakit\n"
                                  f"with rakit.kunci(Path('_tmp/rakit.pekerjaan'), apa='{apa}'):\n"
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
        # perhatian wajib ditangani: walau PDF TERKINI, pemeriksa belum boleh jalan sebelum tiap perhatian dibereskan
        # atau diterima («terima <kode> <alasan>» di riset.txt). Menerima tidak mengubah naskah: PDF tetap TERKINI.
        luar = 'قال الباحث: "القدر من أعظم أبواب الاعتقاد"[^بحث وهمي، ص5. <<luar>>].\n'  # satu perhatian, bisa diterima

        def naskah_(teks, riset_):
            (ikhlas / "naskah.txt").write_text(teks, encoding="utf8")
            (ikhlas / "riset.txt").write_text(riset_, encoding="utf8")
            out = bahts("cek", "bahts/ahmad/ikhlas").stdout
            (ikhlas / "laporan.txt").write_text(f"NASKAH_SHA256={sidik_naskah(out)}\n", encoding="utf8")
            return out

        def kode_(out):
            return re.findall(r"^  ! ([0-9a-f]{6}) ", out, re.M)

        k = kode_(naskah_(sisip(luar), "tafsir 1:2\ncari الربوبية\n"))
        assert len(k) == 1, k
        out = tahap()
        assert "NASKAH=PERHATIAN" in out and "HASIL=TERKINI" in out and "lalu rakit" not in out, out
        assert out.rstrip().endswith('cek "bahts/ahmad/ikhlas"') and "bukti" not in out, out
        terima = f"tafsir 1:2\ncari الربوبية\nterima {k[0]} lafaz dan halamannya dicocokkan sendiri ke penelitiannya\n"
        (ikhlas / "riset.txt").write_text(terima, encoding="utf8")
        out = tahap()
        assert "NASKAH=LOLOS" in out and "diterima 1" in out and "HASIL=TERKINI" in out, out
        assert 'bukti "bahts/ahmad/ikhlas"' in out and "alasan 1 baris «terima»" in out, out
        assert "alasan: lafaz dan halamannya" in bahts("cek", "bahts/ahmad/ikhlas").stdout
        # baris naskah bergeser: kode tetap, «terima» tidak basi
        assert not kode_(naskah_("\n\n" + sisip(luar), terima))
        # isi baris yang disebut berubah (di luar awal catatan kaki yang tercetak di pesan), atau baris baru ikut
        # tergabung ke perhatian kembar: kode baru, «terima» lama basi, jadi perhatian itu dinilai lagi
        for nama, teks in (("matan berubah", sisip(luar.replace("قال الباحث", "قال باحث آخر"))),
                           ("baris kembar baru", sisip(luar + luar))):
            out = naskah_(teks, terima)
            assert len(kode_(out)) == 2 and "kode itu tidak muncul lagi" in out, (nama, out)
        # perhatian riset.txt tidak bisa diterima: langkahnya dijalankan, atau «belum <langkah> <objek> <alasan>»
        k_riset = kode_(naskah_(dasar, "cari الربوبية\n"))
        assert len(k_riset) == 1, k_riset
        k_cari = kode_(naskah_(dasar, "tafsir 1:2\n"))
        out = naskah_(dasar, f"tafsir 1:2\nterima {k_cari[0]} connector shamela sedang mati\n")
        assert "perhatian riset.txt tidak bisa diterima" in out and len(kode_(out)) == 2, out
        out = naskah_(dasar, f"cari الربوبية\nterima {k_riset[0]} connector tafsir sedang mati\n")
        assert "perhatian riset.txt tidak bisa diterima" in out and len(kode_(out)) == 2, out
        # «terima» yang rusak = perhatian, tidak menerima apa pun
        for isi, pesan in ((f"terima {k[0]}\n", "tulis «terima <kode"), (f"terima {k[0]} ok\n", "paling sedikit 3 kata"),
                           ("terima ZZZ alasan yang panjang\n", "tulis «terima <kode"),
                           (f"terima {k[0]} alasan yang cukup panjang\nterima {k[0]} alasan kedua yang panjang\n",
                            "satukan alasannya"),
                           ("terima 000000 alasan basi yang panjang\n", "kode itu tidak muncul lagi")):
            out = naskah_(sisip(luar), "tafsir 1:2\ncari الربوبية\n" + isi)
            assert pesan in out and not re.search(r"^perhatian \(lolos.*: 0$", out, re.M), (isi, out)
        (ikhlas / "naskah.txt").write_text(dasar, encoding="utf8")
        hasil.append("terima: beralasan tidak menahan; kode tetap saat baris bergeser, baru saat isi/baris kembar "
                     "berubah; perhatian riset, alasan pendek, kode rusak/kembar/basi = perhatian")
        # laporan versi lama tanpa NASKAH_SHA256: tidak diketahui, bukan «naskah diubah»
        (ikhlas / "riset.txt").write_text("tafsir 1:2\ncari الربوبية\n", encoding="utf8")
        (ikhlas / "laporan.txt").write_text("HALAMAN=1\n", encoding="utf8")
        out = tahap()
        assert "HASIL=TIDAK_DIKETAHUI" in out and "naskah diubah" not in out.split("HASIL fasl")[0], out
        # bertahap per فصل: potongan terakhir yang dirakit menentukan; potongan lama yang USANG tidak disuruh rakit
        (ikhlas / "laporan.txt").unlink()
        (ikhlas / "laporan-fasl1.txt").write_text(f"POTONGAN=--fasl 1: المقدمة\nNASKAH_SHA256={'0' * 64}\n", encoding="utf8")
        (ikhlas / "laporan-fasl2.txt").write_text(f"POTONGAN=--fasl 2: الفصل\nNASKAH_SHA256={sidik}\n", encoding="utf8")
        (ikhlas / "ikhlas - الفصل.pdf").write_bytes(b"%PDF")
        (ikhlas / "laporan-fasl10.txt").write_text("HALAMAN=1\n", encoding="utf8")  # tanpa baris POTONGAN
        os.utime(ikhlas / "laporan-fasl1.txt", (1, 1))
        os.utime(ikhlas / "laporan-fasl10.txt", (2, 2))
        out = tahap()
        assert "HASIL fasl1=USANG" in out and "HASIL fasl2=TERKINI" in out and "HASIL fasl10=TIDAK_DIKETAHUI" in out, out
        assert out.index("fasl2=") < out.index("fasl10="), out
        assert 'bukti "bahts/ahmad/ikhlas"' in out, out
        hasil.append("tahap: naskah, hasil (juga --fasl dan laporan lama), perhatian menahan, folder .rakit-*, "
                     "_arsip, rakit bahts ini dan bahts lain")

        # @sampul kapital + @logo: berwarna, @malahiq: akhir tanpa #R, JPEG dengan byte isi 0xFF, saran `ambil` berspasi
        cek("@sampul QISM + @logo berwarna", "@sampul: QISM\n@logo: berwarna\n" + dasar)
        cek("@malahiq akhir tanpa pustaka", "@tanpa: pustaka\n@malahiq: akhir\n" + dasar.split("#R ")[0] + "#K الملاحق\nملحق.\n",
            True, "@malahiq: akhir memerlukan #R")
        (f / "isi_ff.jpg").write_bytes(b"\xff\xd8\xff\xff\xc0\x00\x0b\x08\x00\x0a\x00\x14\x03\x01\x11\x00\xff\xd9")
        cek("JPEG dengan byte pengisi 0xFF", sisip("#G isi_ff.jpg | شكل"))
        (f / "sof_pendek.jpg").write_bytes(b"\xff\xd8\xff\xc0\x00\x05\x08\x00\x0a\xff\xd9")
        cek("JPEG SOF0 panjang < 7 ditolak", sisip("#G sof_pendek.jpg | شكل"), True, "rusak")
        spasi = akar / "naskah uji"
        spasi.mkdir()
        (spasi / "naskah.txt").write_text(
            "@judul: فحص\n@nama: فلان\n@tanpa: pustaka\n@minimal_halaman: 0\n"
            "#K المقدمة\nنص[^كتاب، ص5. <<999999|-|5>>].\n#K الخاتمة\nنتائج.\n", encoding="utf8")
        r = bahts("cek", "naskah uji")
        assert r.returncode != 0 and 'ambil "naskah uji"' in r.stdout, r.stdout + r.stderr
        hasil.append("sampul kapital + logo berwarna, malahiq akhir tanpa #R, JPEG 0xFF, saran ambil berspasi")
        print(f"uji struktur: {len(hasil)} skenario sesuai, termasuk beban 2000 nukilan/4000 catatan kaki dan 500 data salah ketik")


if __name__ == "__main__":
    utama()
