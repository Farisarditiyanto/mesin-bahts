"""الدراسات السابقة: cari penelitian terdahulu (jurnal, risalah kampus) di katalog OpenAlex dan DOAJ.
Gratis, butuh internet. Dipanggil lewat bahts.py.

OpenAlex tanpa kunci hanya melayani sekitar 100 pencarian sehari per alamat internet. Kunci gratis
(daftar di https://openalex.org, lalu salin «API key» dari halaman akun) menaikkannya jadi sekitar 1.000:
simpan kuncinya sebagai satu baris di kunci_openalex.txt, di samping folder mesin/.
"""
import json, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path

KUNCI = Path(__file__).parent.parent / "kunci_openalex.txt"
OPENALEX = "https://api.openalex.org/works"
KOLOM = "title,publication_year,type,authorships,primary_location,best_oa_location,doi,abstract_inverted_index"
DOAJ = "https://doaj.org/api/search/articles/"
ARAH = re.compile("[‎‏‪-‮⁦-⁩]")  # tanda arah tulisan yang ikut tersalin dari PDF


def _json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "bahts/1"}), timeout=60) as r:
        return json.load(r)


def _doi(d):
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d or "").lower()


def _openalex(kata, maks):
    """(jumlah yang cocok, [penelitian]) dari OpenAlex."""
    url = f"{OPENALEX}?per-page={maks}&select={KOLOM}&search={urllib.parse.quote(kata)}"
    if KUNCI.exists():
        url += "&api_key=" + urllib.parse.quote(KUNCI.read_text(encoding="utf-8-sig").strip())
    try:
        d = _json(url)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise OSError(f"kunci di {KUNCI.name} ditolak: salin ulang dari halaman akun OpenAlex, atau pindahkan berkas itu")
        if e.code == 429:
            raise OSError("jatah hari ini habis. " + ("Coba lagi besok." if KUNCI.exists() else
                          f"Kunci gratis menaikkannya 10 kali: pemakai daftar di https://openalex.org, lalu simpan kuncinya di {KUNCI.name}"))
        raise
    hasil = []
    for w in d["results"]:
        asal = w.get("primary_location") or {}
        # OpenAlex menyimpan ringkasan sebagai {kata: [posisi]}: susun lagi jadi kalimat
        idx = w.get("abstract_inverted_index") or {}
        hasil.append({
            "judul": w["title"], "peneliti": [a["author"]["display_name"] for a in w["authorships"]],
            "tahun": w["publication_year"], "jenis": w["type"], "wadah": (asal.get("source") or {}).get("display_name"),
            "doi": _doi(w.get("doi")), "tautan": w.get("doi") or asal.get("landing_page_url"),
            "pdf": (w.get("best_oa_location") or {}).get("pdf_url") or asal.get("pdf_url"),
            "ringkasan": " ".join(k for _, k in sorted((p, k) for k, v in idx.items() for p in v))})
    return d["meta"]["count"], hasil


def _doaj(kata, maks):
    """(jumlah yang cocok, [penelitian]) dari DOAJ: jurnal akses terbuka, banyak jurnal kampus Arab."""
    d = _json(f"{DOAJ}{urllib.parse.quote(kata, safe='')}?pageSize={maks}")
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
    return d.get("total", 0), hasil


SUMBER = (("OpenAlex", _openalex), ("DOAJ", _doaj))


def cari(kata, maks=10, lebar=400):
    """Judul, peneliti, tahun, jenis, jurnal/kampus, tautan, dan ringkasan tiap penelitian yang cocok, dari tiap sumber."""
    n, sudah, gagal = 0, set(), 0
    for nama, ambil in SUMBER:
        try:
            jumlah, hasil = ambil(kata, maks)
        except OSError as e:  # satu sumber mati tidak menghentikan sumber lain
            print(f"\n{nama}: GAGAL — {e}")
            gagal += 1
            continue
        print(f"\n{nama}: {jumlah} penelitian cocok: {kata}")
        for w in hasil:
            if w["doi"] and w["doi"] in sudah:
                continue  # sudah tercetak dari sumber sebelumnya
            sudah.add(w["doi"])
            n += 1
            print(f"\n[{n}] {ARAH.sub('', w['judul'] or '')}")
            print(f"    {'، '.join(w['peneliti']) or '(peneliti tidak tercatat)'} | {w['tahun']} | {w['jenis']} | {w['wadah'] or '-'}")
            print(f"    {w['tautan'] or '-'}" + (f" | PDF: {w['pdf']}" if w["pdf"] else ""))
            if ringkas := ARAH.sub("", re.sub(r"\s+", " ", w["ringkasan"]))[:lebar]:
                print(f"    ملخص: {ringkas}")
    if gagal == len(SUMBER):
        raise ConnectionError("semua sumber penelitian gagal dihubungi")
    if not n:
        print("Coba kata kunci lebih pendek (2-3 kata inti).")
