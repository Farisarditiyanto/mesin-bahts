# SPDX-License-Identifier: AGPL-3.0-or-later
"""Layanan Shamela offline: tafsir per ayat dan takhrij silang hadits, dari tabel `_meta` dataset Shamela yang sama dengan
`ambil` (tafsir_xrefs: ayat -> halaman 14 kitab tafsir; hadith_xrefs: hadits -> halamannya di 10 kitab hadits). Tabel
itu buatan Shamela sendiri (layanan «التفسير» dan «التخريج» di program Shamela), bukan tebakan mesin. Dipanggil lewat
bahts.py.

Penunjuk jalan saja: halaman yang ditunjuk tetap dibaca dengan `halaman`, dan yang dikutip tetap harus lolos `cek`.
Tanpa internet sesudah tabelnya diunduh sekali (`siapkan`), jadi tidak berkuota seperti connector.
"""
import functools, re

import shamela
from shamela import ROOT, RAW, perintah

TABEL = {"tafsir": "_meta/tafsir_xrefs.parquet", "hadits": "_meta/hadith_xrefs.parquet"}


def siapkan():
    """Unduh tabel layanan yang belum ada (±0,6 MB)."""
    for nama, jalur in TABEL.items():
        f = ROOT / jalur
        if not f.exists():
            f.parent.mkdir(parents=True, exist_ok=True)
            print(f"layanan {nama}: mengunduh …", flush=True)
            shamela._unduh(f"{RAW}/{jalur}", f, lambda q: open(q, "wb"))
    print(f"layanan Shamela: {', '.join(TABEL)} siap")


@functools.cache
def _baris(nama):
    """[(kunci, shamela_id, shamela_page_id)] satu tabel layanan; diunduh dulu kalau belum ada."""
    f = ROOT / TABEL[nama]
    if not f.exists():
        siapkan()
    import pyarrow.parquet as pq
    t = pq.read_table(f, columns=["key_id", "book_id", "page_id"]).to_pydict()
    return list(zip(t["key_id"], t["book_id"], t["page_id"]))


@functools.cache
def _katalog():
    return {r["shamela_id"]: r for r in shamela._meta()}


WAFAT_MAKS = 2000  # katalog menulis 99999 untuk pengarang yang masih hidup, kolektif, atau tidak diketahui


def _wafat(sid):
    """Tahun wafat pengarang, atau None kalau tidak tercatat."""
    w = _katalog().get(sid, {}).get("main_author_death_hijri")
    return w if isinstance(w, int) and 0 < w < WAFAT_MAKS else None


def _urut(sid):
    """Urutan sumber: pengarang yang lebih dulu wafat lebih dulu (أبو سليمان ص73); wafat tidak tercatat paling akhir."""
    return (_wafat(sid) is None, _wafat(sid) or 0, sid)


def _nama(sid):
    r, w = _katalog().get(sid, {}), _wafat(sid)
    return f"{r.get('title_ar', '?')} ({r.get('main_author_name_ar', '?')}" + (f"، ت {w}هـ)" if w else ")")


def _tempat(sid, halaman_shamela):
    """{shamela_page_id: (juz, (awal, akhir))} halaman cetak rekaman-rekaman itu di kitab lokal sid."""
    nomor = shamela.rekaman_shamela(sid)
    ix, awal = shamela._indeks(sid)
    hasil = {}
    for s in halaman_shamela:
        i = nomor.get(s)
        if i is not None and awal[i] is not None:
            hasil[s] = (shamela._juz({"part": ix[i][0]}), (awal[i], ix[i][2]))
    return hasil


def _cetak_kitab(sid, halaman_shamela, keterangan=lambda sid, s: ""):
    """Baris-baris satu kitab: juz/halaman cetak tiap tempat (kitab sudah diunduh) atau perintah `ambil`."""
    if sid not in set(shamela.punya()):
        return [f"[{sid}] {_nama(sid)}: belum diunduh -> {perintah(f'ambil {sid}')}"]
    tempat = _tempat(sid, halaman_shamela)
    baris, sudah = [f"[{sid}] {_nama(sid)}:"], set()
    for s in sorted(halaman_shamela):
        if s not in tempat:
            baris.append(f"    halaman Shamela {s} tidak ada di kitab lokal (edisi berbeda?)")
            continue
        juz, (a, z) = tempat[s]
        if (juz, a, z) in sudah:
            continue
        sudah.add((juz, a, z))
        baris.append(f"    {shamela.letak(juz, (a, z))}{keterangan(sid, s)} -> {perintah(f'halaman {sid} {juz} {a}' + (f'-{z}' if z != a else ''))}")
    return baris


