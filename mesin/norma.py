"""Penyamaan tulisan Arab (`norm`, `padat`) dan cache teks `padat` tiap kitab. Dipakai lewat shamela.py.

Hanya berkas ini yang menentukan isi cache: sidiknya (VERSI) jadi nama berkas cache. Aturan penyamaan yang diubah di
sini membuat cache baru; perubahan di berkas lain tidak. Modul berkas hanya menangani penulisan, bukan isi normalisasi.
"""
import array, bisect, gzip, hashlib, json, re, sys, unicodedata, zlib
from pathlib import Path
from berkas import sementara

HARAKAT = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")  # harakat, tanda mushaf, tatwil (ditulis sebagai kode: penyunting teks bisa menukar urutan harakat)
TAGS = re.compile(r"<[^>]+>")
HORMAT = re.compile(
    r"صل[يى] الله عليه(?: وعل[يى] [آا]له| و[آا]له)?(?: وصحبه)? وسلم|رض[يى] الله(?: تعال[يى])? عنه(?:ما|م|ا|ن)?"
    r"|علي(?:هما|هم|ها|ه) (?:الصلا[ةه] و)?السلام|رحمه(?:ما|م|ا)? الله(?: تعال[يى])?|عز وجل|جل جلاله"
    r"|سبحانه وتعالى|تبارك وتعالى|صلعم|قدس الله روحه")
# ligatur kalimat hormat tanpa pecahan NFKC (﵀-﵏ dari Unicode 14, ﷾ ﷿): dibuang, bentuk panjangnya dibuang HORMAT
LIGATUR_HORMAT = re.compile(r"[﵀-﵏﷾﷿]")
# bentuk huruf yang disamakan; huruf Persia (ی ک ە ھ) sering terbawa dari PDF/situs
# ؤ/ئ tidak disamakan dengan ء: بئس («seburuk-buruk») ≠ بؤس («kesengsaraan»); kursi hamzah yang beda menurut cetakan
# variasi ejaannya ditangani di EJAAN
SAMA = (("إ", "ا"), ("أ", "ا"), ("آ", "ا"), ("ٱ", "ا"), ("ٲ", "ا"), ("ٳ", "ا"), ("ى", "ي"), ("ة", "ه"), ("ؤ", "و"), ("ئ", "ي"),
        ("ی", "ي"), ("ے", "ي"), ("ۓ", "ي"), ("ک", "ك"), ("ڪ", "ك"), ("ە", "ه"), ("ھ", "ه"), ("ۀ", "ه"), ("ہ", "ه"), ("ۃ", "ه"),
        ("ں", "ن"), ("ٮ", "ب"))
# Pasangan ejaan yang diterima sesudah SAMA; penggantian ini juga berlaku di dalam kata berimbuhan.
# Jangan menyamakan bentuk kata yang berbeda: تساءل (kata kerja) dan تساؤل (kata benda),
# juga مائة/مئة karena «مائه» dapat berarti «airnya».
# Kursi hamzah ditulis sesudah SAMA (ؤ->و, ئ->ي): مسئول/مسؤول، شئون/شؤون، رءوس/رؤوس
EJAAN = (("سماوات", "سموات"), ("اسحاق", "اسحق"), ("داوود", "داود"), ("طاووس", "طاوس"),
         ("مسيول", "مسوول"), ("شيون", "شوون"), ("رءوس", "رووس"), ("رحمان", "رحمن"))


BUKAN_HURUF = re.compile(r"[^ء-ي0-9]+")
BUKAN_ABJAD = re.compile(r"[^ء-ي]+")
PRESENTASI = re.compile(r"[\u0675-\u0678\ufb50-\ufdfc\ufe70-\ufefc]")  # bentuk presentasi yang dipecah NFKC (﷽ ﷾ ﷿ tidak)
SYAI = re.compile(r"شئ(?![ء-ي])")
SYAI_TANPA_HAMZAH = re.compile(r"(?<![ء-ي])([وفبلك]{0,2}(?:ال)?)شي(?![ء-ي])")  # «شي» = «شيء»; «يمشي», «شيئا» tidak
IBNU = re.compile(r"(?<![ء-ي])ابن(?![ء-ي])")
BAGIAN = (("body", ""), ("footnotes", " [حاشية]"))  # bagian rekaman kitab, dan tandanya di keluaran
PENANDA = re.compile(r"⦗([٠-٩]+)⦘")  # awal halaman cetak berikutnya di dalam satu rekaman


