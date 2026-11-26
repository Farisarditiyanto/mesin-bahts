# SPDX-License-Identifier: AGPL-3.0-or-later
"""Perpustakaan Shamela lokal: unduh kitab per-judul dari dataset Hugging Face
AuthenticIlm/Shamela4_Full_DB ke folder kitab/, lalu cari kutipan secara offline
(tanpa kredit, tanpa internet). Dipanggil lewat bahts.py.
"""
import array, bisect, collections, contextlib, functools, gzip, hashlib, itertools, json, operator, os, re, struct, sys, urllib.parse, zlib
from pathlib import Path

import cocok, gelar, norma
from berkas import sementara
from dasar import angka, perintah
from jaringan import buka, tulis_biner, unduh, unduh_kitab
from norma import BAGIAN, HARAKAT, PENANDA, TAGS, BUKAN_ABJAD, per_halaman, ruas_halaman, norm, padat

MESIN = Path(__file__).parent
ROOT = MESIN.parent / "kitab"


REPO = "AuthenticIlm/Shamela4_Full_DB"
API = f"https://huggingface.co/api/datasets/{REPO}/tree/main"
RAW = f"https://huggingface.co/datasets/{REPO}/resolve/main"


@functools.cache  # daftar folder dataset tidak berubah selama satu perintah
def _ls(path=""):
    url = API + ("/" + urllib.parse.quote(path) if path else "")
    out = []
    while url:
        with buka(url) as r:
            out += json.load(r)
            link = r.headers.get("Link")
        url = link.split(";")[0].strip("<> ") if link and 'rel="next"' in link else None
    return out


_CACHE_KITAB = []


def cache_kitab(maxsize=None):
    """`functools.lru_cache(maxsize)` untuk yang dibaca atau diturunkan dari satu kitab; `lepas` mengosongkannya."""
    def daftarkan(f):
        f = functools.lru_cache(maxsize=maxsize)(f)
        _CACHE_KITAB.append(f)
        return f
    return daftarkan


KATALOG = "_meta/book_metadata.parquet"
KATALOG_VERSI = 1
KATALOG_KOLOM = {"shamela_id": int, "book_id": int, "category_id": int, "title_ar": str, "main_author_id": int,
                 "main_author_name_ar": str, "main_author_death_hijri": int, "category_name_ar": str,
                 "has_multi_part": bool, "group_id": int}
_KATALOG_WAJIB = frozenset(("shamela_id", "book_id", "category_id"))
_KATALOG_BAGIAN = ("baris", "judul_padat", "judul_pokok", "pengarang", "asal")
_BACA_SAJA = False


def sedang_baca_saja():
    """Apakah mode baca-saja (`baca_saja()`) sedang aktif."""
    return _BACA_SAJA


@contextlib.contextmanager
def baca_saja():
    """Hentikan penulisan berkas cache turunan selama aktif (untuk perintah baca-saja seperti `tahap`)."""
    global _BACA_SAJA
    lama = _BACA_SAJA
    _BACA_SAJA = True
    try:
        yield
    finally:
        _BACA_SAJA = lama


def siapkan():
    """Unduh katalog kitab (judul, pengarang, letak tiap kitab di dataset) kalau belum ada."""
    f = ROOT / KATALOG
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        print("katalog kitab: mengunduh …", flush=True)
        unduh(f"{RAW}/{KATALOG}", f, tulis_biner)
    print(f"katalog kitab: {len(isi_katalog())} judul")


def _baca_katalog_parquet(f):
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise SystemExit("Pustaka Python belum terpasang; cara memasangnya disebut oleh: " + perintah("periksa"))
    # Katalog hanya perlu kolom ini; kartu lengkap dibaca dari kitab lokal.
    with pq.ParquetFile(f) as h:
        return h.read(columns=list(KATALOG_KOLOM)).to_pylist()


def _hitung_judul_padat(daftar):
    out = {}
    for r in daftar:
        out.setdefault(padat(r["title_ar"] or ""), []).append(int(r["shamela_id"]))
    urut = sorted(((j, idx, ss) for idx, (j, ss) in enumerate(out.items())), key=lambda t: t[0])
    return out, tuple(t[0] for t in urut), tuple((t[1], t[2]) for t in urut)


def _hitung_judul_pokok(daftar):
    out, pcache = {}, {}
    for r in daftar:
        sid = int(r["shamela_id"])
        for b in judul_pokok(r["title_ar"]):
            p = pcache.get(b)
            if p is None:
                p = pcache[b] = padat(b)
            out.setdefault(p, set()).add(sid)
    return out


def _hitung_pengarang_kata(daftar):
    out, norm_cache = {}, {}
    for r in daftar:
        nama = r["main_author_name_ar"] or ""
        if not nama:
            continue
        aid = str(r["main_author_id"])
        kunci_nama = norm_cache.get(nama)
        if kunci_nama is None:
            bagian = [norm(nama)]
            if "،" in nama:
                bagian += [norm(b) for b in nama.split("،")]
            kunci_nama = norm_cache[nama] = tuple(dict.fromkeys(x for x in bagian if x))
        for nb in kunci_nama:
            out.setdefault(nb, set()).add(aid)
    kunci = tuple(sorted(out))
    return out, kunci, tuple(out[k] for k in kunci)


def _hitung_asal(daftar):
    return {int(r["shamela_id"]): (str(r["main_author_id"]), r["group_id"]) for r in daftar}


def _baca_biner(f, n_bagian, **syarat):
    try:
        mentah = f.read_bytes()
        nl = mentah.find(b"\n", 0, 1 << 16)
        if nl < 0:
            return None
        kepala = json.loads(mentah[:nl])
        if not isinstance(kepala, dict):
            return None
        panjang = kepala.get("panjang")
        if (any(kepala.get(k) != v for k, v in syarat.items())
                or type(panjang) is not list or len(panjang) != n_bagian
                or not all(type(n) is int and n >= 0 for n in panjang)):
            return None
        awal = nl + 1
        if len(mentah) - awal != sum(panjang) or zlib.crc32(memoryview(mentah)[awal:]) != kepala.get("crc32"):
            return None
        return mentah, awal, panjang
    except (OSError, ValueError, TypeError):
        return None


def _baca_katalog_bin(f_cache, sumber):
    hasil = _baca_biner(f_cache, len(_KATALOG_BAGIAN), versi=KATALOG_VERSI, norma_versi=norma.VERSI, sumber=sumber)
    if hasil is None:
        return None
    mentah, pos, panjang = hasil
    potong = {}
    for nama, n in zip(_KATALOG_BAGIAN, panjang):
        potong[nama] = mentah[pos:pos + n]
        pos += n
    return potong


def _tulis_katalog_bin(f_cache, sumber, daftar, jp, jpp, pk, asal_):
    """Simpan cache katalog terverifikasi (satu baris kepala JSON + potongan JSON tiap tabel) secara atomik."""
    enc = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf8")
    isi = (
        enc([[r[c] for c in KATALOG_KOLOM] for r in daftar]),
        enc([list(jp[1]), [i for i, _ in jp[2]], [ss for _, ss in jp[2]]]),
        enc([[k, sorted(v)] for k, v in jpp.items()]),
        enc([list(pk[1]), [sorted(v) for v in pk[2]]]),
        enc([[sid, aid, gid] for sid, (aid, gid) in asal_.items()]),
    )
    crc = 0
    for x in isi:
        crc = zlib.crc32(x, crc)
    kepala = {"versi": KATALOG_VERSI, "norma_versi": norma.VERSI, "sumber": sumber,
              "panjang": [len(x) for x in isi], "crc32": crc}
    try:
        with sementara(f_cache) as part:
            with open(part, "wb") as h:
                h.write(json.dumps(kepala, separators=(",", ":")).encode() + b"\n")
                h.writelines(isi)
        for lama in f_cache.parent.glob("katalog-*.bin"):
            if lama != f_cache:
                try:
                    lama.unlink(missing_ok=True)
                except OSError:
                    pass
    except OSError:
        pass


def _bangun_katalog(f_cache, sumber, daftar):
    jp = _hitung_judul_padat(daftar)
    jpp = _hitung_judul_pokok(daftar)
    pk = _hitung_pengarang_kata(daftar)
    asal_ = _hitung_asal(daftar)
    _tulis_katalog_bin(f_cache, sumber, daftar, jp, jpp, pk, asal_)
    return {"baris": daftar, "judul_padat": jp, "judul_pokok": jpp, "pengarang": pk, "asal": asal_}


@functools.cache
def _katalog_sumber(root, baca_saja):
    f_src = root / KATALOG
    if not f_src.exists():
        raise SystemExit("Katalog kitab belum ada: " + perintah("siapkan"))
    sumber = norma.sidik(f_src)
    f_cache = root / "_meta" / f"katalog-{norma.VERSI}.bin"
    potong = _baca_katalog_bin(f_cache, sumber)
    if potong is not None:
        return "bin", f_src, f_cache, sumber, potong
    daftar = _baca_katalog_parquet(f_src)
    if baca_saja:
        return "daftar", daftar
    return "siap", _bangun_katalog(f_cache, sumber, daftar)


