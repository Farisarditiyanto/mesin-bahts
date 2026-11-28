# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tahqiq dan sisipan sebaris lewat `rakit` dan Word asli, diukur di PDF hasil: #N = tabel rumuz naskah; kata yang
diberi {F:} tebal di matan, catatan kaki perbedaan naskahnya «في (ب): …» satu deret nomor dengan catatan kaki biasa
(nomor urut menurut letaknya); {W:} tercetak «[٢/أ]»; {SJ:} = judul tepi di tepi kiri halaman (di luar bidang teks),
sejajar baris pertama paragrafnya, juga untuk paragraf yang terpotong pindah halaman; #T متن = lafaz tebal dalam kurung
bergaris di bawahnya; {U:} di catatan kaki dan #U = kode QR (bidang DISPLAYBARCODE yang tetap hidup di .docx,
tergambar di PDF). Runner tanpa Word melaporkan lewati. Semua bahan di TEMP."""
import importlib.util, re, sys, tempfile, zipfile
from pathlib import Path

from bantu import SAMPUL_UJI, bahts, salin_mesin, tanpa_word

ISI = ("الحمد لله رب العالمين، والصلاة والسلام على نبينا محمد وعلى آله وصحبه أجمعين، ويظهر للباحث أن ترتيب المسائل "
       "على هذا الوجه أقرب إلى الفهم وأبعد عن التكرار، وأن جمع النظائر في موضع واحد يعين القارئ على الضبط. ")
URL = "https://shamela.ws/book/11223"
NASKAH = ("@judul: فحص التحقيق\n" + SAMPUL_UJI + "@berkas: hasil\n@tanpa: pustaka, ayat, maudhuat\n"
          "@nuskhah: أ = نسخة المكتبة الأزهرية | ب = نسخة دار الكتب المصرية\n"
          "#K المقدمة\nوصف النسخ:\n#N\n"
          "قال المصنف: الحمد لله الذي هدانا{F:ب|أرشدنا} لهذا {W:2/أ} وقسم الشيخ الناس في القدر[^انظر: رسالة في القضاء "
          "والقدر، ابن عثيمين، ص6. <<11223|-|6|انقسمت في القدر إلى ثلاثة أقسام>>]، وصلى الله على آله{F:أ|وأصحابه|ب|-}.\n"
          "{SJ:قاعدة}الأمور بمقاصدها، ويظهر للباحث أن هذه القاعدة كلية. " + ISI + "\n"
          "#T متن | والفقه معرفة الأحكام الشرعية العملية\n"
          "قوله: {MT:معرفة} ويظهر للباحث أن المراد بها مطلق الإدراك[^انظر: النسخة الرقمية: {U:" + URL + "}].\n"
          "#U " + URL + " | امسح الرمز لفتح الكتاب\n"
          + ISI * 5 + "\n{SJ:فرع}" + ISI * 14 + "\n"
          "#K الخاتمة\nأهم النتائج: انتهى الفحص.\n")


def baris(hal):
    """[(x0, y0, x1, teks, tebal)] tiap baris teks halaman."""
    return [(b["bbox"][0], b["bbox"][1], b["bbox"][2], "".join(s["text"] for s in b["spans"]),
             {s["text"].strip() for s in b["spans"] if "Bold" in s["font"]})
            for blk in hal.get_text("dict")["blocks"] for b in blk.get("lines", [])]


def kotak_kecil(hal, y0, y1):
    """Jumlah persegi terisi kecil (modul QR) di antara y0..y1: Word menggambar QR sebagai persegi-persegi."""
    return sum(1 for d in hal.get_drawings() for it in d["items"]
               if it[0] == "re" and y0 <= it[1].y0 <= y1 and it[1].width < 6 and it[1].height < 6)


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji tahqiq Word: " + alasan)
        return
    if not importlib.util.find_spec("pymupdf"):
        print("lewati uji tahqiq Word: pymupdf belum terpasang")
        return
    import pymupdf
    with tempfile.TemporaryDirectory(prefix="bahts-tahqiq-word-") as t:
        akar = Path(t)
        salin_mesin(akar, (11223,))
        f = akar / "uji"
        f.mkdir()
        (f / "naskah.txt").write_text(NASKAH, encoding="utf8")
        (f / "riset.txt").write_text("cari القدر | uji\n", encoding="utf8")
        r = bahts(akar, "rakit", "uji", batas=1800)
        assert r.returncode == 0, r.stdout + r.stderr
        with zipfile.ZipFile(f / "hasil.docx") as z:
            kode = z.read("word/document.xml").decode() + z.read("word/footnotes.xml").decode()
        assert len(re.findall(r"DISPLAYBARCODE", kode)) == 2, "kode QR bukan bidang DISPLAYBARCODE di .docx"
        with pymupdf.open(f / "hasil.pdf") as pdf:
            hal = [(h, baris(h)) for h in pdf]
            i = next(i for i, (_, b) in enumerate(hal) if any("الرمز" in x[3] for x in b))
            h, b = hal[i]
            kiri = min(x[0] for x in b if len(x[3]) > 60) - 4   # tepi kiri bidang teks (baris matan rata)
            # #N: tabel rumuz
            assert any("(أ)" in x[3] for x in b) and any("دار الكتب" in x[3] for x in b), "tabel #N tanpa isinya"
            # {F:}: lemma tebal; catatan kaki perbedaan naskah dan catatan kaki biasa satu deret, urut letaknya
            assert any("هدانا" in t for x in b for t in x[4]), "kata yang berbeda di naskah tidak tebal"
            nomor = sorted((x[1], x[3]) for x in b if re.match(r"\s*\([٠-٩]+\)", x[3]))   # baris catatan kaki = satu y
            urut = [t + " " + " ".join(x[3] for x in b if abs(x[1] - y) < 3 and x[3] != t) for y, t in nomor]
            harap = ("«أرشدنا", "رسالة في القضاء", "«وأصحابه»، وسقط من")   # PDF membalik urutan run kanan-ke-kiri
            assert [next((k for k, h_ in enumerate(harap) if h_ in u), None) for u in urut][:3] == [0, 1, 2], urut
            assert [re.match(r"\s*\(([٠-٩]+)\)", u)[1] for u in urut][:3] == ["١", "٢", "٣"], urut
            # {W:}
            # PDF memecah «[٢/أ]» kanan-ke-kiri jadi beberapa baris teks pada y yang sama: digabung tanpa spasi
            sebaris = "".join(x[3] for x in b if abs(x[1] - next(y[1] for y in b if "٢" in y[3] and "/" in y[3])) < 3)
            assert re.search(r"٢/أ|أ/٢", re.sub(r"[\s⁠]", "", sebaris)), f"«[٢/أ]» tidak tercetak: {sebaris}"
            # {SJ:} قاعدة: di tepi kiri halaman, di luar bidang teks, sejajar baris pertama paragrafnya
            sj = next(x for x in b if x[3].strip() == "قاعدة")
            awal = next(x for x in b if "الأمور بمقاصدها" in x[3])
            assert sj[2] < kiri and abs(sj[1] - awal[1]) < 12, f"judul tepi {sj[:3]} tidak sejajar paragrafnya {awal[:3]}"
            # #T متن: tebal dalam kurung, garis di bawahnya
            mt = next(x for x in b if "(والفقه" in x[3] or "الأحكام الشرعية العملية)" in x[3])
            assert mt[4], "lafaz matan tidak tebal"
            assert any(d["rect"].width > 100 and 0 < d["rect"].y0 - mt[1] < 40 for d in h.get_drawings()), "matan tanpa garis bawah"
            assert any("معرفة" in t for x in b if "قوله" in x[3] for t in x[4]), "{MT:} tidak tebal"
            # QR: #U di tengah (modul di bawah teks paragraf sebelumnya), {U:} di catatan kaki bersama alamatnya
            u = next(x for x in b if "امسح الرمز" in x[3])
            assert kotak_kecil(h, u[1] - 90, u[1]) > 40, "kode QR #U tidak tergambar di atas keterangannya"
            alamat = [x for x in b if URL in x[3]]
            assert len(alamat) == 2, f"alamat QR tidak tercetak dua kali: {alamat}"
            catatan = max(alamat, key=lambda x: x[1])
            assert kotak_kecil(h, catatan[1] - 45, catatan[1] + 25) > 40, "kode QR catatan kaki tidak tergambar"
            # {SJ:} فرع pada paragraf panjang yang terpotong halaman: judul tepi di halaman awal paragrafnya
            j = next(j for j, (_, bb) in enumerate(hal) if any(x[3].strip() == "فرع" for x in bb))
            bb = hal[j][1]
            sj = next(x for x in bb if x[3].strip() == "فرع")
            sesudah = sorted((x for x in bb if x[1] > sj[1] - 12 and len(x[3]) > 40), key=lambda x: x[1])
            assert sesudah and abs(sesudah[0][1] - sj[1]) < 12 and sj[2] < kiri, f"judul tepi فرع tidak sejajar: {sj[:3]}"
            assert j + 1 < len(hal) and "الحمد" in "".join(x[3] for x in hal[j + 1][1]), "paragraf فرع tidak terpotong halaman"
        print(f"lolos tahqiq Word: judul tepi x {sj[0]:.0f}-{sj[2]:.0f} (bidang teks mulai {kiri:.0f}), catatan kaki "
              f"{len(urut)} urut, QR 2 bidang hidup", flush=True)


if __name__ == "__main__":
    utama()
