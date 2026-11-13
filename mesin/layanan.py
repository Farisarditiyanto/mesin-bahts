# SPDX-License-Identifier: AGPL-3.0-or-later
"""Layanan Shamela offline: tafsir per ayat dan takhrij silang hadits, dari tabel `_meta` dataset Shamela yang sama dengan
`ambil` (diekstrak dari basis data program Shamela 4): tafsir_xrefs = ayat -> halaman awal tafsirnya di 14 kitab tafsir;
hadith_xrefs = hadits -> halamannya di 8 kitab hadits (10 edisi, lihat EDISI_HADITS). Dipanggil lewat bahts.py.

Tabel itu menunjuk satu edisi tertentu tiap kitab. Edisi lain kitab yang sama (group_id katalog sama, mis. صحيح مسلم
ت عبد الباقي 1727 untuk ط التركية 711) dijembatani lewat nomor hadits: edisi yang ditunjuk tabel harus sudah diunduh,
lalu nomor yang sama dicari sebagai kepala hadits di edisi lokal dan lafaznya dibandingkan (penomoran edisi bisa beda).
Tafsir tidak bernomor, jadi edisi lain kitab tafsir hanya disebut.

Penunjuk jalan saja: halaman yang ditunjuk tetap dibaca dengan `halaman`, dan yang dikutip tetap harus lolos `cek`.
Tanpa internet sesudah tabelnya diunduh sekali (`siapkan`), jadi tidak berkuota seperti connector.
"""
import functools, re

import norma, shamela
from shamela import ROOT, RAW, TAGS, perintah

TABEL = {"tafsir": "_meta/tafsir_xrefs.parquet", "hadits": "_meta/hadith_xrefs.parquet"}
WAFAT_MAKS = 2000  # katalog menulis 99999 untuk pengarang yang masih hidup, kolektif, atau tidak diketahui
SIRAP = 4  # kata berurutan; dua edisi bernomor sama dianggap hadits yang sama kalau berbagi ≥ SIRAP_MIN deret sepanjang ini
SIRAP_MIN = 3


def siapkan(*nama):
    """Unduh tabel layanan yang belum ada (semua ±0,6 MB; `nama` = hanya tabel itu)."""
    for n in nama or TABEL:
        f = ROOT / TABEL[n]
        if not f.exists():
            f.parent.mkdir(parents=True, exist_ok=True)
            print(f"layanan {n}: mengunduh …", flush=True)
            shamela._unduh(f"{RAW}/{TABEL[n]}", f, lambda q: open(q, "wb"))
    if not nama:
        print(f"layanan Shamela: {', '.join(TABEL)} siap")


def siap():
    return all((ROOT / j).exists() for j in TABEL.values())


@functools.cache
def _baris(nama):
    """[(kunci, shamela_id, shamela_page_id)] satu tabel layanan; diunduh dulu kalau belum ada."""
    siapkan(nama)
    import pyarrow.parquet as pq
    t = pq.read_table(ROOT / TABEL[nama], columns=["key_id", "book_id", "page_id"]).to_pydict()
    return list(zip(t["key_id"], t["book_id"], t["page_id"]))


@functools.cache
def _katalog():
    return {r["shamela_id"]: r for r in shamela._meta()}


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


def _karya(sid):
    """Penanda kitab lintas edisi: group_id katalog (edisi-edisi satu kitab berbagi nomor ini), atau nomor kitabnya."""
    return _katalog().get(sid, {}).get("group_id") or sid


def _edisi_lokal(sid):
    """Edisi lain kitab yang sama yang sudah diunduh."""
    return [e for e in shamela.punya() if e != sid and _karya(e) == _karya(sid)]


def _tabel_kitab(nama):
    return sorted({b for _, b, _ in _baris(nama)}, key=_urut)


def _rentang(teks):
    m = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*", str(teks))
    return range(int(m[1]), int(m[2] or m[1]) + 1) if m and int(m[2] or m[1]) >= int(m[1]) else None


