"""Bukti <<luar|berkas.pdf|hal>>: kutipan dari PDF penelitian (jurnal, risalah) yang disimpan di folder bahts
dicari di teks PDF itu, bukan di Shamela. Dipanggil `cek` (olah.py).

Teks PDF buatan Word (kebanyakan jurnal Arab) terambil dengan huruf sambungan tertukar di dalam katanya:
«المقدمة» jadi «املقدمة», «الله» jadi «هللا», «محمد» jadi «حممد». Sebagian PDF juga menyimpan kata satu baris
dari kiri ke kanan, sehingga urutan katanya terbalik. Karena itu kata dibandingkan menurut hurufnya (urutan huruf
di dalam kata diabaikan), dan tiap halaman dicoba juga dengan urutan kata per baris dibalik. Urutan kata di dalam
kutipan tetap harus sama. Halaman hasil scan (gambar tanpa teks) tidak bisa dibaca mesin.
"""
import functools, re, unicodedata

from norma import padat

ARAB = re.compile(r"[؀-ۿ]")
MIN_ARAB = 50  # huruf Arab di satu halaman; kurang dari ini = halaman gambar (scan) atau kosong


def _sidik(teks):
    """Tiap kata jadi hurufnya yang diurutkan: tahan terhadap huruf sambungan yang tertukar di dalam kata."""
    return tuple("".join(sorted(p)) for p in map(padat, teks.split()) if p)


def _ada(halaman, kutipan):
    n = len(kutipan)
    return n > 0 and any(halaman[i:i + n] == kutipan for i in range(len(halaman) - n + 1))


@functools.lru_cache(maxsize=None)
def _baca(berkas, waktu):
    """((sidik apa adanya, sidik urutan kata per baris dibalik, jumlah huruf Arab), …) tiap halaman.
    `waktu` (saat berkas terakhir diubah) ikut kunci cache: PDF yang diganti dibaca ulang."""
    from pypdf import PdfReader
    hasil = []
    for p in PdfReader(berkas).pages:
        t = unicodedata.normalize("NFKC", p.extract_text() or "")  # bentuk tampilan (ﻣﻠﻒ) -> huruf biasa
        balik = "\n".join(" ".join(b.split()[::-1]) for b in t.splitlines())
        hasil.append((_sidik(t), _sidik(balik), len(ARAB.findall(t))))
    return tuple(hasil)


def halaman(berkas):
    """Isi PDF yang sudah diolah; berkas = Path. OSError/ValueError dari pypdf diteruskan ke pemanggil."""
    return _baca(str(berkas), berkas.stat().st_mtime)


def cari(isi, bagian):
    """Nomor halaman berkas (mulai 1) yang memuat semua `bagian` kutipan; isi = hasil `halaman`."""
    sidik = [_sidik(b) for b in bagian]
    return [n for n, (a, b, _) in enumerate(isi, 1) if all(_ada(a, s) or _ada(b, s) for s in sidik)]


def tanpa_teks(isi, n):
    """Halaman berkas n berupa gambar (scan): teksnya tidak bisa dicocokkan mesin."""
    return isi[n - 1][2] < MIN_ARAB
