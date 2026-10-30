"""Perpustakaan Shamela lokal: unduh kitab per-judul dari dataset Hugging Face
AuthenticIlm/Shamela4_Full_DB ke folder kitab/, lalu cari kutipan secara offline
(tanpa kredit, tanpa internet). `temukan` dan `scan` memakai turath.io sebagai penunjuk jalan. Dipanggil lewat bahts.py.
"""
import functools, gzip, hashlib, html, http.client, json, os, re, shutil, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

import norma
from berkas import sementara
from norma import BAGIAN, HARAKAT, PENANDA, TAGS, BUKAN_ABJAD, _potong, _ruas, norm, padat  # dipakai juga lewat shamela.* (olah, hadits)

MESIN = Path(__file__).parent
ROOT = MESIN.parent / "kitab"


def perintah(argumen):
    """Perintah mesin yang bisa ditempel apa adanya: jalur lengkap kalau dijalankan dari folder lain, Python yang sedang dipakai.
    Semua pesan yang menyuruh menjalankan perintah memakai ini (bahts, shamela, olah, dirasat)."""
    py = "python"
    w = shutil.which("python")
    try:
        if not (w and os.path.samefile(w, sys.executable)):
            py = f'"{sys.executable}"'
    except OSError:
        py = f'"{sys.executable}"'
    try:
        disini = Path.cwd().resolve() == MESIN.parent.resolve()
    except OSError:
        disini = False
    skrip = "mesin/bahts.py" if disini else f'"{MESIN / "bahts.py"}"'
    return f"{py} {skrip} {argumen}".rstrip()
REPO = "AuthenticIlm/Shamela4_Full_DB"
API = f"https://huggingface.co/api/datasets/{REPO}/tree/main"
RAW = f"https://huggingface.co/datasets/{REPO}/resolve/main"
UA = {"User-Agent": "curl/8"}
# unduhan yang putus/gagal di jaringan (bukan nomor kitab yang salah)
GAGAL_JARINGAN = (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError)
COBA = 3  # tiap kitab dicoba sebanyak ini kalau unduhannya putus
SEMENTARA = (500, 502, 503)  # jawaban HTTP yang biasanya hilang sendiri (504 tidak: OpenAlex memakainya untuk «pencarian terlalu berat»)


