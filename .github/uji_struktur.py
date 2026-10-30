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
        print(f"uji struktur: {len(hasil)} skenario sesuai, termasuk beban 2000 nukilan/4000 catatan kaki dan 500 data salah ketik")


if __name__ == "__main__":
    utama()
