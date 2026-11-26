# SPDX-License-Identifier: AGPL-3.0-or-later
"""الدراسات السابقة: cari penelitian terdahulu (jurnal, risalah kampus) di katalog OpenAlex dan DOAJ.
Gratis, butuh internet. Dipanggil lewat bahts.py.

OpenAlex ditanya dua kali: menurut kata (judul, ringkasan, kata kunci) dan menurut makna (menemukan penelitian
yang kata-katanya lain tetapi bahasannya sama; pertanyaan panjang boleh). DOAJ = jurnal akses terbuka.

Kunci OpenAlex (gratis: daftar di https://openalex.org, salin dari Settings > API key) disimpan sebagai satu baris
di kunci_openalex.txt, di samping folder mesin/; berkas itu tidak ada → dibaca dari variabel lingkungan OPENALEX_API_KEY
(untuk komputer yang tidak menyimpan berkas, mis. cloud). Tanpa kunci: jatah sehari sekitar 50 kali `dirasat`, dan `dirasat-pdf`
hanya bisa memakai tautan PDF akses terbuka (salinan yang disimpan OpenAlex butuh kunci). Dengan kunci: sekitar 300 kali `dirasat` atau 100 PDF sehari; jatah kembali penuh tiap 00.00 UTC.
"""
import datetime, functools, json, logging, os, re, time, unicodedata, urllib.error, urllib.parse
from pathlib import Path

import norma
from berkas import sementara
from dasar import ANGKA_LATIN, ARAH, TandaRusak, akhir_catatan, akhir_rumus, perintah
from jaringan import GAGAL_JARINGAN, JAWABAN_ASING, SEBAB_ASING, buka

KUNCI = Path(__file__).parent.parent / "kunci_openalex.txt"
KUNCI_ENV = "OPENALEX_API_KEY"
AKHIR_PDF = 1024  # bita terakhir PDF utuh yang harus memuat %%EOF
OPENALEX = "https://api.openalex.org/works"
PDF = "https://content.openalex.org/works/{}.pdf"  # salinan PDF yang disimpan OpenAlex
KOLOM = ("id,title,publication_year,publication_date,type,language,cited_by_count,biblio,authorships,"
         "primary_location,best_oa_location,doi,has_content,abstract_inverted_index,is_retracted")
CROSSREF = "https://api.crossref.org/works/"
DOI_HANDLE = "https://doi.org/api/handles/"
NASAB = frozenset("بن ابن بنت ابو ابي ابا ام عبد".split())
RUJUK_ULANG = re.compile(r"(?:المرجع|المصدر)\s+(?:السابق|نفسه)")
MAKNA_MAKS = 50  # OpenAlex menjawab pencarian makna paling banyak sebanyak ini
KATA_POOL_MAKS = 200  # OpenAlex per_page maksimum untuk kolam perankingan ulang (--urut)
DOAJ_POOL_MAKS = 100  # DOAJ pageSize maksimum
RINGKASAN_MAKS = 400  # huruf ringkasan yang dicetak tiap penelitian di daftar hasil
DOAJ = "https://doaj.org/api/search/articles/"
WAKTU_CARI, WAKTU_PDF = 45, 120  # detik menunggu jawaban; pencarian yang macet tidak boleh membuat pemakai menunggu lama
URUT = ("terbaru", "terlama", "dikutip")
OA_ID = re.compile(r"^(?:https?://(?:api\.)?openalex\.org/(?:works/)?)?(W\d+)/?$", re.I)
DOI_POLA = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)(10\.\d{4,}/\S+)$|^(10\.\d{4,}/\S+)$", re.I)


class Ditolak(OSError):
    """Layanan menjawab, tetapi menolak; isinya kalimat untuk pemakai."""


class SaringanSalah(Ditolak):
    """OpenAlex menolak saringannya (nama atau isinya salah)."""


CARA_KUNCI = f"kunci gratis: daftar di https://openalex.org, salin dari Settings > API key, simpan sebagai satu baris di {KUNCI.name}"


def _kunci():
    if KUNCI.exists():
        return KUNCI.read_text(encoding="utf-8-sig").strip()
    return os.environ.get(KUNCI_ENV, "").strip()


def _buka(url, waktu=WAKTU_CARI):
    """Buka alamat (kunci OpenAlex ikut hanya ke openalex.org); penolakan OpenAlex yang dikenal dijadikan kalimat."""
    kepala = {"User-Agent": "bahts/1 (+https://github.com/Farisarditiyanto/mesin-bahts)"}
    openalex = (urllib.parse.urlsplit(url).hostname or "").endswith(".openalex.org")
    if openalex and _kunci():
        kepala["Authorization"] = "Bearer " + _kunci()
    for sisa_coba in (1, 0):
        try:
            return buka(url, kepala=kepala, waktu=waktu)  # galat sementara dicoba lagi di sana
        except urllib.error.HTTPError as e:
            if not openalex:
                raise
            pesan = e.read().decode("utf8", "replace")
            # mesin pencari makna OpenAlex kadang kewalahan dan menjawabnya sebagai 400: tunggu, coba lagi
            if sisa_coba and "Failed to embed" in pesan:
                time.sleep(3)
                continue
            if e.code == 504 and "query_timeout" in pesan:  # diulang pun sama; tidak memotong jatah
                raise Ditolak("pencarian ini kehabisan waktu di OpenAlex (tidak memotong jatah); hasil sumber lain tetap berlaku. "
                              "Kalau ini pencarian makna: tulis masalahnya sebagai kalimat yang lebih khusus")
            if e.code == 401:
                raise Ditolak(f"kunci di {KUNCI.name} (atau {KUNCI_ENV}) ditolak atau belum ada; {CARA_KUNCI}")
            if e.code == 429:
                raise Ditolak("jatah hari ini habis (kembali penuh 00.00 UTC). " + ("" if _kunci() else
                              f"Kunci menaikkannya 10 kali; {CARA_KUNCI}"))
            if "Failed to embed" in pesan:
                raise Ditolak("mesin pencari makna OpenAlex sedang sibuk: ulangi sebentar lagi")
            if e.code == 400:
                try:
                    pesan = json.loads(pesan)["message"]
                except (ValueError, KeyError, TypeError):
                    pass
                salah = SaringanSalah if "filter=" in url and re.search("filter|field", pesan, re.I) else Ditolak
                raise salah(f"OpenAlex menolak permintaan ini: {pesan[:300]}")
            raise


def _doi(d):
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d or "").lower()


def id_karya(teks):
    """Kenali pengenal tunggal (nomor OpenAlex W…/URL, atau DOI/URL) -> (selector OpenAlex, label singkat), atau None."""
    s = (teks or "").strip()
    if m := OA_ID.fullmatch(s):
        nomor = m.group(1).upper()
        return nomor, nomor
    if m := DOI_POLA.fullmatch(s):
        doi = re.split(r"[?#]", m.group(1) or m.group(2), maxsplit=1)[0].rstrip(".,;/")
        while doi.endswith(")") and doi.count(")") > doi.count("("):
            doi = doi[:-1]
        if re.fullmatch(r"10\.\d{4,}/\S+", doi):
            return f"doi:{doi}", doi.lower()
    return None


