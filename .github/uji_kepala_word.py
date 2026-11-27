# SPDX-License-Identifier: AGPL-3.0-or-later
"""Kepala dan kaki halaman tiap `@kepala` dan garis pemisah catatan kaki lewat `rakit` dan Word asli, dibaca dari PDF.
Runner tanpa Word melaporkan lewati.

Naskah uji: sampul, المقدمة dua halaman (bercatatan kaki), مبحث, lalu فهرس الموضوعات. Yang dijaga: letak judul dan
nomor tiap bentuk (judul bagian yang berjalan ikut #K/#F dan judul فهرس, ganjil/genap bergantian), sampul tanpa
nomor, tidak ada halaman kosong sisipan Word (ganjil/genap), tanpa PERINGATAN nomor halaman, dan garis pemisah
catatan kaki 4,5 cm di kanan. Semua bahan di TEMP."""
import sys, tempfile
from pathlib import Path

import pymupdf

from bantu import bahts, salin_mesin, tanpa_word

JUDUL = "اختبار رأس الصفحة"
FASL = "المبحث الأول: عنوان الاختبار"
ISI = "هذا سطر من نص الاختبار يطول قليلا حتى يملأ الصفحة الأولى من المقدمة وينتقل إلى الثانية."
NASKAH = (f"@judul: {JUDUL}\n@nama: طالب\n@berkas: uji\n@tanpa: ayat, hadits, alam, firaq, pustaka\n"
          "@minimal_halaman: 0\n{kepala}#K المقدمة\n" + f"{ISI}[^حاشية للاختبار.]\n" + f"{ISI}\n" * 24
          + f"#F {FASL}\n{ISI}\n#K الخاتمة\n{ISI}\n")
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


def rata(s):
    return s.replace(" ", "")


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji kepala halaman Word: " + alasan)
        return
    j, fasl = rata(JUDUL), rata(FASL)
    with tempfile.TemporaryDirectory(prefix="bahts-kepala-word-") as t:
        akar = Path(t)
        salin_mesin(akar)
        pdf = {k: rakit(akar, k) for k in ("", "-", "bagian", "bagian_hias", "bintang", "bergantian", "kaki")}
        n = len(pdf["-"])
        assert n == 6, f"naskah uji: sampul, المقدمة 2 halaman, مبحث, الخاتمة, فهرس = 6 halaman, bukan {n}"
        for k, doc in pdf.items():
            assert len(doc) == n, f"@kepala: {k or '(bawaan)'}: {len(doc)} halaman, bukan {n} (halaman sisipan?)"
            assert tepi(doc[0]) == ("", ""), f"@kepala: {k}: sampul berkepala/bernomor: {tepi(doc[0])}"
        kepala = {k: [tepi(doc[i]) for i in range(1, n)] for k, doc in pdf.items()}
        nomor = ["١", "٢", "٣", "٤", "٥"]
        # bawaan (klasik): judul bahts + nomor di kepala, kaki kosong
        for i, (atas, bawah) in enumerate(kepala[""]):
            assert j in atas and nomor[i] in atas and not bawah, ("bawaan", i + 2, atas, bawah)
        for i, (atas, bawah) in enumerate(kepala["-"]):
            assert not atas and bawah == nomor[i], ("-", i + 2, atas, bawah)
        for i, (atas, bawah) in enumerate(kepala["kaki"]):
            assert not atas and bawah == f"-{nomor[i]}-", ("kaki", i + 2, atas, bawah)
        # judul bagian berjalan: halaman ke-2 المقدمة (tanpa judul di halaman itu), lalu مبحث, الخاتمة, judul فهرس
        berjalan = ["المقدمة", "المقدمة", fasl, "الخاتمة", "فهرسالموضوعات"]
        for k in ("bagian", "bagian_hias"):
            for i, (atas, bawah) in enumerate(kepala[k]):
                assert berjalan[i] in atas and nomor[i] in atas and not bawah, (k, i + 2, atas, bawah)
        for i, (atas, bawah) in enumerate(kepala["bergantian"]):   # nomor ganjil: judul bagian, genap: judul bahts
            harap = berjalan[i] if i % 2 == 0 else j
            assert harap in atas and bawah == nomor[i], ("bergantian", i + 2, atas, bawah)
        for i, (atas, bawah) in enumerate(kepala["bintang"]):
            assert j in atas and nomor[i] in atas and not bawah, ("bintang", i + 2, atas, bawah)
        hias = [g for g in pdf["bagian_hias"][1].get_image_info() if g["bbox"][1] < TEPI]
        assert hias and not [g for g in pdf["bagian"][1].get_image_info() if g["bbox"][1] < TEPI], "hiasan kitab bagian_hias"
        hal = pdf["bintang"][1]
        bentuk = [d for d in hal.get_drawings() if d["rect"].y1 < TEPI + 10 and d["rect"].x1 < hal.rect.width / 2]
        assert len(bentuk) >= 3, f"bintang delapan (persegi, belah ketupat, lingkaran) di kiri atas: {len(bentuk)} bentuk"
        # garis pemisah catatan kaki: 4,5 cm, ujung kanannya di tepi kanan bidang teks (tepi kanan kertas 3,5 cm)
        for k, doc in pdf.items():
            hal = doc[1]; w, h = hal.rect.width, hal.rect.height
            garis = [d["rect"] for d in hal.get_drawings() if h / 2 < d["rect"].y0 < h - TEPI and d["rect"].height < 2]
            assert len(garis) == 1, f"@kepala: {k}: garis pemisah catatan kaki: {garis}"
            g = garis[0]
            assert abs(g.width - 4.5 * CM) < 3 and abs(g.x1 - (w - 3.5 * CM)) < 3, f"@kepala: {k}: garis pemisah {g}"
        print(f"lolos kepala halaman Word: {len(pdf)} bentuk @kepala, {n} halaman tanpa sisipan; "
              "garis pemisah catatan kaki 4,5 cm di kanan")


if __name__ == "__main__":
    utama()
