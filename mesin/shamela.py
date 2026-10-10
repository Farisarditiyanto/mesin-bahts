"""Perpustakaan Shamela lokal: unduh kitab per-judul dari dataset Hugging Face
AuthenticIlm/Shamela4_Full_DB ke folder kitab/, lalu cari kutipan secara offline
(tanpa kredit, tanpa internet). Hanya `temukan` yang bertanya ke luar (turath.io). Dipanggil lewat bahts.py.
"""
import gzip, html, json, re, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent / "kitab"
REPO = "AuthenticIlm/Shamela4_Full_DB"
API = f"https://huggingface.co/api/datasets/{REPO}/tree/main"
RAW = f"https://huggingface.co/datasets/{REPO}/resolve/main"
UA = {"User-Agent": "curl/8"}

HARAKAT = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
TAGS = re.compile(r"<[^>]+>")
HORMAT = re.compile(
    r"صل[يى] الله عليه وسلم|رض[يى] الله عنه(?:ما|م|ا)?|عليه(?:ما)? السلام|رحمه الله|عز وجل|قدس الله روحه")


BUKAN_HURUF = re.compile(r"[^ء-ي0-9]+")
BUKAN_ABJAD = re.compile(r"[^ء-ي]+")


def norm(s):
    """Samakan tulisan Arab: buang harakat/tatwil dan kalimat hormat, satukan bentuk alif/ya/ta marbuthah."""
    s = HORMAT.sub("", HARAKAT.sub("", TAGS.sub("", s)))
    for dari, ke in (("إ", "ا"), ("أ", "ا"), ("آ", "ا"), ("ٱ", "ا"), ("شئ", "شيء"), ("ى", "ي"), ("ة", "ه"), ("ؤ", "و"), ("ئ", "ي")):
        s = s.replace(dari, ke)  # str.replace jauh lebih cepat daripada regex untuk ganti satu huruf
    return BUKAN_HURUF.sub(" ", s).strip()


def _ls(path=""):
    url = API + ("/" + urllib.parse.quote(path) if path else "")
    out = []
    while url:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA))
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
    """Unduh ke <tujuan>.part, baru dinamai <tujuan> kalau utuh: unduhan yang putus tidak pernah dianggap jadi."""
    part = tujuan.with_name(tujuan.name + ".part")
    n = 0
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as resp, buka(part) as o:
        while chunk := resp.read(1 << 20):
            o.write(chunk); n += len(chunk)
        janji = resp.headers.get("Content-Length")
    if janji and int(janji) != n:
        raise ConnectionError(f"unduhan terpotong: {n} dari {janji} byte ({tujuan.name})")
    part.replace(tujuan)


def _meta():
    if not (ROOT / KATALOG).exists():
        raise SystemExit("Katalog kitab belum ada: python mesin/bahts.py siapkan")
    try:
        import pandas as pd
    except ImportError:
        raise SystemExit("Pustaka Python belum terpasang: pip install -r requirements.txt")
    return pd.read_parquet(ROOT / KATALOG)


def katalog(pat):
    """Cari kitab di katalog Shamela (judul atau nama pengarang)."""
    df = _meta()
    hit = df[df["title_ar"].str.contains(pat, regex=True, na=False)
             | df["main_author_name_ar"].str.contains(pat, regex=True, na=False)]
    for _, r in hit.iterrows():
        ada = "ADA" if (ROOT / str(r.shamela_id) / "pages.jsonl.gz").exists() else "-"
        print(f"{r.shamela_id}\t{ada}\t{r.title_ar}\t{r.main_author_name_ar}\t{r.category_name_ar}")


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
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
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
        print("Kata-katanya tidak ketemu berurutan; ini hasil pencarian longgar:")
    print(f"{d['count']} tempat cocok di seluruh Shamela: {frasa}")
    ada = set(punya())
    df = _meta()
    berjilid = set(df[df["has_multi_part"] == True]["shamela_id"])  # turath menulis «ج1» juga untuk kitab satu jilid
    for x in d["data"][:maks]:
        m = json.loads(x["meta"])
        cuplikan = re.sub(r"\s+", " ", HARAKAT.sub("", html.unescape(TAGS.sub("", x["snip"]))))
        juz = m.get("vol") if x["book_id"] in berjilid else "-"
        print(f"[{x['book_id']}] {'ADA' if x['book_id'] in ada else '-'}\tج{juz or '-'} ص{m.get('page')}\t"
              f"{m['book_name']} — {m['author_name']} :: {cuplikan[:160]}")
    if d["count"] > maks:
        print(f"(ditampilkan {min(maks, len(d['data']))}, paling banyak {TURATH_MAKS}; persempit frasanya untuk hasil lain)")
    if not d["count"]:
        print("Coba frasa lebih pendek (2-4 kata inti), atau ejaan lain.")


