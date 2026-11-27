# SPDX-License-Identifier: AGPL-3.0-or-later
"""Kepala dan kaki halaman tiap `@kepala` dan garis pemisah catatan kaki lewat `rakit` dan Word asli, dibaca dari PDF.
Runner tanpa Word melaporkan lewati.

Naskah uji: sampul, الإهداء, المقدمة dua halaman (bercatatan kaki), مبحث, الخاتمة, lalu فهرس الموضوعات. Yang dijaga:
letak judul dan nomor tiap bentuk di halaman isi (judul bagian yang berjalan ikut #K/#F, ganjil/genap bergantian),
halaman depan (الإهداء) dan belakang (فهرس) tanpa kepala dengan nomor polos di tengah kaki, sampul tanpa nomor, tidak
ada halaman kosong sisipan Word (ganjil/genap atau pemisah bagian), tanpa PERINGATAN nomor halaman, bintang kecil
setinggi baris judul dengan nomor di tengahnya, dan garis pemisah catatan kaki 4,5 cm di kanan. `@kepala: kotak`
dirakit sekali lagi dengan الإهداء, judul panjang, dan persamaan #E yang turun ke baris kedua (diperkecil MuatRumus
sesudah gaya kepala kepala_kotak.docx disalin): rakit jadi, الإهداء tanpa kotak, judul rata kanan tanpa kasyidah dan
tidak menimpa kotak nomor, dan PERINGATAN @kepala_judul. Semua bahan di TEMP."""
import sys, tempfile
from pathlib import Path

import pymupdf

from bantu import bahts, salin_mesin, tanpa_word

JUDUL = "اختبار رأس الصفحة"
FASL = "المبحث الأول: عنوان الاختبار"
ISI = "هذا سطر من نص الاختبار يطول قليلا حتى يملأ الصفحة الأولى من المقدمة وينتقل إلى الثانية."
NASKAH = (f"@judul: {JUDUL}\n@nama: طالب\n@berkas: uji\n@tanpa: ayat, hadits, alam, firaq, pustaka\n"
          "@minimal_halaman: 0\n{kepala}#K الإهداء\nإلى والديّ الكريمين.\n#K المقدمة\n" + f"{ISI}[^حاشية للاختبار.]\n"
          + f"{ISI}\n" * 24
          + f"#F {FASL}\n{ISI}\n#K الخاتمة\n{ISI}\n")
# judul yang lebih panjang daripada satu baris kepala kotak, dan persamaan #E (bertag dan tanpa tag) yang lebih lebar
# daripada satu baris matan
JUDUL_PANJANG = "زكاة الأسهم والصناديق الاستثمارية المعاصرة: دراسة فقهية محاسبية مقارنة بين المذاهب الأربعة والمعايير المحاسبية الدولية"
RUMUS = (r"\text{زكاة أسهم الاقتناء} = \text{عدد الأسهم المملوكة} \times \text{وعاء السهم الزكوي في آخر الحول}"
         r" \times \text{نسبة الزكاة الواجبة} \times 2.5\%")
NASKAH_KOTAK = (f"@judul: {JUDUL_PANJANG}\n@nama: طالب\n@berkas: uji\n@tanpa: ayat, hadits, alam, firaq, pustaka\n"
                f"@minimal_halaman: 0\n@kepala: kotak\n#K الإهداء\nإلى والديّ الكريمين.\n#K المقدمة\n{ISI}\n"
                f"#E {RUMUS} \\tag{{1}}\n{ISI}\n"
                f"#E {RUMUS}\n{ISI}\n#K الخاتمة\n{ISI}\n")
TEPI = 72  # pt dari tepi atas/bawah kertas: kepala/kaki halaman (bidang teks mulai 2,5 cm = 71 pt)
CM = 72 / 2.54


def tepi(hal):
    """(teks kepala, teks kaki) satu halaman PDF, tanpa spasi."""
    h = hal.rect.height
    atas = "".join(b[4] for b in hal.get_text("blocks") if b[3] < TEPI)
    bawah = "".join(b[4] for b in hal.get_text("blocks") if b[1] > h - TEPI)
    return atas.replace("\n", "").replace(" ", ""), bawah.replace("\n", "").replace(" ", "")


def rakit(akar, kepala):
    nama = {"": "bawaan", "-": "polos"}.get(kepala, kepala)
    f = akar / nama
    f.mkdir()
    (f / "naskah.txt").write_text(NASKAH.format(kepala=f"@kepala: {kepala}\n" if kepala else ""), encoding="utf8")
    r = bahts(akar, "rakit", nama, batas=1800)
    assert r.returncode == 0, r.stdout + r.stderr
    for jebak in ("nomor halaman tercetak", "halaman kosong"):
        assert jebak not in r.stdout, f"@kepala: {kepala}: PERINGATAN «{jebak}»\n{r.stdout}"
    return pymupdf.open(stream=(f / "uji.pdf").read_bytes(), filetype="pdf")   # tanpa memegang berkasnya (TEMP dibersihkan)


