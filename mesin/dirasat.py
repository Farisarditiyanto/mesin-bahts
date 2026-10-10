"""الدراسات السابقة: cari penelitian terdahulu (jurnal, risalah kampus) di katalog OpenAlex dan DOAJ.
Gratis, butuh internet. Dipanggil lewat bahts.py.

OpenAlex ditanya dua kali: menurut kata (judul, ringkasan, kata kunci) dan menurut makna (menemukan penelitian
yang kata-katanya lain tetapi bahasannya sama; pertanyaan panjang boleh). DOAJ = jurnal akses terbuka.

Kunci OpenAlex (gratis: daftar di https://openalex.org, salin dari Settings > API key) disimpan sebagai satu baris
di kunci_openalex.txt, di samping folder mesin/; berkas itu tidak ada → dibaca dari variabel lingkungan OPENALEX_API_KEY
(untuk komputer yang tidak menyimpan berkas, mis. cloud). Tanpa kunci: jatah sehari sekitar 50 kali `dirasat`, dan `dirasat-pdf`
tidak jalan. Dengan kunci: sekitar 300 kali `dirasat` atau 100 PDF sehari; jatah kembali penuh tiap 00.00 UTC.
"""
import json, os, re, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

KUNCI = Path(__file__).parent.parent / "kunci_openalex.txt"
KUNCI_ENV = "OPENALEX_API_KEY"
OPENALEX = "https://api.openalex.org/works"
PDF = "https://content.openalex.org/works/{}.pdf"  # salinan PDF yang disimpan OpenAlex
KOLOM = ("id,title,publication_year,type,language,cited_by_count,authorships,primary_location,best_oa_location,"
         "doi,has_content,abstract_inverted_index")
MAKNA_MAKS = 50  # OpenAlex menjawab pencarian makna paling banyak sebanyak ini
DOAJ = "https://doaj.org/api/search/articles/"
ARAH = re.compile("[‎‏‪-‮⁦-⁩]")  # tanda arah tulisan yang ikut tersalin dari PDF


class Ditolak(OSError):
    """Layanan menjawab, tetapi menolak; isinya kalimat untuk pemakai."""


def _kunci():
    if KUNCI.exists():
        return KUNCI.read_text(encoding="utf-8-sig").strip()
    return os.environ.get(KUNCI_ENV, "").strip()


def _buka(url):
    """Buka alamat (kunci OpenAlex ikut hanya ke openalex.org); penolakan OpenAlex yang dikenal dijadikan kalimat."""
    kepala = {"User-Agent": "bahts/1"}
    openalex = urllib.parse.urlsplit(url).hostname.endswith(".openalex.org")
    if openalex and _kunci():
        kepala["Authorization"] = "Bearer " + _kunci()
    for sisa_coba in (2, 1, 0):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=kepala), timeout=120)
        except urllib.error.HTTPError as e:
            pesan = e.read().decode("utf8", "replace")
            # mesin pencari makna OpenAlex kadang kewalahan (dijawabnya sebagai 400), begitu juga 5xx: tunggu, coba lagi
            if sisa_coba and (e.code >= 500 or "Failed to embed" in pesan):
                time.sleep(3)
                continue
            if not openalex:
                raise
            if e.code == 401:
                raise Ditolak(f"kunci di {KUNCI.name} (atau {KUNCI_ENV}) ditolak atau belum ada: salin ulang dari Settings > API key di https://openalex.org")
            if e.code == 429:
                raise Ditolak("jatah hari ini habis (kembali penuh 00.00 UTC). " + ("" if _kunci() else
                              f"Kunci gratis menaikkannya 10 kali: pemakai daftar di https://openalex.org, lalu simpan kuncinya di {KUNCI.name}"))
            if "Failed to embed" in pesan:
                raise Ditolak("mesin pencari makna OpenAlex sedang sibuk: ulangi sebentar lagi")
            if e.code == 400:
                try:
                    pesan = json.loads(pesan)["message"]
                except (ValueError, KeyError, TypeError):
                    pass
                raise Ditolak(f"OpenAlex menolak permintaan ini: {pesan[:300]}")
            raise