def punya():
    """shamela_id semua kitab yang sudah diunduh."""
    return sorted(int(d.name) for d in ROOT.glob("*") if (d / "pages.jsonl.gz").exists())


def info(sid):
    f = ROOT / str(sid) / "book_metadata.json"
    if not f.exists():
        raise SystemExit(f"Kitab {sid} belum diunduh: python mesin/bahts.py ambil {sid}")
    return json.load(open(f, encoding="utf8"))


def daftar():
    for sid in punya():
        m = info(sid)
        print(f"{sid}\t{m['title_ar']}\t{m['main_author_name_ar']}")


def kartu(sid):
    """Data cetak kitab (pengarang, muhaqqiq, penerbit, cetakan) untuk rujukan pertama dan daftar pustaka."""
    print(info(sid)["betaka_text"].replace("\r", "\n"))


def ambil(sid):
    if not str(sid).isdigit():
        print(sid, "bukan nomor kitab (nomornya dari `katalog` atau `temukan`)"); return
    sid = int(sid)
    dst = ROOT / str(sid)
    if (dst / "pages.jsonl.gz").exists():
        print(sid, "sudah ada"); return
    df = _meta()
    row = df[df.shamela_id == sid]
    if row.empty:
        print(sid, "TIDAK ADA di katalog"); return
    r = row.iloc[0]
    top = [x["path"] for x in _ls() if x["path"].startswith(f"{int(r.category_id):02d}__")][0]
    folder = [x["path"] for x in _ls(top) if x["path"].split("/")[-1].split("__")[0] == str(r.book_id)]
    if not folder:
        print(sid, "folder tidak ketemu"); return
    dst.mkdir(parents=True, exist_ok=True)
    # isi kitab disimpan terkompres (.gz) supaya hemat disk: teks Arab menyusut ±5x
    # pages.jsonl terakhir: dialah tanda "sudah ada", jadi kitab yang unduhannya putus diunduh ulang
    for f in ("book_metadata.json", "toc.jsonl", "pages.jsonl"):
        url = f"{RAW}/{urllib.parse.quote(folder[0])}/{f}"
        if f.endswith(".jsonl"):
            _unduh(url, dst / (f + ".gz"), lambda q: gzip.open(q, "wb"))
        else:
            _unduh(url, dst / f, lambda q: open(q, "wb"))
    mb = (dst / "pages.jsonl.gz").stat().st_size / 1e6
    print(f"{sid} OK  {r.title_ar}  ({mb:.1f} MB)")


PENANDA = re.compile(r"⦗([٠-٩]+)⦘")


def _pages(sid):
    f = ROOT / str(sid) / "pages.jsonl.gz"
    if not f.exists():
        raise SystemExit(f"Kitab {sid} belum diunduh: python mesin/bahts.py ambil {sid}")
    with gzip.open(f, "rt", encoding="utf8") as g:
        for line in g:
            yield json.loads(line)


def _juz(p):
    return "-" if p.get("part") is None else p["part"]


def _potong(p):
    """Satu rekaman bisa memuat beberapa halaman cetak (penanda ⦗n⦘): pecah jadi [(halaman, teks)]."""
    hal, out = p.get("page_num"), []
    for k, b in enumerate(PENANDA.split(p.get("body") or "")):
        if k % 2:
            hal = int(b)  # int() membaca angka Arab ٠-٩ juga
        else:
            out.append((hal, b))
    return out


def padat(s):
    """Huruf Arab saja, tanpa spasi dan angka: bentuk yang dicocokkan `cari`, `teks`, `bab`, dan `cek`.
    Spasi diabaikan supaya «و "الإحياء"» tetap ketemu dengan «والإحياء»."""
    return BUKAN_ABJAD.sub("", norm(s))


def _kunci(frasa):
    q = padat(frasa)
    if not q:
        raise SystemExit("Frasa pencarian harus berhuruf Arab.")
    return q


