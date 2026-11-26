# SPDX-License-Identifier: AGPL-3.0-or-later
"""Huruf Latin di tengah teks Arab lewat `rakit` dan Microsoft Word asli: di PDF hasil, kata Latin di paragraf, sel #J,
catatan kaki, dan المصادر tercetak Times New Roman dengan ukuran sebanding (lebih kecil daripada teks Arab di sekitarnya),
dan teks Arab tetap huruf profilnya. Rujukan Latin di catatan kaki dan المصادر kiri-ke-kanan: angkanya 0-9, titik penutupnya
di belakang; baris المصادر tanpa huruf Arab rata kiri dan dicetak sesudah rujukan Arab. Runner tanpa Word melaporkan lewati. Semua bahan tinggal di TEMP."""
import importlib.util, re, subprocess, sys, tempfile
from pathlib import Path

from bantu import salin_mesin, tanpa_word

NASKAH = """@format: imam_ayat16
@judul: اختبار الحروف اللاتينية
@nama: اسم الطالب
@berkas: uji
@minimal_halaman: 0
#K المقدمة
يستعمل نظام Banner في الجامعة منذ مدة، وهو نظام ISO 9001 معتمد في Islamic Banking (IB) المعاصرة[^انظر: Hoo & Ibrahim, Biometric-Based Attendance Tracking System, Vol. 3, No. 12, 2019, p. 45. <<luar>>].
#J البند | Item
#J الحضور | Attendance rate
#J الجدول | BIO_TEMPLATE
#K الخاتمة
أهم النتائج: نجح الاختبار.
#R المصادر والمراجع
Hoo, Seng Chun, Biometric-Based Attendance Tracking System for Education Sectors, 2019.
المغني، عبد الله بن أحمد بن قدامة، دار عالم الكتب، الرياض، 1417هـ.
(2019) Annual Report of Bank Indonesia, Jakarta, 2019.
"""


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji huruf Latin Word: " + alasan)
        return
    if not importlib.util.find_spec("pymupdf"):
        print("lewati uji huruf Latin Word: pymupdf belum terpasang")
        return
    import pymupdf
    with tempfile.TemporaryDirectory(prefix="bahts-latin-word-") as t:
        akar = Path(t)
        salin_mesin(akar, ("_meta",))
        folder = akar / "uji"
        folder.mkdir()
        (folder / "naskah.txt").write_text(NASKAH, encoding="utf8")
        r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), "rakit", "uji"],
                           cwd=akar, capture_output=True, encoding="utf8", timeout=1800)
        assert r.returncode == 0 and (folder / "uji.pdf").is_file(), r.stdout + r.stderr
        # (huruf, ukuran) tiap potongan teks PDF sesudah sampul; potongan berhuruf Latin lawan potongan berhuruf Arab
        latin, arab = {}, []
        with pymupdf.open(folder / "uji.pdf") as pdf:
            # baris teks per halaman: (y, x0, teks), untuk arah dan urutan rujukan
            baris_hal = [[(round(b["bbox"][1]), b["bbox"][0], "".join(s["text"] for s in b["spans"]))
                          for blk in h.get_text("dict")["blocks"] for b in blk.get("lines", [])] for h in pdf]
            lebar = pdf[0].rect.width
            # (garis dasar y, x, ukuran, teks) tiap potongan di halaman المصادر
            dasar = [(s["origin"][1], s["origin"][0], s["size"], s["text"])
                     for blk in next(h for h in pdf if "Hoo, Seng" in h.get_text()).get_text("dict")["blocks"]
                     for b in blk.get("lines", []) for s in b["spans"] if s["text"].strip()]
            for hal in list(pdf)[1:]:
                for blok in hal.get_text("dict")["blocks"]:
                    for baris in blok.get("lines", []):
                        for s in baris["spans"]:
                            if any("a" <= c.lower() <= "z" for c in s["text"]):
                                latin[s["text"].strip()] = (s["font"], s["size"])
                            elif any("؀" <= c <= "ۿ" or "ﭐ" <= c <= "ﻼ" for c in s["text"]):
                                arab.append((s["font"], s["size"]))

        def ukuran(kata):
            cocok = [(f, u) for teks, (f, u) in latin.items() if kata in teks]
            assert cocok and all("Times" in f for f, _ in cocok), (kata, latin)
            return cocok[0][1]
        assert arab and not any("Times" in f for f, _ in arab), sorted(set(arab))
        matan, tabel, catatan, pustaka = ukuran("Banner"), ukuran("Attendance rate"), ukuran("Hoo & Ibrahim"), ukuran("Hoo, Seng")
        assert ukuran("ISO") == matan and 11.5 <= matan <= 12.5, latin      # matan Arab 18
        assert 9.5 <= catatan <= 10.5, latin                                # catatan kaki Arab 14
        assert catatan < tabel < matan and pustaka <= matan, latin          # sel tabel Arab 16
        # kurung yang dibuka di dalam rentang Latin dan garis bawah nama teknis ikut rentangnya (satu potongan Times)
        assert ukuran("(IB)") == matan and ukuran("BIO_TEMPLATE") == tabel, latin
        # catatan kaki: angka rujukan Latin 0-9 dan titik penutup di belakang (tidak «.Hoo» / «٤٥»)
        semua = [t for h in baris_hal for _, _, t in h]
        fn = " ".join(t for t in semua if "Tracking System" in t or "2019, p." in t)
        assert "No. 12, 2019, p. 45." in fn and "٤٥" not in fn and ".Hoo" not in fn, fn
        # المصادر: rujukan Arab (المغني) di atas rujukan Latin, dan baris Latin rata kiri
        hal_r = next(h for h in baris_hal if any("المغني" in t for _, _, t in h) and any("Hoo, Seng" in t for _, _, t in h))
        y_ar = min(y for y, _, t in hal_r if "المغني" in t); y_la, x_la = min((y, x) for y, x, t in hal_r if "Hoo, Seng" in t)
        assert y_ar < y_la and x_la < lebar * 0.3, (y_ar, y_la, x_la, lebar)
        # nomor baris Latin sebaris dengan baris pertama teksnya (bukan turun setengah baris)
        y_teks = min(y for y, x, _, t in dasar if "Hoo, Seng" in t)
        no = min((d for d in dasar if d[1] > lebar * 0.7 and abs(d[0] - y_teks) < 15), key=lambda d: abs(d[0] - y_teks))
        uk_ar = [d[2] for d in dasar if d[1] > lebar * 0.7 and re.fullmatch("[.٠-٩]+", d[3].strip())]
        assert abs(no[0] - y_teks) <= 1.5 and abs(no[2] - max(uk_ar)) < 0.5, (no, y_teks, uk_ar)
        # baris Latin yang diawali kurung dan angka: seluruhnya kiri-ke-kanan, angkanya 0-9
        tahun = " ".join(t for t in semua if "Annual Report" in t)
        assert "(2019) Annual Report" in tahun and "٢٠١٩" not in tahun, tahun
        print(f"lolos huruf Latin Word: matan {matan:.1f}, sel {tabel:.1f}, catatan kaki {catatan:.1f}, المصادر {pustaka:.1f}")


if __name__ == "__main__":
    utama()