@functools.cache
def _ambil_katalog(root, baca_saja, bagian, urai, hitung=None):
    s = _katalog_sumber(root, baca_saja)
    if s[0] == "siap":
        return s[1][bagian]
    if s[0] == "daftar":
        return s[1] if bagian == "baris" else hitung(s[1])
    try:
        return urai(json.loads(s[4][bagian]))
    except (ValueError, KeyError, TypeError):
        daftar = _baca_katalog_parquet(s[1])
        if not baca_saja:
            _katalog_sumber.cache_clear()
            return _bangun_katalog(s[2], s[3], daftar)[bagian]
        return daftar if bagian == "baris" else hitung(daftar)


def _urai_baris(raw):
    if type(raw) is not list or not all(
        type(r) is list and len(r) == len(KATALOG_KOLOM)
        and all(type(v) is jenis or (v is None and k not in _KATALOG_WAJIB)
                for (k, jenis), v in zip(KATALOG_KOLOM.items(), r))
        for r in raw
    ):
        raise ValueError("baris katalog rusak")
    return [dict(zip(KATALOG_KOLOM, r)) for r in raw]


def _daftar_jenis(raw, jenis):
    return type(raw) is list and all(type(x) is jenis for x in raw)


def _kunci_urut(raw):
    return _daftar_jenis(raw, str) and all(a < b for a, b in itertools.pairwise(raw))


def _urai_judul_padat(raw):
    if not (type(raw) is list and len(raw) == 3 and _kunci_urut(raw[0])
            and _daftar_jenis(raw[1], int) and set(raw[1]) == set(range(len(raw[0])))
            and len(raw[0]) == len(raw[1]) and type(raw[2]) is list and len(raw[0]) == len(raw[2])
            and all(ss and _daftar_jenis(ss, int) for ss in raw[2])):
        raise ValueError("judul_padat katalog rusak")
    kunci = tuple(raw[0])
    return dict(zip(kunci, raw[2])), kunci, tuple(zip(raw[1], raw[2]))


def _urai_judul_pokok(raw):
    if type(raw) is not list or not all(
        type(x) is list and len(x) == 2 and type(x[0]) is str and x[1] and _daftar_jenis(x[1], int) for x in raw
    ):
        raise ValueError("judul_pokok katalog rusak")
    hasil = {k: set(v) for k, v in raw}
    if len(hasil) != len(raw):
        raise ValueError("judul_pokok katalog ganda")
    return hasil


def _urai_pengarang(raw):
    if not (type(raw) is list and len(raw) == 2 and _kunci_urut(raw[0]) and type(raw[1]) is list
            and len(raw[0]) == len(raw[1]) and all(ids and _daftar_jenis(ids, str) for ids in raw[1])):
        raise ValueError("pengarang katalog rusak")
    kunci = tuple(raw[0])
    nilai = tuple(set(v) for v in raw[1])
    return dict(zip(kunci, nilai)), kunci, nilai


def _urai_asal(raw):
    if type(raw) is not list or not all(
        type(x) is list and len(x) == 3 and type(x[0]) is int and type(x[1]) is str
        and (x[2] is None or type(x[2]) is int) for x in raw
    ):
        raise ValueError("asal katalog rusak")
    hasil = {sid: (aid, gid) for sid, aid, gid in raw}
    if len(hasil) != len(raw):
        raise ValueError("asal katalog ganda")
    return hasil


def isi_katalog():
    return _ambil_katalog(ROOT, _BACA_SAJA, "baris", _urai_baris)


def ada_keterangan():
    return f"(ADA = sudah diunduh; - = belum, unduh dengan: {perintah('ambil <nomor>')})"


KATALOG_MAKS = 30  # baris katalog yang dicetak; pola pendek bisa cocok dengan ribuan judul
REGEX = re.compile(r"[\\^$.|?*+()\[\]{}]")  # pola katalog yang memuat tanda ini dicoba juga sebagai regex


def katalog(pola):
    """Cari kitab di katalog Shamela (judul atau nama pengarang). Ejaan disamakan seperti `cari` (hamzah, ta marbuthah,
    harakat, spasi). Pola bertanda regex dicoba dulu sebagai regex; tidak ada hasil -> sebagai teks biasa."""
    if not pola.strip():
        raise SystemExit("Tulis sebagian judul atau nama pengarang, mis.: " + perintah('katalog "مدارج السالكين"'))
    daftar = isi_katalog()
    hit = []
    if REGEX.search(pola):
        try:
            regex = re.compile(pola)
            hit = [r for r in daftar if regex.search(r["title_ar"] or "") or regex.search(r["main_author_name_ar"] or "")]
        except (re.error, OverflowError):
            pass  # judul bertanda kurung yang disalin persis: dicocokkan sebagai teks biasa di bawah
    rata = padat if not re.search(r"[A-Za-z]", pola) else str  # padat membuang huruf Latin
    q = rata(pola)
    if not hit and len(q) < 2:
        raise SystemExit(f"«{pola}» terlalu pendek untuk katalog (paling sedikit 2 huruf judul/nama).")
    if not hit:
        hit = [r for r in daftar if q in rata(r["title_ar"] or "") or q in rata(r["main_author_name_ar"] or "")]
    if not hit:
        latin = " Katalognya berhuruf Arab: tulis judul/nama dengan huruf Arab." if re.search(r"[A-Za-z]", pola) else ""
        print(f"TIDAK KETEMU di katalog: {pola}\nCoba satu kata judul atau nama pengarang saja, "
              f"atau `temukan \"<frasa>\"` untuk mencari di isi kitab.{latin}")
        return 0
    print("nomor\tADA\tjudul\tpengarang\tbidang  " + ada_keterangan())
    for r in hit[:KATALOG_MAKS]:
        ada = "ADA" if (ROOT / str(r['shamela_id']) / "pages.jsonl.gz").exists() else "-"
        print(f"{r['shamela_id']}\t{ada}\t{r['title_ar']}\t{r['main_author_name_ar']}\t{r['category_name_ar']}")
    if len(hit) > KATALOG_MAKS:
        print(f"({len(hit)} cocok, ditampilkan {KATALOG_MAKS}: persempit judul/pengarangnya)")
    return len(hit)


def _judul_padat():
    """({judul `padat`: [nomor kitab]}, kunci terurut, [(urutan_katalog, [nomor kitab])]) dari katalog lokal;
    kosong kalau katalog atau pyarrow belum ada (cek tetap jalan)."""
    try:
        return _ambil_katalog(ROOT, _BACA_SAJA, "judul_padat", _urai_judul_padat, _hitung_judul_padat)
    except SystemExit:
        return {}, (), ()


@functools.cache
def _nomor_judul_padat(q):
    semua, kunci, nilai = _judul_padat()
    persis = semua.get(q, ())
    if not kunci:
        return tuple(persis), ()
    i, n = bisect.bisect_left(kunci, q), len(kunci)
    if i < n and kunci[i] == q:
        i += 1
    cocok_ = []
    while i < n and kunci[i].startswith(q):
        cocok_.append(nilai[i])
        i += 1
    if len(cocok_) > 1:
        cocok_.sort()
    return tuple(persis), tuple(s for _, ss in cocok_ for s in ss)


def nomor_judul(judul):
    """(persis, mirip): nomor kitab Shamela yang judulnya persis `judul`, dan yang judulnya diawali `judul`
    (judul pendek, mis. «مدارج السالكين»), ejaan disamakan. ([], []) kalau katalog belum ada."""
    q = padat(judul)
    if len(q) < 6:
        return [], []
    persis, mirip = _nomor_judul_padat(q)
    return list(persis), list(mirip)


# «المغني لابن قدامة»; nisbah pengarang yang ditempel «الأعلام للزركلي» (لل + nisbah berakhir ي), bukan «المدخل للفقه»
PENGARANG_SESUDAH = re.compile(r"^(?:للشيخ|للإمام|للعلامة|للحافظ|للقاضي|لابن|لأبي|لأبى|لل[ء-ي]{2,}ي)$")
_PISAH_STRIP = re.compile(r"\s+-\s+")
_PISAH_SAMA = re.compile(r"\s+=\s+")


def kata_judul(judul):
    """Kata judul sebelum pengarang tempelan («المغني لابن قدامة» -> [«المغني»])."""
    kata = judul.split()
    for i in range(1, len(kata)):
        w = kata[i]
        if w[0] == "ل" and PENGARANG_SESUDAH.match(w):
            return kata[:i]
    return kata


def judul_pokok(judul):
    """Judul katalog tanpa keterangan edisi sesudah « - » («صحيح مسلم - ت عبد الباقي»), dipecah di « = » (judul lain:
    «تفسير السعدي = تيسير الكريم الرحمن»), juga tanpa pengarang yang ditempel («المغني لابن قدامة» → «المغني»)."""
    if not judul:
        return []
    utama = (_PISAH_STRIP.split(judul, 1)[0] if "-" in judul else judul).strip()
    bagian = _PISAH_SAMA.split(utama) if "=" in utama else (utama,)
    out = []
    for b in bagian:
        if not b:
            continue
        out.append(b)
        kj = " ".join(kata_judul(b))
        if kj and kj != b:
            out.append(kj)
    return list(dict.fromkeys(out)) if len(out) > 1 else out


def judul_pokok_padat():
    """{judul_pokok `padat`: {nomor kitab}}: «صحيح مسلم» = semua edisinya."""
    try:
        return _ambil_katalog(ROOT, _BACA_SAJA, "judul_pokok", _urai_judul_pokok, _hitung_judul_pokok)
    except SystemExit:
        return {}