def _perintah_halaman(sid, juz, a, z):
    return perintah(f"halaman {sid} {juz} {a}" + (f"-{z}" if z != a else ""))


def _tempat(sid, s):
    """(juz, awal, akhir) halaman cetak rekaman ber-shamela_page_id s di kitab lokal sid, atau None."""
    i = shamela.rekaman_shamela(sid).get(s)
    if i is None:
        return None
    ix, awal = shamela._indeks(sid)
    return None if awal[i] is None else (shamela._juz({"part": ix[i][0]}), awal[i], ix[i][2])


# --- hadits: nomor dan lafaz ---

@functools.cache
def _kepala(sid, i):
    """Nomor kepala hadits di rekaman ke-i (aturan `cek`)."""
    import cek_hadits
    return sorted({n for _, n in cek_hadits.kepala_hadits(shamela.rekaman_ke(sid, i).get("body") or "")[1]})


@functools.cache
def _nomor_rekaman(sid):
    """{nomor hadits: rekaman pertama tempat nomor itu jadi kepala hadits} seluruh kitab sid (dibaca sekali per perintah)."""
    import cek_hadits
    hasil = {}
    for i, p in enumerate(shamela._rekaman_di(sid, range(len(shamela.indeks(sid))))):
        for _, n in cek_hadits.kepala_hadits(p.get("body") or "")[1]:
            hasil.setdefault(n, i)
    return hasil


def _sirap(sid, i):
    kata = norma.norm(TAGS.sub(" ", shamela.rekaman_ke(sid, i).get("body") or "")).split()
    return {tuple(kata[k:k + SIRAP]) for k in range(len(kata) - SIRAP + 1)}


def _seberang(asal, i, tujuan):
    """Rekaman edisi `tujuan` untuk hadits-hadits di rekaman i edisi `asal`, lewat nomor yang sama:
    [(nomor, rekaman tujuan atau None, lafaznya cocok?)]."""
    peta, hasil = _nomor_rekaman(tujuan), []
    for n in _kepala(asal, i):
        j = peta.get(n)
        hasil.append((n, j, j is not None and len(_sirap(asal, i) & _sirap(tujuan, j)) >= SIRAP_MIN))
    if any(c for *_, c in hasil):  # nomor kedua (مسلم: nomor urut dalam كتاب, «(103) - 165») yang tidak cocok tidak dicetak
        hasil = [h for h in hasil if h[2]]
    return hasil


def _baris_seberang(asal, i, e):
    """Baris «edisi lokal e» untuk hadits di rekaman i edisi asal."""
    ix, awal = shamela._indeks(e)
    out = []
    for n, j, cocok in _seberang(asal, i, e):
        if j is None:
            out.append(f"      edisi lokal [{e}]: nomor {n} tidak ditemukan sebagai kepala hadits (penomoran edisi beda?)")
            continue
        juz, a, z = shamela._juz({"part": ix[j][0]}), awal[j], ix[j][2]
        catat = "" if cocok else " — LAFAZ TIDAK COCOK: penomoran edisi beda, jangan dipakai tanpa dibaca"
        out.append(f"      edisi lokal [{e}] {_katalog()[e]['title_ar']}: رقم {n}، {shamela.letak(juz, (a, z))}{catat} -> "
                   + _perintah_halaman(e, juz, a, z))
    return out