def _doi(d):
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d or "").lower()


def _openalex(cara, kata, maks, saringan):
    """(jumlah yang cocok, [penelitian], sisa jatah USD) dari OpenAlex; cara = nama parameter pencariannya."""
    # corpus=all: ikut mencari di kumpulan tambahan OpenAlex, tempat banyak risalah kampus berada
    p = {cara: kata, "per_page": maks, "select": KOLOM, "corpus": "all"}
    if saringan:
        p["filter"] = saringan
    if cara == "search" and _kunci():
        p["rerank"] = "true"  # urutan diperbaiki OpenAlex menurut kecocokan isi; tanpa kunci jatahnya terlalu kecil
    with _buka(OPENALEX + "?" + urllib.parse.urlencode(p)) as r:
        d, sisa = json.load(r), r.headers.get("X-RateLimit-Remaining-USD")
    hasil = []
    for w in d["results"]:
        asal = w.get("primary_location") or {}
        # OpenAlex menyimpan ringkasan sebagai {kata: [posisi]}: susun lagi jadi kalimat
        idx = w.get("abstract_inverted_index") or {}
        hasil.append({
            "judul": w["title"], "peneliti": [a["author"]["display_name"] for a in w["authorships"]],
            "tahun": w["publication_year"], "jenis": w["type"], "wadah": (asal.get("source") or {}).get("display_name"),
            "bahasa": w.get("language"), "dikutip": w.get("cited_by_count"),
            "doi": _doi(w.get("doi")), "tautan": w.get("doi") or asal.get("landing_page_url"),
            "pdf": (w.get("best_oa_location") or {}).get("pdf_url") or asal.get("pdf_url"),
            "nomor": w["id"].rsplit("/", 1)[-1], "tersimpan": bool((w.get("has_content") or {}).get("pdf")),
            "ringkasan": " ".join(k for _, k in sorted((p, k) for k, v in idx.items() for p in v))})
    return d["meta"]["count"], hasil, sisa


def _kata(kata, maks, saringan):
    return _openalex("search", kata, maks, saringan)


def _makna(kata, maks, saringan):
    time.sleep(1)  # OpenAlex: pencarian makna paling cepat satu kali per detik
    return _openalex("search.semantic", kata, min(maks, MAKNA_MAKS), saringan)


def _doaj(kata, maks, saringan):
    """Jurnal akses terbuka, banyak jurnal kampus Arab. Saringan OpenAlex tidak berlaku di sini."""
    with _buka(f"{DOAJ}{urllib.parse.quote(kata, safe='')}?pageSize={maks}") as r:
        d = json.load(r)
    hasil = []
    for w in d.get("results", []):
        b = w["bibjson"]
        doi = _doi(next((i["id"] for i in b.get("identifier", []) if i.get("type") == "doi" and i.get("id")), ""))
        taut = [t["url"] for t in b.get("link", []) if t.get("url")]
        hasil.append({
            "judul": b.get("title"), "peneliti": [a["name"] for a in b.get("author", []) if a.get("name")],
            "tahun": b.get("year"), "jenis": "article", "wadah": (b.get("journal") or {}).get("title"),
            "doi": doi, "tautan": ("https://doi.org/" + doi) if doi else (taut[0] if taut else None),
            "pdf": next((t for t in taut if t.lower().endswith(".pdf")), None), "ringkasan": b.get("abstract") or ""})
    return d.get("total", 0), hasil, None


SUMBER = (("OpenAlex, menurut kata", _kata), ("OpenAlex, menurut makna", _makna), ("DOAJ", _doaj))


