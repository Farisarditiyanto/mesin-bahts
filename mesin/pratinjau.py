# SPDX-License-Identifier: AGPL-3.0-or-later
"""`pratinjau <folder> [halaman]`: halaman PDF hasil `rakit` yang terakhir (seluruh naskah atau potongan --fasl) jadi
gambar PNG di folder baru di TEMP: grid 2×2 (urut kanan-ke-kiri), atau satu halaman penuh kalau satu nomor diminta.
Untuk pemeriksa langkah 5 menilai tata letak (sampul, tepi, tabel #J, gambar #G, rumus #E, halaman hampir kosong)."""
import contextlib, re, shutil, sys, tempfile, time
from pathlib import Path

import tahap
from dasar import perintah

TEPI = 24  # pt: bingkai luar dan celah antarhalaman di grid
KEPALA = 22  # pt: ruang label «hal N / total» di atas tiap halaman
SKALA_GRID = 1.6  # ±115 DPI per halaman A4: matan masih terbaca, berkasnya ringan
SKALA_SATU = 2.0  # ±144 DPI untuk satu halaman penuh
POSISI = ((1, 0), (0, 0), (1, 1), (0, 1))  # (kolom, baris) halaman ke-1..4 di grid: mulai kanan atas
UMUR_PRATINJAU_DETIK = 3600


def _berkas(folder):
    try:
        teks = (folder / "naskah.txt").read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        sys.exit(f"{folder.name}/naskah.txt bukan UTF-8: simpan ulang sebagai UTF-8, lalu ulangi.")
    berkas = ""
    for baris in teks.splitlines():
        if baris.startswith("@"):
            k, _, v = baris[1:].partition(":")
            if k.strip() == "berkas":
                berkas = v.strip()
    return berkas or folder.name


def _bersihkan_lama(induk, awalan, umur=UMUR_PRATINJAU_DETIK):
    batas = time.time() - umur
    try:
        calon = [p for p in induk.iterdir()
                 if p.name.startswith(awalan) and p.is_dir() and not p.is_symlink() and not p.is_junction()]
    except OSError:
        return
    for p in calon:
        with contextlib.suppress(OSError):
            if p.stat().st_mtime < batas:
                shutil.rmtree(p, ignore_errors=True)


def _halaman(rentang, total):
    """«3» atau «2-5» -> indeks halaman (mulai 0); None = semua."""
    if rentang is None:
        return list(range(total))
    m = re.fullmatch(r"(\d+)(?:-(\d+))?", rentang)
    if not m:
        raise ValueError(f"halaman ditulis angka (mis. 3) atau rentang awal-akhir (mis. 1-4), bukan «{rentang}»")
    a, z = int(m[1]), int(m[2] or m[1])
    if a > z:
        raise ValueError(f"rentang halaman ditulis dari kecil ke besar, bukan «{rentang}»")
    if not 1 <= a <= z <= total:
        raise ValueError(f"halaman {rentang} di luar PDF ini (1-{total})")
    return list(range(a - 1, z))


def render(folder, jalur, rentang=None):
    """Cetak satu baris «<isi>: <jalur PNG>» per gambar."""
    try:
        import pymupdf
    except ImportError:
        sys.exit(f"`pratinjau` butuh pustaka pymupdf: jalankan `{perintah('periksa')}`")
    pdf = tahap.pdf_terakhir(folder, _berkas(folder))
    if pdf is None or not pdf.is_file():
        sys.exit(f"PDF hasil rakit belum ada di folder ini: jalankan `{perintah(f'rakit "{jalur}"')}` dulu")
    awalan = f"bahts-pratinjau-{folder.name}__"
    _bersihkan_lama(Path(tempfile.gettempdir()), awalan)
    with pymupdf.open(pdf) as doc:
        total = len(doc)
        indeks = _halaman(rentang, total)
        tujuan = Path(tempfile.mkdtemp(prefix=awalan))
        if len(indeks) == 1:
            keluar = tujuan / f"hal_{indeks[0] + 1}.png"
            doc[indeks[0]].get_pixmap(matrix=pymupdf.Matrix(SKALA_SATU, SKALA_SATU), alpha=False).save(keluar)
            print(f"hal {indeks[0] + 1}: {keluar}")
            return
        lebar = max(doc[i].rect.width for i in indeks)
        tinggi = max(doc[i].rect.height for i in indeks)
        for g, awal in enumerate(range(0, len(indeks), 4), 1):
            isi = indeks[awal:awal + 4]
            with pymupdf.open() as kanvas:
                p = kanvas.new_page(width=TEPI * 3 + lebar * 2, height=TEPI * 3 + (tinggi + KEPALA) * 2)
                p.draw_rect(p.rect, color=None, fill=(0.95, 0.95, 0.95))
                for i, (kolom, baris) in zip(isi, POSISI):
                    x, y = TEPI + kolom * (lebar + TEPI), TEPI + baris * (tinggi + KEPALA + TEPI)
                    kotak = pymupdf.Rect(x, y + KEPALA, x + lebar, y + KEPALA + tinggi)
                    p.draw_rect(kotak, color=(0.55, 0.55, 0.55), fill=(1, 1, 1), width=1.0)  # bingkai = batas kertas
                    p.show_pdf_page(kotak, doc, i)
                    p.insert_text((x + 4, y + KEPALA - 6), f"hal {i + 1} / {total}", fontsize=13, color=(0.2, 0.2, 0.2))
                keluar = tujuan / f"grid_{g}.png"
                p.get_pixmap(matrix=pymupdf.Matrix(SKALA_GRID, SKALA_GRID), alpha=False).save(keluar)
            print(f"grid {g} (hal {isi[0] + 1}" + (f"-{isi[-1] + 1}" if len(isi) > 1 else "") + f"): {keluar}")