def _tanggal_batas(nilai, akhir=False):
    """Validasi batas tanggal --dari/--sampai: YYYY atau YYYY-MM-DD -> YYYY-MM-DD."""
    s = (nilai or "").strip()
    if not s:
        return ""
    if re.fullmatch(r"\d{4}", s):
        s = f"{s}-{'12-31' if akhir else '01-01'}"
    try:
        return datetime.date.fromisoformat(s).isoformat()
    except ValueError:
        raise ValueError(f"tanggal «{nilai}» tidak sah: tulis tahun (mis. 2020) atau YYYY-MM-DD (mis. 2020-01-01)") from None


def _kunci_judul(w):
    """Judul (huruf Arab lewat norma, huruf Latin tanpa diakritik) + tahun: penelitian yang sama dari sumber lain yang
    tidak memuat DOI-nya. Tahun ikut supaya dua penelitian berjudul sama («مقدمة», «Editorial») tidak saling membuang."""
    judul = ARAH.sub("", w.get("judul") or "")
    latin = re.sub(r"[^a-z0-9]+", " ", _huruf_latin(judul)).strip()
    k = " ".join(x for x in (norma.norm(judul), latin) if x)
    return f"{k}|{str(w.get('tahun') or '')[:4]}" if len(k) >= 8 else ""


def _format_biblio(vol, isu, hal_awal, hal_akhir):
    """Susun jilid, nomor, dan halaman jurnal («مج 12، ع 3، ص 45-70») bila tercatat (halaman «0» = tidak tercatat)."""
    hal_awal, hal_akhir = (h if str(h or "").strip("0 ") else "" for h in (hal_awal, hal_akhir))
    bagian = []
    if vol:
        bagian.append(f"مج {vol}")
    if isu:
        bagian.append(f"ع {isu}")
    if hal_awal and hal_akhir and str(hal_awal) != str(hal_akhir):
        bagian.append(f"ص {hal_awal}-{hal_akhir}")
    elif hal_awal or hal_akhir:
        bagian.append(f"ص {hal_awal or hal_akhir}")
    return "، ".join(bagian)


