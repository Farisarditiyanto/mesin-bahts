# SPDX-License-Identifier: AGPL-3.0-or-later
"""Klien turath.io: `temukan` (pencarian isi seluruh Shamela) dan `scan` (alamat PDF cetakan satu halaman). Penunjuk
jalan saja: layanan orang lain, tanpa janji tetap ada; `cek` dan `rakit` tidak memakainya. Dipanggil lewat bahts.py."""
import gzip, html, json, re, urllib.error, urllib.parse

import jaringan, shamela
from cocok import kunci_frasa
from dasar import angka
from norma import HARAKAT, TAGS

TURATH = "https://api.turath.io/search"  # pencarian isi seluruh Shamela; nomor kitabnya = shamela_id (sama dengan `ambil`)
TURATH_MAKS = 20  # turath menjawab sebanyak ini tiap pencarian
# nomor bidang katalog Shamela (category_id), sama dengan nomor bidang turath. Saringan `cat`, `book`, dan `page` dibaca dari
# kode situs app.turath.io, tidak terdokumentasi, jadi bisa berubah tanpa kabar
MAZHAB = {"hanafi": 14, "maliki": 15, "syafii": 16, "hanbali": 17}


def temukan(frasa, maks=20, mazhab=(), kitab=(), halaman=1):
    """Cari frasa di ISI semua kitab Shamela lewat turath.io, termasuk yang belum diunduh: kitab mana, juz/halaman berapa.
    mazhab = kunci MAZHAB dan kitab = nomor kitab mempersempit pencarian; halaman = hasil ke-(halaman-1)*20+1 dan seterusnya.
    Hanya penunjuk jalan: layanan orang lain, tanpa janji tetap ada. Kitabnya tetap di-`ambil`, kutipannya tetap lewat `cek`."""
    kunci_frasa(frasa)  # frasa tanpa huruf Arab ditolak di sini, bukan oleh turath
    maks = min(maks, TURATH_MAKS)
    if asing := [m for m in mazhab if m not in MAZHAB]:
        raise ValueError(f"mazhab «{asing[0]}» tidak dikenal; yang ada: {', '.join(MAZHAB)}")
    if mazhab and kitab:
        raise ValueError("pilih salah satu: --mazhab atau --kitab")
    saring = {"page": halaman}
    if mazhab:
        saring["cat"] = ",".join(str(MAZHAB[m]) for m in mazhab)
    if kitab:
        saring["book"] = ",".join(str(shamela.nomor_kitab(k)) for k in kitab)
        ada = {r["shamela_id"] for r in shamela.isi_katalog()}
        if asing := [k for k in saring["book"].split(",") if int(k) not in ada]:
            raise ValueError(f"kitab {asing[0]} tidak ada di katalog Shamela (nomornya dari `katalog`)")
    tempat = f"kitab {saring['book']}" if kitab else f"fikih {', '.join(mazhab)}" if mazhab else "seluruh Shamela"

    def tanya(ketat):
        url = TURATH + "?" + urllib.parse.urlencode({"q": frasa, "ver": 3, "precision": 3 if ketat else 2, **saring})
        with jaringan.buka_berjatah("Jatah pencarian turath.io untuk komputer ini habis; terbuka lagi sekitar {menit} menit lagi. "
                                    "Sementara itu: connector `turath` (jatahnya terpisah), `katalog`, atau `cari semua`.", url) as r:
            return json.load(r)
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
    print(f"{d['count']} tempat cocok di {tempat}: {frasa}\n" + shamela.ada_keterangan())
    ada = set(shamela.punya())
    berjilid = {r["shamela_id"] for r in shamela.isi_katalog() if r["has_multi_part"]}  # turath menulis «ج1» juga untuk kitab satu jilid
    for x in d["data"][:maks]:
        m = json.loads(x["meta"])
        cuplikan = re.sub(r"\s+", " ", HARAKAT.sub("", html.unescape(TAGS.sub("", x["snip"]))))
        juz = m.get("vol") if x["book_id"] in berjilid else "-"
        print(f"[{x['book_id']}] {'ADA' if x['book_id'] in ada else '-'}\t{shamela.letak(juz or '-', m.get('page'))}\t"
              f"{m['book_name']} — {m['author_name']} :: {cuplikan[:160]}")
    awal = (halaman - 1) * TURATH_MAKS
    tampil = min(maks, len(d["data"]))
    lanjut = f"naikkan maks (paling banyak {TURATH_MAKS})" if tampil < len(d["data"]) else f"--halaman {halaman + 1}"
    if d["count"] > awal + tampil:
        persempit = "frasanya" if mazhab or kitab else "dengan frasa, --mazhab, atau --kitab"
        print(f"(ditampilkan {awal + 1}-{awal + tampil} dari {d['count']}; persempit {persempit}; hasil berikutnya: {lanjut})")
    return d["count"]


# Scan cetakan di turath.io: berkas data tiap kitab dan PDF-nya. Dibaca dari kode situs app.turath.io, tidak
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
        with jaringan.buka(f"{TURATH_FILES}/books-v3/{int(sid)}.json", waktu=30) as r:
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
    shamela.nomor_kitab(sid)  # nomor yang bukan angka ditolak dengan pesan yang sama dengan perintah kitab lain
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
    if shamela.OTOMATIS.search(str(meta.get("info", ""))):
        print("perhatian: nomor halaman kitab ini buatan Shamela (مرقم آليا), jadi halaman scan bisa meleset; "
              "cari bacaannya di halaman sekitar.")
    return True