def kotak(akar):
    """@kepala: kotak + judul panjang + #E yang turun baris: rakit jadi; di kepala halaman isi judul rata kanan, tanpa
    kasyidah, tidak masuk kotak nomor di kiri; PERINGATAN @kepala_judul. Mengembalikan jumlah baris judul."""
    f = akar / "kotak_rumus"
    f.mkdir()
    (f / "naskah.txt").write_text(NASKAH_KOTAK, encoding="utf8")
    r = bahts(akar, "rakit", f.name, batas=1800)
    assert r.returncode == 0, "@kepala: kotak + #E: " + r.stdout + r.stderr
    assert "(@kepala: kotak)" in r.stdout and "@kepala_judul" in r.stdout, "PERINGATAN judul kepala kotak panjang\n" + r.stdout
    doc = pymupdf.open(stream=(f / "uji.pdf").read_bytes(), filetype="pdf")
    ihda, hal = doc[1], doc[2]   # الإهداء (halaman depan), lalu halaman pertama المقدمة
    assert not [d for d in ihda.get_drawings() if d["rect"].y1 < TEPI + 20] and tepi(ihda) == ("", "١"), \
        f"@kepala: kotak: halaman الإهداء berkepala: {tepi(ihda)}"
    w = hal.rect.width
    kotak = [d["rect"] for d in hal.get_drawings() if d["rect"].y1 < TEPI + 10 and 25 < d["rect"].width < 50]
    assert kotak and kotak[0].x1 < w / 2, f"kotak nomor halaman di kiri kepala: {kotak}"
    k = kotak[0]
    judul = [(sp["bbox"], sp["text"]) for b in hal.get_text("dict")["blocks"] for ln in b.get("lines", ())
             for sp in ln["spans"] if sp["bbox"][1] < TEPI - 5 and sp["text"].strip() and not sp["text"].strip().isdigit()]
    assert judul, "judul di kepala kotak"
    for bb, t in judul:
        assert bb[0] >= k.x1, f"judul kepala menimpa kotak nomor (x {k.x0:.0f}-{k.x1:.0f}): «{t}» mulai x={bb[0]:.0f}"
        assert "ـ" not in t, f"judul kepala diregang kasyidah: «{t}»"
    kanan = w - 3.5 * CM
    assert abs(max(bb[2] for bb, _ in judul) - kanan) < 6, f"judul kepala rata kanan (x={kanan:.0f}): {judul}"
    garis = [d["rect"] for d in hal.get_drawings() if d["rect"].y1 < TEPI + 20 and d["rect"].height < 2]
    assert garis and all(g.x0 < k.x0 + 1 and g.x1 > kanan - 3 for g in garis), f"garis ganda kepala selebar bidang teks: {garis}"
    baris = sorted({round(bb[3]) for bb, _ in judul})
    for y in baris[:-1]:   # baris yang bukan terakhir: rata kanan, tidak diregang sampai kotak nomor (rata kanan-kiri)
        kiri = min(bb[0] for bb, _ in judul if round(bb[3]) == y)
        assert kiri > k.x1 + 3, f"baris judul kepala y={y} diregang sampai kotak nomor (x={kiri:.0f})"
    return len(baris)


