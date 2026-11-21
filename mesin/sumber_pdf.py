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

from norma import HARAKAT, padat

ARAB = re.compile(r"[؀-ۿ]")
ARAH = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
KATA_ARAB = re.compile(r"[ء-ي]+")
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
    dibalik = baris[::-1].translate(CERMIN)
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


@functools.lru_cache(maxsize=None)
def _baca(berkas, waktu):
    """(tuple sidik halaman (dipulihkan + urutan kata dibalik), jumlah huruf Arab) tiap halaman.
    `waktu` (saat berkas terakhir diubah) ikut kunci cache: PDF yang diganti dibaca ulang."""
    from pypdf import PdfReader
    hasil = []
    for p in PdfReader(berkas).pages:
        mentah = unicodedata.normalize("NFKC", p.extract_text() or "")  # bentuk tampilan (ﻣﻠﻒ, ﳌ) -> huruf biasa
        t = pulihkan_arab(mentah)
        balik = "\n".join(" ".join(b.split()[::-1]) for b in t.splitlines())
        varian = (_sidik(t), _sidik(balik)) if t == mentah else (_sidik(t), _sidik(balik), _sidik(mentah))
        hasil.append((varian, len(ARAB.findall(t))))
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


def _teks_rentang(berkas, a, z):
    """(jumlah halaman total, [(nomor, teks bersih)]) halaman a..z (mulai 1); pakai pymupdf bila terpasang (urutan huruf
    Arab lebih rapi), jatuh ke pypdf bila tidak."""
    try:
        import pymupdf
        with pymupdf.open(berkas) as doc:
            total = len(doc)
            if z > total:
                raise IndexError(f"PDF hanya {total} halaman")
            return total, [(n, pulihkan_arab(doc[n - 1].get_text("text") or "")) for n in range(a, z + 1)]
    except ImportError:
        from pypdf import PdfReader
        pages = PdfReader(berkas).pages
        total = len(pages)
        if z > total:
            raise IndexError(f"PDF hanya {total} halaman")
        return total, [(n, pulihkan_arab(pages[n - 1].extract_text() or "")) for n in range(a, z + 1)]


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
