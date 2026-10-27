"""Bukti <<luar|berkas.pdf|hal>>: kutipan dari PDF penelitian (jurnal, risalah) yang disimpan di folder bahts
dicari di teks PDF itu, bukan di Shamela. Dipanggil `cek` (olah.py).

Dua cara cocok, per kata, urutan kata kutipan tetap harus sama:
- persis: huruf tiap kata sama dan berurutan (bentuk `padat`). Bentuk tampilan (ﻣﻠﻒ, ﳌ) dibuka dulu dengan NFKC.
- tertukar: huruf tiap kata sama, urutannya diabaikan. Teks PDF buatan Word (kebanyakan jurnal Arab) mengambil
  huruf sambungan dengan urutan terbalik: «المقدمة» jadi «املقدمة», «الله» jadi «هللا», «محمد» jadi «حممد». Cara
  ini juga menyamakan kata yang memang berbeda (العلم/العمل), jadi hasilnya hanya penunjuk halaman, bukan bukti.
Sebagian PDF menyimpan kata satu baris dari kiri ke kanan: tiap halaman dicoba juga dengan urutan kata per baris
dibalik. Halaman hasil scan (gambar tanpa teks) tidak bisa dibaca mesin.
"""
import functools, logging, re, unicodedata

from norma import padat

ARAB = re.compile(r"[؀-ۿ]")
MIN_ARAB = 50  # huruf Arab di satu halaman; kurang dari ini = halaman gambar (scan) atau kosong
logging.getLogger("pypdf").setLevel(logging.ERROR)  # keluhan pypdf soal PDF cacat tidak ikut tercetak di laporan `cek`


def _kata(teks):
    return tuple(p for p in map(padat, teks.split()) if p)


def _tertukar(kata):
    return tuple("".join(sorted(k)) for k in kata)


def _ada(halaman, kutipan):
    n = len(kutipan)
    return n > 0 and any(halaman[i:i + n] == kutipan for i in range(len(halaman) - n + 1))


@functools.lru_cache(maxsize=None)
def _baca(berkas, waktu):
    """Tiap halaman: {"persis": (kata, kata baris dibalik), "tertukar": (…), "arab": jumlah huruf Arab}.
    `waktu` (saat berkas terakhir diubah) ikut kunci cache: PDF yang diganti dibaca ulang."""
    from pypdf import PdfReader
    hasil = []
    for p in PdfReader(berkas).pages:
        t = unicodedata.normalize("NFKC", p.extract_text() or "")
        kata = (_kata(t), _kata("\n".join(" ".join(b.split()[::-1]) for b in t.splitlines())))
        hasil.append({"persis": kata, "tertukar": tuple(map(_tertukar, kata)), "arab": len(ARAB.findall(t))})
    return tuple(hasil)


def halaman(berkas):
    """Isi PDF yang sudah diolah; berkas = Path. Galat pypdf (PDF rusak, bersandi) diteruskan ke pemanggil."""
    return _baca(str(berkas), berkas.stat().st_mtime)


def cari(isi, bagian, cara="persis"):
    """Nomor halaman berkas (mulai 1) yang memuat semua `bagian` kutipan; isi = hasil `halaman`, cara = persis/tertukar."""
    ubah = _tertukar if cara == "tertukar" else (lambda k: k)
    cari_ = [ubah(_kata(b)) for b in bagian]
    return [n for n, h in enumerate(isi, 1) if all(any(_ada(v, k) for v in h[cara]) for k in cari_)]


def tanpa_teks(isi, n):
    """Halaman berkas n berupa gambar (scan): teksnya tidak bisa dicocokkan mesin."""
    return isi[n - 1]["arab"] < MIN_ARAB
