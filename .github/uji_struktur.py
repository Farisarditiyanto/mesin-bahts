# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regresi struktur lewat CLI asli di salinan TEMP, memakai contoh dan kitab asli.
Tidak menjalankan Word: naskah yang kehilangan isi harus ditolak sebelum perakit dipanggil.
"""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf8")


def utama():
    with tempfile.TemporaryDirectory(prefix="bahts-struktur-") as t:
        akar = Path(t)
        shutil.copytree(AKAR / "mesin", akar / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__", "*.ttf"))
        for sid in ("_meta", "11223", "1681", "2348"):
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

        cek("contoh asli", dasar)
        # riset.txt: jejak langkah connector hanya pernah jadi perhatian, apa pun isinya (olah.periksa_riset)
        riset = f / "riset.txt"
        for nama, isi, pesan in (
                ("tanpa riset.txt", None, "ayat {Q:1:2} belum tercatat"),
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
        assert out.count("masalah khilaf ke-") == 2, out
        riset.write_text("tafsir 1:2\nkhilaf مسألة\n", encoding="utf8")
        out = cek("khilaf satu tercatat", dasar.replace("#K الخاتمة", "#B مسألة\nالقول الأول: يجوز.\n#B مسألة أخرى\n"
                                                        "الرأي الأول: يجوز.\n#K الخاتمة"))
        assert out.count("masalah khilaf ke-") == 1 and "masalah khilaf ke-2" in out, out
        riset.unlink()
        # di tengah kalimat (المناقشة, nukilan) bukan masalah baru; «#S القول الأول» lalu «#B أدلة القول الأول» = satu
        out = cek("khilaf bukan masalah baru", dasar.replace("#K الخاتمة", "#S القول الأول\nيجوز.\n#B أدلة القول الأول ومناقشتها\n"
                                                             "اختار القول الأول جماعة، ثم قال: \"والصحيح هو القول الأول\".\n"
                                                             "#K الخاتمة"))
        assert out.count("masalah khilaf ke-") == 1, out
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

        for akhir in (",", ";", ":", "]", "…", "）", "\u200f,\u200f", ". اهـ,", " انتهى كلامه؛"):
            cek("kutipan palsu dengan tanda baca " + repr(akhir), sisip(
                'قال الشيخ: «القدر سر مكشوف»' + akhir +
                '[^رسالة في القضاء والقدر، ابن عثيمين، ص5. <<11223|-|5|توحيد الربوبية وهو إفراد الله>>].'),
                True, "kutipan sebelum catatan kaki tidak ada")
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
        print(f"uji struktur: {len(hasil)} skenario sesuai, termasuk beban 2000 nukilan/4000 catatan kaki dan 500 data salah ketik")


if __name__ == "__main__":
    utama()
