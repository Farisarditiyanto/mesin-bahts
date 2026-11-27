# SPDX-License-Identifier: AGPL-3.0-or-later
"""Varian judul, sampul, dan bagian akhir lewat `cek`, `rakit`, dan Word asli, dibaca dari PDF: `@judul_fasl: pemisah`
(halaman pemisah tanpa nomor dengan «وفيه …» dan sub-judul rata tengah; isi mulai halaman berikutnya; فهرس الموضوعات
menunjuk halaman pemisah), `pemisah_bingkai` (bingkai ganda di halaman itu saja), `kotak` (kotak garis ganda di atas
judul #F), `@sampul: kop` dan `tanpa_kop`, `@tamma` (halaman penutup terakhir tanpa nomor), `@pustaka_gaya:
judul_tebal` («•» dan judul tebal di depan, tanpa nomor), dan `@maudhuat: titik` (baris #K/#F tebal, tanpa «❖»).
Bilangan «وفيه …» dan GAGAL-nya dinilai `cek` di mana saja; bagian Word dilewati di runner tanpa Word. Semua bahan di TEMP."""
import re, sys, tempfile
from pathlib import Path

import pymupdf

from bantu import bahts, salin_mesin, tanpa_word

KEPALA = ("@judul: اختبار الصفحات الفاصلة - دراسة\n@jenis: بحث تكميلي\n@nama: طالب\n@nim: 441012345\n@musyrif: د. مشرف\n"
          "@berkas: uji\n@tanpa: hadits\n@minimal_halaman: 0\n")
ISI = ("#K المقدمة\nهذا نص المقدمة.\n#S ❖ أهمية البحث\nنص الأهمية.\n"
       "#F المبحث الأول: الموضوع الأول\n#B المطلب الأول: الفرع الأول\nقال الله تعالى: {Q:1:2}[^سورة الفاتحة، آية: ٢.].\n"
       "#B المطلب الثاني: الفرع الثاني\nنص المطلب الثاني.\n"
       "#F المبحث الثاني: الموضوع الثاني\n#B المطلب الأول: أ\nنص.\n#B المطلب الثاني: ب\nنص.\n#B المطلب الثالث: ج\nنص.\n"
       "#K الخاتمة\nهذه الخاتمة.\n#R المصادر\nالقرآن الكريم.\n"
       "**ابن كثير، إسماعيل بن عمر** (ت 774هـ). __تفسير القرآن العظيم__. دار طيبة، 1420هـ.\n"
       "**الألباني، محمد ناصر الدين** (ت 1420هـ). __سلسلة الأحاديث الصحيحة__. مكتبة المعارف، 1415هـ.\n")
RISET = "tafsir 1:2\ncari الموضوع | uji\n"
TEPI = 72  # pt dari tepi atas/bawah kertas: kepala/kaki halaman


def tulis(akar, nama, kunci, isi=ISI):
    f = akar / nama
    f.mkdir()
    (f / "naskah.txt").write_text(KEPALA + kunci + isi, encoding="utf8")
    (f / "riset.txt").write_text(RISET, encoding="utf8")
    return f


def rakit(akar, nama, kunci):
    f = tulis(akar, nama, kunci)
    r = bahts(akar, "rakit", nama, batas=1800)
    assert r.returncode == 0, r.stdout + r.stderr
    # PT Bold Heading tidak ikut repo: tanpanya PERINGATAN huruf, sisanya tetap harus bersih
    sisa = [b for b in r.stdout.splitlines() if "PERINGATAN" in b and "PT Bold Heading" not in b]
    assert not sisa, f"{nama}: {sisa}\n{r.stdout}"
    return pymupdf.open(stream=(f / "uji.pdf").read_bytes(), filetype="pdf")   # tanpa memegang berkasnya (TEMP dibersihkan)


def baris(hal):
    """[(teks, pusat x, y atas, tebal)] tiap baris teks di halaman."""
    hasil = []
    for b in hal.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            sp = [s for s in ln["spans"] if s["text"].strip()]
            if sp:
                hasil.append((" ".join(s["text"] for s in sp), *ln["bbox"], all("Bold" in s["font"] or s["flags"] & 16 for s in sp)))
    # potongan sebaris (mis. «الرقم الجامعي:» dan nomornya) = satu baris
    gabung = []
    for t, x0, y0, x1, _, tb in sorted(hasil, key=lambda h: h[2]):
        if gabung and abs(gabung[-1][2] - y0) < 3:
            g = gabung[-1]
            gabung[-1] = [g[0] + " " + t, min(g[1], x0), g[2], max(g[3], x1), g[4] and tb]
        else:
            gabung.append([t, x0, y0, x1, tb])
    return [(t, (x0 + x1) / 2, y0, tb) for t, x0, y0, x1, tb in gabung]