@functools.cache
def _nomor_pengarang_norm(awal):
    out, kunci, nilai = _pengarang_kata()
    if not awal or " " not in awal:
        return frozenset(out.get(awal, ())) if awal.startswith("ال") and len(awal) >= 5 else frozenset()
    hasil = set(out.get(awal, ()))
    awalan = awal + " "
    i, n = bisect.bisect_left(kunci, awalan), len(kunci)
    while i < n and kunci[i].startswith(awalan):
        hasil.update(nilai[i])
        i += 1
    return frozenset(hasil)


def nomor_pengarang(nama):
    """main_author_id pengarang katalog yang namanya `nama`, atau diawali `nama` utuh sekata («ابن حجر» = ابن حجر
    العسقلاني dan ابن حجر الهيتمي). Nama satu kata hanya nisbah ber-«ال» yang persis sama («النووي»): «مسلم», «مالك»,
    «أحمد» juga kata biasa, dan satu kata tidak boleh jadi awalan nama orang lain."""
    return set(_nomor_pengarang_norm(norm(nama)))


def _pengarang_kata():
    """({nama pengarang `norm`: {main_author_id}}, kunci terurut, [{main_author_id}]) dari katalog lokal."""
    try:
        return _ambil_katalog(ROOT, _BACA_SAJA, "pengarang", _urai_pengarang, _hitung_pengarang_kata)
    except SystemExit:
        return {}, (), ()


def _asal():
    """{nomor kitab: (main_author_id, group_id)} dari katalog; group_id menyatukan edisi dan ringkasan satu kitab."""
    try:
        return _ambil_katalog(ROOT, _BACA_SAJA, "asal", _urai_asal, _hitung_asal)
    except SystemExit:
        return {}


def asal(sid):
    """(main_author_id, group_id) kitab sid menurut katalog; (None, None) kalau tidak ada."""
    return _asal().get(int(sid), (None, None))


@functools.cache
def _nomor_judul_pokok_padat(q):
    return tuple(sorted(judul_pokok_padat().get(q, ())))


def nomor_judul_pokok(judul):
    """Nomor kitab yang salah satu judul_pokok-nya persis `judul` («صحيح البخاري», «تيسير الكريم الرحمن»)."""
    q = padat(judul)
    return list(_nomor_judul_pokok_padat(q)) if len(q) >= 6 else []


def letak(juz, h):
    """Juz dan halaman untuk dicetak: «ج2 ص15», «ج- ص15-16», «ج«المقدمة» ص3». h = halaman, atau (awal, akhir)."""
    a, z = h if isinstance(h, tuple) else (h, h)
    j = f"ج{juz}" if juz == "-" or str(juz).isdigit() else f"ج«{juz}»"  # juz bernama tidak menempel ke «ج»
    if a is None:
        return f"{j} ص? (rekaman ini tanpa nomor halaman)"
    if z is not None and z < a:  # penanda halaman yang menurun di satu rekaman: bukti hanya menerima kecil-besar
        a, z = z, a
    return f"{j} ص{a}" + (f"-{z}" if z not in (None, a) else "")


def punya():
    """shamela_id semua kitab yang sudah diunduh."""
    out = []
    try:
        with os.scandir(ROOT) as it:
            for e in it:
                if e.name.isdigit() and os.path.isfile(os.path.join(e.path, "pages.jsonl.gz")):
                    out.append(int(e.name))
    except (FileNotFoundError, NotADirectoryError):
        return []
    out.sort()
    return out


def nomor_kitab(sid):
    """Nomor kitab sid sebagai angka; sid yang bukan angka ditolak dengan pesan, bukan disuruh `ambil`."""
    if not str(sid).isdigit():
        raise SystemExit(f"«{sid}» bukan nomor kitab. Nomornya dari `kitab`, `katalog`, atau `temukan`.")
    return int(sid)


def folder(sid):
    """Folder kitab sid (`nomor_kitab`)."""
    return ROOT / str(nomor_kitab(sid))


def _belum(sid):
    """Pesan kitab yang tidak ada di kitab/: nomor yang tidak ada di katalog tidak disuruh `ambil` (`ambil` akan menolaknya)."""
    try:
        dikenal = any(r["shamela_id"] == int(sid) for r in isi_katalog())
    except SystemExit:  # katalog/pyarrow belum ada: tidak bisa dipastikan
        dikenal = True
    if not dikenal:
        return SystemExit(f"Kitab {sid} TIDAK ADA di katalog Shamela. Nomornya dari `kitab`, `katalog`, atau `temukan`.")
    return SystemExit(f"Kitab {sid} belum diunduh: " + perintah(f"ambil {sid}"))


@cache_kitab()  # `cek` membacanya untuk tiap bukti
def info(sid):
    f = folder(sid) / "book_metadata.json"
    try:
        return json.loads(f.read_bytes())
    except FileNotFoundError:
        raise _belum(sid) from None


def daftar():
    semua = punya()
    if not semua:
        print('Belum ada kitab yang diunduh. Cari nomornya dengan `katalog "<judul>"` atau `temukan "<frasa>"`, '
              "lalu: " + perintah("ambil <nomor>"))
        return
    root_str = str(ROOT)
    baris = []
    for sid in semua:
        try:
            with open(os.path.join(root_str, str(sid), "book_metadata.json"), "rb") as f:
                m = json.loads(f.read())
        except FileNotFoundError:
            m = info(sid)
        baris.append(f"{sid}\t{m['title_ar']}\t{m['main_author_name_ar']}")
    sys.stdout.write("\n".join(baris) + "\n")


def wajib_ada(sid):
    """Pastikan kitab `sid` sudah diunduh utuh (`pages.jsonl.gz`); tidak ada -> hentikan dengan pesan yang jelas."""
    if not (folder(sid) / "pages.jsonl.gz").exists():
        raise _belum(sid)


def kartu(sid):
    """Data cetak kitab (pengarang, muhaqqiq, penerbit, cetakan) untuk rujukan pertama dan daftar pustaka, lalu satu
    baris bentuk bukti <<…>> kitab itu (contoh_bukti). Gelar di nama muhaqqiq/penyusun dibuang (gelar.buang_gelar):
    data ini disalin apa adanya ke catatan kaki dan المصادر."""
    wajib_ada(sid)
    print("\n".join(gelar.buang_gelar(b) for b in info(sid)["betaka_text"].replace("\r", "\n").rstrip("\n").split("\n")))
    print(contoh_bukti(sid))


def ambil(*sid):
    """Unduh kitab (sekali saja). Semua nomor dicoba; unduhan yang putus diulang sampai COBA kali.
    Kembalikan nomor yang gagal (kosong = semua ada); bahts.py yang memberi kode keluar."""
    return unduh_kitab(sid, ambil_satu)


def ambil_satu(sid):
    if not str(sid).isdigit():
        raise LookupError("bukan nomor kitab (nomornya dari `katalog` atau `temukan`)")
    sid = int(sid)
    dst = ROOT / str(sid)
    if (dst / "pages.jsonl.gz").exists():
        print(sid, "sudah ada"); return
    r = next((r for r in isi_katalog() if r["shamela_id"] == sid), None)
    if r is None:
        raise LookupError("TIDAK ADA di katalog Shamela (nomornya dari `katalog` atau `temukan`)")
    top = [x["path"] for x in _ls() if x["path"].startswith(f"{int(r['category_id']):02d}__")]
    asal = [x["path"] for x in _ls(top[0]) if x["path"].split("/")[-1].split("__")[0] == str(r['book_id'])] if top else []
    if not asal:
        raise LookupError("folder kitabnya tidak ketemu di dataset Shamela (mungkin belum tersedia di sana)")
    dst.mkdir(parents=True, exist_ok=True)
    print(f"{sid}: mengunduh {r['title_ar']} …", flush=True)  # kitab besar: unduh + indeks makan belasan detik
    # isi kitab disimpan terkompres (.gz) supaya hemat disk: teks Arab menyusut ±5x
    # pages.jsonl terakhir: dialah tanda "sudah ada", jadi kitab yang unduhannya putus diunduh ulang
    for f in ("book_metadata.json", "toc.jsonl", "pages.jsonl"):
        url = f"{RAW}/{urllib.parse.quote(asal[0])}/{f}"
        if f.endswith(".jsonl"):
            unduh(url, dst / (f + ".gz"), lambda q: gzip.open(q, "wb", compresslevel=6))  # 9: 4x lebih lambat, hemat 6% saja
        else:
            unduh(url, dst / f, tulis_biner)
    mb = (dst / "pages.jsonl.gz").stat().st_size / 1e6
    print(f"{sid}: menyiapkan indeks pencarian ({mb:.1f} MB) …", flush=True)
    padat_kitab(sid)  # sekarang, bukan saat `cari` pertama: kitab besar makan belasan detik
    print(f"{sid} OK  {r['title_ar']}  ({mb:.1f} MB)")


_PADAT_UKURAN = {n: array.array(norma.Padat.JENIS[n]).itemsize for n in norma.Padat.DERET}
_PADAT_STRUCT = {n: struct.Struct(norma.Padat.JENIS[n]) for n in ("mulai", "ruas")}


def _kena_bagian(mentah, base, end, mulai, qb, j0):
    """Indeks rekaman (urut naik) yang bagian ini memuat `qb` (tidak melintasi batas rekaman), mulai dari letak `j0`."""
    qlen, j = len(qb), j0
    while j >= 0:
        rel = j - base
        i = bisect.bisect_right(mulai, rel) - 1
        batas = mulai[i + 1]
        if rel + qlen <= batas:
            yield i
            j = mentah.find(qb, base + batas, end)
        else:
            j = mentah.find(qb, j + 1, end)