def norm(s):
    """Samakan tulisan Arab: buang harakat/tatwil dan kalimat hormat, satukan bentuk alif/ya/ta marbuthah."""
    # NFKC paling awal: memecah ﻻ dan bentuk presentasi lain (ﷺ/ﷻ jadi kalimat hormat, yang lalu dibuang HORMAT).
    # ﷺ dan ﷻ (ada di hampir tiap halaman kitab hadits) langsung dibuang: hasilnya sama, NFKC-nya tidak perlu.
    s = LIGATUR_HORMAT.sub(" ", s.replace("ﷺ", " ").replace("ﷻ", " "))
    if "﷽" in s:  # ligatur basmalah: dijabarkan, bukan dibuang (NFKC tidak memecahnya)
        s = s.replace("﷽", " بسم الله الرحمن الرحيم ")
    if PRESENTASI.search(s):
        s = unicodedata.normalize("NFKC", s)
    s = HORMAT.sub(" ", HARAKAT.sub("", TAGS.sub("", s)))
    if "شئ" in s:  # ejaan lama «شئ» = «شيء»; «شئت» (kehendak) tidak ikut
        s = SYAI.sub("شيء", s)
    if "شي" in s:  # ketikan Shamela tanpa hamzah: «كل شي» = «كل شيء»
        s = SYAI_TANPA_HAMZAH.sub(r"\1شيء", s)
    for dari, ke in SAMA:
        s = s.replace(dari, ke)  # str.replace jauh lebih cepat daripada regex untuk ganti satu huruf
    for dari, ke in EJAAN:
        if dari in s:
            s = s.replace(dari, ke)
    if "ابن" in s:  # «محمد ابن يحيى» = «محمد بن يحيى»: alif «ابن» ditulis atau tidak menurut penyunting
        s = IBNU.sub("بن", s)
    return BUKAN_HURUF.sub(" ", s).strip()


def _potong(p, bagian="body"):
    """Satu rekaman bisa memuat beberapa halaman cetak (penanda ⦗n⦘): pecah jadi [(halaman, teks)].
    Teks sebelum penanda pertama milik page_num."""
    hal, out = p.get("page_num"), []
    for k, b in enumerate(PENANDA.split(p.get(bagian) or "")):
        if k % 2:
            hal = int(b)  # int() membaca angka Arab ٠-٩ juga
        else:
            out.append((hal, b))
    return out


def padat(s):
    """Huruf Arab saja, tanpa spasi dan angka: bentuk yang dicocokkan `cari`, `teks`, `bab`, dan `cek`.
    Spasi diabaikan supaya «و "الإحياء"» tetap ketemu dengan «والإحياء»."""
    return BUKAN_ABJAD.sub("", norm(s))


def _ruas(p, bagian):
    """Teks `padat` satu bagian rekaman dan ruas halamannya [(awal, akhir, hal_awal, hal_akhir)]; dihitung sekali per rekaman.
    حاشية tanpa penanda ⦗n⦘ di rekaman banyak halaman: halaman tiap catatan tidak tercatat, jadi ruasnya = seluruh rekaman."""
    kunci = "_padat_" + bagian
    if kunci not in p:
        potong = _potong(p, bagian)
        if bagian != "body" and len(potong) == 1:
            ruas = [(p.get("page_num"), _potong(p)[-1][0], potong[0][1])]
        else:
            ruas = [(h, h, b) for h, b in potong]
        teks, batas = "", []
        for h1, h2, b in ruas:
            n = padat(b)
            batas.append((len(teks), len(teks) + len(n), h1, h2))
            teks += n
        p[kunci] = teks, batas
    return p[kunci]


# Teks `padat` seluruh kitab (kitab/<id>/padat-<VERSI>.bin): menormalisasi seluruh kitab tiap `cari`/`teks` makan
# detik-an untuk kitab besar. VERSI = sidik isi berkas INI (bukan shamela.py): yang menentukan isi berkas itu hanya
# berkas ini, jadi perubahan mesin di luarnya tidak membuat seluruh perpustakaan dihitung ulang (154 kitab: ±2,5 menit).
VERSI = hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:12]
TANPA_HAL = -(1 << 63)  # halaman None di deret halaman (rekaman/penanda tanpa nomor)


