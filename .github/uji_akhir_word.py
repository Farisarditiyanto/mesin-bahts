# SPDX-License-Identifier: AGPL-3.0-or-later
"""Halaman terakhir PDF lewat `rakit` dan Word asli: bahts tanpa المصادر dan فهرس (`@tanpa`, tanpa #R) yang isinya pas
memenuhi halaman tidak berakhir dengan halaman kosong bernomor. Runner tanpa Word melaporkan lewati.

Jebakannya paragraf kosong penutup dokumen Word: 50 baris pendek berakhir tepat di tepi bawah halaman, jadi paragraf
itu tumpah ke halaman baru walau dikecilkan sampai 1 pt. Tes memastikan naskahnya memang masih pas memenuhi halaman
(kalau Word/huruf mengubah tata letaknya, tes gagal dan meminta jumlah barisnya disesuaikan). Semua bahan di TEMP."""
import re, sys, tempfile, zipfile
from pathlib import Path

import pymupdf

from bantu import bahts, salin_mesin, tanpa_word

KEPALA = ("@judul: اختبار الصفحة الأخيرة\n@nama: طالب\n@berkas: uji\n@tanpa: ayat, hadits, maudhuat, pustaka\n"
          "@minimal_halaman: 0\n#K المقدمة\n")


def baris(n):
    return "".join(f"هذا هو السطر رقم {i} من نص الاختبار.\n" for i in range(1, n + 1))


def rakit(akar, nama, teks):
    f = akar / nama
    f.mkdir()
    (f / "naskah.txt").write_text(KEPALA + teks, encoding="utf8")
    r = bahts(akar, "rakit", nama, batas=1800)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "halaman kosong" not in r.stdout, f"{nama}: {r.stdout}"
    with zipfile.ZipFile(f / "uji.docx") as z:
        xml = z.read("word/document.xml").decode("utf8")
    doc = pymupdf.open(f / "uji.pdf")
    hal = int(re.search(r"^HALAMAN=(\d+)", r.stdout, re.M).group(1))
    assert hal == len(doc), (hal, len(doc))
    tepi = int(re.findall(r'<w:pgMar [^>]*w:bottom="(\d+)"', xml)[-1]) / 20   # bagian Word terakhir (bukan sampul)
    akhir = doc[-1]
    # baris isi = berhuruf, selain nomor halaman di kaki (hanya angka)
    isi = [l for b in akhir.get_text("dict")["blocks"] for l in b.get("lines", [])
           if (t := "".join(s["text"] for s in l["spans"]).strip()) and not t.isdigit()]
    teks, sisa = akhir.get_text(), akhir.rect.height - tepi - max((l["bbox"][3] for l in isi), default=0)
    doc.close()
    assert isi, f"{nama}: halaman PDF terakhir (ke-{hal}) kosong"
    return hal, teks, sisa


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji halaman akhir Word: " + alasan)
        return
    with tempfile.TemporaryDirectory(prefix="bahts-akhir-word-") as t:
        akar = Path(t)
        salin_mesin(akar)
        # 50 baris: baris ke-50 tepat di tepi bawah halaman ketiga
        hal, teks, sisa = rakit(akar, "pas", baris(50))
        assert sisa < 3, (f"naskah uji tidak lagi pas memenuhi halaman (sisa {sisa:.1f} pt di bawah baris terakhir): "
                          "jebakannya tidak teruji, sesuaikan jumlah barisnya")
        assert "٥٠" in teks or "٠٥" in teks, teks   # teks PDF Word: angka ٠-٩ bisa terbaca terbalik
        print(f"lolos halaman akhir: 50 baris pas di tepi bawah (sisa {sisa:.1f} pt), {hal} halaman tanpa halaman kosong")
        # 24 baris: sisa ruang di bawah baris terakhir kurang dari satu baris matan
        hal, _, sisa = rakit(akar, "hampir", baris(24))
        print(f"lolos halaman akhir: 24 baris (sisa {sisa:.1f} pt), {hal} halaman tanpa halaman kosong")


if __name__ == "__main__":
    utama()