def _kena_urut(mentah, awal_isi, teks_span, deret, qb, j_awal):
    """Indeks rekaman (urut naik, unik) yang salah satu bagiannya memuat `qb`, dihitung malas (berhenti begitu cukup)."""
    it = [iter(_kena_bagian(mentah, awal_isi + a, awal_isi + z, d["mulai"], qb, j0))
          for (a, z), d, j0 in zip(teks_span, deret, j_awal) if j0 >= 0]
    kepala = [next(g, None) for g in it]
    while True:
        pilih = None
        for v in kepala:
            if v is not None and (pilih is None or v < pilih):
                pilih = v
        if pilih is None:
            return
        yield pilih
        for idx, v in enumerate(kepala):
            if v == pilih:
                kepala[idx] = next(it[idx], None)


def _berkas_padat(sid):
    return folder(sid) / f"padat-{norma.VERSI}.bin"


def _baca_padat_kena(sid, q, qb, sumber):
    """Seperti `(padat_kitab(sid), iter(padat_.kena(q)))`, membaca `padat-*.bin` sekali dengan verifikasi penuh
    (kepala, panjang, EOF, crc32, bentuk deret). Kitab yang tidak memuat `qb` langsung mengembalikan `(None, None)`
    tanpa menyalin/mengurai deret; berkas rusak/usang/hilang dibangun ulang lewat `padat_kitab`."""
    f = _berkas_padat(sid)
    deret_nama, jenis = norma.Padat.DERET, norma.Padat.JENIS
    hasil = _baca_biner(f, len(BAGIAN) * (1 + len(deret_nama)), sumber=sumber, urutan=sys.byteorder)
    if hasil is not None:
        mentah, awal_isi, panjang = hasil
        mv = memoryview(mentah)[awal_isi:]
        teks_span, deret_span, pos, k, n_rek_0, sah = [], [], 0, 0, None, True
        for _ in BAGIAN:
            t_len = panjang[k]; teks_span.append((pos, pos + t_len)); pos += t_len; k += 1
            off, cnt = {}, {}
            for n in deret_nama:
                d_len = panjang[k]
                if d_len % _PADAT_UKURAN[n]:
                    sah = False
                    break
                cnt[n] = d_len // _PADAT_UKURAN[n]
                off[n] = (pos, pos + d_len)
                pos += d_len; k += 1
            if not sah:
                break
            n_rek = cnt["mulai"]
            if n_rek_0 is None:
                n_rek_0 = n_rek
            if not (n_rek == cnt["ruas"] == n_rek_0 and n_rek
                    and _PADAT_STRUCT["mulai"].unpack_from(mv, off["mulai"][1] - _PADAT_UKURAN["mulai"])[0] == t_len
                    and _PADAT_STRUCT["ruas"].unpack_from(mv, off["ruas"][1] - _PADAT_UKURAN["ruas"])[0] == cnt["awal"]
                    and all(cnt[x] == cnt["awal"] for x in ("akhir", "h1", "h2"))):
                sah = False
                break
            deret_span.append(off)
        if sah:
            j_awal = [mentah.find(qb, awal_isi + a, awal_isi + z) for a, z in teks_span]
            if all(j < 0 for j in j_awal):
                return None, None
            teks_ = [mv[a:z] for a, z in teks_span]
            deret = [{n: mv[a:z].cast(jenis[n]) for n, (a, z) in off.items()} for off in deret_span]
            gen = _kena_urut(mentah, awal_isi, teks_span, deret, qb, j_awal)
            pertama = next(gen, None)
            if pertama is None:
                return None, None
            return norma.Padat(teks_, deret), itertools.chain((pertama,), gen)
    padat_ = padat_kitab(sid, sumber=sumber)
    kena = padat_.kena(q)
    return (padat_, iter(kena)) if kena else (None, None)


def padat_kitab(sid, *, sumber=None):
    """`norma.Padat` kitab sid: teks `padat` seluruh kitab, dibaca dari berkasnya (atau dibuat sekali)."""
    sumber = _sidik(sid) if sumber is None else sumber
    if _BACA_SAJA:
        return norma.Padat.baca(_berkas_padat(sid), sumber) or norma.Padat.buat(
            norma.rekaman(folder(sid) / "pages.jsonl.gz")
        )
    return norma.cache(folder(sid), sumber)


@cache_kitab()
def _sidik(sid):
    """Sidik pages.jsonl.gz kitab sid, sekali per perintah: indeks dan teks `padat` sama-sama mencocokkan diri dengannya."""
    return norma.sidik(folder(sid) / "pages.jsonl.gz")


INDEKS = "indeks.json"  # di folder tiap kitab
INDEKS_VERSI = 3  # naikkan kalau isi indeks (lihat `indeks`) berubah cara hitungnya atau bentuknya


def _isi(sid):
    """Isi pages.jsonl.gz yang sudah dibuka (satu rekaman per baris), utuh: hanya untuk membuat indeks."""
    with gzip.open(folder(sid) / "pages.jsonl.gz") as g:
        return g.read()


class _Lompat:
    """Isi berkas .gz yang dibaca per potongan [a, z) tanpa membuka seluruhnya ke memori. Selama dibaca maju, tiap
    ±LANGKAH byte isi dicatat titik lanjutnya (letak isi, letak di .gz, salinan keadaan zlib ±42 KB); bacaan berikutnya
    mulai dari titik terdekat sebelum a. Blok (isi antara dua titik) yang terakhir dibuka, dari kitab mana pun, disimpan
    sebentar (BLOK_MAKS).
    Berkas .gz yang anggotanya lebih dari satu (bukan buatan `ambil`) dibuka utuh sekali."""
    LANGKAH = 1 << 19  # 512 KB isi: satu rekaman yang diminta = membuka paling banyak sebanyak ini lebih dulu
    POTONG = 1 << 16  # byte .gz yang diberikan ke zlib sekali jalan
    BLOK_MAKS = 32
    blok = {}  # (pembaca, nomor titik) -> isi blok itu, urut terakhir dipakai; bersama semua kitab

    def __init__(self, f):
        self.f = f
        self.titik = [(0, 0, zlib.decompressobj(31))]  # urut letak isi; titik terakhir = sejauh mana sudah dibaca
        self.ujung = False  # akhir berkas sudah tercapai
        self.utuh = None  # isi utuh, hanya untuk .gz beranggota banyak

    def _buka(self, k):
        """Isi dari titik k sampai titik k+1 (titik k+1 dibuat dulu kalau belum ada); b"" kalau k = akhir berkas."""
        if (self, k) in self.blok:
            self.blok[self, k] = self.blok.pop((self, k))
            return self.blok[self, k]
        isi, letak, z = self.titik[k]
        z, keluar, n = z.copy(), [], 0
        with open(self.f, "rb") as h:
            h.seek(letak)
            if k + 1 < len(self.titik):  # blok lama: masukannya tepat sampai titik berikutnya
                keluar.append(z.decompress(h.read(self.titik[k + 1][1] - letak)))
            elif not self.ujung:
                while n < self.LANGKAH and not z.eof:
                    masuk = h.read(self.POTONG)
                    if not masuk:
                        raise EOFError(f"{self.f} terpotong")
                    keluar.append(z.decompress(masuk)); n += len(keluar[-1]); letak += len(masuk)
                if z.eof:
                    if (z.unused_data + h.read()).strip(b"\0"):  # anggota gzip berikutnya: gzip.open yang membacanya
                        with gzip.open(self.f) as g:
                            self.utuh = g.read()
                    self.ujung = True
                if n:
                    self.titik.append((isi + n, letak, z.copy()))
        hasil = b"".join(keluar)
        self.blok[self, k] = hasil
        if len(self.blok) > self.BLOK_MAKS:
            del self.blok[next(iter(self.blok))]
        return hasil

    def baca(self, a, z=None):
        """Isi [a, z); z None = sampai akhir."""
        if self.utuh is not None:
            return self.utuh[a:z]
        out = []
        k = bisect.bisect_right(self.titik, a, key=lambda t: t[0]) - 1
        while True:
            mulai = self.titik[k][0]
            blok = self._buka(k)
            if self.utuh is not None:
                return self.utuh[a:z]
            out.append(blok[max(0, a - mulai):None if z is None else max(0, z - mulai)])
            k += 1
            if not blok or z is not None and mulai + len(blok) >= z or k >= len(self.titik):
                return b"".join(out)


@cache_kitab(64)
def _lompat(sid):
    return _Lompat(folder(sid) / "pages.jsonl.gz")


def lepas():
    """Lepas semua yang dibaca dari kitab beserta bentuk turunannya (titik baca, blok, indeks, dan tiap `cache_kitab`
    di modul mana pun): untuk perintah yang membaca kitab satu per satu."""
    _Lompat.blok.clear()
    for f in _CACHE_KITAB:
        f.cache_clear()


@cache_kitab(256)
def rekaman_ke(sid, i):
    """Rekaman ke-i kitab sid (urutan berkas), tanpa cache `padat`: dihitung `ruas_halaman` hanya untuk rekaman yang disentuh."""
    ix = indeks(sid)
    return json.loads(_lompat(sid).baca(ix[i][3], ix[i + 1][3] if i + 1 < len(ix) else None))