def cari(kata, maks=10, saringan="", lebar=400):
    """Judul, peneliti, tahun, jenis, jurnal/kampus, tautan, dan ringkasan tiap penelitian yang cocok, dari tiap sumber.
    saringan = saringan OpenAlex apa adanya, mis. «language:ar», «type:dissertation», «publication_year:>2014»
    (beberapa dipisah koma)."""
    if not kata.strip() or not 1 <= maks <= 100:
        raise ValueError('bentuknya: dirasat "<kata kunci>" [maks 1-100] [saringan]')
    n, sudah, gagal, sisa = 0, set(), 0, None
    for nama, ambil in SUMBER:
        try:
            jumlah, hasil, jatah = ambil(kata, maks, saringan)
        except OSError as e:  # satu sumber mati tidak menghentikan sumber lain
            print(f"\n{nama}: GAGAL — {e}")
            gagal += 1
            continue
        sisa = jatah or sisa
        baru = [w for w in hasil if not ({w["doi"], w.get("nomor")} - {"", None}) & sudah]
        print(f"\n{nama}: {jumlah} penelitian cocok" + (f", {len(hasil) - len(baru)} sudah tercetak di atas" if len(baru) < len(hasil) else ""))
        for w in baru:
            sudah |= {w["doi"], w.get("nomor")} - {"", None}
            n += 1
            print(f"\n[{n}] {ARAH.sub('', w['judul'] or '')}")
            rinci = [f"{apa} {w[k]}" for k, apa in (("bahasa", "bahasa"), ("dikutip", "dikutip")) if w.get(k)]
            print(f"    {'، '.join(w['peneliti']) or '(peneliti tidak tercatat)'} | {w['tahun']} | {w['jenis']} | "
                  + " | ".join([w["wadah"] or "-"] + rinci))
            print(f"    {w['tautan'] or '-'}" + (f" | PDF: {w['pdf']}" if w["pdf"] else ""))
            if w.get("nomor"):
                print(f"    OpenAlex {w['nomor']}" + (f" | PDF tersimpan: python mesin/bahts.py dirasat-pdf {w['nomor']} <folder>" if w["tersimpan"] else ""))
            if ringkas := ARAH.sub("", re.sub(r"\s+", " ", w["ringkasan"]))[:lebar]:
                print(f"    ملخص: {ringkas}")
    if gagal == len(SUMBER):
        raise ConnectionError("semua sumber penelitian gagal dihubungi")
    if sisa:
        print(f"\nSisa jatah OpenAlex hari ini: ${float(sisa):.2f}" + ("" if _kunci() else f" (tanpa kunci; lihat kepala mesin/{Path(__file__).name})"))
    if not n:
        print("Coba kata kunci lebih pendek (2-3 kata inti), atau buang saringannya.")


def pdf(nomor, folder):
    """Unduh salinan PDF sebuah penelitian (nomor OpenAlex, W…) ke folder bahts, supaya isinya bisa dibaca."""
    if not re.fullmatch(r"W\d+", nomor):
        raise ValueError(f"«{nomor}» bukan nomor OpenAlex (bentuknya W123…, tercetak oleh `dirasat`)")
    tujuan = Path(folder) / f"{nomor}.pdf"
    if tujuan.exists():
        print(f"Sudah ada: {tujuan}")
        return
    try:
        with _buka(PDF.format(nomor)) as r:
            isi = r.read()
    except Ditolak as e:
        raise SystemExit(f"PDF {nomor} tidak terunduh: {e}")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        raise SystemExit(f"OpenAlex tidak menyimpan PDF {nomor}: pakai tautan «PDF:» yang dicetak `dirasat`, kalau ada")
    if not isi.startswith(b"%PDF"):
        raise SystemExit(f"Jawaban OpenAlex untuk {nomor} bukan PDF.")
    tujuan.write_bytes(isi)
    print(f"Jadi: {tujuan} ({len(isi) / 1e6:.1f} MB)")