def rekaman(f):
    with gzip.open(f, "rt", encoding="utf8") as g:
        for line in g:
            yield json.loads(line)


def bait(s):
    """Teks `padat` -> satu byte per huruf: huruf ء-ي (U+0621-U+064A) semuanya berbait tinggi 06, jadi cukup bait rendahnya.
    Letak di bait = letak di teks; `find` di bait = `find` di teks."""
    b = s.encode("utf-16-le")
    if b[1::2].strip(b"\x06"):
        raise ValueError("bukan teks padat")
    return b[::2]


def teks(b):
    """Kebalikan `bait`."""
    x = bytearray(2 * len(b))
    x[::2] = b
    x[1::2] = b"\x06" * len(b)
    return x.decode("utf-16-le")


class Padat:
    """Teks `padat` seluruh kitab, satu deret per bagian (BAGIAN), bukan satu objek per rekaman:
    bagian s rekaman i = teks[s][mulai[s][i]:mulai[s][i+1]] (`bait`); ruasnya [(awal, akhir, h1, h2)] (letak relatif
    terhadap awal rekaman) = baris ruas[s][i]..ruas[s][i+1] deret awal/akhir/h1/h2. Sama dengan `_ruas` tiap rekaman."""
    DERET = ("mulai", "ruas", "awal", "akhir", "h1", "h2")
    JENIS = {"mulai": "Q", "ruas": "Q", "awal": "Q", "akhir": "Q", "h1": "q", "h2": "q"}

    def __init__(self, teks, deret):
        self.teks, self.deret = teks, deret  # teks[s]: bytes; deret[s][nama]: array (atau list, lihat `buat`)

    def bagian(self, i, s):
        """(teks padat, ruas) bagian s rekaman i, seperti `_ruas`."""
        d = self.deret[s]
        a, z = d["mulai"][i], d["mulai"][i + 1]
        r = range(d["ruas"][i], d["ruas"][i + 1])
        h = lambda x: None if x == TANPA_HAL else x
        return teks(self.teks[s][a:z]), [(d["awal"][k], d["akhir"][k], h(d["h1"][k]), h(d["h2"][k])) for k in r]

    def isi(self, p, i):
        """Pasang teks padat rekaman i ke rekaman p (yang dibaca `_ruas`); kembalikan p."""
        for s, (b, _) in enumerate(BAGIAN):
            p["_padat_" + b] = self.bagian(i, s)
        return p

    def kena(self, q):
        """Nomor rekaman (urut) yang salah satu bagiannya memuat q (teks padat). Kecocokan yang melintasi batas dua
        rekaman tidak dihitung: sama dengan mencari di tiap rekaman sendiri-sendiri."""
        qb, out = bait(q), set()
        for s in range(len(BAGIAN)):
            t, mulai = self.teks[s], self.deret[s]["mulai"]
            j = t.find(qb)
            while j >= 0:
                i = bisect.bisect_right(mulai, j) - 1
                if j + len(qb) <= mulai[i + 1]:
                    out.add(i)
                    j = t.find(qb, mulai[i + 1])
                else:
                    j = t.find(qb, j + 1)
        return sorted(out)

    @classmethod
    def buat(cls, semua):
        """Dari rekaman-rekaman kitab (urut berkas). Halaman di luar 64 bit tetap terbaca (list), hanya tidak disimpan."""
        potong = [[] for _ in BAGIAN]
        deret = [{n: [] for n in cls.DERET} for _ in BAGIAN]
        panjang = [0] * len(BAGIAN)
        for p in semua:
            for s, (b, _) in enumerate(BAGIAN):
                t, batas = _ruas(p, b)
                d = deret[s]
                d["mulai"].append(panjang[s]); d["ruas"].append(len(d["awal"]))
                potong[s].append(bait(t)); panjang[s] += len(t)
                for a, z, h1, h2 in batas:
                    d["awal"].append(a); d["akhir"].append(z)
                    d["h1"].append(TANPA_HAL if h1 is None else h1); d["h2"].append(TANPA_HAL if h2 is None else h2)
        for s, d in enumerate(deret):
            d["mulai"].append(panjang[s]); d["ruas"].append(len(d["awal"]))
            try:
                deret[s] = {n: array.array(cls.JENIS[n], x) for n, x in d.items()}
            except (OverflowError, TypeError):  # halaman yang bukan bilangan 64 bit: tetap list
                pass
        return cls([b"".join(x) for x in potong], deret)

    def tulis(self, f, sumber):
        """Simpan: satu baris kepala JSON (sidik sumber, panjang tiap deret, crc32 isi), lalu isi apa adanya."""
        isi = [x for s in range(len(BAGIAN)) for x in [self.teks[s]] + [self.deret[s][n].tobytes() for n in self.DERET]]
        crc = 0
        for x in isi:
            crc = zlib.crc32(x, crc)
        kepala = {"sumber": sumber, "urutan": sys.byteorder, "panjang": [len(x) for x in isi], "crc32": crc}
        with sementara(f) as part:
            with open(part, "wb") as h:
                h.write(json.dumps(kepala).encode() + b"\n")
                h.writelines(isi)

    @classmethod
    def baca(cls, f, sumber):
        """Berkas `tulis` yang sidik sumbernya `sumber` dan isinya utuh (crc32); None kalau tidak ada, usang, atau rusak."""
        try:
            with open(f, "rb") as h:
                kepala = json.loads(h.readline(1 << 16))
                panjang = kepala["panjang"]
                if (kepala["sumber"] != sumber or kepala["urutan"] != sys.byteorder
                        or len(panjang) != len(BAGIAN) * (1 + len(cls.DERET)) or not all(type(n) is int and n >= 0 for n in panjang)):
                    return None
                isi = [h.read(n) for n in panjang]
                if h.read(1) or [len(x) for x in isi] != panjang:
                    return None
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None
        crc = 0
        for x in isi:
            crc = zlib.crc32(x, crc)
        if crc != kepala.get("crc32"):  # kepala rusak tanpa kunci crc32 = berkas rusak, dibangun ulang
            return None
        teks_, deret, k = [], [], 0
        for _ in BAGIAN:
            teks_.append(isi[k]); k += 1
            d = {}
            for n in cls.DERET:
                d[n] = array.array(cls.JENIS[n])
                if len(isi[k]) % d[n].itemsize:
                    return None
                d[n].frombytes(isi[k]); k += 1
            # isinya utuh (crc32), tetapi bentuknya tetap dicocokkan: jumlah rekaman, ujung teks, dan ujung ruas
            n = len(d["mulai"])
            if not (n == len(d["ruas"]) == len(deret[0]["mulai"] if deret else d["mulai"]) and n
                    and d["mulai"][-1] == len(teks_[-1]) and d["ruas"][-1] == len(d["awal"])
                    and all(len(d[x]) == len(d["awal"]) for x in ("akhir", "h1", "h2"))):
                return None
            deret.append(d)
        return cls(teks_, deret)


def sidik(f):
    """sha256 berkas f (pages.jsonl.gz): isi .gz sama = isi kitab sama."""
    with open(f, "rb") as h:
        return hashlib.file_digest(h, "sha256").hexdigest()


def cache(folder, sumber=None):
    """`Padat` kitab di `folder`; dibuat sekali kalau belum ada. sumber = `sidik` pages.jsonl.gz (dihitung kalau None).
    Berkas yang rusak, usang, atau tidak bisa ditulis tidak menghentikan apa pun: dihitung biasa."""
    f = folder / f"padat-{VERSI}.bin"
    sumber = sumber or sidik(folder / "pages.jsonl.gz")
    hasil = Padat.baca(f, sumber)
    if hasil is not None:
        return hasil
    hasil = Padat.buat(rekaman(folder / "pages.jsonl.gz"))
    try:
        if all(isinstance(x, array.array) for d in hasil.deret for x in d.values()):
            hasil.tulis(f, sumber)
        for lama in folder.glob("padat-*"):  # versi norma.py lama (juga bentuk lama .json.gz) tidak terpakai lagi
            if lama != f and not lama.name.endswith(".part"):
                lama.unlink()
    except OSError:
        pass
    return hasil