@cache_kitab()
def indeks(sid):
    """[(juz, page_num, halaman cetak terakhir, letak byte barisnya)] tiap rekaman, urut berkas: `cek` mengurai hanya
    rekaman halaman yang dirujuk, bukan seluruh kitab (bahts 32 kitab: ±8 detik -> ±2). Disimpan di kitab/<id>/indeks.json;
    tidak bergantung pada norm(), jadi tidak dibuat ulang saat mesin berubah. Yang rusak atau tidak cocok dengan berkasnya
    dibuat ulang."""
    return indeks_awal(sid)[0]


@cache_kitab()
def indeks_awal(sid):
    """(indeks, halaman cetak terkecil tiap rekaman atau None). Cocok tidaknya indeks.json dilihat dari sidik berkas .gz
    (isi .gz sama = isi kitab sama), jadi indeks yang sah terbaca tanpa membuka seluruh kitab. Indeks lama tanpa sidik
    itu dibuat ulang sekali. Di berkas, tiap kolom satu daftar (juz, hal, akhir, letak, awal), bukan satu daftar per
    rekaman: dibaca dan diperiksa per kolom, tanpa satu objek per rekaman."""
    d = _baca_indeks(sid)
    if d is not None:
        return list(zip(d["juz"], d["hal"], d["akhir"], d["letak"])), d["awal"]
    return _bangun_indeks(sid)[:2]


_SIDIK_AWAL = b'{"sidik_isi":"'


