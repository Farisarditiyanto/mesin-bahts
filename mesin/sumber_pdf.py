# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bukti <<luar|berkas.pdf|hal>>: kutipan dari PDF penelitian (jurnal, risalah) yang disimpan di folder bahts
dicari di teks PDF itu, bukan di Shamela. Dipanggil `cek` (cek_kutipan.cek_pdf). Hasilnya hanya PENUNJUK HALAMAN, tidak pernah
bukti: teks PDF tidak bisa dipercaya seperti teks Shamela.

- Teks PDF buatan Word (kebanyakan jurnal Arab) mengambil huruf sambungan dengan urutan terbalik: «المقدمة» jadi
  «املقدمة», «الله» jadi «هللا». Karena itu kata dicocokkan menurut hurufnya, urutan huruf di dalam kata diabaikan;
  akibatnya kata yang memang berbeda (العلم/العمل) tidak bisa dibedakan.
- Sebagian PDF menyimpan kata satu baris dari kiri ke kanan: tiap halaman dicoba juga dengan urutan kata per baris
  dibalik; akibatnya kutipan yang urutan katanya dibalik bisa ikut cocok.
- Angka tidak dicocokkan (`padat` membuangnya). Halaman hasil scan (gambar tanpa teks) tidak bisa dibaca mesin.
"""
import functools, logging, re, unicodedata
from collections import Counter

from norma import HARAKAT, padat

ARAB = re.compile(r"[؀-ۿ]")
ARAH = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
KATA_ARAB = re.compile(r"[ء-ي]+")
# Sebagian pembaca PDF membalik teks visual per titik kode, sehingga harakat berpindah ke depan kata.
HARAKAT_LEPAS = re.compile(r"(?<!\S)[\u064b-\u065f\u0670]+(?=[ء-ي])")
# Kata fungsi/umum yang mustahil (atau amat jarang) muncul terbalik pada teks Arab normal; dipakai membedakan
# baris PDF yang hurufnya tersimpan dalam urutan visual kiri-ke-kanan («ةيبرعلا ةغللا») dari baris normal.
BALIK_KHAS = frozenset("يف نم ىلع ىلإ نع اذه يتلا يذلا كلذ ثحبلا ةساردلا ةيبرعلا يملاسإلا".split())
NORMAL_KHAS = frozenset("في من على إلى عن هذا التي الذي ذلك البحث الدراسة العربية الإسلامي".split())
CERMIN = str.maketrans("()[]{}«»<>", ")(][}{»«><")
# Segmen LTR (URL, surel, kata/frasa Latin, bilangan/rentang/daftar bertanda koma) yang ikut terbalik saat baris dibalik
# utuh: tiap segmen dibalik kembali agar kembali kiri-ke-kanan («71 SRFI» -> «IFRS 17», «moc.elpmaxe@resu» -> «user@example.com»).
_LTR_KATA = r"/?[A-Za-z0-9٠-٩](?:[A-Za-z0-9٠-٩._:/?=&%+\-–@#~]*[A-Za-z0-9٠-٩])?"
LTR_SEGMEN = re.compile(rf"{_LTR_KATA}(?:(?:\s*[,;]\s*|\s+){_LTR_KATA})*")
# Ligatur Word PDF yang urutannya pasti terbalik («الله» -> «هللا», «الإ/الأ/الآ» -> «اإل/األ/اآل»).
LIGATUR_WORD = (("هللا", "الله"), ("اإل", "الإ"), ("األ", "الأ"), ("اآل", "الآ"))
MIN_ARAB = 50  # huruf Arab di satu halaman; kurang dari ini = halaman gambar (scan) atau kosong
MIN_TEKS = 20  # huruf bukan spasi (Arab maupun Latin) untuk menganggap halaman PDF punya lapisan teks terbaca
logging.getLogger("pypdf").setLevel(logging.ERROR)  # keluhan pypdf soal PDF cacat tidak ikut tercetak di laporan `cek`


def _terbalik_visual(baris):
    """True bila bukti kuat menunjukkan baris PDF Arab ini tersimpan dalam urutan huruf visual kiri-ke-kanan.
    Konservatif: butuh minimal satu sinyal pasti (awal ة/ى/ئ atau kata fungsi terbalik), sehingga baris normal
    berakhiran «لا» («مثلا قليلا طويلا جميلا») tidak pernah dibalik."""
    polos = HARAKAT.sub("", baris)
    kata = [k for k in KATA_ARAB.findall(polos) if len(k) >= 2]
    if not kata:
        return False
    skor_balik = skor_normal = 0
    ada_kuat = False
    for k in kata:
        if k[0] in "ةىئ":  # huruf akhir/tengah yang tidak pernah mengawali kata Arab baku
            skor_balik += 3
            ada_kuat = True
        if k in BALIK_KHAS:
            skor_balik += 2
            ada_kuat = True
        if len(k) >= 5 and k.endswith("لا"):
            skor_balik += 1
        if k.startswith("ال") and len(k) >= 4:
            skor_normal += 2
        if k[-1] in "ةى":
            skor_normal += 2
        if k in NORMAL_KHAS:
            skor_normal += 2
    return ada_kuat and skor_balik >= 3 and skor_balik > skor_normal * 2


def _balik_baris_visual(baris):
    """Balik baris visual-reversed ke urutan baca Arab sambil menjaga kurung, angka, dan segmen Latin tetap utuh."""
    gugus = []
    for huruf in baris:
        if gugus and unicodedata.category(huruf).startswith("M"):
            gugus[-1] += huruf
        else:
            gugus.append(huruf)
    dibalik = "".join(reversed(gugus)).translate(CERMIN)
    # Setelah dibalik utuh, segmen LTR (angka, Latin, URL) ikut terbalik: balik kembali segmen LTR itu saja.
    return LTR_SEGMEN.sub(lambda m: m.group(0)[::-1], dibalik)


def pulihkan_arab(teks):
    """Pulihkan ekstraksi PDF Arab yang rusak: normalisasi NFKC, buang penanda BiDi tersembunyi, balik baris
    visual-reversed secara konservatif, dan betulkan ligatur Word PDF yang pasti terbalik («هللا» -> «الله»)."""
    teks = ARAH.sub("", unicodedata.normalize("NFKC", teks or ""))
    baris_out = []
    for b in teks.splitlines():
        if _terbalik_visual(b):
            b = _balik_baris_visual(b)
        for dari, ke in LIGATUR_WORD:
            if dari in b:
                b = b.replace(dari, ke)
        baris_out.append(b)
    return "\n".join(baris_out)


def _sidik(teks):
    """Tiap kata jadi hurufnya yang diurutkan (tahan terhadap huruf sambungan yang tertukar)."""
    return tuple("".join(sorted(p)) for p in map(padat, teks.split()) if p)


def _ada(halaman, kutipan):
    n = len(kutipan)
    return n > 0 and any(halaman[i:i + n] == kutipan for i in range(len(halaman) - n + 1))


def _olah_halaman(halaman):
    """(tuple sidik halaman (dipulihkan + urutan kata dibalik), jumlah huruf Arab) untuk satu halaman pypdf."""
    mentah = unicodedata.normalize("NFKC", halaman.extract_text() or "")  # bentuk tampilan (ﻣﻠﻒ, ﳌ) -> huruf biasa
    t = pulihkan_arab(mentah)
    # Pemulihan satu baris tidak membuang pencocokan lama untuk baris lain di halaman yang sama.
    ekstraksi = (t,) if t == mentah else (t, mentah)
    varian = tuple(dict.fromkeys(s for teks in ekstraksi for s in (_sidik(teks), _sidik_urutan_balik(teks))))
    return varian, len(ARAB.findall(t))


class _DokPDF:
    """Isi PDF yang diolah malas per halaman dan di-cache di memori."""

    def __init__(self, berkas):
        from pypdf import PdfReader
        self._pages = PdfReader(berkas).pages
        self._n = len(self._pages)
        self._cache = {}

    def __len__(self):
        return self._n

    def __getitem__(self, idx):
        if idx < 0:
            idx += self._n
        if not 0 <= idx < self._n:
            raise IndexError(idx)
        hasil = self._cache.get(idx)
        if hasil is None:
            hasil = _olah_halaman(self._pages[idx])
            self._cache[idx] = hasil
        return hasil

    def __iter__(self):
        for i in range(self._n):
            yield self[i]


@functools.lru_cache(maxsize=None)
def _baca(berkas, mtime_ns, ukuran):
    """`_DokPDF` malas per halaman; kunci cache (berkas, mtime_ns, ukuran): PDF yang diganti dibaca ulang."""
    return _DokPDF(berkas)


def _sidik_urutan_balik(teks):
    return _sidik(" ".join(" ".join(baris.split()[::-1]) for baris in teks.splitlines()))


def halaman(berkas):
    """Isi PDF yang diolah malas per halaman; berkas = Path. Galat pypdf (PDF rusak, bersandi) diteruskan ke pemanggil."""
    st = berkas.stat()
    return _baca(str(berkas), st.st_mtime_ns, st.st_size)


def _cocok_halaman(varian, cari_):
    return all(any(_ada(x, k) for x in varian) for k in cari_)


def ada_di_rentang(isi, bagian, a, z):
    """True bila ada halaman di rentang a..z (mulai 1, inklusif) yang memuat semua `bagian` kutipan."""
    cari_ = [_sidik(b) for b in bagian]
    for n in range(max(1, a), min(z, len(isi)) + 1):
        if _cocok_halaman(isi[n - 1][0], cari_):
            return True
    return False


def cari(isi, bagian):
    """Nomor halaman berkas (mulai 1) yang memuat semua `bagian` kutipan; isi = hasil `halaman`."""
    cari_ = [_sidik(b) for b in bagian]
    return [n for n, (v, _) in enumerate(isi, 1) if _cocok_halaman(v, cari_)]


def tanpa_teks(isi, n):
    """Halaman berkas n berupa gambar (scan): teksnya tidak bisa dicocokkan mesin."""
    return isi[n - 1][1] < MIN_ARAB


def _teks_rentang(berkas, a, z):
    """(jumlah halaman total, [(nomor, teks bersih)]) halaman a..z (mulai 1)."""
    pages = None
    try:
        import pymupdf
        with pymupdf.open(berkas) as doc:
            total = len(doc)
            if z > total:
                raise IndexError(f"PDF hanya {total} halaman")
            baris = [(n, pulihkan_arab(doc[n - 1].get_text("text") or "")) for n in range(a, z + 1)]
    except ImportError:
        from pypdf import PdfReader
        pages = PdfReader(berkas).pages
        total = len(pages)
        if z > total:
            raise IndexError(f"PDF hanya {total} halaman")
        baris = [(n, pulihkan_arab(pages[n - 1].extract_text() or "")) for n in range(a, z + 1)]
    if any(HARAKAT_LEPAS.search(teks) for _, teks in baris):
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError
        try:
            pages = PdfReader(berkas).pages if pages is None else pages
            baris = [(n, _coba_tata_letak(pages[n - 1], teks) if HARAKAT_LEPAS.search(teks) else teks)
                     for n, teks in baris]
        except (OSError, PyPdfError, IndexError, TypeError, ValueError):
            pass  # pertahankan teks yang berhasil dibaca bila ekstraksi cadangan gagal
    return total, baris


def _coba_tata_letak(halaman, teks):
    """Mode layout mempertahankan urutan glyph sebelum pembaca menerapkan BiDi."""
    tata_letak = pulihkan_arab(halaman.extract_text(extraction_mode="layout", layout_mode_strip_rotated=False) or "")
    def angka_dan_aksara_lain(teks_):
        return Counter(c for c in teks_ if c.isalnum() and (c.isdecimal() or not ARAB.fullmatch(c)))

    if (not HARAKAT_LEPAS.search(tata_letak) and len(padat(tata_letak)) >= len(padat(teks))
            and angka_dan_aksara_lain(teks) <= angka_dan_aksara_lain(tata_letak)):
        return tata_letak
    return teks


def cuplikan(berkas, hal, kutipan=None, sekitar=300):
    """Untuk `bukti`: (status, cuplikan teks) halaman PDF `hal` («3» atau «3-4»).
    status = 'scan' bila lapisan teks kosong, 'terbaca' bila kutipan ditemukan (cuplikan di sekitarnya), atau
    'tanpa kutipan' (awal halaman: kutipan tidak diberikan atau tidak ditemukan di teks PDF). Dipakai pemeriksa untuk menilai kutipan dan parafrase
    dari PDF penelitian (<<luar|berkas.pdf|hal>>); tidak dipakai putusan `cek`."""
    m = re.fullmatch(r"(\d+)(?:-(\d+))?", str(hal).strip())
    if not m:
        raise ValueError(f"halaman PDF «{hal}» tidak sah")
    a, z = int(m[1]), int(m[2] or m[1])
    if not 1 <= a <= z:
        raise ValueError(f"rentang halaman PDF «{hal}» tidak sah")
    _, daftar = _teks_rentang(berkas, a, z)
    gabung = " ".join(f"⦗{n}⦘ {' '.join(t.split())}" for n, t in daftar if t.strip()).strip()
    bersih = re.sub(r"⦗\d+⦘|\s+", "", gabung)
    if len(bersih) < MIN_TEKS:
        return "scan", ""
    if kutipan:
        import cocok
        q = padat(kutipan)
        if len(q) >= 6:
            p_gabung = padat(gabung)
            # coba awalan kutipan terpanjang (per kata) agar cuplikan tetap mendarat di sekitar kutipan meski ada salah OCR/PDF
            kata_ = kutipan.split()
            for k in range(len(kata_), 0, -1):
                qk = padat(" ".join(kata_[:k]))
                if len(qk) < 6:
                    break
                if qk in p_gabung:
                    i = cocok.letak_asli(gabung, qk)
                    mulai, akhir = max(0, i - sekitar), i + len(kutipan) + sekitar
                    return "terbaca", f"{'…' * (mulai > 0)}{gabung[mulai:akhir]}{'…' * (akhir < len(gabung))}"
        # fallback untuk kutipan Latin (padat hanya menyimpan huruf Arab)
        pot = re.sub(r"\s+", " ", kutipan).strip()
        if pot:
            j = gabung.lower().find(pot[:40].lower())
            if j >= 0:
                mulai, akhir = max(0, j - sekitar), j + len(pot) + sekitar
                return "terbaca", f"{'…' * (mulai > 0)}{gabung[mulai:akhir]}{'…' * (akhir < len(gabung))}"
    potong = gabung[:2 * sekitar]
    return "tanpa kutipan", potong + ("…" if len(gabung) > 2 * sekitar else "")