class _AlihAman(urllib.request.HTTPRedirectHandler):
    """Kunci hanya ikut pengalihan di asal yang sama (protokol, nama host, dan port)."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        baru = super().redirect_request(req, fp, code, msg, headers, newurl)

        def asal(url):
            u = urllib.parse.urlsplit(url)
            port = u.port if u.port is not None else {"http": 80, "https": 443}.get(u.scheme)
            return u.scheme, u.hostname, port

        if baru is not None and asal(req.full_url) != asal(baru.full_url):
            baru.remove_header("Authorization")
        return baru


def buka(url, data=None, kepala=UA, waktu=60, coba=3):
    """Satu pintu permintaan ke layanan luar (temukan, hadits, dirasat, font). Galat sementara (koneksi putus/direset,
    SSL terputus, waktu habis, HTTP 500/502/503) dicoba lagi sampai `coba` kali dengan jeda 1, 2, 4 detik.
    Penolakan lain (4xx, 429 jatah habis, 504) langsung dilempar: artinya beda per layanan, pemanggil yang menjelaskan."""
    pembuka = urllib.request.build_opener(_AlihAman)
    for i in range(coba):
        try:
            return pembuka.open(urllib.request.Request(url, data, kepala), timeout=waktu)
        except urllib.error.HTTPError as e:
            if e.code not in SEMENTARA or i == coba - 1:
                raise
        except GAGAL_JARINGAN:
            if i == coba - 1:
                raise
        time.sleep(2 ** i)

SAMBUNG = "وفبلك"  # huruf sambung di depan kata: kutipan boleh mulai sesudahnya («و"الإحياء"» = «والإحياء»)
NAFI_SAMBUNG = {"ما", "لا", "لم", "لن", "ليس"}  # kutipan tidak boleh mulai dengan kata ini kalau di kitab ia didahului ب/ل


@functools.cache  # daftar folder dataset tidak berubah selama satu perintah
def _ls(path=""):
    url = API + ("/" + urllib.parse.quote(path) if path else "")
    out = []
    while url:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            out += json.load(r)
            link = r.headers.get("Link")
        url = link.split(";")[0].strip("<> ") if link and 'rel="next"' in link else None
    return out


KATALOG = "_meta/book_metadata.parquet"


def siapkan():
    """Unduh katalog kitab (judul, pengarang, letak tiap kitab di dataset) kalau belum ada."""
    f = ROOT / KATALOG
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        _unduh(f"{RAW}/{KATALOG}", f, lambda q: open(q, "wb"))
    print(f"katalog kitab: {len(_meta())} judul")


def _unduh(url, tujuan, buka):
    """Unduh ke nama sementara unik, lalu ganti tujuan kalau utuh; dua unduhan tidak berbagi penulisan."""
    with sementara(tujuan) as part:
        n = 0
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as resp, buka(part) as o:
            while chunk := resp.read(1 << 20):
                o.write(chunk); n += len(chunk)
            janji = resp.headers.get("Content-Length")
        if janji and int(janji) != n:
            raise ConnectionError(f"unduhan terpotong: {n} dari {janji} byte ({tujuan.name})")


@functools.cache
def _meta():
    if not (ROOT / KATALOG).exists():
        raise SystemExit("Katalog kitab belum ada: " + perintah("siapkan"))
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise SystemExit("Pustaka Python belum terpasang; cara memasangnya disebut oleh: " + perintah("periksa"))
    # Katalog hanya perlu tujuh kolom ini; kartu lengkap dibaca dari kitab lokal.
    with pq.ParquetFile(ROOT / KATALOG) as f:
        return f.read(columns=["shamela_id", "book_id", "category_id", "title_ar",
                               "main_author_name_ar", "category_name_ar", "has_multi_part"]).to_pylist()


def ada_keterangan():
    return f"(ADA = sudah diunduh; - = belum, unduh dengan: {perintah('ambil <nomor>')})"


KATALOG_MAKS = 30  # baris katalog yang dicetak; pola pendek bisa cocok dengan ribuan judul
REGEX = re.compile(r"[\\^$.|?*+()\[\]{}]")  # pola katalog yang memuat tanda ini dicoba juga sebagai regex


def katalog(pola):
    """Cari kitab di katalog Shamela (judul atau nama pengarang). Ejaan disamakan seperti `cari` (hamzah, ta marbuthah,
    harakat, spasi). Pola bertanda regex dicoba dulu sebagai regex; tidak ada hasil -> sebagai teks biasa."""
    if not pola.strip():
        raise SystemExit("Tulis sebagian judul atau nama pengarang, mis.: " + perintah('katalog "مدارج السالكين"'))
    daftar = _meta()
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


@functools.cache
def _judul_padat():
    """{judul `padat`: [nomor kitab]} dari katalog lokal; kosong kalau katalog atau pyarrow belum ada (cek tetap jalan)."""
    try:
        daftar = _meta()
    except SystemExit:
        return {}
    out = {}
    for r in daftar:
        out.setdefault(padat(r["title_ar"] or ""), []).append(int(r["shamela_id"]))
    return out


def nomor_judul(judul):
    """(persis, mirip): nomor kitab Shamela yang judulnya persis `judul`, dan yang judulnya diawali `judul`
    (judul pendek, mis. «مدارج السالكين»), ejaan disamakan. ([], []) kalau katalog belum ada."""
    q = padat(judul)
    if len(q) < 6:
        return [], []
    semua = _judul_padat()
    return semua.get(q, []), [s for j, ss in semua.items() if j != q and j.startswith(q) for s in ss]


TURATH = "https://api.turath.io/search"  # pencarian isi seluruh Shamela; nomor kitabnya = shamela_id (sama dengan `ambil`)
TURATH_MAKS = 20  # turath menjawab sebanyak ini tiap pencarian
TURATH_SABAR = 30  # detik; turath minta menunggu lebih lama dari ini = jatah pencarian habis, bukan sekadar terlalu cepat


def temukan(frasa, maks=20):
    """Cari frasa di ISI semua kitab Shamela lewat turath.io, termasuk yang belum diunduh: kitab mana, juz/halaman berapa.
    Hanya penunjuk jalan: layanan orang lain, tanpa janji tetap ada. Kitabnya tetap di-`ambil`, kutipannya tetap lewat `cek`."""
    _kunci(frasa)  # frasa tanpa huruf Arab ditolak di sini, bukan oleh turath
    maks = min(maks, TURATH_MAKS)

    def tanya(ketat):
        url = TURATH + "?" + urllib.parse.urlencode({"q": frasa, "ver": 3, "precision": 3 if ketat else 2})
        for ulang in (True, False):
            try:
                with buka(url) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code != 429:
                    raise
                tunggu = e.headers.get("retry-after") or ""
                tunggu = int(tunggu) if tunggu.isdigit() else 11  # turath membatasi permintaan beruntun dan jumlah pencarian
                if tunggu > TURATH_SABAR or not ulang:
                    raise SystemExit(f"Jatah pencarian turath.io untuk komputer ini habis; terbuka lagi sekitar {tunggu // 60 + 1} menit lagi. "
                                     "Sementara itu: connector `turath` (jatahnya terpisah), `katalog`, atau `cari semua`.")
                time.sleep(tunggu + 1)
    d = tanya(True)
    if not d["count"]:
        d = tanya(False)
        if d["count"]:
            print("Kata-katanya tidak ketemu berurutan; ini hasil pencarian longgar:")
    if not d["count"]:
        print(f"TIDAK KETEMU di seluruh Shamela, berurutan maupun longgar: {frasa}\n"
              "Coba frasa lebih pendek (2-4 kata inti), atau ejaan lain.")
        return 0
    print(f"{d['count']} tempat cocok di seluruh Shamela: {frasa}\n" + ada_keterangan())
    ada = set(punya())
    berjilid = {r["shamela_id"] for r in _meta() if r["has_multi_part"]}  # turath menulis «ج1» juga untuk kitab satu jilid
    for x in d["data"][:maks]:
        m = json.loads(x["meta"])
        cuplikan = re.sub(r"\s+", " ", HARAKAT.sub("", html.unescape(TAGS.sub("", x["snip"]))))
        juz = m.get("vol") if x["book_id"] in berjilid else "-"
        print(f"[{x['book_id']}] {'ADA' if x['book_id'] in ada else '-'}\t{letak(juz or '-', m.get('page'))}\t"
              f"{m['book_name']} — {m['author_name']} :: {cuplikan[:160]}")
    if d["count"] > maks:
        print(f"(ditampilkan {min(maks, len(d['data']))}, paling banyak {TURATH_MAKS}; persempit frasanya untuk hasil lain)")
    return d["count"]


def letak(juz, h):
    """Juz dan halaman untuk dicetak: «ج2 ص15», «ج- ص15-16», «ج«المقدمة» ص3». h = halaman, atau (awal, akhir)."""
    a, z = h if isinstance(h, tuple) else (h, h)
    j = f"ج{juz}" if juz == "-" or str(juz).isdigit() else f"ج«{juz}»"  # juz bernama tidak menempel ke «ج»
    if a is None:
        return f"{j} ص? (rekaman ini tanpa nomor halaman)"
    return f"{j} ص{a}" + (f"-{z}" if z not in (None, a) else "")


def punya():
    """shamela_id semua kitab yang sudah diunduh."""
    return sorted(int(d.name) for d in ROOT.glob("*") if (d / "pages.jsonl.gz").exists())


def _folder(sid):
    """Folder kitab sid; sid yang bukan angka ditolak dengan pesan, bukan disuruh `ambil`."""
    if not str(sid).isdigit():
        raise SystemExit(f"«{sid}» bukan nomor kitab. Nomornya dari `kitab`, `katalog`, atau `temukan`.")
    return ROOT / str(int(sid))


@functools.cache  # `cek` membacanya untuk tiap bukti
def info(sid):
    f = _folder(sid) / "book_metadata.json"
    if not f.exists():
        raise SystemExit(f"Kitab {sid} belum diunduh: " + perintah(f"ambil {sid}"))
    return json.loads(f.read_text(encoding="utf8"))


def daftar():
    if not punya():
        print('Belum ada kitab yang diunduh. Cari nomornya dengan `katalog "<judul>"` atau `temukan "<frasa>"`, '
              "lalu: " + perintah("ambil <nomor>"))
    for sid in punya():
        m = info(sid)
        print(f"{sid}\t{m['title_ar']}\t{m['main_author_name_ar']}")


def kartu(sid):
    """Data cetak kitab (pengarang, muhaqqiq, penerbit, cetakan) untuk rujukan pertama dan daftar pustaka."""
    print(info(sid)["betaka_text"].replace("\r", "\n"))


def ambil(*sid):
    """Unduh kitab (sekali saja). Semua nomor dicoba; unduhan yang putus diulang sampai COBA kali.
    Kembalikan nomor yang gagal (kosong = semua ada); bahts.py yang memberi kode keluar."""
    gagal = []
    for s in sid:
        for coba in range(1, COBA + 1):
            try:
                _ambil(s)
                break
            except LookupError as e:  # nomornya salah: diulang pun sama
                print(f"{s}: {e}"); gagal.append(str(s)); break
            except GAGAL_JARINGAN as e:
                tetap = isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500 and e.code != 429
                if tetap or coba == COBA:
                    print(f"{s}: GAGAL mengunduh, cek internet lalu ulangi ({e!r})"); gagal.append(str(s)); break
                print(f"{s}: unduhan putus ({e!r}); mencoba lagi ({coba + 1}/{COBA}) ...", flush=True)
                time.sleep(5 * coba)
    return gagal


def _ambil(sid):
    if not str(sid).isdigit():
        raise LookupError("bukan nomor kitab (nomornya dari `katalog` atau `temukan`)")
    sid = int(sid)
    dst = ROOT / str(sid)
    if (dst / "pages.jsonl.gz").exists():
        print(sid, "sudah ada"); return
    r = next((r for r in _meta() if r["shamela_id"] == sid), None)
    if r is None:
        raise LookupError("TIDAK ADA di katalog Shamela (nomornya dari `katalog` atau `temukan`)")
    top = [x["path"] for x in _ls() if x["path"].startswith(f"{int(r['category_id']):02d}__")]
    folder = [x["path"] for x in _ls(top[0]) if x["path"].split("/")[-1].split("__")[0] == str(r['book_id'])] if top else []
    if not folder:
        raise LookupError("folder kitabnya tidak ketemu di dataset Shamela (mungkin belum tersedia di sana)")
    dst.mkdir(parents=True, exist_ok=True)
    # isi kitab disimpan terkompres (.gz) supaya hemat disk: teks Arab menyusut ±5x
    # pages.jsonl terakhir: dialah tanda "sudah ada", jadi kitab yang unduhannya putus diunduh ulang
    for f in ("book_metadata.json", "toc.jsonl", "pages.jsonl"):
        url = f"{RAW}/{urllib.parse.quote(folder[0])}/{f}"
        if f.endswith(".jsonl"):
            _unduh(url, dst / (f + ".gz"), lambda q: gzip.open(q, "wb", compresslevel=6))  # 9: 4x lebih lambat, hemat 6% saja
        else:
            _unduh(url, dst / f, lambda q: open(q, "wb"))
    mb = (dst / "pages.jsonl.gz").stat().st_size / 1e6
    _cache(sid)  # sekarang, bukan saat `cari` pertama: kitab besar makan belasan detik
    print(f"{sid} OK  {r['title_ar']}  ({mb:.1f} MB)")


def _cache(sid):
    return norma.cache(_folder(sid))


def _pages(sid):
    f = _folder(sid) / "pages.jsonl.gz"
    if not f.exists():
        raise SystemExit(f"Kitab {sid} belum diunduh: " + perintah(f"ambil {sid}"))
    cache = _cache(sid)
    for i, p in enumerate(norma.rekaman(f)):
        if i < len(cache):
            for (bagian, _), (teks, batas) in zip(BAGIAN, cache[i]):
                p["_padat_" + bagian] = teks, batas
        yield p


INDEKS = "indeks.json"  # di folder tiap kitab
INDEKS_VERSI = 1  # naikkan kalau isi indeks (lihat `indeks`) berubah cara hitungnya


@functools.cache
def _isi(sid):
    """Isi pages.jsonl.gz yang sudah dibuka (satu rekaman per baris), sekali per perintah."""
    with gzip.open(_folder(sid) / "pages.jsonl.gz") as g:
        return g.read()


@functools.cache
def rekaman_ke(sid, i):
    """Rekaman ke-i kitab sid (urutan berkas), tanpa cache `padat`: dihitung `_ruas` hanya untuk rekaman yang disentuh."""
    ix = indeks(sid)
    return json.loads(_isi(sid)[ix[i][3]:ix[i + 1][3] if i + 1 < len(ix) else None])


@functools.cache
def indeks(sid):
    """[(juz, page_num, halaman cetak terakhir, letak byte barisnya)] tiap rekaman, urut berkas: `cek` mengurai hanya
    rekaman halaman yang dirujuk, bukan seluruh kitab (bahts 32 kitab: ±8 detik -> ±2). Disimpan di kitab/<id>/indeks.json;
    tidak bergantung pada norm(), jadi tidak dibuat ulang saat mesin berubah. Yang rusak atau tidak cocok dengan berkasnya
    dibuat ulang."""
    folder = _folder(sid)
    f = folder / INDEKS
    sumber = hashlib.sha256(_isi(sid)).hexdigest()
    try:
        d = json.loads(f.read_text(encoding="utf8"))
        if (d["versi"] == INDEKS_VERSI and d["sumber"] == sumber and isinstance(d["rekaman"], list)
                and all(isinstance(x, list) and len(x) == 4 and type(x[3]) is int
                        and 0 <= x[3] < len(_isi(sid)) for x in d["rekaman"])):
            return [tuple(x) for x in d["rekaman"]]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    isi, letak = [], 0
    for baris in _isi(sid).splitlines(keepends=True):
        if baris.strip():
            r = json.loads(baris)
            isi.append((r.get("part"), r.get("page_num"),
                        max([r.get("page_num") or 0] + [int(n) for n in PENANDA.findall(r.get("body") or "")]), letak))
        letak += len(baris)
    try:
        with sementara(f) as part:
            part.write_text(json.dumps({"versi": INDEKS_VERSI, "sumber": sumber, "rekaman": isi}, ensure_ascii=False), encoding="utf8")
    except OSError:
        pass
    return isi


def _juz(p):
    return "-" if p.get("part") is None else p["part"]


def _kunci(frasa):
    q = padat(frasa)
    if not q:
        raise SystemExit("Frasa pencarian harus berhuruf Arab.")
    return q


def _batas_kata(p, bagian):
    """Letak awal dan akhir tiap kata di teks `padat` bagian itu. Dihitung hanya untuk rekaman yang memuat kutipan."""
    kunci = "_kata_" + bagian
    if kunci not in p:
        awal, akhir, n = set(), set(), 0
        for _, b in _potong(p, bagian):
            for w in norm(b).split():
                w = BUKAN_ABJAD.sub("", w)
                if w:
                    awal.add(n); n += len(w); akhir.add(n)
        p[kunci] = awal, akhir
    return p[kunci]


def kata_dalam(teks):
    """Letak awal tiap kata kutipan (selain kata pertama) di teks `padat`-nya, dihitung seperti `_batas_kata`."""
    out, n = set(), 0
    for w in norm(teks).split():
        w = BUKAN_ABJAD.sub("", w)
        if w:
            if n:
                out.add(n)
            n += len(w)
    return frozenset(out)


def _utuh(p, bagian, j, k, kata=()):
    """Potongan teks[j:k] mulai dan berakhir di batas kata kitab. Di depannya boleh ada huruf sambung (و ف ب ل ك, paling banyak dua).
    kata = letak awal kata di dalam kutipan (`kata_dalam`): batas kata yang bergeser dari batas kitab tidak dihitung."""
    awal, akhir = _batas_kata(p, bagian)
    if k not in akhir or not _sebatas(awal, j, k, kata):
        return False
    if j in awal:
        return True
    teks = _ruas(p, bagian)[0]
    for d in (1, 2):
        if j - d in awal and all(c in SAMBUNG for c in teks[j - d:j]):
            # ك hanya awalan kalau sesudahnya «ال» («كالله»); selain itu hurufnya milik kata («كان», «كأنه»). ب/ل (huruf jar:
            # «لأن»/«بأن» → «أن») bukan awalan di «لكن», «لله» (→ «له»), dan di depan kata nafi («لما», «بلا» → «ما», «لا»)
            awalan, sisa = teks[j - d:j], teks[j:min(a for a in akhir if a > j)]
            if "ك" in awalan:
                return teks.startswith("ال", j)
            if set(awalan) - set("وف") and sisa in NAFI_SAMBUNG:
                return False
            return not ("ل" in awalan and teks.startswith(("ل", "كن"), j))
    return False


def _sebatas(awal, j, k, kata):
    """Batas kata kutipan dan kitab tidak bergeser di antara dua batas yang sama-sama ada: «بل أشك» ≠ «بلا شك».
    Kata yang disambung atau dipisah di satu pihak saja boleh («عبد الله»/«عبدالله», «و الإحياء»)."""
    naskah = kitab = False
    for x in range(j + 1, k):
        di_naskah, di_kitab = x - j in kata, x in awal
        if di_naskah and di_kitab:
            naskah = kitab = False
        else:
            naskah, kitab = naskah or di_naskah, kitab or di_kitab
            if naskah and kitab:
                return False
    return True


def _letak(p, q, bagian="body", utuh=False, kata=()):
    """Tiap letak (awal, akhir) q di teks `padat` bagian rekaman p, berurutan."""
    teks = _ruas(p, bagian)[0]
    j = teks.find(q)
    while j >= 0:
        if not utuh or _utuh(p, bagian, j, j + len(q), kata):
            yield j, j + len(q)
        j = teks.find(q, j + 1)


def _cocok(p, q, bagian="body", utuh=False, kata=()):
    """Letak (awal, akhir) pertama q di teks `padat` bagian rekaman p; None kalau tidak ada."""
    return next(_letak(p, q, bagian, utuh, kata), None)


def tempat(p, q, bagian="body", utuh=False, kata=(), dalam=None):
    """Halaman cetak (awal, akhir) tempat q (sudah `padat`) berada di rekaman p; None kalau tidak ada.
    bagian "footnotes" = حاشية, dihitung per penanda halaman seperti matan.
    utuh=True: q harus mulai dan berakhir di batas kata kitab (kutipan yang terpotong di tengah kata tidak dihitung).
    dalam=(p1, p2): q yang muncul lebih dari sekali di rekaman ini: yang di halaman p1..p2 didahulukan.
    Halamannya None kalau rekaman itu tidak bernomor halaman."""
    batas, pertama = _ruas(p, bagian)[1], None
    for c in _letak(p, q, bagian, utuh, kata):
        h = (next(h for a, z, h, _ in batas if a <= c[0] < z), next(h for a, z, _, h in batas if a <= c[1] - 1 < z))
        if dalam is None or dalam[0] <= (h[0] or 0) and (h[1] or 0) <= dalam[1]:
            return h
        pertama = pertama or h
    return pertama


def cari(sid, frasa, konteks=90, maks=15, diam=False):
    """Cari frasa di satu kitab; sid "semua" = di semua kitab yang sudah diunduh. Kembalikan jumlah temuan."""
    if sid == "semua":
        n = sum(cari(s, frasa, konteks, 4, diam=True) for s in punya())
        if not n:
            print("TIDAK KETEMU di kitab mana pun:", frasa)
        return n
    q = _kunci(frasa)
    n = 0
    for p in _pages(sid):
        for bagian, tanda in BAGIAN:
            if q not in _ruas(p, bagian)[0]:  # saringan cepat dari cache; teks norm (untuk dicetak) hanya rekaman yang cocok
                continue
            t = norm(p.get(bagian) or "")
            j = BUKAN_ABJAD.sub("", t).find(q)
            if j >= 0:
                peta = [k for k, c in enumerate(t) if "ء" <= c <= "ي"]  # letak tiap huruf `padat` di t
                n += 1
                i, akhir = peta[j], peta[j + len(q) - 1] + 1
                h = tempat(p, q, bagian) or (p.get("page_num"),) * 2  # None hanya kalau q melintasi penanda halaman
                print(f"[{sid}] {letak(_juz(p), h)}{tanda}: …{t[max(0, i - konteks): akhir + konteks]}…")
                if n >= maks:
                    print(f"[{sid}] (dipotong, masih ada lagi)"); return n
    if n == 0 and not diam:
        print(f"[{sid}] TIDAK KETEMU: {frasa}")
    return n


def _letak_asli(raw, q):
    """Awal kata tempat q (sudah `padat`) mulai di teks asli raw. Dicari lewat panjang `padat` tiap awalan,
    karena norm() mengubah panjang teks (kalimat hormat dibuang, tanda baca jadi spasi)."""
    j = padat(raw).find(q)
    awal = [m.start() for m in re.finditer(r"\S+", raw)]
    if j <= 0 or not awal:
        return 0
    lo, hi = 0, len(awal) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if len(padat(raw[:awal[mid]])) <= j:
            lo = mid
        else:
            hi = mid - 1
    return awal[lo]


def teks(sid, frasa, lebar=260, maks=3):
    """Seperti `cari`, tapi menampilkan teks ASLI (huruf apa adanya, tanpa harakat) untuk disalin persis."""
    q = _kunci(frasa)
    n = 0
    for p in _pages(sid):
        for bagian, tanda in BAGIAN:
            h = tempat(p, q, bagian)
            if h is None:
                continue
            n += 1
            raw = re.sub(r"\s+", " ", HARAKAT.sub("", TAGS.sub("", p.get(bagian) or "")))
            i = _letak_asli(raw, q)
            print(f"[{sid}] {letak(_juz(p), h)}{tanda}: {raw[max(0, i - lebar // 3): i + lebar]}")
            if n >= maks:
                return n
    if n == 0:
        print(f"[{sid}] TIDAK KETEMU: {frasa}")
    return n


JUDUL = re.compile(r'data-type="?title"?\s+id="?toc-(\d+)')  # tanda judul di matan; nomornya = shamela_title_id di toc


def _judul_calon(p, toc, c, h, bagian):
    """Judul toc yang menaungi letak c (dari `_cocok`) di rekaman p. Satu judul = pasti; lebih = ragu.
    Satu rekaman bisa memuat beberapa judul: letaknya dari tanda judul di matan, atau dari tulisan judulnya."""
    sebelum, di_sini = None, []
    for t in toc:  # toc urut page_id, lalu urutan judul
        if t["page_id"] < p["page_id"]:
            sebelum = t
        elif t["page_id"] == p["page_id"]:
            di_sini.append(t)
        else:
            break
    teks, batas = _ruas(p, "body")
    body = p.get("body") or ""
    span = {int(m.group(1)): m.start() for m in JUDUL.finditer(body)}
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


def bab(sid, frasa):
    """Tampilkan rantai judul (kitab > bab) tempat sebuah frasa berada, plus juz/halaman."""
    q = _kunci(frasa)
    info(sid)  # kitab belum diunduh -> pesan yang jelas
    with gzip.open(_folder(sid) / "toc.jsonl.gz", "rt", encoding="utf8") as f:
        toc = [json.loads(x) for x in f]
    byid = {t["title_id"]: t for t in toc}
    toc.sort(key=lambda t: (t["page_id"], t["title_id"]))

    def rantai(t):
        r = []
        while t:
            r.append(HARAKAT.sub("", t["title_text"]).strip()); t = byid.get(t.get("parent_id"))
        return " < ".join(r[:3]) or "(sebelum judul pertama)"
    for p in _pages(sid):
        for bagian, tanda in BAGIAN:
            c = _cocok(p, q, bagian)
            if c is None:
                continue
            h = tempat(p, q, bagian)
            calon = _judul_calon(p, toc, c, h, bagian)
            kepala = f"[{sid}] {letak(_juz(p), h)}{tanda}: "
            if len(calon) == 1:
                print(kepala + rantai(calon[0]))
            else:
                print(kepala + "RAGU, judulnya salah satu dari ini (lihat sendiri dengan `halaman`):")
                for t in calon:
                    print("  - " + rantai(t))
            return True
    print(f"[{sid}] TIDAK KETEMU: {frasa}")
    return False


# kalimat di kartu kitab Shamela yang berarti nomor halamannya bukan nomor cetakan (dipakai `cek` di olah.py dan `scan`)
OTOMATIS = re.compile("مرقمة? آليا|بترقيم الشاملة")

# Scan cetakan di turath.io: berkas data tiap kitab dan PDF-nya. Dibaca dari kode situs app.turath.io (17 Okt 2026), tidak
# terdokumentasi, jadi bisa berubah tanpa kabar: hanya penunjuk jalan, `cek` dan `rakit` tidak memakainya.
TURATH_FILES = "https://files.turath.io"
# Kunci berkas books-v3 dipadatkan jadi satu huruf (U+064B + urutan nama di daftar ini); berkas yang punya `source`
# menyisipkannya sesudah `version`. Urutan = `hm` di kode situsnya.
TURATH_KUNCI = ("meta id name type printed pdf_links info info_long version author_id cat_id date_built "
                "author_page_start indexes volumes headings print_pg_to_pg volume_bounds page_map page_headings non_author").split()
TURATH_KUNCI_SUMBER = TURATH_KUNCI[:9] + ["source"] + TURATH_KUNCI[9:]


def _turath_buku(sid):
    """Data satu kitab di turath.io dengan nama kunci asli, atau None kalau turath tidak punya kitab itu."""
    try:
        with buka(f"{TURATH_FILES}/books-v3/{int(sid)}.json", waktu=30) as r:
            mentah = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or mentah[:2] == b"\x1f\x8b":
                mentah = gzip.decompress(mentah)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return None
        raise
    data = json.loads(mentah)
    kunci = TURATH_KUNCI_SUMBER if chr(0x64B + TURATH_KUNCI_SUMBER.index("indexes")) in data else TURATH_KUNCI

    def urai(o):
        if isinstance(o, dict):
            return {(kunci[ord(k) - 0x64B] if len(k) == 1 and 0 <= ord(k) - 0x64B < len(kunci) else k): urai(v)
                    for k, v in o.items()}
        return [urai(x) for x in o] if isinstance(o, list) else o
    return urai(data)


def _turath_berkas(berkas, jilid):
    """Berkas PDF untuk satu jilid: tiruan `_re` di kode situsnya (nomor di nama berkas, atau penanda «|n»)."""
    if len(berkas) == 1:
        return berkas[0]
    per_jilid, tanpa_nomor, cadangan = {}, [], ""
    for b in berkas:
        if "|" in b:
            n = next((x for x in b.split("|")[1:] if x), "")
            if n == "0":
                cadangan = cadangan or b
                continue
        else:
            m = re.search(r"0*(\d+)", b)
            if not m:
                tanpa_nomor.append(b)
                continue
            n = m.group(1)
        if n:
            per_jilid[n] = b
    return per_jilid.get(str(jilid)) or cadangan or (tanpa_nomor[0] if len(tanpa_nomor) == 1 else "")


def scan(sid, juz, hal):
    """Alamat scan cetakan (PDF di turath.io) untuk satu halaman cetak, untuk mencocokkan bacaan yang meragukan.
    Juz "-" = kitab satu jilid. Penunjuk jalan saja: hasilnya dibuka dan dibaca orang."""
    angka = lambda x: str(int(x)) if str(x).isdigit() else str(x)  # «05» dan «٥» = 5
    _folder(sid)  # nomor yang bukan angka ditolak dengan pesan yang sama dengan perintah kitab lain
    buku = _turath_buku(sid)
    if buku is None:
        print(f"[{sid}] turath.io tidak punya kitab ini.")
        return False
    meta, ix = buku.get("meta") or {}, buku.get("indexes") or {}
    pdf = meta.get("pdf_links") or {}
    if not pdf.get("files"):
        print(f"[{sid}] {meta.get('name', '')}: turath.io tidak punya scan cetakan kitab ini.")
        return False
    jilid_ada = ix.get("volumes") or ["1"]
    if str(juz).strip() in ("-", "") and len(jilid_ada) > 1:  # «-» hanya untuk kitab satu jilid, seperti `halaman`
        print(f"[{sid}] kitab ini berjilid; sebut juznya. Yang ada: " + "، ".join(f"juz {j}" for j in jilid_ada))
        return False
    jilid = jilid_ada[0] if str(juz).strip() in ("-", "") else angka(juz)
    logis = (ix.get("print_pg_to_pg") or {}).get(f"{jilid},{angka(hal)}")
    if not logis:
        batas = ix.get("volume_bounds") or {}
        print(f"[{sid}] TIDAK ADA halaman {juz}/{hal} di turath. Yang ada: "
              + "، ".join(f"juz {j} ص{a}-{z}" for j, (a, z) in batas.items()) + " (juz \"-\" = kitab satu jilid)")
        return False
    jilid_pdf, fisik = (str((ix.get("page_map") or [])[logis - 1] if logis <= len(ix.get("page_map") or []) else ",")
                        .split(",") + [""])[:2]
    berkas = _turath_berkas(pdf["files"], jilid_pdf or jilid)
    if not fisik.isdigit():
        print(f"[{sid}] scan ada, tetapi halaman {juz}/{hal} tidak tercatat di daftar halamannya.")
        return False
    if not berkas:  # mis. nama berkas bertanda «|#n» yang tidak menyebut jilid; situs turath sendiri juga buntu di sini
        print(f"[{sid}] scan ada ({len(pdf['files'])} berkas), tetapi berkas untuk juz {jilid_pdf or jilid} tidak bisa ditentukan.")
        return False
    jalur = berkas.split("|")[0]
    if pdf.get("root"):
        jalur = pdf["root"].rstrip("/") + "/" + jalur
    if "archive.org" in jalur:
        jalur = "archive/" + jalur.replace("https://archive.org/download/", "").replace("/", "_=_", 1)
    print(f"[{sid}] {meta.get('name', '')} — juz {jilid_pdf or jilid}، ص{angka(hal)} = halaman PDF ke-{fisik}")
    print(f"{TURATH_FILES}/pdf/{urllib.parse.quote(jalur)}#page={fisik}")
    if OTOMATIS.search(str(meta.get("info", ""))):
        print("perhatian: nomor halaman kitab ini buatan Shamela (مرقم آليا), jadi halaman scan bisa meleset; "
              "cari bacaannya di halaman sekitar.")
    return True


def halaman(sid, juz, hal):
    """Isi satu halaman cetak (juz "-" untuk kitab satu jilid), dengan حاشية milik halaman itu. «05» dan «٥» = 5."""
    ada, rentang = False, {}  # juz -> [halaman terkecil, terbesar], untuk pesan kalau halamannya tidak ada
    angka = lambda x: int(x) if str(x).isdigit() else x  # int() membaca angka Arab ٠-٩ juga
    juz, hal = angka(juz), angka(hal)
    for p in _pages(sid):
        hh = [h for h, _ in _potong(p) if h is not None]
        if hh:
            r = rentang.setdefault(_juz(p), [min(hh), max(hh)])
            r[0], r[1] = min(r[0], *hh), max(r[1], *hh)
        if angka(_juz(p)) != juz:
            continue
        bagian = [b for h, b in _potong(p) if h == hal]
        if bagian:
            ada = True
            print(TAGS.sub("", "".join(bagian)))
            fn = _potong(p, "footnotes")
            if len(fn) > 1:  # حاشية bertanda halaman: cetak yang milik halaman ini saja
                isi, catat = "".join(b for h, b in fn if h == hal), ""
            else:
                a, z = p.get("page_num"), _potong(p)[-1][0]
                isi = fn[0][1]
                catat = f" (حاشية rekaman ص{a}-{z}; halaman tiap catatan tidak tercatat)" if z != a else ""
            if isi.strip():
                print("ـــــ" + catat + "\n" + TAGS.sub("", isi))
    if not ada:
        print(f"[{sid}] TIDAK ADA halaman {juz}/{hal}. Yang ada: "
              + "، ".join(f"juz {j} ص{a}-{z}" for j, (a, z) in rentang.items()) + " (juz \"-\" = kitab satu jilid)")
    return ada
