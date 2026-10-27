"""Bukti <<luar|berkas.pdf|hal>>: kutipan dari PDF penelitian (jurnal, risalah) yang disimpan di folder bahts
dicari di teks PDF itu, bukan di Shamela. Dipanggil `cek` (olah.py). Hasilnya hanya PENUNJUK HALAMAN, tidak pernah
bukti: teks PDF tidak bisa dipercaya seperti teks Shamela.

- Teks PDF buatan Word (kebanyakan jurnal Arab) mengambil huruf sambungan dengan urutan terbalik: «المقدمة» jadi
  «املقدمة», «الله» jadi «هللا». Karena itu kata dicocokkan menurut hurufnya, urutan huruf di dalam kata diabaikan;
  akibatnya kata yang memang berbeda (العلم/العمل) tidak bisa dibedakan.
- Sebagian PDF menyimpan kata satu baris dari kiri ke kanan: tiap halaman dicoba juga dengan urutan kata per baris
  dibalik; akibatnya kutipan yang urutan katanya dibalik bisa ikut cocok.
- Angka tidak dicocokkan (`padat` membuangnya). Halaman hasil scan (gambar tanpa teks) tidak bisa dibaca mesin.
"""
import functools, logging, re, unicodedata

from norma import padat

ARAB = re.compile(r"[؀-ۿ]")
MIN_ARAB = 50  # huruf Arab di satu halaman; kurang dari ini = halaman gambar (scan) atau kosong
logging.getLogger("pypdf").setLevel(logging.ERROR)  # keluhan pypdf soal PDF cacat tidak ikut tercetak di laporan `cek`


def _sidik(teks):
    """Tiap kata jadi hurufnya yang diurutkan (tahan terhadap huruf sambungan yang tertukar)."""
    return tuple("".join(sorted(p)) for p in map(padat, teks.split()) if p)


def _ada(halaman, kutipan):
    n = len(kutipan)
    return n > 0 and any(halaman[i:i + n] == kutipan for i in range(len(halaman) - n + 1))


@functools.lru_cache(maxsize=None)
def _baca(berkas, waktu):
    """((sidik apa adanya, sidik urutan kata per baris dibalik), jumlah huruf Arab) tiap halaman.
    `waktu` (saat berkas terakhir diubah) ikut kunci cache: PDF yang diganti dibaca ulang."""
    from pypdf import PdfReader
    hasil = []
    for p in PdfReader(berkas).pages:
        t = unicodedata.normalize("NFKC", p.extract_text() or "")  # bentuk tampilan (ﻣﻠﻒ, ﳌ) -> huruf biasa
        balik = "\n".join(" ".join(b.split()[::-1]) for b in t.splitlines())
        hasil.append(((_sidik(t), _sidik(balik)), len(ARAB.findall(t))))
    return tuple(hasil)


def halaman(berkas):
    """Isi PDF yang sudah diolah; berkas = Path. Galat pypdf (PDF rusak, bersandi) diteruskan ke pemanggil."""
    return _baca(str(berkas), berkas.stat().st_mtime)


def cari(isi, bagian):
    """Nomor halaman berkas (mulai 1) yang memuat semua `bagian` kutipan; isi = hasil `halaman`."""
    cari_ = [_sidik(b) for b in bagian]
    return [n for n, (v, _) in enumerate(isi, 1) if all(any(_ada(x, k) for x in v) for k in cari_)]


def tanpa_teks(isi, n):
    """Halaman berkas n berupa gambar (scan): teksnya tidak bisa dicocokkan mesin."""
    return isi[n - 1][1] < MIN_ARAB