def tempat(p, q):
    """Halaman cetak (awal, akhir) tempat q (sudah `padat`) berada di badan rekaman p; None kalau tidak ada."""
    if "_padat" not in p:  # dinormalkan sekali saja per rekaman
        teks, batas = "", []
        for hal, b in _potong(p):
            n = padat(b)
            batas.append((len(teks), len(teks) + len(n), hal or 0))
            teks += n
        p["_padat"] = teks, batas
    teks, batas = p["_padat"]
    j = teks.find(q)
    if j < 0:
        return None
    k = j + len(q) - 1
    return (next(h for a, z, h in batas if a <= j < z or a == z == j), next(h for a, z, h in batas if a <= k < z))


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
        for bagian in ("body", "footnotes"):
            t = norm(p.get(bagian) or "")
            j = BUKAN_ABJAD.sub("", t).find(q)
            if j >= 0:
                peta = [k for k, c in enumerate(t) if "ء" <= c <= "ي"]  # letak tiap huruf `padat` di t
                n += 1
                i, akhir = peta[j], peta[j + len(q) - 1] + 1
                hal, tanda = (tempat(p, q)[0], "") if bagian == "body" else (p.get("page_num"), " [حاشية]")
                print(f"[{sid}] ج{_juz(p)} ص{hal}{tanda}: …{t[max(0, i - konteks): akhir + konteks]}…")
                if n >= maks:
                    print(f"[{sid}] (dipotong, masih ada lagi)"); return n
    if n == 0 and not diam:
        print(f"[{sid}] TIDAK KETEMU: {frasa}")
    return n


def teks(sid, frasa, lebar=260, maks=3):
    """Seperti `cari`, tapi menampilkan teks ASLI (huruf apa adanya, tanpa harakat) untuk disalin persis."""
    q = _kunci(frasa)
    n = 0
    for p in _pages(sid):
        hal = (tempat(p, q) or [None])[0]
        if hal is not None:
            n += 1
            raw = re.sub(r"\s+", " ", HARAKAT.sub("", TAGS.sub("", p.get("body") or "")))
            # posisi kasar di teks asli lewat kata pertama frasa
            kata = HARAKAT.sub("", frasa).split()[0]
            i = max(raw.find(kata), 0)
            for m in re.finditer(re.escape(kata), raw):
                if q[:12] in padat(raw[m.start(): m.start() + 200]):
                    i = m.start(); break
            print(f"[{sid}] ج{_juz(p)} ص{hal}: {raw[max(0, i - lebar // 3): i + lebar]}")
            if n >= maks: return
    if n == 0:
        print(f"[{sid}] TIDAK KETEMU: {frasa}")


def bab(sid, frasa):
    """Tampilkan rantai judul (kitab > bab) tempat sebuah frasa berada, plus juz/halaman."""
    q = _kunci(frasa)
    info(sid)  # kitab belum diunduh -> pesan yang jelas
    with gzip.open(ROOT / str(sid) / "toc.jsonl.gz", "rt", encoding="utf8") as f:
        toc = [json.loads(x) for x in f]
    byid = {t["title_id"]: t for t in toc}
    toc.sort(key=lambda t: (t["page_id"], t["title_id"]))
    for p in _pages(sid):
        hal = (tempat(p, q) or [None])[0]
        if hal is not None:
            last = None
            for t in toc:
                if t["page_id"] <= p["page_id"]: last = t
                else: break
            rantai = []
            while last:
                rantai.append(HARAKAT.sub("", last["title_text"]).strip()); last = byid.get(last.get("parent_id"))
            print(f"[{sid}] ج{_juz(p)} ص{hal}: " + " < ".join(rantai[:3]))
            return
    print(f"[{sid}] TIDAK KETEMU: {frasa}")


def halaman(sid, juz, hal):
    """Isi satu halaman cetak (juz "-" untuk kitab satu jilid)."""
    ada = False
    for p in _pages(sid):
        if str(_juz(p)) != str(juz):
            continue
        bagian = [b for h, b in _potong(p) if str(h) == str(hal)]
        if bagian:
            ada = True
            print(TAGS.sub("", "".join(bagian)))
            if p.get("footnotes"):
                print("ـــــ\n" + TAGS.sub("", p["footnotes"]))
    if not ada:
        print(f"[{sid}] TIDAK ADA halaman {juz}/{hal}")