def _cetak_kitab(sid, halaman_shamela, hadits=False):
    """Baris-baris satu kitab tabel: juz/halaman cetak tiap tempat (kitab sudah diunduh), lalu edisi lokal lain kitab itu
    (hadits: lewat nomor; tafsir: hanya disebut). Kitab yang belum diunduh: edisi lokalnya disebut lebih dulu, baru `ambil`."""
    lain = _edisi_lokal(sid)
    if sid not in set(shamela.punya()):
        if not lain:
            return [f"[{sid}] {_nama(sid)}: belum diunduh -> {perintah(f'ambil {sid}')}"]
        guna = ("unduh sekali sebagai jembatan nomor hadits ke edisi lokal" if hadits
                else "halaman yang ditunjuk Shamela hanya berlaku di edisi ini")
        return [f"[{sid}] {_nama(sid)}: belum diunduh. Edisi lokal kitab yang sama (halamannya beda): "
                + "، ".join(f"[{e}] {_katalog()[e]['title_ar']}" for e in lain) + f"; {guna}: {perintah(f'ambil {sid}')}"]
    baris, sudah = [f"[{sid}] {_nama(sid)}:"], set()
    for s in sorted(halaman_shamela):
        t = _tempat(sid, s)
        if t is None:
            baris.append(f"    halaman Shamela {s} tidak ada di kitab lokal (berkas kitab berbeda dari tabel layanan?)")
            continue
        if t in sudah:
            continue
        sudah.add(t)
        juz, a, z = t
        i = shamela.rekaman_shamela(sid)[s]
        nomor = _kepala(sid, i) if hadits else []
        baris.append(f"    {shamela.letak(juz, (a, z))}" + (f" (رقم {'، '.join(map(str, nomor))})" if nomor else "")
                     + f" -> {_perintah_halaman(sid, juz, a, z)}")
        if hadits:
            for e in lain:
                baris += _baris_seberang(sid, i, e)
    if lain and not hadits:
        baris.append("    edisi lokal kitab yang sama (halamannya beda, cari ayatnya sendiri): "
                     + "، ".join(f"[{e}] {_katalog()[e]['title_ar']}" for e in lain))
    return baris


# --- pintu ---

def tafsir(rujukan):
    """`tafsir <surat:ayat>` (atau surat:ayat-ayat): kitab tafsir yang menafsirkan ayat itu beserta juz/halaman cetak
    awal pembahasannya, urut dari pengarang yang lebih dulu wafat. Kembalikan jumlah kitab."""
    import cek_ayat
    m = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)(?:\s*-\s*(\d+))?\s*", rujukan)
    if not m:
        raise SystemExit(f"Tulis ayatnya surat:ayat atau surat:ayat-ayat, mis. «2:219» atau «2:219-220», bukan «{rujukan}».")
    s, a, z = int(m[1]), int(m[2]), int(m[3] or m[2])
    if not 1 <= s <= 114:
        raise SystemExit(f"Surat {s} tidak ada: nomor surat 1-114.")
    urut = {k: i + 1 for i, k in enumerate(cek_ayat.QURAN)}  # nomor ayat se-mushaf = kunci layanan tafsir Shamela
    kunci = [urut.get(f"{s}:{x}") for x in range(a, z + 1)]
    if z < a or None in kunci:
        raise SystemExit(f"Ayat {rujukan} tidak ada di mushaf (surat {s} punya {sum(k.startswith(f'{s}:') for k in urut)} ayat).")
    per_kitab = {}
    for k, sid, hal in _baris("tafsir"):
        if k in kunci:
            per_kitab.setdefault(sid, set()).add(hal)
    print(f"Tafsir {rujukan} di {len(per_kitab)} kitab (indeks layanan Shamela; urut dari pengarang yang lebih dulu wafat). "
          "Halaman = awal pembahasan ayat itu menurut Shamela: baca sampai ayat berikutnya, dan halaman sebelumnya kalau "
          "beberapa ayat ditafsirkan bersama. Penunjuk saja: yang dikutip tetap harus lolos `cek`.")
    for sid in sorted(per_kitab, key=_urut):
        print("\n".join(_cetak_kitab(sid, per_kitab[sid])))
    return len(per_kitab)


