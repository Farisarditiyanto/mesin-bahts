# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sisipan berdata `#D`: mahasiswa menulis DATA (rukun qiyas, aqwal khilaf, cabang pohon…), mesin menggambarnya.

Satu jenis = satu modul di paket ini, ditemukan sendiri (`JENIS`): tambah jenis = tambah satu berkas. Tiap modul punya
`NAMA` (kata Arab di kepala `#D`), `KUNCI` ({kunci baris isi: bentuk nilainya}), `URAIAN` dan `CONTOH` (dicetak `tanda`),
`urai(n_kepala, baris) -> data` (galat bentuk = `Salah`), dan `html(data, angka) -> str` (HTML RTL tanpa gaya: seluruh
gaya di `tema.css`, supaya tampilan semua jenis diganti di satu berkas).

Gambar = HTML -> PNG lewat Chrome/Edge (`diagram.browser()`) dan puppeteer-core (Node.js `npx`, versi dikunci), sekali
jalan untuk semua sisipan yang belum ada. PNG disimpan di `<folder bahts>/.sisipan/<sidik>.png`; sidik = SHA-256 halaman
HTML utuh (data, tema, huruf, lebar) + versi perender, jadi data atau tema yang berubah = gambar baru, dan `cek` di
komputer yang sudah punya PNG-nya tidak butuh Node/Chrome."""
import hashlib, html, importlib, json, os, pkgutil, re, subprocess, tempfile, zlib
from pathlib import Path

import diagram
from berkas import sementara

PUPPETEER = "puppeteer-core@24.39.1"  # versi dikunci: hasil sama di komputer lain
DPI = 300
SKALA = DPI / 96  # piksel PNG per piksel CSS; DPI ditulis di PNG (pHYs): Word menyisipkannya seukuran rancangan (pt)
FOLDER = ".sisipan"
TEMA = Path(__file__).with_name("tema.css")
POTRET = Path(__file__).with_name("potret.js")
GAMBAR = Path(__file__).with_name("gambar.js")  # kurung kurawal; ikut halaman, jadi ikut sidik
ANGKA_HINDI = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
ANGKA_BARAT = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
URUTAN = ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس", "السابع", "الثامن", "التاسع", "العاشر")
E = html.escape


class Salah(Exception):
    """Galat bentuk data satu sisipan, di baris naskah ke-n."""

    def __init__(self, n, pesan):
        super().__init__(pesan)
        self.n = n


def pisah(nilai):
    """«a | b | c» -> ["a", "b", "c"]."""
    return [x.strip() for x in nilai.split("|")]


def daftar(nilai):
    """«a، b، c» (atau koma Latin) -> ["a", "b", "c"], tanpa butir kosong."""
    return [x.strip() for x in re.split(r"[،,]", nilai) if x.strip()]


def bilangan(n, nilai, nama):
    """Bilangan bulat dari teks berangka Arab/Persia/Latin; Salah kalau bukan."""
    t = nilai.strip().translate(ANGKA_BARAT)
    if not t.isdigit():
        raise Salah(n, f"{nama} harus bilangan, bukan «{nilai}»")
    return int(t)


def satu(n_kepala, baris, kunci, wajib=True):
    """(n, nilai) baris `kunci` yang ditulis sekali; ditulis dua kali = Salah, tidak ada = Salah (wajib) atau None."""
    ada = [(n, v) for n, k, v in baris if k == kunci]
    if len(ada) > 1:
        raise Salah(ada[1][0], f"«{kunci}:» ditulis dua kali (pertama di baris {ada[0][0]})")
    if not ada and wajib:
        raise Salah(n_kepala, f"baris «#D {kunci}: …» belum ada")
    return ada[0] if ada else None


def urutan(i):
    """Kata urutan Arab ke-i (0 = الأول)."""
    return URUTAN[i] if i < len(URUTAN) else str(i + 1)


def nomor(i, angka):
    """«١- » untuk butir ke-i (0 = pertama), angka menurut @angka."""
    return f"{angka(i + 1)}- "


def kurung(induk, anak, kelas=""):
    """Induk (HTML) yang bercabang ke anak-anaknya (daftar HTML) lewat kurung kurawal (gambar.js)."""
    return f'<div class="br {kelas}">{induk}<div class="bs"></div><div class="ch">{"".join(anak)}</div></div>'


def butir(isi):
    """Satu baris daftar di bawah kurung."""
    return f'<div class="lf">{isi}</div>'


def _temukan():
    jenis = {}
    for m in pkgutil.iter_modules(__path__):
        modul = importlib.import_module(f"{__name__}.{m.name}")
        if hasattr(modul, "NAMA"):
            jenis[modul.NAMA] = modul
    return jenis


JENIS = _temukan()  # kata Arab di kepala «#D <jenis> | …» -> modulnya


def halaman(modul, data, huruf, lebar_cm, angka):
    """Dokumen HTML utuh satu sisipan: tema, huruf profil, lebar teks halaman, isinya (#fig), dan penggambar kurungnya."""
    ubah = (lambda s: str(s).translate(ANGKA_HINDI)) if angka == "hindi" else str
    return (f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>'
            f':root{{--huruf:"{huruf}";--lebar:{lebar_cm}cm}}\n{TEMA.read_text(encoding="utf8")}</style></head>'
            f'<body><div id="fig" class="{modul.__name__.rsplit(".", 1)[1]}">{modul.html(data, ubah)}</div>'
            f'<script>{GAMBAR.read_text(encoding="utf8")}</script></body></html>')


def sidik(dokumen):
    """Nama berkas PNG sebuah halaman sisipan: yang mengubah gambar (HTML, perender) mengubah sidiknya."""
    return hashlib.sha256("\n".join((dokumen, PUPPETEER, str(SKALA), POTRET.read_text(encoding="utf8"))).encode("utf8")).hexdigest()


def belum_bisa():
    """Kalimat syarat yang belum ada untuk menggambar (Node.js, browser), atau ""."""
    if not diagram.npx():
        return f"Node.js (npx) tidak ditemukan: pasang {diagram.PASANG_NODE}"
    if not diagram.browser():
        return (f"browser Chromium tidak ditemukan: pasang {diagram.PASANG_BROWSER}, "
                "atau tulis jalur chrome.exe di variabel lingkungan BAHTS_CHROME")
    return ""


def _dpi(png):
    """PNG dengan potongan pHYs = DPI (menggantikan pHYs lama): ukuran cetak Word = ukuran rancangan."""
    ppm = round(DPI / 0.0254).to_bytes(4, "big")
    isi = b"pHYs" + ppm + ppm + b"\x01"
    potongan = len(isi[4:]).to_bytes(4, "big") + isi + zlib.crc32(isi).to_bytes(4, "big")
    keluar, i = bytearray(png[:8]), 8
    while i < len(png):
        n = int.from_bytes(png[i:i + 4], "big")
        jenis = png[i + 4:i + 8]
        if jenis != b"pHYs":
            keluar += png[i:i + 12 + n]
        if jenis == b"IHDR":
            keluar += potongan
        i += 12 + n
    return bytes(keluar)


def gambar(kerja):
    """Render [(dokumen HTML, jalur PNG)] dalam satu sesi browser. Kembalikan {jalur PNG: pesan galat} yang gagal."""
    if not kerja:
        return {}
    if syarat := belum_bisa():
        return {png: syarat for _, png in kerja}
    gagal = {}
    with tempfile.TemporaryDirectory(prefix="bahts-sisipan-") as t:
        t = Path(t)
        tugas = []
        for i, (dokumen, _) in enumerate(kerja):
            (t / f"{i}.html").write_text(dokumen, encoding="utf8")
            tugas.append({"html": (t / f"{i}.html").as_uri(), "png": str(t / f"{i}.png")})
        (t / "tugas.json").write_text(json.dumps({"chrome": diagram.browser(), "skala": SKALA, "tugas": tugas}), encoding="utf8")
        try:
            r = subprocess.run([diagram.npx(), "-y", "-p", PUPPETEER, "node", str(POTRET), str(t / "tugas.json")],
                               capture_output=True, text=True, encoding="utf8", errors="replace", timeout=600,
                               env={**os.environ, "npm_config_update_notifier": "false"})
            pesan = (r.stderr or r.stdout).strip().splitlines()
            umum = next((x for x in pesan if "rror" in x), pesan[-1] if pesan else "perender tidak menghasilkan PNG")
        except (OSError, subprocess.TimeoutExpired) as e:
            umum = "perender kehabisan waktu" if isinstance(e, subprocess.TimeoutExpired) else str(e)
        for (_, png), tg in zip(kerja, tugas):
            hasil = Path(tg["png"])
            if not hasil.is_file() or not hasil.stat().st_size:
                gagal[png] = umum
                continue
            with sementara(png) as part:
                part.write_bytes(_dpi(hasil.read_bytes()))
    return gagal
