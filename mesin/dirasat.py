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
import datetime, json, os, re, time, unicodedata, urllib.error, urllib.parse
from pathlib import Path

import norma
from jaringan import GAGAL_JARINGAN, JAWABAN_ASING, SEBAB_ASING, buka
from dasar import perintah
from berkas import sementara

KUNCI = Path(__file__).parent.parent / "kunci_openalex.txt"
KUNCI_ENV = "OPENALEX_API_KEY"
AKHIR_PDF = 1024  # bita terakhir PDF utuh yang harus memuat %%EOF
OPENALEX = "https://api.openalex.org/works"
PDF = "https://content.openalex.org/works/{}.pdf"  # salinan PDF yang disimpan OpenAlex
KOLOM = ("id,title,publication_year,publication_date,type,language,cited_by_count,biblio,authorships,"
         "primary_location,best_oa_location,doi,has_content,abstract_inverted_index")
MAKNA_MAKS = 50  # OpenAlex menjawab pencarian makna paling banyak sebanyak ini
KATA_POOL_MAKS = 200  # OpenAlex per_page maksimum untuk kolam perankingan ulang (--urut)
DOAJ_POOL_MAKS = 100  # DOAJ pageSize maksimum
RINGKASAN_MAKS = 400  # huruf ringkasan yang dicetak tiap penelitian di daftar hasil
DOAJ = "https://doaj.org/api/search/articles/"
WAKTU_CARI, WAKTU_PDF = 45, 120  # detik menunggu jawaban; pencarian yang macet tidak boleh membuat pemakai menunggu lama
ARAH = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069]")  # tanda arah tulisan yang ikut tersalin dari PDF
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
    kepala = {"User-Agent": "bahts/1"}
    openalex = (urllib.parse.urlsplit(url).hostname or "").endswith(".openalex.org")
    if openalex and _kunci():
        kepala["Authorization"] = "Bearer " + _kunci()
    for sisa_coba in (1, 0):
        try:
            return buka(url, kepala=kepala, waktu=waktu)  # galat sementara dicoba lagi di sana
        except urllib.error.HTTPError as e:
            pesan = e.read().decode("utf8", "replace")
            # mesin pencari makna OpenAlex kadang kewalahan dan menjawabnya sebagai 400: tunggu, coba lagi
            if sisa_coba and "Failed to embed" in pesan:
                time.sleep(3)
                continue
            if not openalex:
                raise
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
    latin = "".join(c for c in unicodedata.normalize("NFKD", judul).lower() if not unicodedata.combining(c))
    latin = re.sub(r"[^a-z0-9]+", " ", latin).strip()
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
    print(f"\n{kepala}{ARAH.sub('', w['judul'] or '')}")
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
    except Exception:  # format rusak/bersandi tidak boleh dianggap unduhan yang selesai
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