def rata(s):
    return s.replace(" ", "")


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji kepala halaman Word: " + alasan)
        return
    # #F «المبحث الأول: …» dicetak dua baris (@judul_fasl bawaan dua_baris): judul berjalan = baris pertamanya
    j, fasl = rata(JUDUL), rata(FASL.split(":")[0])
    with tempfile.TemporaryDirectory(prefix="bahts-kepala-word-") as t:
        akar = Path(t)
        salin_mesin(akar)
        pdf = {k: rakit(akar, k) for k in ("", "-", "bagian", "bagian_hias", "bintang", "bergantian", "kaki")}
        n = len(pdf["-"])
        assert n == 7, f"naskah uji: sampul, الإهداء, المقدمة 2 halaman, مبحث, الخاتمة, فهرس = 7 halaman, bukan {n}"
        for k, doc in pdf.items():
            assert len(doc) == n, f"@kepala: {k or '(bawaan)'}: {len(doc)} halaman, bukan {n} (halaman sisipan?)"
            assert tepi(doc[0]) == ("", ""), f"@kepala: {k}: sampul berkepala/bernomor: {tepi(doc[0])}"
            # halaman depan (الإهداء, nomor ١) dan belakang (فهرس, nomor ٦): tanpa kepala, nomor polos di tengah kaki
            for i, no in ((1, "١"), (6, "٦")):
                assert tepi(doc[i]) == ("", no), f"@kepala: {k or '(bawaan)'}: halaman {i + 1} di luar isi: {tepi(doc[i])}"
                assert not [d for d in doc[i].get_drawings() if d["rect"].y1 < TEPI + 20], f"@kepala: {k}: garis/bintang di luar isi"
                assert not [g for g in doc[i].get_image_info() if g["bbox"][1] < TEPI], f"@kepala: {k}: hiasan di luar isi"
        isi = range(2, 6)   # halaman PDF المقدمة (2), مبحث, الخاتمة; nomor tercetak = indeks halaman PDF
        kepala = {k: {i: tepi(doc[i]) for i in isi} for k, doc in pdf.items()}
        nomor = dict(zip(range(1, 7), "١٢٣٤٥٦"))
        # bawaan (klasik): judul bahts + nomor di kepala, kaki kosong
        for i, (atas, bawah) in kepala[""].items():
            assert j in atas and nomor[i] in atas and not bawah, ("bawaan", i + 1, atas, bawah)
        for i, (atas, bawah) in kepala["-"].items():
            assert not atas and bawah == nomor[i], ("-", i + 1, atas, bawah)
        for i, (atas, bawah) in kepala["kaki"].items():
            assert not atas and bawah == f"-{nomor[i]}-", ("kaki", i + 1, atas, bawah)
        # judul bagian berjalan: halaman ke-2 المقدمة (tanpa judul di halaman itu), lalu مبحث, الخاتمة
        berjalan = {2: "المقدمة", 3: "المقدمة", 4: fasl, 5: "الخاتمة"}
        for k in ("bagian", "bagian_hias"):
            for i, (atas, bawah) in kepala[k].items():
                assert berjalan[i] in atas and nomor[i] in atas and not bawah, (k, i + 1, atas, bawah)
        for i, (atas, bawah) in kepala["bergantian"].items():   # nomor ganjil: judul bagian, genap: judul bahts
            harap = berjalan[i] if i % 2 else j
            assert harap in atas and bawah == nomor[i], ("bergantian", i + 1, atas, bawah)
        for i, (atas, bawah) in kepala["bintang"].items():
            assert j in atas and nomor[i] in atas and not bawah, ("bintang", i + 1, atas, bawah)
        hias = [g for g in pdf["bagian_hias"][2].get_image_info() if g["bbox"][1] < TEPI]
        assert hias and not [g for g in pdf["bagian"][2].get_image_info() if g["bbox"][1] < TEPI], "hiasan kitab bagian_hias"
        # bintang: kecil (setinggi baris judul, ±0,7 cm), nomornya di tengah bintang
        hal = pdf["bintang"][2]
        bentuk = [d["rect"] for d in hal.get_drawings() if d["rect"].y1 < TEPI + 10 and d["rect"].x1 < hal.rect.width / 2]
        assert len(bentuk) >= 2, f"bintang delapan (persegi, belah ketupat) di kiri atas: {len(bentuk)} bentuk"
        luar = max(bentuk, key=lambda r: r.width)
        assert 0.5 * CM < luar.width < 0.9 * CM and abs(luar.width - luar.height) < 1, f"ukuran bintang: {luar}"
        # pusat gambar angka (kotak huruf yang pas di gambarnya, bukan kotak span: tinggi baris dan spasi ikut di situ)
        rd = hal.get_text("rawdict", flags=pymupdf.TEXT_ACCURATE_BBOXES)
        no = [pymupdf.Rect(c["bbox"]) for b in rd["blocks"] for ln in b.get("lines", ()) for sp in ln["spans"]
              for c in sp["chars"] if c["c"] == nomor[2] and c["bbox"][1] < TEPI]
        assert no, "nomor halaman di bintang"
        tengah = ((no[0].x0 + no[0].x1) / 2, (no[0].y0 + no[0].y1) / 2)
        assert abs(tengah[0] - (luar.x0 + luar.x1) / 2) < 1.5 and abs(tengah[1] - (luar.y0 + luar.y1) / 2) < 1.5, \
            f"nomor {no[0]} tidak di tengah bintang {luar}"
        # garis pemisah catatan kaki: 4,5 cm, ujung kanannya di tepi kanan bidang teks (tepi kanan kertas 3,5 cm)
        for k, doc in pdf.items():
            hal = doc[2]; w, h = hal.rect.width, hal.rect.height
            garis = [d["rect"] for d in hal.get_drawings() if h / 2 < d["rect"].y0 < h - TEPI and d["rect"].height < 2]
            assert len(garis) == 1, f"@kepala: {k}: garis pemisah catatan kaki: {garis}"
            g = garis[0]
            assert abs(g.width - 4.5 * CM) < 3 and abs(g.x1 - (w - 3.5 * CM)) < 3, f"@kepala: {k}: garis pemisah {g}"
        baris = kotak(akar)
        print(f"lolos kepala halaman Word: {len(pdf)} bentuk @kepala hanya di halaman isi, {n} halaman tanpa sisipan; "
              f"الإهداء dan فهرس bernomor polos di kaki; bintang {luar.width / CM:.2f} cm bernomor di tengah; garis pemisah "
              f"catatan kaki 4,5 cm di kanan; kotak + #E turun baris: judul {baris} baris di samping kotak nomor")


if __name__ == "__main__":
    utama()
