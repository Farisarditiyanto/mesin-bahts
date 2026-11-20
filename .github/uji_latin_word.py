# SPDX-License-Identifier: AGPL-3.0-or-later
"""Huruf Latin di tengah teks Arab lewat `rakit` dan Microsoft Word asli: di PDF hasil, kata Latin di paragraf, sel #J,
catatan kaki, dan المصادر tercetak Times New Roman dengan ukuran sebanding (lebih kecil daripada teks Arab di sekitarnya),
dan teks Arab tetap huruf profilnya. Runner tanpa Word melaporkan lewati. Semua bahan tinggal di TEMP."""
import importlib.util, subprocess, sys, tempfile
from pathlib import Path

from bantu import salin_mesin, tanpa_word

NASKAH = """@format: imam_ayat16
@judul: اختبار الحروف اللاتينية
@nama: اسم الطالب
@berkas: uji
@minimal_halaman: 0
#K المقدمة
يستعمل نظام Banner في الجامعة منذ مدة، وهو نظام ISO 9001 معتمد في Islamic Banking (IB) المعاصرة[^انظر: Hoo & Ibrahim, Biometric-Based Attendance Tracking System, p. 4. <<luar>>].
#J البند | Item
#J الحضور | Attendance rate
#J الجدول | BIO_TEMPLATE
#K الخاتمة
أهم النتائج: نجح الاختبار.
#R المصادر والمراجع
Hoo, Seng Chun, Biometric-Based Attendance Tracking System for Education Sectors, 2019.
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
        print(f"lolos huruf Latin Word: matan {matan:.1f}, sel {tabel:.1f}, catatan kaki {catatan:.1f}, المصادر {pustaka:.1f}")


if __name__ == "__main__":
    utama()
