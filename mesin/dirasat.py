"""الدراسات السابقة: cari penelitian terdahulu (jurnal, risalah kampus) di katalog OpenAlex.
Gratis, tanpa kunci, butuh internet. Dipanggil lewat bahts.py.
"""
import json, re, urllib.parse, urllib.request

API = "https://api.openalex.org/works"
KOLOM = "title,publication_year,type,authorships,primary_location,best_oa_location,doi,abstract_inverted_index"
ARAH = re.compile("[‎‏‪-‮⁦-⁩]")  # tanda arah tulisan yang ikut tersalin dari PDF


def _ringkasan(w, lebar):
    """OpenAlex menyimpan ringkasan sebagai {kata: [posisi]}: susun lagi jadi kalimat."""
    idx = w.get("abstract_inverted_index") or {}
    t = " ".join(k for _, k in sorted((p, k) for k, v in idx.items() for p in v))
    return ARAH.sub("", t)[:lebar]


def cari(kata, maks=10, lebar=400):
    """Judul, peneliti, tahun, jenis, jurnal/kampus, tautan, dan ringkasan tiap penelitian yang cocok."""
    url = f"{API}?per-page={maks}&select={KOLOM}&search={urllib.parse.quote(kata)}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "bahts/1"}), timeout=60) as r:
        d = json.load(r)
    print(f"{d['meta']['count']} penelitian cocok: {kata}")
    for n, w in enumerate(d["results"], 1):
        asal = (w.get("primary_location") or {})
        pdf = (w.get("best_oa_location") or {}).get("pdf_url") or asal.get("pdf_url")
        peneliti = "، ".join(a["author"]["display_name"] for a in w["authorships"]) or "(peneliti tidak tercatat)"
        print(f"\n[{n}] {ARAH.sub('', w['title'] or '')}")
        print(f"    {peneliti} | {w['publication_year']} | {w['type']} | {(asal.get('source') or {}).get('display_name') or '-'}")
        print(f"    {w.get('doi') or asal.get('landing_page_url') or '-'}" + (f" | PDF: {pdf}" if pdf else ""))
        if ringkas := _ringkasan(w, lebar):
            print(f"    ملخص: {ringkas}")
    if not d["results"]:
        print("Coba kata kunci lebih pendek (2-3 kata inti).")
