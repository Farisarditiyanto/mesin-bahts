# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sisipan bergaya kitab cetak lama lewat `rakit` dan Word asli, diukur di PDF hasil: kotak #T فائدة bergaris di
keempat sisinya (garis kanan di kanan teks, garis kiri di kiri teks), catatan kaki di dalam kotak tercetak, dan kotak
yang lebih panjang daripada satu halaman tetap bergaris di kedua halamannya; #T تنبيه hanya bergaris atas-bawah; butir
#- tiga tingkat makin ke kiri tiap tingkat dengan label «أولًا:»/«أ-»/«١-»; #P = teks Arab di kanan dan terjemah Latin di
kiri pada baris yang sama dengan garis tegak di antaranya; #Z = «٭ ٭ ٭» di tengah. Runner tanpa Word melaporkan lewati.
Semua bahan di TEMP."""
import importlib.util, sys, tempfile
from pathlib import Path

from bantu import SAMPUL_UJI, bahts, salin_mesin, tanpa_word

ISI = ("الحمد لله رب العالمين، والصلاة والسلام على نبينا محمد وعلى آله وصحبه أجمعين، ويظهر للباحث أن ترتيب المسائل "
       "على هذا الوجه أقرب إلى الفهم وأبعد عن التكرار، وأن جمع النظائر في موضع واحد يعين القارئ على الضبط. ")
NASKAH = ("@judul: فحص السيسبان\n" + SAMPUL_UJI + "@berkas: hasil\n@tanpa: pustaka, ayat, maudhuat\n"
          "#K المقدمة\nوهذا تمهيد للفحص.\n"
          "#T فائدة | وقسم الشيخ الناس في القدر[^انظر: رسالة في القضاء والقدر، ابن عثيمين، ص6. "
          "<<11223|-|6|انقسمت في القدر إلى ثلاثة أقسام>>]، ويظهر للباحث أن التقسيم حاصر.\n"
          "#T تنبيه | ويظهر للباحث أن تقديم التعريف على التقسيم أولى.\n"
          "وتنقسم المسائل إلى ما يأتي:\n"
          "#- tartib مسائل التعريف:\n#-- abjad التعريف اللغوي:\n#--- raqm أصل الكلمة.\n#--- اشتقاقها.\n"
          "#-- التعريف الاصطلاحي.\n#- مسائل الأدلة.\n"
          "#P العلم قبل القول والعمل. | Ilmu sebelum ucapan dan perbuatan.\n"
          "#Z\n" + ISI + "\n"
          "#T فائدة | " + ISI * 16 + "\n"
          "#K الخاتمة\nأهم النتائج: انتهى الفحص.\n")
TINGKAT = ("مسائل التعريف", "التعريف اللغوي", "أصل الكلمة")  # butir tingkat 1, 2, 3


def garis(hal):
    """(mendatar, tegak) garis tipis di halaman: tiap garis = (x0, y0, x1, y1). Garis paragraf Word di PDF = persegi
    panjang terisi setebal garisnya."""
    datar, tegak = [], []
    for d in hal.get_drawings():
        for it in d["items"]:
            r = it[1] if it[0] == "re" else None
            if it[0] == "l":
                (a, b) = it[1], it[2]
                r = type("R", (), {"x0": min(a.x, b.x), "y0": min(a.y, b.y), "x1": max(a.x, b.x), "y1": max(a.y, b.y)})
            if r is None:
                continue
            w, h = r.x1 - r.x0, r.y1 - r.y0
            if w > 20 and h < 3:
                datar.append((r.x0, r.y0, r.x1, r.y1))
            elif h > 10 and w < 3:
                tegak.append((r.x0, r.y0, r.x1, r.y1))
    return datar, tegak


def baris(hal):
    """[(x0, y0, x1, teks)] tiap baris teks halaman."""
    return [(b["bbox"][0], b["bbox"][1], b["bbox"][2], "".join(s["text"] for s in b["spans"]))
            for blk in hal.get_text("dict")["blocks"] for b in blk.get("lines", [])]


def awal(b, teks):
    """Tepi kanan (awal baris kanan-ke-kiri, termasuk labelnya) baris yang memuat `teks`."""
    y = next(x[1] for x in b if teks in x[3])
    return max(x[2] for x in b if abs(x[1] - y) < 3)


def sisi(tegak, x, y0, y1, kanan):
    """Garis tegak di kanan (kanan=True) atau kiri `x` yang menutupi rentang y0..y1 (Word menggambarnya per baris)."""
    g = [s for s in tegak if (s[0] >= x - 1 if kanan else s[2] <= x + 1) and s[3] > y0 and s[1] < y1]
    return g and min(s[1] for s in g) <= y0 + 3 and max(s[3] for s in g) >= y1


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji sisipan Word: " + alasan)
        return
    if not importlib.util.find_spec("pymupdf"):
        print("lewati uji sisipan Word: pymupdf belum terpasang")
        return
    import pymupdf
    with tempfile.TemporaryDirectory(prefix="bahts-sisipan-word-") as t:
        akar = Path(t)
        salin_mesin(akar, (11223,))
        f = akar / "uji"
        f.mkdir()
        (f / "naskah.txt").write_text(NASKAH, encoding="utf8")
        (f / "riset.txt").write_text("cari القدر | uji\n", encoding="utf8")
        r = bahts(akar, "rakit", "uji", batas=1800)
        assert r.returncode == 0, r.stdout + r.stderr
        with pymupdf.open(f / "hasil.pdf") as pdf:
            hal = [(baris(h), *garis(h)) for h in pdf]
            tengah = pdf[0].rect.width / 2
        isi = next(i for i, (b, _, _) in enumerate(hal) if any("وقسم الشيخ" in x[3] for x in b))
        b, datar, tegak = hal[isi]
        # kotak فائدة: garis tegak di kanan dan kiri teksnya, garis mendatar di atas dan di bawahnya
        faidah = [x for x in b if "وقسم الشيخ" in x[3] or "التقسيم حاصر" in x[3]]
        x0, x1 = min(x[0] for x in faidah), max(x[2] for x in faidah)
        y0, y1 = min(x[1] for x in faidah), max(x[1] for x in faidah)
        assert sisi(tegak, x1, y0, y1, True) and sisi(tegak, x0, y0, y1, False), \
            f"kotak فائدة tanpa garis kanan/kiri: teks {x0:.0f}-{x1:.0f}, tegak {tegak}"
        assert any(g[1] < y0 for g in datar) and any(g[1] > y1 for g in datar), f"kotak tanpa garis atas/bawah: {datar}"
        assert any("رسالة في القضاء" in x[3] and x[1] > y1 for x in b), "catatan kaki kotak hilang"
        # تنبيه: garis atas-bawah saja (ganda), tanpa garis tegak di sampingnya
        tanbih = next(x for x in b if "تقديم التعريف" in x[3])
        assert not [g for g in tegak if g[1] <= tanbih[1] + 5 <= g[3]], "kotak تنبيه bergaris tegak"
        assert sum(1 for g in datar if 0 < tanbih[1] - g[1] < 30) >= 2, "kotak تنبيه tanpa garis ganda di atasnya"
        # daftar: label tiap tingkat makin ke kiri (tepi kanan baris = awal baris kanan-ke-kiri)
        tepi = [round(awal(b, t)) for t in TINGKAT]
        assert tepi[0] > tepi[1] > tepi[2], f"tingkat daftar tidak makin menjorok: {tepi}"
        # #P: Arab di kanan, Latin di kiri pada baris yang sama, garis tegak di antaranya
        lat = next(x for x in b if "Ilmu sebelum" in x[3])
        arab = next(x for x in b if "قبل القول" in x[3])
        assert lat[2] < tengah < arab[0] and abs(lat[1] - arab[1]) < 12, (lat, arab)
        assert any(lat[2] <= g[0] <= arab[0] for g in tegak), "#P tanpa garis tegak di tengah"
        # #Z di tengah
        z = next(x for x in b if "٭" in x[3])
        assert abs((z[0] + z[2]) / 2 - tengah) < 30, f"#Z tidak di tengah: {z}"
        # kotak panjang: bergaris tegak di dua halaman berturut-turut
        panjang = [i for i, (bb, _, tg) in enumerate(hal) if i >= isi and tg
                   and any("يعين القارئ" in x[3] for x in bb) and not any("Ilmu" in x[3] for x in bb)]
        assert len(panjang) >= 2 and panjang[1] == panjang[0] + 1, f"kotak panjang tidak bergaris di dua halaman: {panjang}"
        print(f"lolos sisipan Word: kotak bergaris 4 sisi (teks {x0:.0f}-{x1:.0f}), awal butir tingkat 1-3 di x {tepi}, "
              f"kotak panjang di halaman {panjang[:2]}", flush=True)


if __name__ == "__main__":
    utama()