def _sidik_indeks(d):
    isi = {k: v for k, v in d.items() if k != "sidik_isi"}
    return hashlib.sha256(json.dumps(isi, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")).hexdigest()


def _sidik_indeks_cocok(mentah, d):
    sidik = d["sidik_isi"]
    if (type(sidik) is str and len(sidik) == 64
            and mentah.startswith(_SIDIK_AWAL) and len(mentah) > 80 and mentah[78:80] == b'",'
            and mentah[14:78].decode("ascii", "ignore") == sidik
            and b'"sidik_isi"' not in mentah[80:]):
        h = hashlib.sha256(b"{")
        h.update(memoryview(mentah)[80:])
        if h.hexdigest() == sidik:
            return True
    return sidik == _sidik_indeks(d)


def _baca_indeks(sid, sumber=None):
    """Isi indeks.json kitab sid kalau sah untuk berkas .gz-nya sekarang; None = rusak, lama, atau tidak ada."""
    try:
        mentah = (folder(sid) / INDEKS).read_bytes()
        d = json.loads(mentah)
        kolom, awal, panjang = [d["juz"], d["hal"], d["akhir"], d["letak"]], d["awal"], d["panjang"]
        letak = kolom[3]
        if (d["versi"] == INDEKS_VERSI and d["sumber_gz"] == (_sidik(sid) if sumber is None else sumber)
                and _sidik_indeks_cocok(mentah, d)
                and type(panjang) is int
                and all(type(x) is list and len(x) == len(awal) for x in kolom + [awal])
                and set(map(type, awal)) <= {int, type(None)} and set(map(type, letak)) <= {int}
                and (not letak or 0 <= min(letak) and max(letak) < panjang)):
            return d
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def _bangun_indeks(sid, sumber=None):
    """(indeks, awal, sp) dari seluruh isi kitab, lalu disimpan ke indeks.json. sp = shamela_page_id tiap rekaman
    (nomor halaman di layanan Shamela: tafsir per ayat dan takhrij silang menunjuk rekaman lewat nomor ini)."""
    mentah = _isi(sid)
    isi, awal, sp, letak = [], [], [], 0
    for baris in mentah.splitlines(keepends=True):
        if baris.strip():
            r = json.loads(baris)
            nomor = [int(n) for n in PENANDA.findall(r.get("body") or "")]
            isi.append((r.get("part"), r.get("page_num"), max([r.get("page_num") or 0] + nomor), letak))
            awal.append(min([n for n in [r.get("page_num")] + nomor if n is not None], default=None))
            s = r.get("shamela_page_id")
            sp.append(int(s) if str(s).isdigit() else None)
        letak += len(baris)
    if not _BACA_SAJA:
        try:
            with sementara(folder(sid) / INDEKS) as part:
                kolom = dict(zip(("juz", "hal", "akhir", "letak"), map(list, zip(*isi)))) if isi else dict.fromkeys(("juz", "hal", "akhir", "letak"), [])
                d = {"versi": INDEKS_VERSI, "sumber_gz": _sidik(sid) if sumber is None else sumber, "panjang": len(mentah), **kolom, "awal": awal, "sp": sp}
                isi_bytes = json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
                sidik_isi = hashlib.sha256(isi_bytes).hexdigest()
                part.write_bytes(_SIDIK_AWAL + sidik_isi.encode("ascii") + b'",' + isi_bytes[1:])
        except OSError:
            pass
    return isi, awal, sp


def _letak_lokal(sid, sumber):
    """Daftar letak byte tiap rekaman kitab sid dengan `sumber` yang sudah dihitung, tanpa menyentuh cache bersama."""
    d = _baca_indeks(sid, sumber)
    if d is not None:
        return d["letak"]
    return [r[3] for r in _bangun_indeks(sid, sumber)[0]]


def _rekaman_maju(gz_bytes, letak, urut):
    """Hasilkan `(i, rekaman)` pada indeks `urut` (urut naik) dari isi .gz di memori sekali jalan tanpa membuka ulang berkas."""
    zobj = zlib.decompressobj(31)
    mv = memoryview(gz_bytes)
    gz_len, gz_pos = len(gz_bytes), 0
    buf, off, pos, utuh = b"", 0, 0, None  # isi tersisa = buf[off:] dimulai pada offset byte `pos`
    for i in urut:
        a = letak[i]
        z = letak[i + 1] if i + 1 < len(letak) else None
        if utuh is not None:
            yield i, json.loads(utuh[a:z])
            continue
        sisa = len(buf) - off
        while pos + sisa <= a and not zobj.eof and gz_pos < gz_len:
            pos += sisa
            jarak = a - pos
            step = 1 << 18 if jarak > 200_000 else 1 << 15
            akhir = min(gz_pos + step, gz_len)
            buf = zobj.decompress(mv[gz_pos:akhir])
            off, sisa = 0, len(buf)
            gz_pos = akhir
            if zobj.eof and (zobj.unused_data + gz_bytes[gz_pos:]).strip(b"\0"):
                utuh = gzip.decompress(gz_bytes)
                break
        if utuh is not None:
            yield i, json.loads(utuh[a:z])
            continue
        if a > pos:
            off += a - pos
            pos = a
        if z is None:
            bagian = [buf[off:]]
            while not zobj.eof and gz_pos < gz_len:
                akhir = min(gz_pos + (1 << 15), gz_len)
                bagian.append(zobj.decompress(mv[gz_pos:akhir]))
                gz_pos = akhir
                if zobj.eof and (zobj.unused_data + gz_bytes[gz_pos:]).strip(b"\0"):
                    utuh = gzip.decompress(gz_bytes)
                    break
            yield i, json.loads(utuh[a:z] if utuh is not None else b"".join(bagian))
            continue
        perlu = z - a
        if len(buf) - off < perlu:
            bagian, ada = [buf[off:]], len(buf) - off
            while ada < perlu and not zobj.eof and gz_pos < gz_len:
                akhir = min(gz_pos + (1 << 15), gz_len)
                d = zobj.decompress(mv[gz_pos:akhir])
                gz_pos = akhir
                bagian.append(d); ada += len(d)
                if zobj.eof and (zobj.unused_data + gz_bytes[gz_pos:]).strip(b"\0"):
                    utuh = gzip.decompress(gz_bytes)
                    break
            if utuh is not None:
                yield i, json.loads(utuh[a:z])
                continue
            buf, off = b"".join(bagian), 0
        yield i, json.loads(buf[off:off + perlu])
        off += perlu
        pos = z


@cache_kitab()
def rekaman_shamela(sid):
    """{shamela_page_id: nomor rekaman} kitab sid. Indeks sah yang dibuat sebelum kolom «sp» ada dibuat ulang sekali di
    sini saja, bukan di `cek`: kitab yang tidak pernah dibuka lewat layanan Shamela tidak dibaca ulang."""
    d = _baca_indeks(sid)
    sp = d.get("sp") if d is not None else None
    if not (type(sp) is list and len(sp) == len(d["awal"]) and set(map(type, sp)) <= {int, type(None)}):
        sp = _bangun_indeks(sid)[2]
        indeks_awal.cache_clear(); indeks.cache_clear()
    return {n: i for i, n in reversed(list(enumerate(sp))) if n is not None}


def nama_juz(part):
    """Juz rekaman yang `part`-nya itu: kitab satu jilid (part None) = «-»."""
    return "-" if part is None else part


def _temuan(sid, frasa, potongan=False, *, padat_=None, rekaman_=None):
    """Tiap tempat frasa di kitab sid, satu per bagian rekaman: (rekaman, bagian, tanda, letak (awal, akhir) di teks `padat`,
    halaman, kata utuh?). Letaknya kecocokan kata utuh (`cocok.frasa_utuh`) pertama; tidak ada → kecocokan pertama, utuh False.
    potongan=True: kecocokan pertama apa pun (perilaku lama, untuk mencari potongan kata)."""
    q, kata = cocok.kunci_frasa(frasa), cocok.kata_dalam(frasa)
    for p in berisi(sid, q, padat_=padat_, rekaman_=rekaman_):
        for bagian, tanda in BAGIAN:
            semua = list(cocok.semua_letak(p, q, bagian))
            if not semua:
                continue
            c = next((c for c in semua if cocok.frasa_utuh(p, bagian, *c, kata)), None)
            pilih = semua[0] if potongan or c is None else c
            yield p, bagian, tanda, pilih, cocok.halaman_letak(p, bagian, pilih), c is not None


def _potongan(sid, lain, frasa, perintah_, sebagian=False):
    """Baris jumlah tempat yang hanya cocok sebagai potongan kata (tidak dicetak tanpa --potongan).
    sebagian=True: tidak semua rekaman dipilah, jadi jumlahnya batas bawah."""
    if lain:
        print(f"[{sid}] {'paling sedikit ' if sebagian else ''}{lain} tempat lain hanya cocok sebagai potongan kata (menyeberang batas kata, mis. «العرب ان» untuk "
              f"«العربان»); tampilkan juga: " + perintah(f'{perintah_} {sid} "{frasa}" --potongan'))


CARI_SEMUA_MAKS = 40  # baris `cari semua` yang dicetak; frasa umum di ratusan kitab = ribuan baris
CARI_SEMUA_PER_KITAB = 4
CARI_SEMUA_PROSES = 64  # di bawah ini tetap utas agar pustaka kecil/uji tanpa biaya buat proses


def _baris_cari(sid, p, bagian, tanda, c, h, q, konteks):
    t = norm(p.get(bagian) or "")  # teks norm (untuk dicetak) hanya rekaman yang cocok
    s = BUKAN_ABJAD.sub("", t)
    j = c[0] if s[c[0]:c[1]] == q else s.find(q)
    peta = [k for k, ch in enumerate(t) if "ء" <= ch <= "ي"]  # letak tiap huruf `padat` di t
    i, akhir = peta[j], peta[j + len(q) - 1] + 1
    return f"[{sid}] {letak(nama_juz(p.get('part')), h)}{tanda}: …{t[max(0, i - konteks): akhir + konteks]}…"


def _cari_satu(sid, frasa, konteks, maks, potongan, sekilas=False, *, padat_=None, rekaman_=None):
    """Cetak paling banyak maks tempat frasa di kitab sid; kembalikan (dicetak, tempat cocok, tempat potongan kata saja,
    seluruh kitab sudah dipilah?). sekilas=True (`cari semua`): berhenti begitu maks tempat (paling sedikit satu) dicetak,
    supaya kata umum di ratusan kitab tidak memilah ribuan rekaman; hitungannya lalu belum lengkap."""
    q = cocok.kunci_frasa(frasa)
    tampil = jumlah = lain = 0
    for p, bagian, tanda, c, h, utuh in _temuan(sid, frasa, potongan, padat_=padat_, rekaman_=rekaman_):
        if not (utuh or potongan):
            lain += 1
            continue
        if sekilas and jumlah and tampil >= maks:
            return tampil, jumlah, lain, False
        jumlah += 1
        if tampil < maks:
            tampil += 1
            print(_baris_cari(sid, p, bagian, tanda, c, h, q, konteks))
    return tampil, jumlah, lain, True


def _scan_buku(sid, q, qb):
    """Pindai satu kitab di pekerja: baca & sidik .gz sekali, cek padat sekali, muat letak indeks bila cocok."""
    gz_bytes = (folder(sid) / "pages.jsonl.gz").read_bytes()
    sumber = hashlib.sha256(gz_bytes).hexdigest()
    padat_, kena = _baca_padat_kena(sid, q, qb, sumber)
    if kena is None:
        return sid, None, None, None, None
    return sid, gz_bytes, _letak_lokal(sid, sumber), padat_, kena


def _hitung_buku_siap(sid, frasa, konteks, potongan, gz_bytes, letak_, padat_, kena):
    """Hitung kecocokan satu kitab sesudah kuota cetak `cari semua` penuh (maks=0, tanpa cetak)."""
    if kena is None:
        return False, 0, True
    _, c, lain, habis = _cari_satu(sid, frasa, konteks, 0, potongan, sekilas=True,
                                   padat_=padat_, rekaman_=_rekaman_maju(gz_bytes, letak_, kena))
    return bool(c), lain, habis and c == 0


def _hitung_buku(sid, frasa, konteks, q, qb, potongan):
    """Pindai dan hitung satu kitab secara mandiri di pekerja (maks=0, tanpa cetak)."""
    _, gz_bytes, letak_, padat_, kena = _scan_buku(sid, q, qb)
    return _hitung_buku_siap(sid, frasa, konteks, potongan, gz_bytes, letak_, padat_, kena)


def _siap_pekerja_cari(root_str, baca_saja_):
    global ROOT, _BACA_SAJA
    ROOT = Path(root_str)
    _BACA_SAJA = baca_saja_


def _cari_kumpulan_baris(sids, frasa, konteks, q, qb, potongan):
    """Pindai sekumpulan kitab di proses pekerja: kembalikan `(baris, lain_akhir, lain_sebelum)` untuk tiap kitab yang
    punya kecocokan atau potongan, agar induk bisa memotong tepat ke kuota tersisa tanpa memindai ulang."""
    out = []
    for sid in sids:
        _, gz_bytes, letak_, padat_, kena = _scan_buku(sid, q, qb)
        if kena is None:
            continue
        baris_, lain_sebelum, jumlah, lain = [], [], 0, 0
        for p, bagian, tanda, c, h, utuh in _temuan(
            sid, frasa, potongan, padat_=padat_, rekaman_=_rekaman_maju(gz_bytes, letak_, kena)
        ):
            if not (utuh or potongan):
                lain += 1
                continue
            if jumlah >= 1:
                lain_sebelum.append(lain)
            if jumlah >= CARI_SEMUA_PER_KITAB:
                break
            jumlah += 1
            baris_.append(_baris_cari(sid, p, bagian, tanda, c, h, q, konteks))
        if baris_ or lain:
            out.append((baris_, lain, lain_sebelum))
    return out


def _cari_kumpulan_hitung(sids, frasa, konteks, q, qb, potongan):
    """Pindai dan hitung sekumpulan kitab di proses pekerja sesudah kuota cetak penuh (maks=0, tanpa cetak)."""
    kitab_n = lain_n = 0
    lengkap = True
    for sid in sids:
        ada, lain, tuntas = _hitung_buku(sid, frasa, konteks, q, qb, potongan)
        kitab_n += ada
        lain_n += lain
        lengkap = lengkap and tuntas
    return kitab_n, lain_n, lengkap


def _cari_semua_proses(semua, frasa, konteks, q, qb, potongan):
    """Pindai pustaka besar lewat beberapa proses agar pemilahan batas kata dan indeks tidak tertahan GIL Python."""
    import concurrent.futures
    pekerja = min(10, os.cpu_count() or 4, len(semua))
    potong_awal, potong_lanjut = 12, 24
    tampil = kitab_n = lain_n = 0
    lengkap = True
    idx = 0
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=pekerja, initializer=_siap_pekerja_cari, initargs=(str(ROOT), _BACA_SAJA)
    ) as pool:
        antre = collections.deque()
        while idx < len(semua) and len(antre) < pekerja:
            akhir = min(len(semua), idx + potong_awal)
            antre.append(pool.submit(_cari_kumpulan_baris, semua[idx:akhir], frasa, konteks, q, qb, potongan))
            idx = akhir
        while antre and tampil < CARI_SEMUA_MAKS:
            for baris_, lain_akhir, lain_sebelum in antre.popleft().result():
                m = min(CARI_SEMUA_PER_KITAB, CARI_SEMUA_MAKS - tampil)
                batas_henti = max(1, m) - 1
                cetak = baris_[:m]
                if cetak:
                    print("\n".join(cetak))
                    tampil += len(cetak)
                if batas_henti < len(lain_sebelum):
                    kitab_n += 1
                    lain_n += lain_sebelum[batas_henti]
                    lengkap = False
                else:
                    kitab_n += bool(baris_)
                    lain_n += lain_akhir
                    lengkap = lengkap and len(baris_) <= m
            while tampil < CARI_SEMUA_MAKS and idx < len(semua) and len(antre) < pekerja * 2:
                akhir = min(len(semua), idx + potong_lanjut)
                antre.append(pool.submit(_cari_kumpulan_baris, semua[idx:akhir], frasa, konteks, q, qb, potongan))
                idx = akhir
        futs = []
        while idx < len(semua):
            akhir = min(len(semua), idx + potong_lanjut)
            futs.append(pool.submit(_cari_kumpulan_hitung, semua[idx:akhir], frasa, konteks, q, qb, potongan))
            idx = akhir
        while antre:
            for baris_, lain_akhir, lain_sebelum in antre.popleft().result():
                if lain_sebelum:
                    kitab_n += 1
                    lain_n += lain_sebelum[0]
                    lengkap = False
                else:
                    kitab_n += bool(baris_)
                    lain_n += lain_akhir
                    lengkap = lengkap and not baris_
        for fut in concurrent.futures.as_completed(futs):
            kn, ln, lk = fut.result()
            kitab_n += kn
            lain_n += ln
            lengkap = lengkap and lk
    return tampil, kitab_n, lain_n, lengkap


def cari(sid, frasa, konteks=90, maks=15, potongan=False):
    """Cari frasa di satu kitab; sid "semua" = di semua kitab yang sudah diunduh (paling banyak CARI_SEMUA_MAKS baris,
    lalu ringkasan jumlah kitab dan tempat yang cocok). Bawaan: frasa cocok sebagai kata utuh (`cocok.frasa_utuh`); tempat yang
    hanya cocok sebagai potongan kata dihitung dan disebut jumlahnya. potongan=True: potongan kata juga dicetak.
    Kembalikan jumlah tempat yang cocok."""
    if sid == "semua":
        q = cocok.kunci_frasa(frasa)
        qb = norma.bait(q)
        semua = punya()
        tampil = kitab_n = lain_n = 0
        lengkap = True  # semua tempat yang cocok sudah dicetak
        if len(semua) >= CARI_SEMUA_PROSES:
            import multiprocessing
            pakai_proses = multiprocessing.current_process().name == "MainProcess"
        else:
            pakai_proses = False
        if pakai_proses:
            tampil, kitab_n, lain_n, lengkap = _cari_semua_proses(semua, frasa, konteks, q, qb, potongan)
        elif len(semua) <= 1:
            for s in semua:
                _, gz_bytes, letak_, padat_, kena = _scan_buku(s, q, qb)
                if kena is not None:
                    t, c, lain, habis = _cari_satu(s, frasa, konteks, min(CARI_SEMUA_PER_KITAB, CARI_SEMUA_MAKS - tampil),
                                                   potongan, sekilas=True, padat_=padat_,
                                                   rekaman_=_rekaman_maju(gz_bytes, letak_, kena))
                    tampil, kitab_n, lain_n, lengkap = tampil + t, kitab_n + bool(c), lain_n + lain, lengkap and habis and c == t
        else:
            import concurrent.futures
            pekerja = min(8, os.cpu_count() or 4, len(semua))
            jendela = pekerja * 2
            with concurrent.futures.ThreadPoolExecutor(max_workers=pekerja) as pool:
                antre = collections.deque(pool.submit(_scan_buku, s, q, qb) for s in semua[:jendela])
                idx = jendela
                while antre and tampil < CARI_SEMUA_MAKS:
                    s, gz_bytes, letak_, padat_, kena = antre.popleft().result()
                    if idx < len(semua):
                        antre.append(pool.submit(_scan_buku, semua[idx], q, qb))
                        idx += 1
                    if kena is not None:
                        t, c, lain, habis = _cari_satu(s, frasa, konteks, min(CARI_SEMUA_PER_KITAB, CARI_SEMUA_MAKS - tampil),
                                                       potongan, sekilas=True, padat_=padat_,
                                                       rekaman_=_rekaman_maju(gz_bytes, letak_, kena))
                        tampil, kitab_n, lain_n, lengkap = tampil + t, kitab_n + bool(c), lain_n + lain, lengkap and habis and c == t
                if antre or idx < len(semua):
                    futs = []
                    while antre:
                        s, gz_bytes, letak_, padat_, kena = antre.popleft().result()
                        if kena is not None:
                            futs.append(pool.submit(_hitung_buku_siap, s, frasa, konteks, potongan, gz_bytes, letak_, padat_, kena))
                    for s in semua[idx:]:
                        futs.append(pool.submit(_hitung_buku, s, frasa, konteks, q, qb, potongan))
                    for fut in concurrent.futures.as_completed(futs):
                        ada, lain, tuntas = fut.result()
                        kitab_n += ada
                        lain_n += lain
                        lengkap = lengkap and tuntas
        if not kitab_n:
            print("TIDAK KETEMU di kitab mana pun" + (" sebagai kata utuh" if lain_n else "") + ":", frasa)
        elif not lengkap:
            print(f"({kitab_n} kitab cocok; ditampilkan {tampil} baris, paling banyak {CARI_SEMUA_PER_KITAB} tiap kitab. "
                  "Persempit frasanya, atau cari di satu kitab (jumlah tempatnya ikut dicetak): "
                  + perintah(f'cari <nomor> "{frasa}"') + ")")
        _potongan("semua", lain_n, frasa, "cari", sebagian=not lengkap)
        return kitab_n
    tampil, jumlah, lain, _ = _cari_satu(sid, frasa, konteks, maks, potongan)
    if jumlah > tampil:
        print(f"[{sid}] (ditampilkan {tampil} dari {jumlah} tempat; persempit frasanya)")
    if not jumlah:
        print(f"[{sid}] TIDAK KETEMU" + (" sebagai kata utuh" if lain else "") + f": {frasa}")
    _potongan(sid, lain, frasa, "cari")
    return jumlah


def teks(sid, frasa, lebar=260, maks=3, potongan=False):
    """Seperti `cari`, tapi menampilkan teks ASLI (huruf apa adanya, tanpa harakat) untuk disalin persis."""
    q = cocok.kunci_frasa(frasa)
    n = lain = 0
    for p, bagian, tanda, c, h, utuh in _temuan(sid, frasa, potongan):
        if not (utuh or potongan):
            lain += 1
            continue
        n += 1
        raw = re.sub(r"\s+", " ", HARAKAT.sub("", TAGS.sub("", p.get(bagian) or "")))
        i = cocok.letak_asli(raw, q, sum(1 for x in cocok.semua_letak(p, q, bagian) if x[0] < c[0]))  # kecocokan ke berapa di rekaman ini
        print(f"[{sid}] {letak(nama_juz(p.get('part')), h)}{tanda}: {raw[max(0, i - lebar // 3): i + lebar]}")
        if n >= maks:
            return n
    if n == 0:
        print(f"[{sid}] TIDAK KETEMU" + (" sebagai kata utuh" if lain else "") + f": {frasa}")
    _potongan(sid, lain, frasa, "teks")
    return n


JUDUL = re.compile(r"""<span\b(?=[^>]*\bdata-type\s*=\s*(?:"title"|'title'))
    (?=[^>]*\bid\s*=\s*["']?toc-(?P<nomor>\d+)\b)[^>]*>""", re.X)  # tanda judul di matan; nomornya = shamela_title_id di toc


def judul_calon(p, toc, c, h, bagian, page_ids=None):
    """Judul toc yang menaungi letak c (dari `cocok.letak_pertama`) di rekaman p. Satu judul = pasti; lebih = ragu.
    Satu rekaman bisa memuat beberapa judul: letaknya dari tanda judul di matan, atau dari tulisan judulnya."""
    pid = p["page_id"]
    if page_ids is not None:
        lo = bisect.bisect_left(page_ids, pid)
        hi = bisect.bisect_right(page_ids, pid, lo)
    else:
        lo = bisect.bisect_left(toc, pid, key=operator.itemgetter("page_id"))
        hi = bisect.bisect_right(toc, pid, lo, key=operator.itemgetter("page_id"))
    sebelum = toc[lo - 1] if lo > 0 else None
    di_sini = toc[lo:hi]
    if not di_sini:
        return [sebelum]
    teks, batas = ruas_halaman(p, "body")
    body = p.get("body") or ""
    span = {int(m["nomor"]): m.start() for m in JUDUL.finditer(body)}
    letak_judul, mulai = [], 0  # letak judul yang tidak terbaca = None; letaknya tetap sesudah judul sebelumnya
    for t in di_sini:
        if t.get("shamela_title_id") in span:
            x = len(padat(body[:span[t["shamela_title_id"]]]))
        else:
            x = teks.find(padat(t["title_text"]), mulai) if padat(t["title_text"]) else -1
        letak_judul.append(x if x >= 0 else None); mulai = x + 1 if x >= 0 else mulai
    if bagian == "body":
        a, z = c[0], c[0] + 1
    else:  # حاشية: ruas matan halaman yang sama
        r = [(a, z) for a, z, h1, _ in batas if h[0] is not None and h[0] <= (h1 or 0) <= h[1]]
        a, z = (r[0][0], r[-1][1]) if r else (0, len(teks))
    naung, bawah, calon = sebelum, 0, []
    for t, x in zip(di_sini, letak_judul):
        if x is not None and x <= a:
            naung, bawah, calon = t, x, []  # judul sebelumnya tertutup judul ini
        elif x is None and bawah < z or x is not None and x < z:
            calon.append(t)  # mungkin mulai sebelum akhir ruas
        bawah = max(bawah, x or 0)
    return [naung] + calon


@cache_kitab()  # `bukti` dan `cek` membacanya untuk tiap catatan kaki
def daftar_isi(sid):
    """(judul toc urut page_id lalu title_id, {title_id: judul}); kitab tanpa toc.jsonl.gz = kosong."""
    try:
        mentah = gzip.decompress((folder(sid) / "toc.jsonl.gz").read_bytes()).strip()
    except OSError:
        mentah = b""
    if not mentah:
        toc = []
    else:
        try:
            toc = json.loads(b"[" + mentah.replace(b"\n", b",") + b"]")
        except json.JSONDecodeError:
            toc = [json.loads(x) for x in mentah.splitlines() if x.strip()]
    return sorted(toc, key=operator.itemgetter("page_id", "title_id")), {t["title_id"]: t for t in toc}


@cache_kitab()
def _toc_page_ids(sid):
    """Daftar `page_id` terurut milik `daftar_isi(sid)[0]` untuk pencarian biner `judul_calon`."""
    return [t["page_id"] for t in daftar_isi(sid)[0]]


def _rantai_telusur(byid, t):
    r = []
    while t and len(r) < 50:  # toc rusak yang induknya berputar tidak membuat macet
        r.append(" ".join(HARAKAT.sub("", t["title_text"]).split()))
        t = byid.get(t.get("parent_id"))
    return r


@cache_kitab()
def _rantai_id(sid, tid):
    byid = daftar_isi(sid)[1]
    return tuple(_rantai_telusur(byid, byid.get(tid)))


def rantai_judul(sid, t):
    """Judul t lalu induk-induknya (tanpa harakat, spasi dirapikan), dari yang terdalam."""
    if not t:
        return []
    byid = daftar_isi(sid)[1]
    tid = t.get("title_id")
    if tid is not None and byid.get(tid) is t:
        return list(_rantai_id(sid, tid))
    return _rantai_telusur(byid, t)


def rekaman(sid):
    """Tiap rekaman kitab sid, urut berkasnya (urut kitab), satu-satu tanpa membuka seluruh kitab ke memori."""
    yield from norma.rekaman(folder(sid) / "pages.jsonl.gz")


def rantai_calon(sid, p, c, h, bagian):
    """Rantai judul (kitab > bab) tiap judul yang mungkin menaungi letak c (`padat`) di rekaman p: satu = pasti, lebih = ragu."""
    return [" < ".join(rantai_judul(sid, t)[:3]) or "(sebelum judul pertama)"
            for t in judul_calon(p, daftar_isi(sid)[0], c, h, bagian, _toc_page_ids(sid))]


def judul_naung(sid, p, c):
    """Judul toc yang menaungi letak c (dari `cocok.letak_pertama`, di matan) rekaman p, atau None (sebelum judul pertama, kitab
    tanpa toc, atau rekaman tanpa page_id)."""
    toc = daftar_isi(sid)[0]
    if not toc or p.get("page_id") is None:
        return None
    return judul_calon(p | {"page_id": int(p["page_id"])}, toc, c, None, "body", _toc_page_ids(sid))[0]


def bagian_halaman(sid, p1, p2):
    """Juz (bagian) kitab yang punya rekaman di halaman cetak p1..p2: «-» kitab satu jilid, angka jilid, atau nama
    bagian (المقدمة، الكتاب). Dipakai `cek` untuk juz «-» di kitab yang bagiannya hanya bernama; `halaman` memakai aturan
    yang sama, dari isi halamannya."""
    ix, awal = indeks_awal(sid)
    return {nama_juz(j) for (j, _, z, _), a in zip(ix, awal) if a is not None and a <= p2 and z >= p1}


def bab(sid, frasa, potongan=False):
    """Tampilkan rantai judul (kitab > bab) tempat sebuah frasa berada (kata utuh, kecuali potongan=True), plus juz/halaman."""
    cocok.kunci_frasa(frasa)
    info(sid)  # kitab belum diunduh -> pesan yang jelas
    lain = 0
    for p, bagian, tanda, c, h, utuh in _temuan(sid, frasa, potongan):
        if not (utuh or potongan):
            lain += 1
            continue
        calon = rantai_calon(sid, p, c, h, bagian)
        kepala = f"[{sid}] {letak(nama_juz(p.get('part')), h)}{tanda}: "
        if len(calon) == 1:
            print(kepala + calon[0])
        else:
            print(kepala + "RAGU, judulnya salah satu dari ini (lihat sendiri dengan `halaman`):")
            for t in calon:
                print("  - " + t)
        return True
    print(f"[{sid}] TIDAK KETEMU" + (" sebagai kata utuh" if lain else "") + f": {frasa}")
    _potongan(sid, lain, frasa, "bab")
    return False


# kalimat di kartu kitab Shamela yang berarti nomor halamannya bukan nomor cetakan (dipakai `cek` di cek_kutipan.py dan `scan`)
OTOMATIS = re.compile("مرقمة? آليا|بترقيم الشاملة")


def rekaman_di(sid, nomor):
    """Rekaman ke-n kitab sid untuk tiap n di `nomor` (urut berkas), dibaca bergeser maju di berkas .gz: kitab tidak
    dibuka utuh ke memori dan bacaan berhenti di rekaman terakhir yang diminta (satu halaman kitab besar: ±3 detik -> ±0,5)."""
    urut = sorted(nomor)
    if not urut:
        return
    ix, isi = indeks(sid), _lompat(sid)
    for i in urut:
        yield json.loads(isi.baca(ix[i][3], ix[i + 1][3] if i + 1 < len(ix) else None))


def berisi(sid, q, *, padat_=None, rekaman_=None):
    """Rekaman kitab sid yang memuat q (sudah `padat`), urut berkas, dengan cache `padat`-nya. Rekaman lain tidak diurai."""
    if rekaman_ is not None:
        for i, p in rekaman_:
            yield padat_.isi(p, i)
        return
    wajib_ada(sid)
    padat_, kena_it = _baca_padat_kena(sid, q, norma.bait(q), _sidik(sid))
    if kena_it is None:
        return
    kena = list(kena_it)
    if not kena:
        return
    for i, p in zip(kena, rekaman_di(sid, kena)):
        yield padat_.isi(p, i)


def baris(teks):
    """Teks kitab untuk dicetak: pemisah baris Shamela «\\r» jadi baris baru. «\\r» mentah di konsol menimpa baris atau
    hilang saat disalin, sehingga dua kata tersambung («نستعينالحمد»)."""
    return re.sub(r"\r\n?", "\n", teks)


def rekaman_halaman(sid, juz, hal):
    """[(rekaman, potongan body milik halaman itu)] untuk halaman cetak juz/hal kitab sid (juz/hal sudah angka kalau
    angka). Juz «-» di kitab yang bagiannya hanya bernama (المقدمة، الكتاب) = satu-satunya bagian yang punya halaman
    itu, seperti `cek`; ada di dua bagian = kosong (sebut bagiannya)."""
    ix, awal = indeks_awal(sid)
    bernama = juz == "-" and not any(j is None or str(j).isdigit() for j, *_ in ix)
    calon = [i for i, (j, _, akhir, _) in enumerate(ix) if awal[i] is not None and awal[i] <= hal <= akhir
             and (bernama or angka(nama_juz(j)) == juz)] if isinstance(hal, int) else []
    kena = [(p, b) for p in rekaman_di(sid, calon) if (b := [b for h, b in per_halaman(p) if h == hal])]
    if bernama and len({nama_juz(p.get("part")) for p, _ in kena}) > 1:
        return []
    return kena


def halaman(sid, juz, hal):
    """Isi satu halaman cetak (juz "-" untuk kitab satu jilid), dengan حاشية milik halaman itu. «05» dan «٥» = 5."""
    juz, hal = angka(juz), angka(hal)
    wajib_ada(sid)
    kena = rekaman_halaman(sid, juz, hal)
    for p, bagian in kena:
        print(baris(TAGS.sub("", "".join(bagian))))
        fn = per_halaman(p, "footnotes")
        if len(fn) > 1:  # حاشية bertanda halaman: cetak yang milik halaman ini saja
            isi, catat = "".join(b for h, b in fn if h == hal), ""
        else:
            a, z = p.get("page_num"), per_halaman(p)[-1][0]
            isi = fn[0][1]
            catat = f" (حاشية rekaman ص{a}-{z}; halaman tiap catatan tidak tercatat)" if z != a else ""
        if isi.strip():
            print("ـــــ" + catat + "\n" + baris(TAGS.sub("", isi)))
    if not kena:
        print(f"[{sid}] TIDAK ADA halaman {juz}/{hal}. Yang ada: {daftar_juz(sid)} (juz \"-\" = kitab satu jilid)")
    return bool(kena)


def rentang_juz(sid):
    """{juz: [halaman terkecil, terbesar]} menurut rekaman kitab (urut kemunculan; juz None = "-"), dari indeks;
    rekaman tanpa nomor halaman dilewati."""
    ix, awal = indeks_awal(sid)
    rentang = {}
    for (j, _, z, _), a in zip(ix, awal):
        if a is not None:
            r = rentang.setdefault(nama_juz(j), [a, z])
            r[0], r[1] = min(r[0], a), max(r[1], z)
    return rentang


def daftar_juz(sid):
    """«juz 1 ص1-538، juz 2 ص539-856»: juz yang dipakai rekaman kitab sid beserta rentang halamannya."""
    return "، ".join(f"juz {j} ص{a}-{z}" for j, (a, z) in rentang_juz(sid).items())


def contoh_bukti(sid):
    """Satu baris bukti siap pakai menurut juz yang dipakai rekaman kitab, bukan «عدد الأجزاء» data cetak: kitab dua
    jilid yang halamannya bersambung («متسلسلة الترقيم») tetap ditulis dengan juz-nya; "-" hanya untuk kitab tanpa juz."""
    rentang = rentang_juz(sid)
    if list(rentang) == ["-"]:
        a, z = rentang["-"]
        return f"bukti: <<{sid}|-|<hal>>> (kitab satu jilid: juz \"-\"; halaman {a}-{z})"
    if not rentang:  # tanpa nomor halaman cetak sama sekali
        return f"bukti: <<{sid}|<juz>|<hal>>> (rekaman kitab ini tanpa nomor halaman; lihat `halaman {sid} <juz> <hal>`)"
    # juz berangka dulu; kitab yang bagiannya hanya bernama (المقدمة + الكتاب): bagian terpanjang, bukan مقدمة المحقق
    j = next((j for j in rentang if str(j).isdigit()), None) or max(rentang, key=lambda j: rentang[j][1] - rentang[j][0])
    a = rentang[j][0]
    return f"bukti: <<{sid}|<juz>|<hal>>>, mis. <<{sid}|{j}|{a}>>; yang ada: {daftar_juz(sid)}"