def _tgl_int(w):
    """Tanggal publikasi jadi bilangan YYYYMMDD (0 = tidak bertanggal) agar karya tanpa tanggal selalu urut terakhir."""
    t = str(w.get("tanggal") or w.get("tahun") or "").strip()
    m = re.match(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?", t)
    if not m:
        return 0
    return int(m[1]) * 10000 + int(m[2] or 0) * 100 + int(m[3] or 0)


def _urutkan(hasil, urut):
    """Ranking ulang kolam hasil yang sudah relevan menurut urutan pilihan (terbaru/terlama/dikutip).
    Karya tanpa tanggal selalu ditaruh di akhir untuk terbaru/terlama."""
    if urut == "terbaru":
        hasil.sort(key=lambda w: (0, -_tgl_int(w)) if _tgl_int(w) else (1, 0))
    elif urut == "terlama":
        hasil.sort(key=lambda w: (0, _tgl_int(w)) if _tgl_int(w) else (1, 0))
    elif urut == "dikutip":
        hasil.sort(key=lambda w: -(w.get("dikutip") or 0))


def _uraikan_openalex(w):
    asal = w.get("primary_location") or {}
    oa = w.get("best_oa_location") or {}
    bib = w.get("biblio") or {}
    # OpenAlex menyimpan ringkasan sebagai {kata: [posisi]}: susun lagi jadi kalimat
    idx = w.get("abstract_inverted_index") or {}
    return {
        "judul": w.get("title"), "peneliti": [a["author"]["display_name"] for a in w.get("authorships") or [] if a.get("author")],
        "tahun": w.get("publication_year"), "tanggal": w.get("publication_date") or "", "jenis": w.get("type"),
        "wadah": (asal.get("source") or {}).get("display_name"),
        "biblio": _format_biblio(bib.get("volume"), bib.get("issue"), bib.get("first_page"), bib.get("last_page")),
        "bahasa": w.get("language"), "dikutip": w.get("cited_by_count"),
        "doi": _doi(w.get("doi")), "tautan": w.get("doi") or asal.get("landing_page_url"),
        "pdf": oa.get("pdf_url") or asal.get("pdf_url"),
        "pdf_calon": [u for u in dict.fromkeys((oa.get("pdf_url"), asal.get("pdf_url"))) if u],
        "nomor": w["id"].rsplit("/", 1)[-1] if w.get("id") else "",
        "tersimpan": bool((w.get("has_content") or {}).get("pdf")),
        "dicabut": bool(w.get("is_retracted")),
        "peringatan": [],
        "ringkasan": " ".join(k for _, k in sorted((p, k) for k, v in idx.items() for p in v)),
    }


def _saringan_openalex(saringan, dari, sampai, bahasa, *, makna=False):
    bagian = [x.strip() for x in (saringan or "").split(",") if x.strip()]
    if makna:
        # OpenAlex search.semantic menolak from/to_publication_date; hanya publication_year yang didukung
        if dari and sampai:
            bagian.append(f"publication_year:{dari[:4]}-{sampai[:4]}")
        elif dari:
            bagian.append(f"publication_year:>{int(dari[:4]) - 1}")
        elif sampai:
            bagian.append(f"publication_year:<{int(sampai[:4]) + 1}")
    else:
        if dari:
            bagian.append(f"from_publication_date:{dari}")
        if sampai:
            bagian.append(f"to_publication_date:{sampai}")
    if bahasa:
        bagian.append(f"language:{bahasa.lower()}")
    return ",".join(bagian)


def _masuk_rentang(w, dari, sampai):
    t = str(w.get("tanggal") or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
        return (not dari or t >= dari) and (not sampai or t <= sampai)
    thn = w.get("tahun")
    try:
        tahun = int(str(thn).strip())
    except (TypeError, ValueError):
        return not (dari or sampai)
    return (not dari or tahun >= int(dari[:4])) and (not sampai or tahun <= int(sampai[:4]))


def _openalex(cara, kata, maks, saringan, dari="", sampai="", bahasa="", urut=""):
    """(jumlah yang cocok, [penelitian], sisa jatah USD) dari OpenAlex; cara = nama parameter pencariannya."""
    makna = cara == "search.semantic"
    batas_pool = MAKNA_MAKS if makna else KATA_POOL_MAKS
    # Urut ulang dilakukan pada kolam relevan yang lebih lebar, bukan menyortir seluruh korpus agar topik tetap tajam
    pool = min(batas_pool, max(50, maks * 4) if (urut or (makna and (dari or sampai))) else maks)
    # corpus=all: ikut mencari di kumpulan tambahan OpenAlex, tempat banyak risalah kampus berada
    p = {cara: kata, "per_page": pool, "select": KOLOM, "corpus": "all"}
    gabung = _saringan_openalex(saringan, dari, sampai, bahasa, makna=makna)
    if gabung:
        p["filter"] = gabung
    if cara == "search" and _kunci():
        p["rerank"] = "true"  # urutan diperbaiki OpenAlex menurut kecocokan isi; tanpa kunci jatahnya terlalu kecil
    with _buka(OPENALEX + "?" + urllib.parse.urlencode(p)) as r:
        d, sisa = json.load(r), r.headers.get("X-RateLimit-Remaining-USD")
    hasil = [_uraikan_openalex(w) for w in d["results"]]
    jumlah = d["meta"]["count"]
    if makna and (dari or sampai):
        asal_n = len(hasil)
        hasil = [w for w in hasil if _masuk_rentang(w, dari, sampai)]
        if len(hasil) < asal_n:
            jumlah = len(hasil)
    if urut:
        _urutkan(hasil, urut)
    return jumlah, hasil[:maks], sisa


def _kata(kata, maks, saringan, dari="", sampai="", bahasa="", urut=""):
    return _openalex("search", kata, maks, saringan, dari, sampai, bahasa, urut)


def _makna(kata, maks, saringan, dari="", sampai="", bahasa="", urut=""):
    time.sleep(1)  # OpenAlex: pencarian makna paling cepat satu kali per detik
    return _openalex("search.semantic", kata, min(maks, MAKNA_MAKS), saringan, dari, sampai, bahasa, urut)


def _doaj(kata, maks, saringan, dari="", sampai="", bahasa="", urut=""):
    """Jurnal akses terbuka, banyak jurnal kampus Arab. --dari/--sampai/--bahasa/--urut diterapkan lokal pada kolam DOAJ."""
    saring_lokal = bool(dari or sampai or bahasa or urut)
    pool = min(DOAJ_POOL_MAKS, max(30, maks * 3)) if saring_lokal else maks
    with _buka(f"{DOAJ}{urllib.parse.quote(kata, safe='')}?pageSize={pool}") as r:
        d = json.load(r)
    thn_dari = int(dari[:4]) if dari else None
    thn_sampai = int(sampai[:4]) if sampai else None
    bhs = bahasa.lower() if bahasa else ""
    hasil = []
    for w in d.get("results", []):
        b = w["bibjson"]
        j = b.get("journal") or {}
        tahun = b.get("year")
        try:
            thn = int(str(tahun)[:4]) if tahun else None
        except ValueError:
            thn = None
        if thn_dari is not None and (thn is None or thn < thn_dari):
            continue
        if thn_sampai is not None and (thn is None or thn > thn_sampai):
            continue
        bahasa_j = [x.lower() for x in (j.get("language") or []) if isinstance(x, str)]
        if bhs and bhs not in bahasa_j:
            continue
        doi = _doi(next((i["id"] for i in b.get("identifier", []) if i.get("type") == "doi" and i.get("id")), ""))
        taut = [t["url"] for t in b.get("link", []) if t.get("url")]
        hasil.append({
            "judul": b.get("title"), "peneliti": [a["name"] for a in b.get("author", []) if a.get("name")],
            "tahun": tahun, "tanggal": str(tahun or ""), "jenis": "article", "wadah": j.get("title"),
            "biblio": _format_biblio(j.get("volume"), j.get("number"), b.get("start_page"), b.get("end_page")),
            "bahasa": bahasa_j[0] if bahasa_j else None,
            "doi": doi, "tautan": ("https://doi.org/" + doi) if doi else (taut[0] if taut else None),
            "pdf": next((t for t in taut if t.lower().endswith(".pdf")), None), "ringkasan": b.get("abstract") or ""})
    if urut in ("terbaru", "terlama"):  # DOAJ tidak memuat jumlah sitasi, jadi --urut dikutip menjaga urutan relevansi
        _urutkan(hasil, urut)
    # Saat disaring lokal (--dari/--sampai/--bahasa), kembalikan jumlah yang benar-benar lolos saringan agar tidak
    # melaporkan total mentah DOAJ atau mematikan peringatan MAKNA_SAJA ketika hasil menurut kata sebenarnya 0.
    jumlah = len(hasil) if (dari or sampai or bahasa) else d.get("total", 0)
    return jumlah, hasil[:maks], None


# urutan cetak; True = menurut makna: selalu mengembalikan sesuatu, juga untuk kata yang tidak ada di penelitian mana pun
SUMBER = (("OpenAlex, menurut kata", _kata, False), ("OpenAlex, menurut makna", _makna, True), ("DOAJ", _doaj, False))
MAKNA_SAJA = ("hanya MIRIP MAKNANYA, karena kata kuncinya tidak ditemukan menurut kata: bisa sama sekali tidak relevan. "
              "Baca judul dan ringkasannya dulu; jangan dipakai sebagai الدراسات السابقة hanya karena muncul di sini")
# jawaban yang bukan JSON (halaman perawatan, halaman masuk wifi) atau JSON berbentuk lain
JAWABAN_RUSAK = (ValueError, KeyError, TypeError, AttributeError)


def _cetak_karya(w, nomor_urut=None, penuh=False):
    kepala = f"[{nomor_urut}] " if nomor_urut is not None else ""
    tanda = " [PERINGATAN: DICABUT / RETRACTED]" if w.get("dicabut") else ""
    if w.get("peringatan"):
        tanda += f" [PERINGATAN: {'; '.join(w['peringatan'])}]"
    print(f"\n{kepala}{ARAH.sub('', w['judul'] or '')}{tanda}")
    wadah = w["wadah"] or "-"
    if w.get("biblio"):
        wadah = f"{wadah} ({w['biblio']})"
    waktu = w.get("tanggal") or w.get("tahun") or "-"
    rinci = [f"{apa} {w[k]}" for k, apa in (("bahasa", "bahasa"), ("dikutip", "dikutip")) if w.get(k)]
    print(f"    {'، '.join(w['peneliti']) or '(peneliti tidak tercatat)'} | {waktu if penuh else w['tahun']} | "
          f"{w['jenis']} | " + " | ".join([wadah] + rinci))
    print(f"    {w['tautan'] or '-'}" + (f" | PDF: {w['pdf']}" if w["pdf"] else ""))
    if w.get("nomor"):
        unduh = (": " + perintah(f"dirasat-pdf {w['nomor']} <folder>") if (_kunci() or w.get("pdf")) else
                 " (mengunduhnya butuh kunci OpenAlex, caranya di bawah)")
        label = "PDF tersimpan" if w.get("tersimpan") else ("PDF akses terbuka" if w.get("pdf") else "")
        print(f"    OpenAlex {w['nomor']}" + (f" | {label}{unduh}" if label else ""))
    teks = ARAH.sub("", re.sub(r"\s+", " ", w["ringkasan"])).strip()
    if teks:
        print(f"    ملخص: {teks if penuh else teks[:RINGKASAN_MAKS]}")


def _baca_karya(selector):
    """Ambil metadata satu karya dari OpenAlex menurut W… atau doi:…; None kalau 404."""
    url = f"{OPENALEX}/{urllib.parse.quote(selector, safe=':/')}?select={KOLOM}"
    try:
        with _buka(url) as r:
            return _uraikan_openalex(json.load(r))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def info(pengenal):
    """Tampilkan rincian lengkap (penulis, jurnal, jilid/nomor/halaman, tautan, dan ringkasan utuh) satu penelitian."""
    sel = id_karya(pengenal)
    if not sel:
        raise ValueError(f"«{pengenal}» bukan nomor OpenAlex (W…) atau DOI (10.…/…)")
    try:
        w = _baca_karya(sel[0])
    except Ditolak as e:
        raise SystemExit(f"Karya {sel[1]} gagal dibaca: {e}")
    except JAWABAN_RUSAK as e:
        raise SystemExit(f"Karya {sel[1]} gagal dibaca: jawabannya {JAWABAN_ASING} ({SEBAB_ASING}): {type(e).__name__} {e}")
    if w is None:
        raise SystemExit(f"Penelitian «{sel[1]}» tidak ditemukan di OpenAlex.")
    _cetak_karya(w, penuh=True)
    if w.get("tersimpan") and not _kunci():
        print(f"\nTanpa kunci OpenAlex: PDF tersimpan tidak bisa diunduh; {CARA_KUNCI}")


def cari(kata, maks=10, saringan="", *, dari="", sampai="", bahasa="", urut=""):
    """Judul, peneliti, tahun, jenis, jurnal/kampus (berikut jilid/nomor/halaman), tautan, dan ringkasan tiap
    penelitian yang cocok, dari tiap sumber. Bila `kata` adalah nomor OpenAlex (W…) atau DOI tanpa saringan pencarian,
    dicetak rincian lengkap dan ringkasan utuhnya."""
    if not kata.strip() or not 1 <= maks <= 100:
        raise ValueError('bentuknya: dirasat "<kata kunci|W…|DOI>" [maks 1-100] [saringan] [--dari t] [--sampai t] [--bahasa b] [--urut terbaru|terlama|dikutip]')
    if bahasa and not re.fullmatch(r"[A-Za-z]{2}", bahasa):
        raise ValueError(f"--bahasa «{bahasa}» bukan kode bahasa dua huruf (mis. ar, en, id); satu bahasa sekali cari")
    if urut and urut not in URUT:
        raise ValueError(f"--urut «{urut}» tidak dikenal: pilih salah satu dari {', '.join(URUT)}")
    dari = _tanggal_batas(dari, akhir=False)
    sampai = _tanggal_batas(sampai, akhir=True)
    if dari and sampai and dari > sampai:
        raise ValueError(f"rentang tanggal terbalik: --dari {dari} lebih baru daripada --sampai {sampai}")
    if id_karya(kata) and not (saringan or dari or sampai or bahasa or urut):
        return info(kata)
    n, sudah, gagal, rusak, saringan_ditolak, sisa, perlu_kunci = 0, set(), 0, 0, 0, None, False
    judul_tercetak = {}  # kunci judul -> (DOI, nomor W…) penelitian yang sudah tercetak ("" = tidak ada)
    menurut_kata, dari_makna = 0, 0  # jumlah cocok menurut kata; hasil tercetak dari pencarian makna
    opsi = (dari, sampai, bahasa, urut)
    for nama, ambil, makna in SUMBER:
        print(f"\n{nama}: ", end="", flush=True)  # tanda masih bekerja selama menunggu jawaban
        try:
            jumlah, hasil, jatah = ambil(kata, maks, saringan, *opsi)
        except OSError as e:  # satu sumber mati tidak menghentikan sumber lain
            print(f"GAGAL — {e}")
            gagal += 1
            saringan_ditolak += isinstance(e, SaringanSalah)
            if saringan_ditolak == 2:  # kedua pencarian OpenAlex menolaknya: yang salah saringannya, bukan layanannya
                raise ValueError(f"saringan «{saringan}» ditolak OpenAlex (alasannya di atas). "
                                 "Contoh yang sah: language:ar, type:dissertation, publication_year:>2014")
            continue
        except JAWABAN_RUSAK as e:
            print(f"GAGAL — jawabannya {JAWABAN_ASING} ({SEBAB_ASING}): {type(e).__name__} {e}")
            gagal += 1
            rusak += 1
            continue
        sisa = jatah or sisa
        baru = []
        for w in hasil:
            pengenal, judul = {w.get("doi"), w.get("nomor")} - {"", None}, _kunci_judul(w)
            # judul sama hanya membuang kalau pengenalnya tidak bertentangan: dua DOI atau dua nomor W… berbeda =
            # dua penelitian (mis. dua risalah kampus berjudul umum)
            lain = judul_tercetak.get(judul)
            if pengenal & sudah or (lain and not any(a and b for a, b in zip(lain, (w.get("doi"), w.get("nomor"))))):
                continue
            sudah |= pengenal
            if judul:
                judul_tercetak.setdefault(judul, (w.get("doi") or "", w.get("nomor") or ""))
            baru.append(w)
        print(f"{jumlah} penelitian cocok" + (f", {len(hasil) - len(baru)} sudah tercetak di atas" if len(baru) < len(hasil) else ""))
        if makna and baru and not menurut_kata:
            print("PERINGATAN: hasil di bawah ini " + MAKNA_SAJA)
        menurut_kata += 0 if makna else jumlah
        dari_makna += len(baru) if makna else 0
        if saringan and ambil is _doaj:
            print("(saringan mentah OpenAlex tidak berlaku di DOAJ: gunakan --dari/--sampai/--bahasa agar DOAJ ikut tersaring)")
        for w in baru:
            n += 1
            if w.get("nomor"):
                perlu_kunci |= w.get("tersimpan", False) and not _kunci()
            _cetak_karya(w, nomor_urut=n, penuh=False)
    if gagal == len(SUMBER):  # internet putus → bahts.py menyuruh cek internet; layanan rusak → cukup alasan di atas
        raise (SystemExit if rusak else ConnectionError)("semua sumber penelitian gagal (alasannya di atas)")
    if sisa:
        print(f"\nSisa jatah OpenAlex hari ini: ${float(sisa):.2f}")
    if (sisa or perlu_kunci) and not _kunci():
        print(f"Tanpa kunci OpenAlex: jatahnya kecil dan PDF tersimpan tidak bisa diunduh; {CARA_KUNCI}")
    if dari_makna and not menurut_kata:
        print("\nPERINGATAN: semua hasil di atas " + MAKNA_SAJA)
    if not n:
        print("Coba kata kunci lebih pendek (2-3 kata inti), longgarkan batas tanggal/bahasa, atau buang saringannya.")


def _pdf_terbaca(berkas):
    """Validasi minimum sebelum menamai hasil .pdf; bukan pemeriksaan ilmiah isinya."""
    from pypdf import PdfReader
    try:
        # pypdf bisa membaca revisi lama dari berkas yang terpotong: akhir berkas harus ikut diperiksa
        with open(berkas, "rb") as f:
            f.seek(-min(AKHIR_PDF, f.seek(0, os.SEEK_END)), os.SEEK_END)
            if b"%%EOF" not in f.read():
                return False
        return bool(len(PdfReader(berkas).pages))
    except Exception:  # noqa: BLE001 — format rusak/bersandi tidak boleh dianggap unduhan yang selesai
        return False


def _simpan_pdf(isi, tujuan, nomor, asal=""):
    if not isi.startswith(b"%PDF"):
        raise ValueError(f"Jawaban untuk {nomor} bukan PDF.")
    # Nama .pdf hanya terbit sesudah penulisan dan pembacaan berhasil; keluar dengan galat membuat `sementara` membuang
    # berkas .part dan tidak pernah menimpa tujuan dengan unduhan terpotong.
    with sementara(tujuan) as part:
        part.write_bytes(isi)
        if not _pdf_terbaca(part):
            raise ValueError(f"PDF {nomor} tidak utuh atau tidak bisa dibaca; ulangi unduhan.")
    ket = f" (dari {asal})" if asal else ""
    print(f"Jadi: {tujuan} ({len(isi) / 1e6:.1f} MB){ket}")


def pdf(nomor, folder):
    """Unduh salinan PDF sebuah penelitian (nomor OpenAlex W… atau DOI) ke folder bahts, supaya isinya bisa dibaca:
    salinan OpenAlex kalau tersimpan (butuh kunci), lalu tautan PDF akses terbuka karya itu."""
    sel = id_karya(nomor)
    if not sel:
        raise ValueError(f"«{nomor}» bukan nomor OpenAlex (W123…) atau DOI (10.…/…)")
    def metadata():  # satu karya; tidak butuh kunci
        try:
            w = _baca_karya(sel[0])
        except Ditolak as e:
            raise SystemExit(f"PDF {sel[1]} tidak terunduh: {e}")
        except JAWABAN_RUSAK as e:
            raise SystemExit(f"PDF {sel[1]} tidak terunduh: jawaban OpenAlex {JAWABAN_ASING} ({SEBAB_ASING}): {e}")
        if w is None or not w["nomor"]:
            raise SystemExit(f"Penelitian «{sel[1]}» tidak ditemukan di OpenAlex.")
        return w

    # DOI baru diketahui nomor W…-nya dari metadata; nomor W… langsung: PDF yang sudah ada tidak butuh internet
    meta = metadata() if sel[0].startswith("doi:") else None
    nomor = meta["nomor"] if meta else sel[0]
    tujuan = Path(folder) / f"{nomor}.pdf"
    if tujuan.exists():
        if _pdf_terbaca(tujuan):
            print(f"Sudah ada: {tujuan}")
            return
        print(f"PDF lama tidak bisa dibaca; mengunduh ulang: {tujuan}")
    meta = meta or metadata()
    tempat, sebab = [], []  # sebab = tiap tempat yang gagal dan alasannya, untuk pemakai
    if not meta["tersimpan"]:
        sebab.append("OpenAlex tidak menyimpan salinannya")
    elif _kunci():
        tempat.append(("salinan OpenAlex", PDF.format(nomor)))
    else:
        sebab.append(f"salinan OpenAlex butuh kunci; {CARA_KUNCI}")
    tempat += [("tautan akses terbuka", u) for u in meta["pdf_calon"]]
    for nama, url in tempat:
        try:
            with _buka(url, WAKTU_PDF) as r:
                _simpan_pdf(r.read(), tujuan, nomor, asal=f"{nama} {url}")
            return
        except (*GAGAL_JARINGAN, OSError, ValueError) as e:  # ditolak, HTTP 4xx/5xx, koneksi, bukan PDF, tidak utuh: tempat berikutnya
            sebab.append(f"{nama} {url}: {e}")
    if not meta["pdf_calon"]:
        sebab.append("OpenAlex tidak mencatat tautan PDF akses terbuka")
    raise SystemExit(f"PDF {nomor} tidak terunduh:\n  - " + "\n  - ".join(sebab)
                     + f"\nBuka tautan aslinya di peramban, lalu simpan PDF-nya di folder bahts: {meta['tautan'] or '-'}")


_EPOCH_HIJRIAH = 1948439  # Julian Day Number 1 Muharram 1 H (kalender Hijriah tabular)
# Pengenal ilmiah di dalam teks naskah (catatan kaki, الدراسات السابقة, #R, bukti <<luar|W….pdf|…>>)
DOI_DI_TEKS = re.compile(r"(?:https?://(?:dx\.)?doi\.org/|doi\s*[:：]\s*)?(10\.\d{4,}/[^\s\]<>«»\"'،؛]+)", re.I)
# URL OpenAlex selalu sah; nama berkas <<luar|W….pdf|…>> hanya dianggap ID OpenAlex bila berhuruf besar W + ≥6 digit
# (ID OpenAlex nyata 9-10 digit) agar PDF lokal seperti `w1.pdf` tidak pernah dianggap ID OpenAlex.
OA_URL_DI_TEKS = re.compile(r"https?://(?:api\.)?openalex\.org/(?:works/)?(W\d+)", re.I)
OA_PDF_DI_TEKS = re.compile(r"<<luar\|(W\d{6,})\.pdf\|")
KEPALA_TERBIT = re.compile(r"\b(?:vol(?:ume)?|issue|no\.|published|journal|copyright)\b|©|المجلد|العدد|مجلة|نشر|السنة", re.I)
TERIMA_NASKAH = re.compile(r"\b(?:received|accepted|submitted|revised)\b|استلام|قبول", re.I)
PDF_LUAR_DI_TEKS = re.compile(r"<<luar\|([^|<>]+\.pdf)\|", re.I)
WAFAT_DI_TEKS = re.compile(r"\(?\s*(?:المتوفى|ت)\s*[:：]?\s*\d{3,4}\s*(?:هـ|ه|م)?\s*\)?")
TAHUN_DI_TEKS = re.compile(r"(?<!\d)(1[3-4]\d\d|19\d\d|20\d\d)(?!\d)(?:\s*(هـ|ه|م|AH|CE))?", re.I)
KATA_ABAI_LATIN = frozenset("the and for with from into this that study analysis research journal article review".split())
JUDUL_RINGKAS = 4  # rujukan ringkas boleh memotong judul pokok; paling sedikit kata sebanyak ini (atau seluruhnya)
TANDA_SEBARIS = re.compile(r"\{[QHNMAP]:[^{}]*\}")


def _buang_tanda_rumus(teks):
    teks = TANDA_SEBARIS.sub(" ", teks)
    out, i = [], 0
    while (j := teks.find("{E:", i)) >= 0:
        out.append(teks[i:j])
        out.append(" ")
        try:
            i = akhir_rumus(teks, j + 3) + 1
        except TandaRusak:
            return "".join(out)
    return "".join(out) + teks[i:]


def _awal_hijriah_jdn(h):
    return (h - 1) * 354 + (3 + 11 * h) // 30 + _EPOCH_HIJRIAH


def _jdn_ke_masehi(jdn):
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - 146097 * b // 4
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    return 100 * b + d - 4800 + m // 10


def tahun_masehi_hijriah(h):
    """Himpunan tahun Masehi (1-2 tahun) yang disentuh tahun Hijriah `h` (kalender tabular)."""
    awal = _jdn_ke_masehi(_awal_hijriah_jdn(h))
    akhir = _jdn_ke_masehi(_awal_hijriah_jdn(h + 1) - 1)
    return set(range(awal, akhir + 1))


def _bersih_doi(raw):
    d = re.split(r"[?#]", raw.strip(), maxsplit=1)[0].rstrip(".,;:/")
    d = urllib.parse.unquote(d)
    while d.endswith(")") and d.count(")") > d.count("("):
        d = d[:-1].rstrip(".,;:/")
    return d.lower() if re.fullmatch(r"10\.\d{4,}/\S+", d) else ""


def _tanggal_crossref(obj):
    bagian = (obj or {}).get("date-parts") or []
    if bagian and bagian[0]:
        angka = [x for x in bagian[0] if isinstance(x, int)]
        if angka:
            return tuple((angka + [0, 0, 0])[:3])
    ts = (obj or {}).get("timestamp")
    if isinstance(ts, (int, float)):
        d = datetime.datetime.fromtimestamp(ts / 1000, datetime.UTC)
        return (d.year, d.month, d.day)
    return (0, 0, 0)


def _uraikan_crossref(msg, doi=""):
    tahun = None
    for kunci in ("published-print", "published-online", "issued", "created"):
        bagian = (msg.get(kunci) or {}).get("date-parts") or []
        if bagian and bagian[0] and isinstance(bagian[0][0], int):
            tahun = bagian[0][0]
            break
    updated_by = msg.get("updated-by") or ()
    status_cabut, peringatan = [], []
    for i, u in enumerate(updated_by):
        jenis = (u.get("type") or "").lower().replace("_", "-")
        if jenis in ("retraction", "reinstatement"):
            status_cabut.append((_tanggal_crossref(u.get("updated")), i, jenis))
        elif jenis in ("expression-of-concern", "withdrawal"):
            peringatan.append(f"Crossref: {jenis}")
    for u in msg.get("update-to") or ():
        jenis = (u.get("type") or "").lower().replace("_", "-")
        if jenis in ("retraction", "expression-of-concern", "withdrawal"):
            peringatan.append(f"pemberitahuan {jenis} untuk {u.get('DOI') or '-'}")
    if status_cabut:
        status_cabut.sort()
        dicabut = status_cabut[-1][2] == "retraction"
    else:
        dicabut = bool((msg.get("relation") or {}).get("is-retracted-by"))
    peringatan = list(dict.fromkeys(peringatan))
    doi_fix = _doi(msg.get("DOI") or doi)
    return {
        "judul": (msg.get("title") or [""])[0],
        "peneliti": [f"{a.get('given', '')} {a.get('family', '')}".strip()
                     for a in msg.get("author") or [] if a.get("family") or a.get("given")],
        "tahun": tahun, "tanggal": str(tahun or ""), "jenis": msg.get("type") or "",
        "wadah": (msg.get("container-title") or [""])[0], "biblio": "", "bahasa": None, "dikutip": None,
        "doi": doi_fix, "tautan": ("https://doi.org/" + doi_fix) if doi_fix else "",
        "pdf": None, "pdf_calon": [], "nomor": "", "tersimpan": False, "dicabut": dicabut,
        "peringatan": peringatan, "ringkasan": "",
    }


def _baca_crossref(doi):
    url = CROSSREF + urllib.parse.quote(doi, safe="")
    try:
        with _buka(url) as r:
            msg = json.load(r)["message"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return _uraikan_crossref(msg, doi)


def _kata_latin(teks):
    return [w for w in re.findall(r"[a-z]{4,}", _huruf_latin(teks)) if w not in KATA_ABAI_LATIN]


def _huruf_latin(teks):
    return "".join(c for c in unicodedata.normalize("NFKD", teks or "").lower() if not unicodedata.combining(c))


def _kata_nama(nama):
    """{tulisan: kata terakhir} nama peneliti katalog = nama keluarga atau nisbahnya («Seng Chun Hoo» → hoo,
    «فهد مطلق العتيبي» → العتيبي). Nama depan tidak dihitung: «فهد» atau «Aderonke» bukan bukti penelitinya."""
    out = {}
    for tulisan, kata in (("latin", re.findall(r"[a-z]{3,}", _huruf_latin(nama))),
                          ("arab", [k for k in norma.norm(nama or "").split() if len(k) > 2 and k not in NASAB])):
        if kata:
            out[tulisan] = {kata[-1]}
    return out


def _kata_nama_teks(teks):
    """{tulisan: semua kata} di `teks`, dalam bentuk yang sama dengan `_kata_nama`."""
    return {"latin": set(re.findall(r"[a-z]{3,}", _huruf_latin(teks))), "arab": set(norma.norm(teks).split())}


@functools.cache
def _tahun_berkas(berkas):
    """Tahun Masehi di baris kepala terbitan (jurnal, jilid, nomor, tanggal terbit, hak cipta) dua halaman pertama satu
    PDF. Tahun di kalimat isi («As of December 2017») dan tanggal terima naskah bukan tahun terbit."""
    from pypdf import PdfReader
    logging.getLogger("pypdf").setLevel(logging.ERROR)  # keluhan pypdf soal PDF cacat bukan isi laporan
    try:
        isi = " ".join(p.extract_text() or "" for p in PdfReader(berkas).pages[:2])
    except Exception:  # noqa: BLE001 — PDF hilang, rusak, atau bersandi: tahunnya tidak bisa dibaca, katalog tetap dibandingkan
        return frozenset()
    return frozenset(int(t) for baris in isi.translate(ANGKA_LATIN).splitlines() if KEPALA_TERBIT.search(baris)
                     and not TERIMA_NASKAH.search(baris) for t in re.findall(r"(?<!\d)(19\d\d|20\d\d)(?!\d)", baris))


def _tahun_pdf(folder, teks):
    """Tahun Masehi yang tercetak di PDF `<<luar|berkas.pdf|…>>` yang disebut `teks`."""
    return frozenset().union(*(_tahun_berkas(str(Path(folder) / nama))
                               for nama in dict.fromkeys(PDF_LUAR_DI_TEKS.findall(teks))))


def _banding_rujukan(konteks, w, ringkas=False, tercetak=frozenset):
    """Bandingkan petunjuk tiap bidang pada satu baris. Teks bebas dan terjemahan bisa tidak memuat judul katalog.
    `ringkas` = rujukan kedua dan seterusnya: cukup judul pokok (sebelum «:») atau awal judulnya, tanpa sub-judul.
    `tercetak()` = tahun yang tercetak di PDF penelitian itu (dibaca hanya kalau tahunnya beda): tahun naskah yang
    sama dengan cetakannya tidak dinilai salah walau katalog menulis tahun lain sampai dua tahun (terbit daring dan
    nomor cetak sering beda)."""
    polos = _buang_tanda_rumus(ARAH.sub("", konteks)).translate(ANGKA_LATIN)
    # Buang DOI/URL agar angka tahun di dalam string DOI (mis. 10.1234/2020.01) tidak dibaca sebagai tahun terbit.
    tanpa_url = re.sub(r"https?://\S+|10\.\d{4,}/\S+|<<[^<>]+>>", " ", polos)
    beda, belum = [], []
    tahun_rec = w.get("tahun")
    if isinstance(tahun_rec, int):
        tanpa_wafat = WAFAT_DI_TEKS.sub(" ", tanpa_url)
        tahun_ada = []
        for angka, tanda in TAHUN_DI_TEKS.findall(tanpa_wafat):
            v = int(angka)
            t = (tanda or "").lower()
            hijri = t in ("هـ", "ه", "ah") or (not t and 1300 <= v <= 1499)
            if hijri and 1300 <= v <= 1500:
                tahun_ada.append((v, "هـ", tahun_masehi_hijriah(v)))
            elif not hijri and 1900 <= v <= 2100:
                tahun_ada.append((v, "م", {v}))
        # Selisih lebih dari dua tahun bukan beda terbit daring dan cetak; tahun lain di halaman PDF (tanggal terima,
        # daftar pustaka) tidak boleh menutupinya.
        dekat = [masehi for _, _, masehi in tahun_ada if any(abs(t - tahun_rec) <= 2 for t in masehi)]
        if tahun_ada and not any(tahun_rec in masehi for _, _, masehi in tahun_ada) and not any(
                masehi & tercetak() for masehi in dekat):
            tertulis = "، ".join(f"{v}{t}" for v, t, _ in tahun_ada[:3])
            beda.append(f"tahun di naskah ({tertulis}) ≠ katalog ({tahun_rec})")
    if ringkas and RUJUK_ULANG.search(tanpa_url):
        return beda, belum
    def arab(teks):
        return [k for k in norma.norm(teks).split() if not k.isdecimal()]

    def ada(kata, konteks):
        return bool(kata) and f" {' '.join(kata)} " in f" {' '.join(konteks)} "

    judul = w.get("judul") or ""
    pasangan = [(urai(judul), urai(tanpa_url), urai(judul.split(":")[0])) for urai in (arab, _kata_latin)]
    judul_cocok = any(
        ada(kata, konteks) or ringkas and len(pokok) >= 2 and ada(pokok[:JUDUL_RINGKAS], konteks)
        for kata, konteks, pokok in pasangan
    )
    if any(kata and len(konteks) >= 2 for kata, konteks, _ in pasangan) and not judul_cocok:
        belum.append("judul katalog belum terkonfirmasi di baris ini")
    # Nama dibandingkan dalam tulisan yang sama: nama Latin di baris berhuruf Arab saja tidak bisa dinilai, termasuk
    # baris #R Arab yang hanya menyertakan judul Inggris di dalam kurung (bukan nama peneliti Latin).
    kata_baris = _kata_nama_teks(tanpa_url)
    judul_kata = _kata_nama_teks(judul)
    sisa_baris = {tulisan: kata_baris[tulisan] - (judul_kata[tulisan] if judul_cocok else set()) for tulisan in kata_baris}
    nama = [(kata, kata_baris[tulisan]) for v in w.get("peneliti") or [] for tulisan, kata in _kata_nama(v).items()
            if len(kata_baris[tulisan]) >= 2 and (tulisan == "arab" or len(sisa_baris[tulisan]) >= 2 or not kata_baris["arab"])]
    if nama and not any(kata & ada_di for kata, ada_di in nama):
        belum.append("nama peneliti katalog belum terkonfirmasi di baris ini")
    return beda, belum


def _registrasi_doi(doi):
    """Status registrasi dari resolver DOI. Galat jaringan/format diteruskan sebagai pemeriksaan yang belum selesai."""
    url = DOI_HANDLE + urllib.parse.quote(doi, safe="")
    try:
        with _buka(url) as jawaban:
            status = json.load(jawaban)["responseCode"]
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        with e:
            status = json.load(e)["responseCode"]
    if status not in (1, 100):
        raise ValueError(f"resolver DOI mengembalikan status {status}")
    return status == 1


def _rekaman_rujukan(sel):
    if w := _baca_karya(sel):
        return w, "OpenAlex", True
    if not sel.startswith("doi:"):
        return None, "OpenAlex", False
    doi = sel[4:]
    if w := _baca_crossref(doi):
        return w, "Crossref", True
    return None, "doi.org", _registrasi_doi(doi)


def _alias_katalog(w):
    alias = {w["nomor"]} if w["nomor"] else set()
    if w["doi"]:
        alias.add(f"doi:{w['doi']}")
    return alias


def _hasil_rujukan(entri):
    """Satu permintaan per identitas yang ditemukan. OpenAlex mengembalikan padanan W… dan DOI."""
    hasil = {}
    for sel in entri:
        if sel in hasil:
            continue
        try:
            w, sumber, terdaftar = hasil[sel] = _rekaman_rujukan(sel)
        except (Ditolak, OSError, *JAWABAN_RUSAK) as e:
            hasil[sel] = str(e)
            continue
        if w:
            for a in _alias_katalog(w):
                if a in entri:
                    hasil.setdefault(a, (w, sumber, terdaftar))
    return hasil


def _pengenal(teks):
    """DOI dan nomor OpenAlex (W…) di `teks`, urut kemunculan."""
    ids = dict.fromkeys(f"doi:{doi}" for m in DOI_DI_TEKS.finditer(teks) if (doi := _bersih_doi(m[1])))
    for pola in (OA_URL_DI_TEKS, OA_PDF_DI_TEKS):
        ids.update(dict.fromkeys(m[1].upper() for m in pola.finditer(teks)))
    return list(ids)


def _kata_catatan(teks):
    """Kata bermakna di dalam potongan catatan kaki (di luar bukti, URL/DOI, «انظر», dan nomor halaman) untuk
    membedakan catatan kaki yang menyebut sumber sendiri dari catatan kaki polos («انظر: ص2. <<luar|…>>»)."""
    bersih = re.sub(r"https?://\S+|10\.\d{4,}/\S+|<<[^<>]+>>", " ", teks)
    bersih = re.sub(r"\b(?:doi|pp?|vol|no)\b|انظر|ينظر|راجع|(?<![ء-ي])ص(?![ء-ي])", " ", bersih, flags=re.I)
    return re.findall(r"[A-Za-z]{3,}|[ء-ي]{2,}", norma.norm(bersih) + " " + _huruf_latin(bersih))


def _potong_catatan(isi_fn, sel):
    """Bila satu catatan kaki menyebut beberapa sumber dipisah «؛», ambil potongan yang memuat `sel` saja."""
    potong = [p for p in isi_fn.split("؛") if sel in _pengenal(p)]
    return "؛ ".join(potong) if potong else isi_fn


def _konteks_pengenal(baris, ids):
    """{pengenal: (teks, pengenal di teks itu)}: isolasi catatan kaki agar tahun kejadian di matan dan catatan kaki
    kitab lain tidak bocor ke penilaian penelitian ini. Bila pengenal hanya di catatan kaki dan catatan kaki itu sudah
    menyebut sumbernya (bukan catatan kaki polos seperti «[^انظر: ص2 <<…>>]»), nilai potongan catatan kaki itu saja."""
    catatan, i = [], 0
    while (awal := baris.find("[^", i)) >= 0:
        try:
            i = akhir_catatan(baris, awal + 2) + 1
        except TandaRusak:
            break
        isi_fn = baris[awal + 2:i - 1]
        catatan.append((awal, i, isi_fn, set(_pengenal(isi_fn))))
    matan = baris
    for awal, akhir, _, _ in reversed(catatan):
        matan = matan[:awal] + " " + matan[akhir:]
    id_matan = set(_pengenal(matan))
    out = {}
    for sel in ids:
        fn_cocok = [_potong_catatan(isi_fn, sel) for _, _, isi_fn, s in catatan if sel in s]
        gabung_fn = " ".join(fn_cocok)
        if sel not in id_matan and fn_cocok and (RUJUK_ULANG.search(gabung_fn) or len(_kata_catatan(gabung_fn)) >= 2):
            teks = gabung_fn
        else:
            teks = baris
            for awal, akhir, isi_fn, s in reversed(catatan):
                if sel not in s:
                    teks = teks[:awal] + " " + teks[akhir:]
                elif len(s) > 1:
                    teks = teks[:awal] + "[^" + _potong_catatan(isi_fn, sel) + "]" + teks[akhir:]
        out[sel] = (teks, _pengenal(teks))
    return out


def cek_rujukan(folder):
    """Verifikasi online DOI dan nomor OpenAlex (W…) di `naskah.txt` (OpenAlex + Crossref + doi.org):
    mendeteksi DOI tidak terdaftar, karya dicabut, dan petunjuk metadata per baris.
    Kode keluar: 1 untuk ID tidak ditemukan/karya dicabut, 2 kalau layanan atau metadata perlu diperiksa, 0 lainnya."""
    naskah = Path(folder) / "naskah.txt"
    if not naskah.exists():
        raise SystemExit(f"Naskah tidak ditemukan: {naskah}")
    entri, baris_naskah = {}, {}
    for n, baris in enumerate(naskah.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not baris.strip() or baris.lstrip().startswith("@"):
            continue
        baris = baris.translate(ANGKA_LATIN)
        if ids := _pengenal(baris):
            baris_naskah[n] = _konteks_pengenal(baris, ids)
            for sel in ids:
                entri.setdefault(sel, []).append(n)
    if not entri:
        print(f"Tidak ada DOI atau nomor OpenAlex (W…) di {naskah.name}.")
        return 0
    fatal, perlu, lengkap, galat = 0, 0, 0, 0
    hasil = _hasil_rujukan(entri)
    sudah_multi, sudah_alias = set(), set()
    for sel, kemunculan in entri.items():
        label = sel.removeprefix("doi:")
        baris_str = ", ".join(map(str, kemunculan))
        jawaban = hasil[sel]
        if isinstance(jawaban, str):
            galat += 1
            print(f"  ? baris {baris_str} [{label}]: GAGAL MEMERIKSA ({jawaban})")
            continue
        w, sumber, terdaftar = jawaban
        if not terdaftar:
            fatal += 1
            print(f"  ✗ baris {baris_str} [{label}]: TIDAK DITEMUKAN di {sumber}")
            continue
        if w is None:
            perlu += 1
            print(f"  ! baris {baris_str} [{label}]: DOI TERDAFTAR di {sumber}; metadata belum ada di OpenAlex/Crossref")
            continue
        judul = ARAH.sub("", w.get("judul") or "-")
        penulis = "، ".join((w.get("peneliti") or [])[:3]) or "-"
        ringkas = f"«{judul[:80]}» ({penulis}, {w.get('tahun') or '-'}) [{sumber}]"
        if w.get("dicabut"):
            fatal += 1
            print(f"  ✗ baris {baris_str} [{label}]: DICABUT (RETRACTED) — {ringkas}")
            continue
        lengkap += 1
        print(f"  • baris {baris_str} [{label}]: ID DITEMUKAN — {ringkas}")
        if w.get("peringatan"):
            perlu += 1
            print(f"    ! baris {baris_str}: PERINGATAN CROSSREF ({'; '.join(w['peringatan'])})")
        for n in kemunculan:
            teks, ids = baris_naskah[n][sel]
            if len(ids) > 1:
                if _alias_katalog(w).issuperset(ids):
                    k_alias = (n, w.get("doi") or w.get("nomor") or sel)
                    if k_alias in sudah_alias:
                        continue
                    sudah_alias.add(k_alias)
                else:
                    if n not in sudah_multi:
                        sudah_multi.add(n)
                        perlu += 1
                        print(f"    ! baris {n}: beberapa pengenal di baris ini; periksa metadata masing-masing")
                    continue
            # Rujukan pertama memuat data lengkap; berikutnya boleh ringkas (nama keluarga + judul pokok).
            beda, belum = _banding_rujukan(teks, w, ringkas=n != kemunculan[0], tercetak=lambda: _tahun_pdf(folder, teks))
            if beda or belum:
                perlu += 1
                status = "TIDAK COCOK" if beda else "PERIKSA METADATA"
                print(f"    ! baris {n}: {status} ({'; '.join(beda + belum)})")
    print(f"\nRingkasan dirasat-cek ({len(entri)} pengenal): {lengkap} rekaman, {perlu} perlu dicek, "
          f"{fatal} fatal (tidak ditemukan/dicabut), {galat} gagal memeriksa.")
    return 1 if fatal else 2 if perlu or galat else 0