def tafsir(rujukan):
    """`tafsir <surat:ayat>` (atau surat:ayat-ayat): kitab tafsir yang menafsirkan ayat itu beserta juz/halaman cetaknya,
    urut dari pengarang yang lebih dulu wafat. Kembalikan jumlah kitab."""
    import cek_ayat
    m = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)(?:\s*-\s*(\d+))?\s*", rujukan)
    if not m:
        raise SystemExit(f"Tulis ayatnya surat:ayat atau surat:ayat-ayat, mis. «2:219» atau «2:219-220», bukan «{rujukan}».")
    s, a, z = int(m[1]), int(m[2]), int(m[3] or m[2])
    urut = {k: i + 1 for i, k in enumerate(cek_ayat.QURAN)}  # nomor ayat se-mushaf = kunci layanan tafsir Shamela
    kunci = [urut.get(f"{s}:{x}") for x in range(a, z + 1)]
    if z < a or None in kunci:
        raise SystemExit(f"Ayat {rujukan} tidak ada di mushaf (surat {s} punya {sum(k.startswith(f'{s}:') for k in urut)} ayat).")
    per_kitab = {}
    for k, sid, hal in _baris("tafsir"):
        if k in kunci:
            per_kitab.setdefault(sid, set()).add(hal)
    print(f"Tafsir {rujukan} di {len(per_kitab)} kitab (indeks layanan Shamela; urut dari pengarang yang lebih dulu wafat). "
          "Penunjuk saja: baca halamannya sendiri, yang dikutip tetap harus lolos `cek`.")
    for sid in sorted(per_kitab, key=_urut):
        print("\n".join(_cetak_kitab(sid, per_kitab[sid])))
    return len(per_kitab)


def takhrij(sid, juz, hal):
    """`takhrij <id> <juz> <hal>`: tiap hadits di halaman itu (kitab hadits yang dicakup layanan Shamela) beserta
    tempat hadits yang sama di kitab hadits lain, dengan nomor kepala haditsnya kalau kitab itu sudah diunduh.
    Kembalikan jumlah hadits yang punya data takhrij."""
    import cek_hadits
    angka = lambda x: int(x) if str(x).isdigit() else x
    sid, juz, hal = int(shamela._folder(sid).name), angka(juz), angka(hal)
    shamela.info(sid)  # belum diunduh -> pesan yang jelas
    halaman_ini = {int(p["shamela_page_id"]) for p, _ in shamela.rekaman_halaman(sid, juz, hal) if str(p.get("shamela_page_id")).isdigit()}
    if not halaman_ini:
        raise SystemExit(f"[{sid}] TIDAK ADA halaman {juz}/{hal}. Yang ada: {shamela.daftar_juz(sid)} (juz \"-\" = kitab satu jilid)")
    baris = _baris("hadits")
    kunci = sorted({k for k, b, h in baris if b == sid and h in halaman_ini})
    if not kunci:
        cakup = sorted({b for _, b, _ in baris}, key=_urut)
        print(f"[{sid}] {juz}/{hal}: tidak ada data takhrij Shamela untuk halaman ini. Layanan ini hanya mencakup: "
              + "؛ ".join(f"{b} {_katalog().get(b, {}).get('title_ar', '?')}" for b in cakup)
              + ". Untuk kitab lain: `hadits`, connector, atau `temukan`.")
        return 0

    def nomor(sid_, s):
        """« (رقم n)» = kepala hadits di rekaman halaman Shamela s, dibaca dengan aturan `cek`."""
        i = shamela.rekaman_shamela(sid_).get(s)
        if i is None:
            return ""
        n = sorted({x for _, x in cek_hadits.kepala_hadits(shamela.rekaman_ke(sid_, i).get("body") or "")[1]})
        return f" (رقم {'، '.join(map(str, n))})" if n else ""

    for k in kunci:
        per_kitab = {}
        for kk, b, h in baris:
            if kk == k:
                per_kitab.setdefault(b, set()).add(h)
        print(f"\n== hadits Shamela #{k}: {len(per_kitab)} kitab (urut dari pengarang yang lebih dulu wafat) ==")
        for b in sorted(per_kitab, key=_urut):
            print("\n".join(_cetak_kitab(b, per_kitab[b], nomor)))
    print("\nPenunjuk saja: baca tiap halaman, tulis takhrij dan derajatnya dari kitab yang dibaca (aturan takhrij di AGENTS.md).")
    return len(kunci)
