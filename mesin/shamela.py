# SPDX-License-Identifier: AGPL-3.0-or-later
"""Perpustakaan Shamela lokal: unduh kitab per-judul dari dataset Hugging Face
AuthenticIlm/Shamela4_Full_DB ke folder kitab/, lalu cari kutipan secara offline
(tanpa kredit, tanpa internet). `temukan` dan `scan` memakai turath.io sebagai penunjuk jalan. Dipanggil lewat bahts.py.
"""
import bisect, functools, gzip, hashlib, html, http.client, json, os, re, shutil, sys, time, urllib.error, urllib.parse, urllib.request, zlib
from pathlib import Path

import norma
from berkas import sementara
from norma import BAGIAN, HARAKAT, PENANDA, TAGS, BUKAN_ABJAD, per_halaman, ruas_halaman, norm, padat

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


SABAR_JATAH = 30  # detik; layanan minta menunggu lebih lama dari ini = jatah pencarian habis, bukan sekadar terlalu cepat


def tunggu_jatah(e, ulang, habis):
    """HTTP 429 dari `buka` = jatah permintaan layanan sementara habis (turath, alminasa): tunggu sesuai retry-after
    (bawaan 11 detik), lalu pemanggil mengulang sekali. Diminta menunggu lebih dari SABAR_JATAH, atau sudah diulang =
    jatahnya habis: SystemExit(habis), «{menit}» di dalamnya = perkiraan menit sampai terbuka lagi. Galat lain dilempar lagi."""
    if e.code != 429:
        raise e
    tunggu = e.headers.get("retry-after") or ""
    tunggu = int(tunggu) if tunggu.isdigit() else 11  # layanan membatasi permintaan beruntun dan jumlah pencarian
    if tunggu > SABAR_JATAH or not ulang:
        raise SystemExit(habis.format(menit=tunggu // 60 + 1))
    time.sleep(tunggu + 1)

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
        print("katalog kitab: mengunduh …", flush=True)
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
    # Katalog hanya perlu sembilan kolom ini; kartu lengkap dibaca dari kitab lokal.
    with pq.ParquetFile(ROOT / KATALOG) as f:
        return f.read(columns=["shamela_id", "book_id", "category_id", "title_ar",
                               "main_author_id", "main_author_name_ar", "category_name_ar", "has_multi_part", "group_id"]).to_pylist()


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


PENGARANG_SESUDAH = re.compile(r"^(?:للشيخ|للإمام|للعلامة|للحافظ|للقاضي|لابن|لأبي|لأبى)$")  # «المغني لابن قدامة»


def kata_judul(judul):
    """Kata judul sebelum pengarang tempelan («المغني لابن قدامة» -> [«المغني»])."""
    kata = judul.split()
    return kata[:next((i for i, w in enumerate(kata) if i and PENGARANG_SESUDAH.match(w)), len(kata))]


def judul_pokok(judul):
    """Judul katalog tanpa keterangan edisi sesudah « - » («صحيح مسلم - ت عبد الباقي»), dipecah di « = » (judul lain:
    «تفسير السعدي = تيسير الكريم الرحمن»), juga tanpa pengarang yang ditempel («المغني لابن قدامة» → «المغني»)."""
    out = []
    for b in re.split(r"\s+=\s+", re.split(r"\s+-\s+", judul or "")[0].strip()):
        out += [b, " ".join(kata_judul(b))]
    return list(dict.fromkeys(x for x in out if x))


@functools.cache
def _judul_pokok_padat():
    """{judul_pokok `padat`: {nomor kitab}}: «صحيح مسلم» = semua edisinya."""
    try:
        daftar = _meta()
    except SystemExit:
        return {}
    out = {}
    for r in daftar:
        for b in judul_pokok(r["title_ar"]):
            out.setdefault(padat(b), set()).add(int(r["shamela_id"]))
    return out


def nomor_pengarang(nama):
    """main_author_id pengarang katalog yang namanya `nama`, atau diawali `nama` utuh sekata («ابن حجر» = ابن حجر
    العسقلاني dan ابن حجر الهيتمي). Nama satu kata hanya nisbah ber-«ال» yang persis sama («النووي»): «مسلم», «مالك»,
    «أحمد» juga kata biasa, dan satu kata tidak boleh jadi awalan nama orang lain."""
    awal = norm(nama)
    if not awal or " " not in awal:
        return set(_pengarang_kata().get(awal, ())) if awal.startswith("ال") and len(awal) >= 5 else set()
    return {i for j, ii in _pengarang_kata().items() if j == awal or j.startswith(awal + " ") for i in ii}


@functools.cache
def _pengarang_kata():
    """{nama pengarang `norm` (berspasi, supaya «ابن حجر» tidak cocok dengan «ابن حجرة»): {main_author_id}}."""
    try:
        daftar = _meta()
    except SystemExit:
        return {}
    out = {}
    for r in daftar:
        nama = r["main_author_name_ar"] or ""
        for b in {nama, *nama.split("،")}:
            if norm(b):
                out.setdefault(norm(b), set()).add(str(r["main_author_id"]))
    return out


@functools.cache
def _asal():
    """{nomor kitab: (main_author_id, group_id)} dari katalog; group_id menyatukan edisi dan ringkasan satu kitab."""
    try:
        return {int(r["shamela_id"]): (str(r["main_author_id"]), r["group_id"]) for r in _meta()}
    except SystemExit:
        return {}


def asal(sid):
    """(main_author_id, group_id) kitab sid menurut katalog; (None, None) kalau tidak ada."""
    return _asal().get(int(sid), (None, None))


def nomor_judul_pokok(judul):
    """Nomor kitab yang salah satu judul_pokok-nya persis `judul` («صحيح البخاري», «تيسير الكريم الرحمن»)."""
    q = padat(judul)
    return sorted(_judul_pokok_padat().get(q, ())) if len(q) >= 6 else []


TURATH = "https://api.turath.io/search"  # pencarian isi seluruh Shamela; nomor kitabnya = shamela_id (sama dengan `ambil`)
TURATH_MAKS = 20  # turath menjawab sebanyak ini tiap pencarian
# nomor bidang katalog Shamela (category_id), sama dengan nomor bidang turath. Saringan `cat`, `book`, dan `page` dibaca dari
# kode situs app.turath.io (2 Nov 2026), tidak terdokumentasi, jadi bisa berubah tanpa kabar
MAZHAB = {"hanafi": 14, "maliki": 15, "syafii": 16, "hanbali": 17}


def temukan(frasa, maks=20, mazhab=(), kitab=(), halaman=1):
    """Cari frasa di ISI semua kitab Shamela lewat turath.io, termasuk yang belum diunduh: kitab mana, juz/halaman berapa.
    mazhab = kunci MAZHAB dan kitab = nomor kitab mempersempit pencarian; halaman = hasil ke-(halaman-1)*20+1 dan seterusnya.
    Hanya penunjuk jalan: layanan orang lain, tanpa janji tetap ada. Kitabnya tetap di-`ambil`, kutipannya tetap lewat `cek`."""
    _kunci(frasa)  # frasa tanpa huruf Arab ditolak di sini, bukan oleh turath
    maks = min(maks, TURATH_MAKS)
    if asing := [m for m in mazhab if m not in MAZHAB]:
        raise ValueError(f"mazhab «{asing[0]}» tidak dikenal; yang ada: {', '.join(MAZHAB)}")
    if mazhab and kitab:
        raise ValueError("pilih salah satu: --mazhab atau --kitab")
    saring = {"page": halaman}
    if mazhab:
        saring["cat"] = ",".join(str(MAZHAB[m]) for m in mazhab)
    if kitab:
        saring["book"] = ",".join(str(int(_folder(k).name)) for k in kitab)
        ada = {r["shamela_id"] for r in _meta()}
        if asing := [k for k in saring["book"].split(",") if int(k) not in ada]:
            raise ValueError(f"kitab {asing[0]} tidak ada di katalog Shamela (nomornya dari `katalog`)")
    tempat = f"kitab {saring['book']}" if kitab else f"fikih {', '.join(mazhab)}" if mazhab else "seluruh Shamela"

    def tanya(ketat):
        url = TURATH + "?" + urllib.parse.urlencode({"q": frasa, "ver": 3, "precision": 3 if ketat else 2, **saring})
        for ulang in (True, False):
            try:
                with buka(url) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                tunggu_jatah(e, ulang, "Jatah pencarian turath.io untuk komputer ini habis; terbuka lagi sekitar {menit} menit lagi. "
                                       "Sementara itu: connector `turath` (jatahnya terpisah), `katalog`, atau `cari semua`.")
    d = tanya(True)
    if not d["count"]:
        d = tanya(False)
        if d["count"]:
            print("Kata-katanya tidak ketemu berurutan; ini hasil pencarian longgar:")
    if not d["count"]:
        print(f"TIDAK KETEMU di {tempat}, berurutan maupun longgar: {frasa}\n"
              "Coba frasa lebih pendek (2-4 kata inti), atau ejaan lain.")
        return 0
    if not d["data"]:
        print(f"Halaman {halaman} melewati akhir hasil: {d['count']} tempat cocok di {tempat}, {TURATH_MAKS} tiap halaman; "
              f"halaman terakhir: --halaman {max(1, -(-d['count'] // TURATH_MAKS))}.")
        return 0
    print(f"{d['count']} tempat cocok di {tempat}: {frasa}\n" + ada_keterangan())
    ada = set(punya())
    berjilid = {r["shamela_id"] for r in _meta() if r["has_multi_part"]}  # turath menulis «ج1» juga untuk kitab satu jilid
    for x in d["data"][:maks]:
        m = json.loads(x["meta"])
        cuplikan = re.sub(r"\s+", " ", HARAKAT.sub("", html.unescape(TAGS.sub("", x["snip"]))))
        juz = m.get("vol") if x["book_id"] in berjilid else "-"
        print(f"[{x['book_id']}] {'ADA' if x['book_id'] in ada else '-'}\t{letak(juz or '-', m.get('page'))}\t"
              f"{m['book_name']} — {m['author_name']} :: {cuplikan[:160]}")
    awal = (halaman - 1) * TURATH_MAKS
    tampil = min(maks, len(d["data"]))
    lanjut = f"naikkan maks (paling banyak {TURATH_MAKS})" if tampil < len(d["data"]) else f"--halaman {halaman + 1}"
    if d["count"] > awal + tampil:
        persempit = "frasanya" if mazhab or kitab else "dengan frasa, --mazhab, atau --kitab"
        print(f"(ditampilkan {awal + 1}-{awal + tampil} dari {d['count']}; persempit {persempit}; hasil berikutnya: {lanjut})")
    return d["count"]


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
    return sorted(int(d.name) for d in ROOT.glob("*") if (d / "pages.jsonl.gz").exists())


def _folder(sid):
    """Folder kitab sid; sid yang bukan angka ditolak dengan pesan, bukan disuruh `ambil`."""
    if not str(sid).isdigit():
        raise SystemExit(f"«{sid}» bukan nomor kitab. Nomornya dari `kitab`, `katalog`, atau `temukan`.")
    return ROOT / str(int(sid))


def _belum(sid):
    """Pesan kitab yang tidak ada di kitab/: nomor yang tidak ada di katalog tidak disuruh `ambil` (`ambil` akan menolaknya)."""
    try:
        dikenal = any(r["shamela_id"] == int(sid) for r in _meta())
    except SystemExit:  # katalog/pyarrow belum ada: tidak bisa dipastikan
        dikenal = True
    if not dikenal:
        return SystemExit(f"Kitab {sid} TIDAK ADA di katalog Shamela. Nomornya dari `kitab`, `katalog`, atau `temukan`.")
    return SystemExit(f"Kitab {sid} belum diunduh: " + perintah(f"ambil {sid}"))


@functools.cache  # `cek` membacanya untuk tiap bukti
def info(sid):
    f = _folder(sid) / "book_metadata.json"
    if not f.exists():
        raise _belum(sid)
    return json.loads(f.read_text(encoding="utf8"))


def daftar():
    if not punya():
        print('Belum ada kitab yang diunduh. Cari nomornya dengan `katalog "<judul>"` atau `temukan "<frasa>"`, '
              "lalu: " + perintah("ambil <nomor>"))
    for sid in punya():
        m = info(sid)
        print(f"{sid}\t{m['title_ar']}\t{m['main_author_name_ar']}")


def kartu(sid):
    """Data cetak kitab (pengarang, muhaqqiq, penerbit, cetakan) untuk rujukan pertama dan daftar pustaka, lalu satu
    baris bentuk bukti <<…>> kitab itu (contoh_bukti). Gelar di nama muhaqqiq/penyusun dibuang (norma.buang_gelar):
    data ini disalin apa adanya ke catatan kaki dan المصادر."""
    print("\n".join(norma.buang_gelar(b) for b in info(sid)["betaka_text"].replace("\r", "\n").rstrip("\n").split("\n")))
    print(contoh_bukti(sid))


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
    print(f"{sid}: mengunduh {r['title_ar']} …", flush=True)  # kitab besar: unduh + indeks makan belasan detik
    # isi kitab disimpan terkompres (.gz) supaya hemat disk: teks Arab menyusut ±5x
    # pages.jsonl terakhir: dialah tanda "sudah ada", jadi kitab yang unduhannya putus diunduh ulang
    for f in ("book_metadata.json", "toc.jsonl", "pages.jsonl"):
        url = f"{RAW}/{urllib.parse.quote(folder[0])}/{f}"
        if f.endswith(".jsonl"):
            _unduh(url, dst / (f + ".gz"), lambda q: gzip.open(q, "wb", compresslevel=6))  # 9: 4x lebih lambat, hemat 6% saja
        else:
            _unduh(url, dst / f, lambda q: open(q, "wb"))
    mb = (dst / "pages.jsonl.gz").stat().st_size / 1e6
    print(f"{sid}: menyiapkan indeks pencarian ({mb:.1f} MB) …", flush=True)
    _cache(sid)  # sekarang, bukan saat `cari` pertama: kitab besar makan belasan detik
    print(f"{sid} OK  {r['title_ar']}  ({mb:.1f} MB)")


def _cache(sid):
    """`norma.Padat` kitab sid: teks `padat` seluruh kitab, dibaca dari berkasnya (atau dibuat sekali)."""
    return norma.cache(_folder(sid), _sidik(sid))


@functools.cache
def _sidik(sid):
    """Sidik pages.jsonl.gz kitab sid, sekali per perintah: indeks dan teks `padat` sama-sama mencocokkan diri dengannya."""
    return norma.sidik(_folder(sid) / "pages.jsonl.gz")


INDEKS = "indeks.json"  # di folder tiap kitab
INDEKS_VERSI = 2  # naikkan kalau isi indeks (lihat `indeks`) berubah cara hitungnya atau bentuknya


def _isi(sid):
    """Isi pages.jsonl.gz yang sudah dibuka (satu rekaman per baris), utuh: hanya untuk membuat indeks."""
    with gzip.open(_folder(sid) / "pages.jsonl.gz") as g:
        return g.read()


class _Lompat:
    """Isi berkas .gz yang dibaca per potongan [a, z) tanpa membuka seluruhnya ke memori. Selama dibaca maju, tiap
    ±LANGKAH byte isi dicatat titik lanjutnya (letak isi, letak di .gz, salinan keadaan zlib ±42 KB); bacaan berikutnya
    mulai dari titik terdekat sebelum a. Blok (isi antara dua titik) yang terakhir dibuka, dari kitab mana pun, disimpan
    sebentar (BLOK_MAKS).
    Berkas .gz yang anggotanya lebih dari satu (bukan buatan `ambil`) dibuka utuh sekali, seperti dulu."""
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


@functools.lru_cache(maxsize=64)
def _lompat(sid):
    return _Lompat(_folder(sid) / "pages.jsonl.gz")


def lepas():
    """Lepas semua yang dibaca dari kitab (titik baca, blok, indeks): untuk perintah yang membaca kitab satu per satu."""
    _lompat.cache_clear(); _Lompat.blok.clear(); indeks.cache_clear(); _indeks.cache_clear()


@functools.cache
def rekaman_ke(sid, i):
    """Rekaman ke-i kitab sid (urutan berkas), tanpa cache `padat`: dihitung `ruas_halaman` hanya untuk rekaman yang disentuh."""
    ix = indeks(sid)
    return json.loads(_lompat(sid).baca(ix[i][3], ix[i + 1][3] if i + 1 < len(ix) else None))


@functools.cache
def indeks(sid):
    """[(juz, page_num, halaman cetak terakhir, letak byte barisnya)] tiap rekaman, urut berkas: `cek` mengurai hanya
    rekaman halaman yang dirujuk, bukan seluruh kitab (bahts 32 kitab: ±8 detik -> ±2). Disimpan di kitab/<id>/indeks.json;
    tidak bergantung pada norm(), jadi tidak dibuat ulang saat mesin berubah. Yang rusak atau tidak cocok dengan berkasnya
    dibuat ulang."""
    return _indeks(sid)[0]


@functools.cache
def _indeks(sid):
    """(indeks, halaman cetak terkecil tiap rekaman atau None). Cocok tidaknya indeks.json dilihat dari sidik berkas .gz
    (isi .gz sama = isi kitab sama), jadi indeks yang sah terbaca tanpa membuka seluruh kitab. Indeks lama tanpa sidik
    itu dibuat ulang sekali. Di berkas, tiap kolom satu daftar (juz, hal, akhir, letak, awal), bukan satu daftar per
    rekaman: dibaca dan diperiksa per kolom, tanpa satu objek per rekaman."""
    folder = _folder(sid)
    f = folder / INDEKS
    gz = _sidik(sid)
    try:
        d = json.loads(f.read_text(encoding="utf8"))
        kolom, awal, panjang = [d["juz"], d["hal"], d["akhir"], d["letak"]], d["awal"], d["panjang"]
        letak = kolom[3]
        if (d["versi"] == INDEKS_VERSI and d["sumber_gz"] == gz and type(panjang) is int
                and all(type(x) is list and len(x) == len(awal) for x in kolom + [awal])
                and set(map(type, awal)) <= {int, type(None)} and set(map(type, letak)) <= {int}
                and (not letak or 0 <= min(letak) and max(letak) < panjang)):
            return list(zip(*kolom)), awal
    except (OSError, ValueError, KeyError, TypeError):
        pass
    mentah = _isi(sid)
    isi, awal, letak = [], [], 0
    for baris in mentah.splitlines(keepends=True):
        if baris.strip():
            r = json.loads(baris)
            nomor = [int(n) for n in PENANDA.findall(r.get("body") or "")]
            isi.append((r.get("part"), r.get("page_num"), max([r.get("page_num") or 0] + nomor), letak))
            awal.append(min([n for n in [r.get("page_num")] + nomor if n is not None], default=None))
        letak += len(baris)
    try:
        with sementara(f) as part:
            kolom = dict(zip(("juz", "hal", "akhir", "letak"), map(list, zip(*isi)))) if isi else dict.fromkeys(("juz", "hal", "akhir", "letak"), [])
            part.write_text(json.dumps({"versi": INDEKS_VERSI, "sumber": hashlib.sha256(mentah).hexdigest(), "sumber_gz": gz,
                                        "panjang": len(mentah), **kolom, "awal": awal}, ensure_ascii=False), encoding="utf8")
    except OSError:
        pass
    return isi, awal


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
        for _, b in per_halaman(p, bagian):
            for w in norm(b).split():
                w = BUKAN_ABJAD.sub("", w)
                if w:
                    awal.add(n); n += len(w); akhir.add(n)
        p[kunci] = awal, akhir
    return p[kunci]


def kata_titik_dua(p, bagian="body"):
    """[(kata `padat`, diikuti «:»)] tiap kata bagian rekaman p («قال الشافعي (¬١):» -> الشافعي diikuti «:»).
    Urutannya sama dengan `_batas_kata` kalau pemotongan katanya sama; pemakai membandingkan dulu."""
    out = []
    for _, b in per_halaman(p, bagian):
        for t in TAGS.sub(" ", b).split():
            out += [[w, False] for w in (BUKAN_ABJAD.sub("", x) for x in norm(t).split()) if w]
            if out:  # tanda tanpa huruf ikut kata sebelumnya: «(¬١):» -> «:»; «[يوسف: ٨٨] .» -> bukan «:» lagi
                out[-1][1] = bool(re.search(r":\W*$", t))
    return out


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
    teks = ruas_halaman(p, bagian)[0]
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
    teks = ruas_halaman(p, bagian)[0]
    j = teks.find(q)
    while j >= 0:
        if not utuh or _utuh(p, bagian, j, j + len(q), kata):
            yield j, j + len(q)
        j = teks.find(q, j + 1)


def _cocok(p, q, bagian="body", utuh=False, kata=()):
    """Letak (awal, akhir) pertama q di teks `padat` bagian rekaman p; None kalau tidak ada."""
    return next(_letak(p, q, bagian, utuh, kata), None)


# Garis pemisah matan dan حاشية di cetakan. Sebagian kitab Shamela menaruh حاشية المحقق di body sesudah garis ini
# (footnotes kosong): teks sesudahnya sampai halaman cetak berikutnya bukan matan.
PEMISAH_CATATAN = re.compile(r"_{5,}")


def catatan_body(t):
    """Ruas [(awal, akhir)] teks asli body t yang sebenarnya حاشية: dari garis pemisah sampai penanda halaman ⦗n⦘
    berikutnya atau akhir teks."""
    out = []
    for m in PEMISAH_CATATAN.finditer(t):
        if not out or m.start() >= out[-1][1]:
            n = PENANDA.search(t, m.end())
            out.append((m.start(), n.start() if n else len(t)))
    return out


def _catatan_padat(p):
    """`catatan_body` rekaman p dalam letak teks `padat` body-nya; dihitung sekali per rekaman."""
    if "_catatan_padat" not in p:
        t = p.get("body") or ""
        p["_catatan_padat"] = [(len(padat(t[:a])), len(padat(t[:z]))) for a, z in catatan_body(t)] if "_" in t else []
    return p["_catatan_padat"]


def _hal(p, bagian, c):
    """Halaman cetak (awal, akhir) letak c = (awal, akhir) di teks `padat` bagian rekaman p; halamannya None kalau rekaman
    itu tidak bernomor halaman."""
    batas = ruas_halaman(p, bagian)[1]
    return (next(h for a, z, h, _ in batas if a <= c[0] < z), next(h for a, z, _, h in batas if a <= c[1] - 1 < z))


def tempat(p, q, bagian="body", utuh=False, kata=(), dalam=None, catatan=None):
    """Halaman cetak (awal, akhir) tempat q (sudah `padat`) berada di rekaman p; None kalau tidak ada.
    bagian "footnotes" = حاشية, dihitung per penanda halaman seperti matan.
    utuh=True: q harus mulai dan berakhir di batas kata kitab (kutipan yang terpotong di tengah kata tidak dihitung).
    dalam=(p1, p2): q yang muncul lebih dari sekali di rekaman ini: yang di halaman p1..p2 didahulukan.
    catatan (body saja): False = hanya letak di luar `catatan_body` (matan), True = hanya yang menyentuhnya (حاشية).
    Halamannya None kalau rekaman itu tidak bernomor halaman."""
    pertama = None
    pilah = catatan is not None and bagian == "body"
    ruas = _catatan_padat(p) if pilah else []
    if pilah and catatan and not ruas:
        return None
    for c in _letak(p, q, bagian, utuh, kata):
        if pilah and catatan != any(a < c[1] and c[0] < z for a, z in ruas):
            continue
        h = _hal(p, bagian, c)
        if dalam is None or dalam[0] <= (h[0] or 0) and (h[1] or 0) <= dalam[1]:
            return h
        pertama = pertama or h
    return pertama


# awalan yang boleh menempel di depan kata pertama frasa `cari`/`teks`/`bab` selain huruf sambung `_utuh`: «ال» («عربان» →
# «العربان», «وبالعربان», «كالعربان»), dan «لل» («للعربان»)
AWALAN_KATA = re.compile(r"[وفبكل]{0,2}ال|[وف]?لل")
IBNU_SAMBUNG = re.compile(r"[وفبكل]{1,2}ا")


def _kata_utuh(p, bagian, j, k, kata):
    """Frasa `cari`/`teks`/`bab` di teks[j:k] cocok sebagai kata utuh: berakhir di akhir kata kitab, mulai di awal kata kitab
    (boleh sesudah huruf sambung seperti `_utuh` di `cek`, atau sesudah «ال»/«لل»), dan tiap kata kitab yang mulai di dalamnya
    juga mulai di awal kata frasa (kata = `kata_dalam`): «العربان» tidak cocok dengan «العرب ان». Kitab yang memisah huruf
    sambung dari katanya («و الإحياء») tetap cocok, begitu juga frasa yang memisah kata yang di kitab tersambung."""
    awal, akhir = _batas_kata(p, bagian)
    if k not in akhir:
        return False
    teks = ruas_halaman(p, bagian)[0]
    if any(x in awal and x - j not in kata and not (x - 1 in awal and teks[x - 1] in SAMBUNG) for x in range(j + 1, k)):
        return False
    if j in awal or _utuh(p, bagian, j, k):
        return True
    a = next((j - d for d in range(1, 5) if j - d in awal), None)
    if a is None:
        return False
    # «ابن» sendirian di-`norm` jadi «بن», yang bersambung tidak («لابن»): frasa «ابن …» tetap menemukan «لابن …»
    return bool(AWALAN_KATA.fullmatch(teks[a:j]) or teks.startswith("بن", j) and IBNU_SAMBUNG.fullmatch(teks[a:j]))


def _temuan(sid, frasa, potongan=False):
    """Tiap tempat frasa di kitab sid, satu per bagian rekaman: (rekaman, bagian, tanda, letak (awal, akhir) di teks `padat`,
    halaman, kata utuh?). Letaknya kecocokan kata utuh (`_kata_utuh`) pertama; tidak ada → kecocokan pertama, utuh False.
    potongan=True: kecocokan pertama apa pun (perilaku lama, untuk mencari potongan kata)."""
    q, kata = _kunci(frasa), kata_dalam(frasa)
    for p in _berisi(sid, q):
        for bagian, tanda in BAGIAN:
            semua = list(_letak(p, q, bagian))
            if not semua:
                continue
            c = next((c for c in semua if _kata_utuh(p, bagian, *c, kata)), None)
            pilih = semua[0] if potongan or c is None else c
            yield p, bagian, tanda, pilih, _hal(p, bagian, pilih), c is not None


def _potongan(sid, lain, frasa, perintah_, sebagian=False):
    """Baris jumlah tempat yang hanya cocok sebagai potongan kata (tidak dicetak tanpa --potongan).
    sebagian=True: tidak semua rekaman dipilah, jadi jumlahnya batas bawah."""
    if lain:
        print(f"[{sid}] {'paling sedikit ' if sebagian else ''}{lain} tempat lain hanya cocok sebagai potongan kata (menyeberang batas kata, mis. «العرب ان» untuk "
              f"«العربان»); tampilkan juga: " + perintah(f'{perintah_} {sid} "{frasa}" --potongan'))


CARI_SEMUA_MAKS = 40  # baris `cari semua` yang dicetak; frasa umum di ratusan kitab = ribuan baris
CARI_SEMUA_PER_KITAB = 4


def _cari_satu(sid, frasa, konteks, maks, potongan, sekilas=False):
    """Cetak paling banyak maks tempat frasa di kitab sid; kembalikan (dicetak, tempat cocok, tempat potongan kata saja,
    seluruh kitab sudah dipilah?). sekilas=True (`cari semua`): berhenti begitu maks tempat (paling sedikit satu) dicetak,
    supaya kata umum di ratusan kitab tidak memilah ribuan rekaman; hitungannya lalu belum lengkap."""
    q = _kunci(frasa)
    tampil = cocok = lain = 0
    for p, bagian, tanda, c, h, utuh in _temuan(sid, frasa, potongan):
        if not (utuh or potongan):
            lain += 1
            continue
        if sekilas and cocok and tampil >= maks:
            return tampil, cocok, lain, False
        cocok += 1
        if tampil < maks:
            tampil += 1
            t = norm(p.get(bagian) or "")  # teks norm (untuk dicetak) hanya rekaman yang cocok
            s = BUKAN_ABJAD.sub("", t)
            j = c[0] if s[c[0]:c[1]] == q else s.find(q)
            peta = [k for k, ch in enumerate(t) if "ء" <= ch <= "ي"]  # letak tiap huruf `padat` di t
            i, akhir = peta[j], peta[j + len(q) - 1] + 1
            print(f"[{sid}] {letak(_juz(p), h)}{tanda}: …{t[max(0, i - konteks): akhir + konteks]}…")
    return tampil, cocok, lain, True


def cari(sid, frasa, konteks=90, maks=15, potongan=False):
    """Cari frasa di satu kitab; sid "semua" = di semua kitab yang sudah diunduh (paling banyak CARI_SEMUA_MAKS baris,
    lalu ringkasan jumlah kitab dan tempat yang cocok). Bawaan: frasa cocok sebagai kata utuh (`_kata_utuh`); tempat yang
    hanya cocok sebagai potongan kata dihitung dan disebut jumlahnya. potongan=True: potongan kata juga dicetak.
    Kembalikan jumlah tempat yang cocok."""
    if sid == "semua":
        q = _kunci(frasa)
        tampil = kitab_n = lain_n = 0
        lengkap = True  # semua tempat yang cocok sudah dicetak
        for s in punya():
            if _cache(s).kena(q):  # saringan cepat; rekaman lain tidak dibaca
                t, c, lain, habis = _cari_satu(s, frasa, konteks, min(CARI_SEMUA_PER_KITAB, CARI_SEMUA_MAKS - tampil),
                                               potongan, sekilas=True)
                tampil, kitab_n, lain_n, lengkap = tampil + t, kitab_n + bool(c), lain_n + lain, lengkap and habis and c == t
            lepas()  # yang dibaca dari kitab yang sudah selesai tidak menumpuk
        if not kitab_n:
            print("TIDAK KETEMU di kitab mana pun" + (" sebagai kata utuh" if lain_n else "") + ":", frasa)
        elif not lengkap:
            print(f"({kitab_n} kitab cocok; ditampilkan {tampil} baris, paling banyak {CARI_SEMUA_PER_KITAB} tiap kitab. "
                  "Persempit frasanya, atau cari di satu kitab (jumlah tempatnya ikut dicetak): "
                  + perintah(f'cari <nomor> "{frasa}"') + ")")
        _potongan("semua", lain_n, frasa, "cari", sebagian=not lengkap)
        return kitab_n
    tampil, cocok, lain, _ = _cari_satu(sid, frasa, konteks, maks, potongan)
    if cocok > tampil:
        print(f"[{sid}] (ditampilkan {tampil} dari {cocok} tempat; persempit frasanya)")
    if not cocok:
        print(f"[{sid}] TIDAK KETEMU" + (" sebagai kata utuh" if lain else "") + f": {frasa}")
    _potongan(sid, lain, frasa, "cari")
    return cocok


def _letak_asli(raw, q, ke=0):
    """Awal kata tempat q (sudah `padat`) yang ke-`ke` (mulai 0) mulai di teks asli raw. Dicari lewat panjang `padat` tiap
    awalan, karena norm() mengubah panjang teks (kalimat hormat dibuang, tanda baca jadi spasi)."""
    pr, j = padat(raw), -1
    for _ in range(ke + 1):
        j = pr.find(q, j + 1)
    if j < 0:  # bacaan raw berbeda dari teks `padat` rekaman: kembali ke yang pertama
        j = pr.find(q)
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


def teks(sid, frasa, lebar=260, maks=3, potongan=False):
    """Seperti `cari`, tapi menampilkan teks ASLI (huruf apa adanya, tanpa harakat) untuk disalin persis."""
    q = _kunci(frasa)
    n = lain = 0
    for p, bagian, tanda, c, h, utuh in _temuan(sid, frasa, potongan):
        if not (utuh or potongan):
            lain += 1
            continue
        n += 1
        raw = re.sub(r"\s+", " ", HARAKAT.sub("", TAGS.sub("", p.get(bagian) or "")))
        i = _letak_asli(raw, q, sum(1 for x in _letak(p, q, bagian) if x[0] < c[0]))  # kecocokan ke berapa di rekaman ini
        print(f"[{sid}] {letak(_juz(p), h)}{tanda}: {raw[max(0, i - lebar // 3): i + lebar]}")
        if n >= maks:
            return n
    if n == 0:
        print(f"[{sid}] TIDAK KETEMU" + (" sebagai kata utuh" if lain else "") + f": {frasa}")
    _potongan(sid, lain, frasa, "teks")
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
    teks, batas = ruas_halaman(p, "body")
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


@functools.cache  # `bukti` dan `cek` membacanya untuk tiap catatan kaki
def _toc(sid):
    """(judul toc urut page_id lalu title_id, {title_id: judul}); kitab tanpa toc.jsonl.gz = kosong."""
    try:
        with gzip.open(_folder(sid) / "toc.jsonl.gz", "rt", encoding="utf8") as f:
            toc = [json.loads(x) for x in f]
    except OSError:
        toc = []
    return sorted(toc, key=lambda t: (t["page_id"], t["title_id"])), {t["title_id"]: t for t in toc}


def rantai_judul(sid, t):
    """Judul t lalu induk-induknya (tanpa harakat, spasi dirapikan), dari yang terdalam."""
    byid, r = _toc(sid)[1], []
    while t and len(r) < 50:  # toc rusak yang induknya berputar tidak membuat macet
        r.append(" ".join(HARAKAT.sub("", t["title_text"]).split())); t = byid.get(t.get("parent_id"))
    return r


def rantai_calon(sid, p, c, h, bagian):
    """Rantai judul (kitab > bab) tiap judul yang mungkin menaungi letak c (`padat`) di rekaman p: satu = pasti, lebih = ragu."""
    return [" < ".join(rantai_judul(sid, t)[:3]) or "(sebelum judul pertama)"
            for t in _judul_calon(p, _toc(sid)[0], c, h, bagian)]


def judul_naung(sid, p, c):
    """Judul toc yang menaungi letak c (dari `_cocok`, di matan) rekaman p, atau None (sebelum judul pertama, kitab
    tanpa toc, atau rekaman tanpa page_id)."""
    if not _toc(sid)[0] or p.get("page_id") is None:
        return None
    return _judul_calon(p | {"page_id": int(p["page_id"])}, _toc(sid)[0], c, None, "body")[0]


def bagian_halaman(sid, p1, p2):
    """Juz (bagian) kitab yang punya rekaman di halaman cetak p1..p2: «-» kitab satu jilid, angka jilid, atau nama
    bagian (المقدمة، الكتاب). Dipakai `cek` untuk juz «-» di kitab yang bagiannya hanya bernama; `halaman` memakai aturan
    yang sama, dari isi halamannya."""
    ix, awal = _indeks(sid)
    return {_juz({"part": j}) for (j, _, z, _), a in zip(ix, awal) if a is not None and a <= p2 and z >= p1}


def bab(sid, frasa, potongan=False):
    """Tampilkan rantai judul (kitab > bab) tempat sebuah frasa berada (kata utuh, kecuali potongan=True), plus juz/halaman."""
    _kunci(frasa)
    info(sid)  # kitab belum diunduh -> pesan yang jelas
    lain = 0
    for p, bagian, tanda, c, h, utuh in _temuan(sid, frasa, potongan):
        if not (utuh or potongan):
            lain += 1
            continue
        calon = rantai_calon(sid, p, c, h, bagian)
        kepala = f"[{sid}] {letak(_juz(p), h)}{tanda}: "
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
    print(f"{TURATH_FILES}/pdf/{urllib.parse.quote(jalur.lstrip('/'))}#page={fisik}")  # root bisa diawali «/»: «pdf//…»
    if OTOMATIS.search(str(meta.get("info", ""))):
        print("perhatian: nomor halaman kitab ini buatan Shamela (مرقم آليا), jadi halaman scan bisa meleset; "
              "cari bacaannya di halaman sekitar.")
    return True


def _rekaman_di(sid, nomor):
    """Rekaman ke-n kitab sid untuk tiap n di `nomor` (urut berkas), dibaca bergeser maju di berkas .gz: kitab tidak
    dibuka utuh ke memori dan bacaan berhenti di rekaman terakhir yang diminta (satu halaman kitab besar: ±3 detik -> ±0,5)."""
    ix, isi = indeks(sid), _lompat(sid)
    for i in sorted(nomor):
        yield json.loads(isi.baca(ix[i][3], ix[i + 1][3] if i + 1 < len(ix) else None))


def _berisi(sid, q):
    """Rekaman kitab sid yang memuat q (sudah `padat`), urut berkas, dengan cache `padat`-nya. Rekaman lain tidak diurai."""
    if not (_folder(sid) / "pages.jsonl.gz").exists():
        raise _belum(sid)
    padat_ = _cache(sid)
    kena = padat_.kena(q)
    for i, p in zip(kena, _rekaman_di(sid, kena)):
        yield padat_.isi(p, i)


def baris(teks):
    """Teks kitab untuk dicetak: pemisah baris Shamela «\\r» jadi baris baru. «\\r» mentah di konsol menimpa baris atau
    hilang saat disalin, sehingga dua kata tersambung («نستعينالحمد»)."""
    return re.sub(r"\r\n?", "\n", teks)


def halaman(sid, juz, hal):
    """Isi satu halaman cetak (juz "-" untuk kitab satu jilid), dengan حاشية milik halaman itu. «05» dan «٥» = 5."""
    angka = lambda x: int(x) if str(x).isdigit() else x  # int() membaca angka Arab ٠-٩ juga
    juz, hal = angka(juz), angka(hal)
    if not (_folder(sid) / "pages.jsonl.gz").exists():
        raise _belum(sid)
    # indeks: rekaman juz itu yang mungkin memuat halaman itu (halaman terkecil s.d. terbesar rekaman, termasuk penanda ⦗n⦘)
    ix, awal = _indeks(sid)
    # kitab yang bagiannya hanya bernama (المقدمة، الكتاب): «-» = satu-satunya bagian yang punya halaman itu (seperti `cek`)
    bernama = juz == "-" and not any(j is None or str(j).isdigit() for j, *_ in ix)
    calon = [i for i, (j, _, akhir, _) in enumerate(ix) if awal[i] is not None and awal[i] <= hal <= akhir
             and (bernama or angka("-" if j is None else j) == juz)] if isinstance(hal, int) else []
    kena = [(p, b) for p in _rekaman_di(sid, calon) if (b := [b for h, b in per_halaman(p) if h == hal])]
    if bernama and len({_juz(p) for p, _ in kena}) > 1:
        kena = []  # ada di dua bagian: sebut bagiannya
    ada = False
    for p, bagian in kena:
        if bagian:
            ada = True
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
    if not ada:
        print(f"[{sid}] TIDAK ADA halaman {juz}/{hal}. Yang ada: {daftar_juz(sid)} (juz \"-\" = kitab satu jilid)")
    return ada


def rentang_juz(sid):
    """{juz: [halaman terkecil, terbesar]} menurut rekaman kitab (urut kemunculan; juz None = "-"), dari indeks;
    rekaman tanpa nomor halaman dilewati."""
    ix, awal = _indeks(sid)
    rentang = {}
    for (j, _, z, _), a in zip(ix, awal):
        if a is not None:
            r = rentang.setdefault("-" if j is None else j, [a, z])
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
