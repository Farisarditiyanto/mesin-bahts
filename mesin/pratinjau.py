# SPDX-License-Identifier: AGPL-3.0-or-later
"""`pratinjau <folder> [halaman]`: ubah halaman PDF hasil `rakit` menjadi gambar PNG grid 2×2 (atau 1 halaman penuh
bila satu nomor diminta) di folder TEMP, supaya pemeriksa (langkah 5) dapat menilai tata letak visual (sampul, margin,
tabel #J, gambar #G, rumus #E, halaman kosong) tanpa mengotori folder bahts. Memakai `pymupdf` (sudah di requirements.txt)."""
import re, tempfile
from pathlib import Path

import produk
from dasar import perintah

TEPI = 24  # pt: bingkai luar & celah antarhalaman pada grid 2×2
KEPALA = 22  # pt: ruang label «hal N» di atas tiap halaman dalam grid
SKALA_GRID = 1.6  # ±115 DPI per halaman A4 dalam grid 2×2: tajam dibaca agen, ukuran berkas tetap ringan
SKALA_SATU = 2.0  # ±144 DPI untuk satu halaman penuh


def _pdf_bahts(folder):
    """Berkas PDF hasil `rakit` untuk folder bahts ini (dari @berkas di naskah.txt, bawaan nama folder)."""
    naskah = (folder / "naskah.txt").read_text(encoding="utf-8-sig")
    m = re.search(r"^@berkas:[ \t]*(\S.*)$", naskah, re.M)
    berkas = m.group(1).strip() if m else folder.name
    return folder / produk.pdf(berkas)


def _urai_rentang(rentang, total):
    """«1» atau «2-5» -> daftar indeks 0-based; None -> seluruh halaman."""
    if rentang is None:
        return list(range(total))
    m = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", rentang.strip())
    if not m:
        raise ValueError(f"halaman ditulis angka (mis. 1) atau rentang awal-akhir (mis. 1-4), bukan «{rentang}»")
    a, z = int(m[1]), int(m[2] or m[1])
    if a < 1 or z < a or z > total:
        raise ValueError(f"halaman {rentang} di luar rentang PDF (1-{total})")
    return list(range(a - 1, z))


def render(folder, rentang=None, *, pdf=None, keluar=None):
    """Render halaman PDF ke PNG di `keluar` (bawaan: folder unik baru di TEMP). Kembalikan daftar Path PNG."""
    try:
        import pymupdf
    except ImportError as e:
        raise RuntimeError("pustaka `pymupdf` belum terpasang (jalankan `python mesin/bahts.py periksa`)") from e

    folder = Path(folder)
    sumber = Path(pdf) if pdf is not None else _pdf_bahts(folder)
    if not sumber.is_file():
        raise FileNotFoundError(f"PDF «{sumber.name}» belum ada di {folder.name}: jalankan `{perintah(f'rakit {folder.name}')}` dulu")

    doc = pymupdf.open(sumber)
    try:
        total = len(doc)
        if not total:
            raise ValueError(f"PDF «{sumber.name}» tidak punya halaman")
        indeks = _urai_rentang(rentang, total)
        tujuan = Path(keluar) if keluar is not None else Path(tempfile.mkdtemp(prefix=f"bahts-pratinjau-{folder.name}-"))
        tujuan.mkdir(parents=True, exist_ok=True)
        hasil = []

        if len(indeks) == 1:
            hal = indeks[0]
            out = tujuan / f"hal_{hal + 1}.png"
            doc[hal].get_pixmap(matrix=pymupdf.Matrix(SKALA_SATU, SKALA_SATU), alpha=False).save(out)
            hasil.append(out)
            print(f"hal {hal + 1}: {out}")
            return hasil

        # Grid 2×2 (kanan-ke-kiri: hal 1 kanan-atas, hal 2 kiri-atas, hal 3 kanan-bawah, hal 4 kiri-bawah)
        # memakai vector show_pdf_page + garis tepi tipis supaya batas margin dan luberan langsung kelihatan
        lebar_hal = max(float(doc[i].rect.width) for i in indeks)
        tinggi_hal = max(float(doc[i].rect.height) for i in indeks)
        sel_w = lebar_hal
        sel_h = tinggi_hal + KEPALA
        kanvas_w = TEPI * 3 + sel_w * 2
        kanvas_h = TEPI * 3 + sel_h * 2
        # Urutan sel 2×2 RTL untuk bahts Arab: (kolom 1 = kanan, baris 0), (kolom 0 = kiri, baris 0), dst.
        posisi = ((1, 0), (0, 0), (1, 1), (0, 1))

        for g, awal in enumerate(range(0, len(indeks), 4), 1):
            potong = indeks[awal:awal + 4]
            kanvas = pymupdf.open()
            try:
                p = kanvas.new_page(width=kanvas_w, height=kanvas_h)
                p.draw_rect(p.rect, color=None, fill=(0.95, 0.95, 0.95))
                for idx, (kol, bar) in zip(potong, posisi):
                    x0 = TEPI + kol * (sel_w + TEPI)
                    y0 = TEPI + bar * (sel_h + TEPI)
                    kotak = pymupdf.Rect(x0, y0 + KEPALA, x0 + lebar_hal, y0 + KEPALA + tinggi_hal)
                    p.draw_rect(kotak, color=(0.55, 0.55, 0.55), fill=(1, 1, 1), width=1.0)
                    p.show_pdf_page(kotak, doc, idx)
                    p.insert_text((x0 + 4, y0 + KEPALA - 6), f"hal {idx + 1} / {total}", fontsize=13, color=(0.2, 0.2, 0.2))
                out = tujuan / f"grid_{g}.png"
                p.get_pixmap(matrix=pymupdf.Matrix(SKALA_GRID, SKALA_GRID), alpha=False).save(out)
            finally:
                kanvas.close()
            hasil.append(out)
            label = f"hal {potong[0] + 1}" if len(potong) == 1 else f"hal {potong[0] + 1}-{potong[-1] + 1}"
            print(f"grid {g} ({label}): {out}")
        return hasil
    finally:
        doc.close()