def takhrij(sid, juz, hal):
    """`takhrij <id> <juz> <hal>` (hal boleh rentang a-b): tiap hadits di halaman itu beserta tempat hadits yang sama di
    kitab hadits lain yang dicakup layanan Shamela. Edisi yang tidak ditunjuk tabel (mis. 1727) dijembatani lewat nomor ke
    edisi yang ditunjuk (mis. 711), yang harus sudah diunduh. Kembalikan jumlah hadits yang punya data takhrij."""
    angka = lambda x: int(x) if str(x).isdigit() else x
    sid, juz = int(shamela._folder(sid).name), angka(juz)
    shamela.info(sid)  # belum diunduh -> pesan yang jelas
    halaman = _rentang(hal)
    if halaman is None or len(halaman) > 20:
        raise SystemExit(f"Halaman ditulis angka (mis. 31) atau rentang awal-akhir paling banyak 20 halaman (mis. 31-32), bukan «{hal}».")
    rekaman = {int(p["shamela_page_id"]): p for h in halaman for p, _ in shamela.rekaman_halaman(sid, juz, h)}
    if not rekaman:
        raise SystemExit(f"[{sid}] TIDAK ADA halaman {juz}/{hal}. Yang ada: {shamela.daftar_juz(sid)} (juz \"-\" = kitab satu jilid)")
    baris, kitab_tabel = _baris("hadits"), _tabel_kitab("hadits")
    if sid in kitab_tabel:
        sumber, halaman_tabel = sid, set(rekaman)
    else:
        tabel_sekarya = [b for b in kitab_tabel if _karya(b) == _karya(sid)]
        if not tabel_sekarya:
            print(f"[{sid}] {_nama(sid)}: kitab ini tidak dicakup layanan takhrij Shamela. Yang dicakup (edisi lain kitab yang "
                  "sama ikut lewat nomor hadits): " + "؛ ".join(f"[{b}] {_katalog()[b]['title_ar']}" for b in kitab_tabel)
                  + ". Untuk kitab lain: `hadits`, connector, atau `temukan`.")
            return 0
        lokal = [b for b in tabel_sekarya if b in set(shamela.punya())]
        if not lokal:
            print(f"[{sid}] {_nama(sid)}: layanan takhrij Shamela memakai edisi "
                  + "، ".join(f"[{b}] {_katalog()[b]['title_ar']}" for b in tabel_sekarya)
                  + ". Unduh sekali sebagai jembatan nomor hadits: " + perintah(f"ambil {tabel_sekarya[0]}"))
            return 0
        sumber, halaman_tabel = lokal[0], set()
        nomor_ke = shamela.rekaman_shamela(sumber)
        sp_dari = {i: s for s, i in nomor_ke.items()}
        print(f"[{sid}] dijembatani lewat nomor hadits ke edisi [{sumber}] {_katalog()[sumber]['title_ar']}:")
        sudah = set()
        for s, p in rekaman.items():
            i = shamela.rekaman_shamela(sid).get(s)
            for n, j, cocok in _seberang(sid, i, sumber):
                if (n, j) in sudah:
                    continue
                sudah.add((n, j))
                if j is None:
                    print(f"    رقم {n}: tidak ditemukan di [{sumber}]")
                    continue
                print(f"    رقم {n} -> [{sumber}]" + ("" if cocok else " — LAFAZ TIDAK COCOK: penomoran edisi beda, dilewati"))
                if cocok:
                    halaman_tabel.add(sp_dari[j])
    kunci = sorted({k for k, b, h in baris if b == sumber and h in halaman_tabel})
    if not kunci:
        print(f"[{sid}] {juz}/{hal}: tidak ada data takhrij Shamela untuk hadits di halaman ini.")
        return 0
    for k in kunci:
        per_kitab = {}
        for kk, b, h in baris:
            if kk == k:
                per_kitab.setdefault(b, set()).add(h)
        print(f"\n== hadits Shamela #{k}: {len(per_kitab)} kitab (urut dari pengarang yang lebih dulu wafat) ==")
        for b in sorted(per_kitab, key=_urut):
            print("\n".join(_cetak_kitab(b, per_kitab[b], hadits=True)))
    print("\nPenunjuk saja: baca tiap halaman, tulis takhrij dan derajatnya dari kitab yang dibaca (aturan takhrij di AGENTS.md).")
    return len(kunci)