def kata(teks):
    """Kata-kata teks tanpa tanda baca: urutan kata Arab di teks PDF bisa terbalik («السعودية العربية المملكة»)."""
    return frozenset(re.sub(r"[:.،]", " ", teks).split())


def tepi(hal):
    return "".join(t for t, _, y, _ in baris(hal) if y < TEPI or y > hal.rect.height - TEPI).replace(" ", "")


def cari(doc, teks):
    """Indeks halaman pertama yang memuat semua kata `teks`."""
    return next(i for i, p in enumerate(doc) if kata(teks) <= kata(p.get_text()))


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    with tempfile.TemporaryDirectory(prefix="bahts-judul-word-") as t:
        akar = Path(t)
        salin_mesin(akar)
        tulis(akar, "tanpa_f", "@judul_fasl: pemisah\n", "#K المقدمة\nنص.\n#K الخاتمة\nنص.\n#R المصادر\nالقرآن الكريم.\n")
        r = bahts(akar, "cek", "tanpa_f")
        assert r.returncode != 0 and "@judul_fasl: pemisah memerlukan judul #F" in r.stdout, r.stdout
        tulis(akar, "pustaka_salah", "@pustaka_gaya: judul_tebal\n", ISI + "كتاب بلا علامة، مؤلف، 1400هـ.\n")
        r = bahts(akar, "cek", "pustaka_salah")
        assert r.returncode != 0 and "judul_tebal" in r.stdout and "كتاب بلا علامة" in r.stdout, r.stdout
        print("lolos cek: @judul_fasl tanpa #F dan baris #R judul_tebal tanpa __judul__ = GAGAL")
        if alasan := tanpa_word():
            print("lewati uji judul/sampul Word: " + alasan)
            return
        doc = rakit(akar, "pemisah", "@sampul: kop\n@judul_fasl: pemisah\n@kepala: bagian\n@maudhuat: titik\n"
                                     "@pustaka_gaya: judul_tebal\n@tamma: ya\n")
        w = doc[0].rect.width
        # sampul kop: kop bertingkat di kanan atas, semuanya tebal, tanpa logo dan kode «(٠٣٢)»
        sampul = baris(doc[0])
        kop = [b for b in sampul if kata(b[0]) in {kata(k) for k in ("المملكة العربية السعودية", "وزارة التعليم", "قسم الشريعة")}]
        assert len(kop) == 3 and all(x > w / 2 and y < 200 for _, x, y, _ in kop), f"kop sampul kop: {sampul}"
        assert all(tb for *_, tb in sampul) and not doc[0].get_images() and "٠٣٢" not in doc[0].get_text(), sampul
        # halaman pemisah: tanpa kepala/kaki, «وفيه مطلبان:» lalu sub-judul rata tengah; isi mulai halaman berikutnya
        for judul, pengantar, anak in (("المبحث الأول", "وفيه مطلبان:", 2), ("المبحث الثاني", "وفيه ثلاثة مطالب:", 3)):
            i = cari(doc, pengantar)
            hal = baris(doc[i])
            assert kata(judul) <= kata(doc[i].get_text()) and not tepi(doc[i]), f"halaman pemisah {judul}: {hal}"
            daftar = [b for b in hal if "المطلب" in b[0]]
            pusat = daftar + [b for b in hal if kata(b[0]) == kata(pengantar)]
            tengah = hal[0][1]   # judul besar: pusat bidang teks (tepi kanan 3,5 cm, kiri 2,5 cm)
            assert len(daftar) == anak and len(pusat) == anak + 1 and all(abs(x - tengah) < 8 for _, x, _, _ in pusat), \
                f"sub-judul pemisah tidak rata tengah: {hal}"
            berikut = tepi(doc[i + 1])
            atas = " ".join(t for t, _, y, _ in baris(doc[i + 1]) if y < TEPI)
            # teks STYLEREF kepala halaman kadang terpotong di tengah kata di PDF («الثا ني»)
            assert all(k in atas.replace(" ", "") for k in kata(judul)), f"kepala halaman sesudah pemisah {judul}: {atas}"
            nomor = re.sub(r"\D", "", berikut.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))
            # فهرس الموضوعات titik: #F menunjuk halaman pemisah (nomornya = nomor halaman sesudahnya - 1), tebal
            fihris = baris(doc[cari(doc, "فهرس الموضوعات")])
            barisF = next(b for b in fihris if kata(judul) <= kata(b[0]))
            angka = re.sub(r"\D", "", barisF[0].translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))
            assert barisF[3] and int(angka) == int(nomor) - 1, f"فهرس {judul}: {barisF}, halaman sesudahnya {nomor}"
        fihris = doc[cari(doc, "فهرس الموضوعات")].get_text()
        assert "❖" not in fihris and kata("أهمية البحث") <= kata(fihris), fihris
        # المصادر judul_tebal: «•» tanpa nomor, judul tebal lebih dulu, urut judul
        mas = doc[cari(doc, "لإسماعيل بن عمر ابن كثير")]
        teks = mas.get_text()
        assert teks.count("•") == 3 and teks.index("تفسير") < teks.index("سلسلة"), teks   # «•» di kolom nomor tiap baris
        tebal = [s["text"] for b in mas.get_text("dict")["blocks"] for ln in b.get("lines", []) for s in ln["spans"]
                 if "Bold" in s["font"] and "تفسير" in s["text"]]
        assert tebal, "judul المصادر tidak tebal"
        # halaman penutup: halaman terakhir, tanpa nomor
        assert "توفيقه" in doc[-1].get_text() and not tepi(doc[-1]), doc[-1].get_text()
        print(f"lolos Word: sampul kop, {2} halaman pemisah tanpa nomor (فهرس menunjuknya), المصادر judul_tebal, "
              "فهرس titik tebal tanpa ❖, halaman penutup")
        doc = rakit(akar, "bingkai", "@sampul: tanpa_kop\n@judul_fasl: pemisah_bingkai\n")
        h = doc[0].rect.height
        sampul = {kata(t): (x, y) for t, x, y, _ in baris(doc[0])}
        y = {k: sampul[kata(k)][1] for k in ("اختبار الصفحات الفاصلة", "إعداد الطالب", "جامعة الإمام محمد بن سعود الإسلامية")}
        assert y["اختبار الصفحات الفاصلة"] < h / 4 < y["إعداد الطالب"] < h * 0.6 < y["جامعة الإمام محمد بن سعود الإسلامية"], y
        assert all(abs(x - w / 2) < 15 for x, _ in sampul.values()), f"sampul tanpa_kop tidak rata tengah: {sampul}"
        i = cari(doc, "وفيه مطلبان:")
        bingkai = [d["rect"] for d in doc[i].get_drawings() if d["rect"].width > w * 0.8 and d["rect"].height > h * 0.8]
        assert len(bingkai) == 2 and not [d for d in doc[i + 1].get_drawings() if d["rect"].height > h * 0.8], bingkai
        print("lolos Word: sampul tanpa_kop (judul atas, إعداد tengah, kampus bawah), bingkai ganda di halaman pemisah saja")
        doc = rakit(akar, "kotak", "@judul_fasl: kotak\n")
        i = cari(doc, "الموضوع الأول")
        garis = [d["rect"] for d in doc[i].get_drawings() if d["rect"].y1 < h / 3]
        judul = [b for b in baris(doc[i]) if kata(b[0]) in (kata("المبحث الأول"), kata("الموضوع الأول"))]
        isi = kata("قال الله") <= kata(doc[i].get_text())
        assert len(judul) == 2 and garis and min(g.y0 for g in garis) < judul[0][2] and isi, (garis, judul)
        # garis ganda: yang tebal di luar, di atas dan di bawah kotak
        datar = sorted((g for g in garis if g.width > w / 2), key=lambda g: g.y0)
        assert datar[0].height > datar[1].height and datar[-1].height > datar[-2].height, f"garis tebal kotak di dalam: {datar}"
        # @pustaka_gaya bawaan tetap bernomor, tanpa «•»
        mas = doc[cari(doc, "المصادر دار طيبة")].get_text()
        assert "•" not in mas and "١." in mas, mas
        print("lolos Word: judul #F di kotak bergaris di atas halaman, isinya menyusul di halaman yang sama; المصادر bawaan bernomor")


if __name__ == "__main__":
    utama()
