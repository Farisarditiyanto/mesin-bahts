# SPDX-License-Identifier: AGPL-3.0-or-later
"""Layanan Shamela offline: tafsir per ayat dan takhrij silang hadits, dari tabel `_meta` dataset Shamela yang sama dengan
`ambil` (diekstrak dari basis data program Shamela 4): tafsir_xrefs = ayat -> halaman awal tafsirnya di 14 kitab tafsir;
hadith_xrefs = hadits -> halamannya di 8 kitab hadits (10 edisi); narrators = 18.989 rawi dengan ringkasan tarjamah dan
ucapan جرح وتعديل beserta kitab sumbernya (rawi di sanad ditautkan Shamela lewat «inr://man-<nomor>» di teks kitab hadits);
root_dictionary = ±1,95 juta bentuk kata -> akarnya (kamus akar program Shamela). Dipanggil lewat bahts.py.

Tabel itu menunjuk satu edisi tertentu tiap kitab. Edisi lain kitab yang sama (group_id katalog sama, mis. صحيح مسلم
ت عبد الباقي 1727 untuk ط التركية 711) dijembatani lewat nomor hadits: edisi yang ditunjuk tabel harus sudah diunduh,
lalu nomor yang sama dicari sebagai kepala hadits di edisi lokal dan lafaznya dibandingkan (penomoran edisi bisa beda,
mis. الموطأ: yang tidak cocok ditandai, bukan dipakai).
Tafsir tidak bernomor, jadi edisi lain kitab tafsir hanya disebut.

Penunjuk jalan saja: halaman yang ditunjuk tetap dibaca dengan `halaman`, dan yang dikutip tetap harus lolos `cek`.
Tanpa internet sesudah tabelnya diunduh sekali (`siapkan`), jadi tidak berkuota seperti connector.
"""
import functools, re

import norma, shamela
from shamela import ROOT, RAW, TAGS, perintah

TABEL = {"tafsir": "_meta/tafsir_xrefs.parquet", "hadits": "_meta/hadith_xrefs.parquet", "rawi": "_meta/narrators.parquet",
         "akar": "_meta/root_dictionary.parquet"}
WAFAT_MAKS = 2000  # katalog menulis 99999 untuk pengarang yang masih hidup, kolektif, atau tidak diketahui
SIRAP = 4  # kata berurutan yang dibandingkan antara dua edisi
MIRIP_MIN = 0.5  # diukur pada 250 rekaman acak: أبو داود 654/1726 dan مسلم 711/1727 sebagian besar ≥0,7; الموطأ 28107/1699 (penomoran beda) ±0


def siapkan(*nama):
    """Unduh tabel layanan yang belum ada (semua ±19 MB; `nama` = hanya tabel itu)."""
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
def _kepala_ruas(sid, i):
    """[(semua nomor satu kepala hadits, nomor globalnya)] di rekaman ke-i (aturan `cek`). مسلم: «134 - (2951)» =
    ((134, 2951), 2951): nomor berkurung = nomor global, angka di depannya = urutan riwayat dalam كتاب itu."""
    import cek_hadits
    _, kepala, batas = cek_hadits.kepala_hadits(shamela.rekaman_ke(sid, i).get("body") or "")
    letak, kurung = {}, dict(batas) if batas is not kepala else {}
    for pos, n in kepala:
        letak.setdefault(pos, []).append(n)
    return [(tuple(sorted(v)), kurung.get(pos, v[-1])) for pos, v in letak.items()]


def _kepala(sid, i):
    """Nomor global hadits-hadits di rekaman ke-i."""
    return sorted({g for _, g in _kepala_ruas(sid, i)})


@functools.cache
def _peta_nomor(sid):
    """({semua nomor satu kepala: [rekaman]}, {nomor global: [rekaman]}) seluruh kitab sid (dibaca sekali per perintah)."""
    ruas, globl = {}, {}
    for i in range(len(shamela.indeks(sid))):
        for tup, g in _kepala_ruas(sid, i):
            ruas.setdefault(tup, []).append(i)
            globl.setdefault(g, []).append(i)
    return ruas, globl


@functools.cache
def _sirap(sid, i):
    kata = norma.norm(TAGS.sub(" ", shamela.rekaman_ke(sid, i).get("body") or "")).split()
    return frozenset(tuple(kata[k:k + SIRAP]) for k in range(len(kata) - SIRAP + 1))


def _mirip(a, b):
    """Bagian deret SIRAP kata yang sama, dari rekaman yang lebih pendek."""
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def _seberang(asal, i, tujuan):
    """Rekaman edisi `tujuan` untuk hadits-hadits di rekaman i edisi `asal`: [(nomor global, rekaman tujuan atau None,
    cocok?)]. Kepala bernomor ganda yang sama persis (مسلم «134 - (2951)») = riwayat yang sama. Selain itu, dari semua
    rekaman bernomor global sama dipilih yang lafaznya paling mirip; cocok kalau ≥ MIRIP_MIN (edisi yang penomorannya
    beda, mis. الموطأ ت الأعظمي dan ت عبد الباقي, jatuh di bawahnya)."""
    ruas, globl = _peta_nomor(tujuan)
    hasil = []
    for tup, g in _kepala_ruas(asal, i):
        if len(tup) > 1 and tup in ruas:  # pasangan yang sama bisa ada di dua كتاب: pilih yang lafaznya paling mirip
            hasil.append((g, max(ruas[tup], key=lambda j: _mirip(_sirap(asal, i), _sirap(tujuan, j))), True))
            continue
        calon = globl.get(g, [])
        if not calon:
            hasil.append((g, None, False))
            continue
        nilai, j = max((_mirip(_sirap(asal, i), _sirap(tujuan, j)), j) for j in calon)
        hasil.append((g, j, nilai >= MIRIP_MIN))
    return list(dict.fromkeys(hasil))


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
                baris += [x for x in _baris_seberang(sid, i, e) if x not in baris]
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
    if not (1 <= a <= z) or f"{s}:{z}" not in urut:
        raise SystemExit(f"Ayat {rujukan} tidak ada di mushaf (surat {s} punya {sum(k.startswith(f'{s}:') for k in urut)} ayat).")
    kunci = {urut[f"{s}:{x}"] for x in range(a, z + 1)}
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
    if halaman is None or halaman.stop - halaman.start > 20:
        raise SystemExit(f"Halaman ditulis angka (mis. 31) atau rentang awal-akhir paling banyak 20 halaman (mis. 31-32), bukan «{hal}».")
    rekaman = {int(p["shamela_page_id"]): p for h in halaman for p, _ in shamela.rekaman_halaman(sid, juz, h)}
    if not rekaman:
        raise SystemExit(f"[{sid}] TIDAK ADA halaman {juz}/{hal}. Yang ada: {shamela.daftar_juz(sid)} (juz \"-\" = kitab satu jilid)")
    baris, kitab_tabel = _baris("hadits"), _tabel_kitab("hadits")
    if sid in kitab_tabel:
        sumber, halaman_tabel, sudah = sid, set(rekaman), set()
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
                  + ". Unduh sekali sebagai jembatan nomor hadits (edisi yang penomorannya beda ditandai «LAFAZ TIDAK COCOK», "
                  "bukan dipakai): " + perintah(f"ambil {tabel_sekarya[0]}"))
            return 0
        sumber, halaman_tabel, sudah = lokal[0], set(), set()
        nomor_ke = shamela.rekaman_shamela(sumber)
        sp_dari = {i: s for s, i in nomor_ke.items()}
        print(f"[{sid}] dijembatani lewat nomor hadits ke edisi [{sumber}] {_katalog()[sumber]['title_ar']}:")
        for s, p in rekaman.items():
            i = shamela.rekaman_shamela(sid).get(s)
            for n, j, cocok in _seberang(sid, i, sumber):
                if (n, cocok) in sudah:
                    if cocok:
                        halaman_tabel.add(sp_dari[j])
                    continue
                sudah.add((n, cocok))
                if j is None:
                    print(f"    رقم {n}: tidak ditemukan di [{sumber}]")
                    continue
                print(f"    رقم {n} -> [{sumber}]" + ("" if cocok else " — LAFAZ TIDAK COCOK: penomoran edisi beda, dilewati"))
                if cocok:
                    halaman_tabel.add(sp_dari[j])
    kunci = sorted({k for k, b, h in baris if b == sumber and h in halaman_tabel})
    if not kunci and sumber != sid and sudah and not any(c for _, c in sudah):
        print(f"[{sid}] tidak bisa dijembatani ke [{sumber}]: tidak satu pun nomor hadits di halaman ini cocok lafaznya "
              f"(penomoran kedua edisi berbeda). Data takhrij Shamela ada di [{sumber}]: cari haditsnya di sana sendiri, mis. "
              + perintah(f'cari {sumber} "<lafaz hadits>"') + f", lalu {perintah(f'takhrij {sumber} <juz> <hal>')}")
        return 0
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


# --- rawi ---

TAUTAN_RAWI = re.compile(r"inr://man-(\d+)")
RINGKAS = ("الرتبة عند ابن حجر", "الرتبة عند الذهبي", "تاريخ الوفاة", "طبقة رواة التقريب")
KUTIPAN_MIN = 12  # huruf `padat`: ucapan sependek «ثقة» ada di ribuan tempat, jadi tempatnya tidak dicari
RAWI_MAKS = 20  # hasil `rawi "<nama>"` yang dicetak
KEMUNCULAN_MAKS = 200  # kemunculan satu ucapan yang dihitung tiap kitab
TARJAMAH_JARAK = 4000  # huruf: nama rawi harus terbaca sejauh ini sebelum ucapannya; lebih jauh = bisa tarjamah rawi lain
JANGKAR_JARAK = 6000  # huruf: ucapan umum dianggap milik tarjamah ini kalau sedekat ini dengan ucapannya yang khas


@functools.cache
def _rawi_semua():
    """{nomor rawi: baris tabel narrators}."""
    siapkan("rawi")
    import pyarrow.parquet as pq
    t = pq.read_table(ROOT / TABEL["rawi"], columns=["id", "short_name", "long_name", "biography_text",
                                                     "criticism_text"]).to_pylist()
    return {int(r["id"]): r for r in t}


def _json(teks, kunci):
    import json
    try:
        return json.loads(teks).get(kunci) or []
    except (TypeError, ValueError, AttributeError):
        return []


def _ringkasan(r):
    return dict(x for x in _json(r["biography_text"], "summary") if isinstance(x, list) and len(x) == 2)


def _bersih(nama):
    return " ".join((nama or "").replace("\u200c", "").split())


def _nama_rawi(n):
    r = _rawi_semua().get(n)
    return f"{_bersih(r['short_name'])} (#{n})" if r else f"#{n}"


def _baris_rawi(n):
    r = _rawi_semua()[n]
    ring = _ringkasan(r)
    isi = " | ".join(f"{k}: {ring[k]}" for k in RINGKAS if ring.get(k))
    return f"  #{n} {_bersih(r['short_name'])}" + (f" — {isi}" if isi else "")


@functools.cache
def _edisi_sumber(judul):
    """Nomor kitab katalog yang judul pokoknya sama dengan awal `judul` sumber («تهذيب الكمال» = «تهذيب الكمال في أسماء
    الرجال»; «الجرح والتعديل لابن أبي حاتم» = ketiga «الجرح والتعديل»), yang paling banyak berbagi kata judul lebih dulu."""
    q = norma.padat(judul)
    hasil = []
    for r in shamela._meta():
        jp = norma.padat(shamela.judul_pokok(r["title_ar"])[0]) if r["title_ar"] else ""
        if len(jp) >= 6 and (q.startswith(jp) or jp.startswith(q)):
            kata = set(judul.split())
            hasil.append((-len(kata & set(r["title_ar"].split() + (r["main_author_name_ar"] or "").split())), r["shamela_id"]))
    return [sid for _, sid in sorted(hasil)]


@functools.cache
def _rangkaian(sid):
    from kitab_lokal import rangkaian_kitab
    return rangkaian_kitab(sid)


def _judul_sumber(sumber):
    import re as re_
    m = re_.match(r"(.*?)\s*\(([^()]*)\)\s*$", sumber or "")
    return m.group(1) if m else (sumber or "")


def _kemunculan(sid, q):
    """[(nomor ruas rangkaian, letak)] tiap kemunculan q (`bait`) di kitab lokal sid."""
    hasil = []
    for k, (_, _, teks, _) in enumerate(_rangkaian(sid)):
        j = teks.find(q)
        while j >= 0 and len(hasil) <= KEMUNCULAN_MAKS:
            hasil.append((k, j))
            j = teks.find(q, j + 1)
    return hasil


def _nama_inti(r):
    """Nama inti rawi untuk mengenali tarjamahnya: kata sebelum «بن» pertama, «بن», dan nama ayahnya («الرحمن بن حميد»;
    kun-yah di depan tidak ikut karena judul tarjamah sering tanpa kun-yah), `padat`. Tanpa «بن»: seluruh nama pendek."""
    kata = _bersih(r["short_name"]).replace("،", " ").split()
    if "بن" in kata[1:]:
        k = kata.index("بن", 1)
        kata = kata[k - 1:k + 2 + (kata[k + 1:k + 2] == ["عبد"])]
    return norma.padat(" ".join(kata))


@functools.cache
def _judul_padat(e):
    return [norma.padat(t["title_text"]) for t in shamela._toc(e)[0]]


def _di_tarjamah(e, k, j, inti):
    """Letak (k, j) kitab e berada di tarjamah rawi ini: judul daftar isi yang menaunginya memuat nama intinya. Kitab
    yang daftar isinya tidak memuat nama rawi ini (judul per bab/huruf), dan حاشية: nama inti harus terbaca
    TARJAMAH_JARAK huruf sebelumnya."""
    import bisect
    if not inti:
        return False
    _, _, teks, (_, s_, awal, rek) = _rangkaian(e)[k]
    if s_ == 0 and any(inti in t for t in _judul_padat(e)):  # judul daftar isinya per tarjamah, bukan per bab
        i = bisect.bisect_right(awal, j) - 1
        p = shamela.rekaman_ke(e, rek[i])
        if shamela._toc(e)[0] and p.get("page_id") is not None:
            calon = shamela._judul_calon(p | {"page_id": int(p["page_id"])}, shamela._toc(e)[0],
                                         (j - awal[i], j - awal[i] + 1), None, "body")
            if calon[0] is not None:  # judul yang mungkin menaungi lebih dari satu = ragu: semuanya harus tarjamah rawi ini
                return all(t is not None and inti in norma.padat(t["title_text"]) for t in calon)
    return norma.bait(inti) in teks[max(0, j - TARJAMAH_JARAK):j]


def _letak_ucapan(daftar, inti=""):
    """Baris letak tiap ucapan [(teks, sumber)] satu rawi, dicari lafaznya di edisi lokal kitab sumbernya (juz/halaman di
    tabel sering dari edisi lain). Ucapan yang lafaznya muncul sekali di kitab itu = jangkar tarjamah rawi ini; ucapan
    umum («قال أبو داود: ثقة») yang muncul berkali-kali hanya ditunjuk kalau satu kemunculannya dekat jangkar."""
    lokal = set(shamela.punya())
    letak, jangkar = [], {}
    for teks, sumber in daftar:
        edisi = _edisi_sumber(_judul_sumber(sumber))
        q = norma.padat(teks)
        ada = {}
        if len(q) >= KUTIPAN_MIN:
            for e in (e for e in edisi if e in lokal):
                try:
                    if m := _kemunculan(e, norma.bait(q)):
                        ada[e] = m
                except (OSError, EOFError, ValueError, KeyError, IndexError):
                    continue
        for e, m in ada.items():
            if len(m) == 1 and _di_tarjamah(e, *m[0], inti):
                jangkar.setdefault(e, []).append(m[0])
        letak.append((edisi, q, ada))
    out = []
    for edisi, q, ada in letak:
        pilih = None
        for e, m in ada.items():
            if len(m) == 1 and m[0] in jangkar.get(e, ()):
                pilih = e, m[0]
                break
            dekat = [(abs(j - a), (k, j)) for k, j in m for kk, a in jangkar.get(e, ())
                     if kk == k and abs(j - a) <= JANGKAR_JARAK and _di_tarjamah(e, k, j, inti)]
            if dekat:
                pilih = e, min(dekat)[1]
                break
        if pilih:
            e, (k, j) = pilih
            juz, tanda, _, ruas = _rangkaian(e)[k]
            from kitab_lokal import halaman_di
            a, z = halaman_di(ruas, j, j + len(q))
            juz = "-" if juz is None else juz
            out.append(f"terbaca di [{e}] {_katalog()[e]['title_ar']} {shamela.letak(juz, (a, z))}{tanda} -> "
                       + _perintah_halaman(e, juz, a, z if z is not None else a))
        elif ada and all(len(m) == 1 for m in ada.values()):
            out.append(f"lafaznya terbaca di [{', '.join(map(str, ada))}], tetapi nama rawi ini tidak terbaca di tarjamah "
                       "sebelumnya (mungkin tarjamah rawi lain): buka tarjamahnya sendiri")
        elif ada:
            out.append(f"lafaz umum ini muncul di banyak tarjamah [{', '.join(map(str, ada))}] dan tidak ada ucapan lain rawi ini "
                       "di dekatnya: buka tarjamahnya sendiri")
        elif len(q) < KUTIPAN_MIN:
            out.append("ucapan pendek, tempatnya tidak dicari: buka tarjamahnya sendiri")
        elif any(e in lokal for e in edisi):
            out.append(f"lafaznya tidak ditemukan di edisi lokal [{', '.join(str(e) for e in edisi if e in lokal)}]: "
                       "jangan dikutip tanpa dibaca sendiri")
        elif edisi:
            out.append(f"kitabnya belum diunduh: {perintah(f'ambil {edisi[0]}')}")
        else:
            out.append("kitabnya tidak dikenali di katalog Shamela")
    return out


def _sanad(p):
    """[(kunci hadits Shamela, [nomor rawi dari pengarang ke sahabi])] rekaman p, dari layanan «esnad» Shamela
    («084 s 3823 4361 … 5495»: kunci, lalu rawi dari sahabi sampai pengarang; 0 = rawi tanpa nomor)."""
    hasil = []
    for x in _json(p.get("services_raw"), "esnad"):
        b = str(x).split()
        if len(b) > 2 and b[0].isdigit() and b[1] == "s":
            hasil.append((int(b[0]), [int(n) for n in reversed(b[2:]) if n.isdigit() and int(n)]))
    return hasil


def _rawi_halaman(sid, juz, hal):
    """(sanad [(kunci, [nomor rawi])], rekaman, jembatan) di halaman itu. Sanad dari layanan «esnad» Shamela; edisi tanpa
    layanan itu (mis. صحيح مسلم 1727) dijembatani lewat nomor hadits ke edisi pilihan Shamela yang sudah diunduh."""
    rekaman = shamela.rekaman_halaman(sid, juz, hal)
    sanad = [x for p, _ in rekaman for x in _sanad(p)]
    jembatan = None
    if not sanad and rekaman:
        tabel = [b for b in _tabel_kitab("hadits") if _karya(b) == _karya(sid) and b != sid and b in set(shamela.punya())]
        if tabel:
            jembatan = tabel[0]
            for p, _ in rekaman:
                i = shamela.rekaman_shamela(sid).get(int(p["shamela_page_id"]))
                for _, j, cocok in _seberang(sid, i, jembatan) if i is not None else ():
                    if cocok:
                        sanad += _sanad(shamela.rekaman_ke(jembatan, j))
    return list(dict.fromkeys((k, tuple(r)) for k, r in sanad)), rekaman, jembatan


def rawi(*a):
    """`rawi <id> <juz> <hal>`: rawi sanad di halaman itu dengan ringkasan rutbahnya; `rawi <nomor>`: tarjamah ringkas
    dan semua ucapan جرح وتعديل rawi itu beserta tempatnya di edisi lokal; `rawi "<nama>"`: cari nomor rawi menurut nama.
    Kembalikan jumlah rawi yang dicetak."""
    if len(a) == 3:
        angka = lambda x: int(x) if str(x).isdigit() else x
        sid = int(shamela._folder(a[0]).name)
        shamela.info(sid)
        juz, hal = angka(a[1]), angka(a[2])
        sanad, rekaman, jembatan = _rawi_halaman(sid, juz, hal)
        if not rekaman:
            raise SystemExit(f"[{sid}] TIDAK ADA halaman {juz}/{hal}. Yang ada: {shamela.daftar_juz(sid)}")
        semua_ = _rawi_semua()
        nomor = list(dict.fromkeys(n for _, r in sanad for n in r if n in semua_))
        # rawi yang ditautkan di teks halaman tetapi tidak ada di data sanad Shamela (hadits/athar tanpa data sanad)
        lain = [n for n in dict.fromkeys(int(x) for _, bagian in rekaman for b in bagian for x in TAUTAN_RAWI.findall(b))
                if n in semua_ and n not in nomor]
        if not nomor and not lain:
            tabel = [b for b in _tabel_kitab("hadits") if _karya(b) == _karya(sid)]
            print(f"[{sid}] {juz}/{hal}: tidak ada sanad dari layanan Shamela di halaman ini."
                  + (f" Edisi yang bertautan: {perintah(f'ambil {tabel[0]}')} (jembatan nomor hadits)." if tabel and tabel[0] not in set(shamela.punya()) else ""))
            return 0
        print(f"[{sid}] {juz}/{hal}: {len(sanad)} sanad, {len(nomor)} rawi (layanan sanad Shamela"
              + (f", lewat edisi [{jembatan}]" if jembatan else "") + "). Rincian جرح وتعديل: " + perintah("rawi <nomor>"))
        for k, r in sanad:
            print(f"  hadits Shamela #{k}: " + " > ".join(_nama_rawi(n) for n in r if n in semua_))
        if lain:
            print("  di luar data sanad Shamela (urut kemunculan di teks; rantainya baca sendiri): "
                  + "، ".join(_nama_rawi(n) for n in lain))
        print("rawi:")
        print("\n".join(_baris_rawi(n) for n in nomor + lain))
        print("Penunjuk saja: rutbah dan ucapan ulama dikutip dari kitab rijal yang dibaca sendiri, bukan dari baris ini.")
        return len(nomor + lain)
    x = a[0].strip().lstrip("#")
    if x.isdigit():
        r = _rawi_semua().get(int(x))
        if r is None:
            raise SystemExit(f"Rawi #{x} tidak ada di tabel rawi Shamela; cari nomornya: " + perintah('rawi "<nama>"'))
        print(f"#{x} {_bersih(r['long_name'] or r['short_name'])}")
        for k, v in _ringkasan(r).items():
            print(f"  {k}: {v}")
        ucapan = _json(r["criticism_text"], "garh")
        if not ucapan:
            print("  (tabel ini tidak memuat ucapan جرح وتعديل untuk rawi ini)")
        semua_ = [(teks, sumber) for _, daftar in ucapan for teks, sumber, *_ in daftar]
        letak = iter(_letak_ucapan(semua_, _nama_inti(r)))
        for ulama, daftar in ucapan:
            print(f"\n  {ulama}:")
            for teks, sumber, *_ in daftar:
                print(f"    «{teks}» — {sumber}\n      {next(letak)}")
        shamela.lepas()
        print("\nPenunjuk saja: yang dikutip di bahts = lafaz di halaman kitab rijal yang dibaca sendiri, dan lolos `cek`.")
        return 1
    q = norma.padat(x)
    if len(q) < 3:
        raise SystemExit("Tulis nama rawi (paling sedikit 3 huruf Arab), nomor rawi, atau <id> <juz> <hal>.")
    kena = [n for n, r in _rawi_semua().items() if q in norma.padat(f"{r['short_name']} {r['long_name']}")]
    for n in kena[:RAWI_MAKS]:
        print(_baris_rawi(n))
    if len(kena) > RAWI_MAKS:
        print(f"(ditampilkan {RAWI_MAKS} dari {len(kena)}; persempit namanya)")
    return len(kena)


# --- akar kata ---

AKAR_MAKS = 30  # kelompok bentuk kata yang dicetak `akar`
SAMBUNG = ("وبال", "وكال", "فبال", "فكال", "ولل", "فلل", "وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ك", "ل")
HAMZAH_AKAR = str.maketrans("أإآؤئ", "ءءءءء")  # kamus menulis hamzah akar sebagai «ء» («ءخذ»)
POKOK_MIN = 3  # huruf: «وقف» tidak dikelompokkan ke «قف» (perintah dari akar yang sama)
KATA_ARAB = re.compile(r"[ء-غف-يٱ-ۓً-ٰٟـ]+")


@functools.cache
def _kamus_akar():
    """(kolom token, kolom akar) tabel root_dictionary sebagai array pyarrow (dibaca sekali, ±0,3 detik)."""
    siapkan("akar")
    import pyarrow.parquet as pq
    t = pq.read_table(ROOT / TABEL["akar"])
    return t["token"], t["roots"].combine_chunks()


def _bentuk_akar(akar):
    """{bentuk `norm`: semua akarnya di kamus} kata berakar itu di kamus Shamela, ditambah akarnya sendiri (kamus tidak
    memuat kata yang sama persis dengan akarnya, mis. «قرض», «شفع»). Kosong kalau akarnya tidak ada di kamus."""
    import pyarrow.compute as pc
    token, akar_ = _kamus_akar()
    baris = pc.unique(pc.filter(pc.list_parent_indices(akar_), pc.equal(pc.list_flatten(akar_), akar)))
    bentuk = {}
    for t, r in zip(pc.take(token, baris).to_pylist(), pc.take(akar_, baris).to_pylist()):
        bentuk.setdefault(norma.norm(t), set()).update(r)
    if bentuk:
        bentuk.setdefault(norma.norm(akar), set()).add(akar)
    return bentuk


def _pokok(w, bentuk):
    """Bentuk kata tanpa huruf sambung dan «ال» di depannya (و ف ب ك ل، لل، ال), selama sisanya masih bentuk akar itu
    dan paling sedikit POKOK_MIN huruf: kelompok yang sama dengan yang dicocokkan `cari` untuk kata pertama frasa."""
    for s in SAMBUNG:
        sisa = w[len(s):]
        if w.startswith(s) and len(sisa) >= POKOK_MIN and sisa in bentuk:
            return _pokok(sisa, bentuk)
    return w


def akar(sid, akar_):
    """`akar <id> <akar>`: bentuk kata berakar itu yang ada di kitab (matan dan حاشية), dikelompokkan seperti `cari`
    mencocokkan kata (huruf sambung dan «ال» di depan boleh), urut dari yang paling sering, dengan ejaan kitab itu
    sendiri. Untuk menemukan istilah yang tidak tertangkap frasa atau `--potongan` («الشفيع» untuk akar شفع).
    Kembalikan jumlah kata yang cocok."""
    sid = int(shamela._folder(sid).name)
    shamela.info(sid)
    a = norma.norm(str(akar_).translate(HAMZAH_AKAR)).replace(" ", "")
    if not 2 <= len(a) <= 5 or not re.fullmatch(r"[ء-ي]+", a):
        raise SystemExit("Tulis akarnya dengan 2-5 huruf Arab tanpa spasi, mis. " + perintah(f'akar {sid} "شفع"'))
    # akar yang diketik tanpa hamzah («اخذ») digabung dengan bentuk berhamzahnya («ءخذ»): kamus memakai keduanya
    dicari = {a, a.replace("ا", "ء")}
    bentuk = {}
    for x in dicari:
        for k, r in _bentuk_akar(x).items():
            bentuk.setdefault(k, set()).update(r)
    if not bentuk:
        raise SystemExit(f"Akar «{a}» tidak ada di kamus akar Shamela (hamzah akar ditulis «ء», mis. «ءخذ»).")
    kunci, ejaan = {}, {}  # kata kitab tanpa harakat -> bentuk `norm`; (bentuk, ejaan kitab) -> jumlah
    for i in range(len(shamela._indeks(sid)[0])):
        p = shamela.rekaman_ke(sid, i)
        for bagian, _ in norma.BAGIAN:
            for w in KATA_ARAB.findall(TAGS.sub(" ", p.get(bagian) or "")):
                w = norma.HARAKAT.sub("", w)
                k = kunci.get(w)
                if k is None:
                    k = kunci[w] = norma.norm(w)
                if k in bentuk:
                    ejaan[k, w] = ejaan.get((k, w), 0) + 1
    shamela.lepas()
    hitung, tulis = {}, {}  # bentuk -> jumlah; bentuk -> ejaan kitab yang paling sering
    for (k, w), n in sorted(ejaan.items(), key=lambda x: -x[1]):
        hitung[k] = hitung.get(k, 0) + n
        tulis.setdefault(k, w)
    kelompok = {}
    for k, n in hitung.items():
        kelompok.setdefault(_pokok(k, bentuk), []).append((n, k))
    urut = sorted(kelompok.items(), key=lambda x: -sum(n for n, _ in x[1]))
    total = sum(hitung.values())
    if not total:
        print(f"[{sid}] TIDAK ADA kata berakar {a} di kitab ini")
        return 0
    print(f"[{sid}] akar {a}: {total} kata, {len(hitung)} bentuk, {len(kelompok)} kelompok. Kamus akar Shamela: satu kata "
          "bisa bertanda beberapa akar (ditandai «[juga akar …]», mis. «بعد» untuk وعد) dan nama orang ikut terhitung («الشافعي» "
          "untuk شفع), jadi pilih sendiri yang memang istilah masalahmu, lalu cari tempatnya dengan `cari`.")
    for pokok, isi in urut[:AKAR_MAKS]:
        isi.sort(reverse=True)
        # ejaan kitab untuk pokoknya: kalau pokoknya tidak tertulis sendirian, huruf sambung di depan bentuk yang paling
        # sering dipotong (huruf sambung tidak diubah `norm`; huruf di dalam kata bisa: «السماوات» -> «السموات»)
        k = isi[0][1]
        nama = tulis.get(pokok) or tulis[k][len(k) - len(pokok):]
        rincian = "، ".join(f"{tulis[k]} {n}" for n, k in isi[:4]) + ("…" if len(isi) > 4 else "")
        # kamus juga mencatat kata benda itu sendiri sebagai «akar» («شفعة»، «سماء»); akar tiga huruf («بعد») tetap akar
        lain = sorted(r for r in bentuk[pokok] - dicari if len(r) <= 3 or norma.norm(r) != pokok)
        print(f"  {nama}: {sum(n for n, _ in isi)}× ({rincian})" + (f" [juga akar {'، '.join(lain)}]" if lain else "")
              + " -> " + perintah(f'cari {sid} "{nama}"'))
    if len(urut) > AKAR_MAKS:
        print(f"(ditampilkan {AKAR_MAKS} dari {len(urut)} kelompok; sisanya lebih jarang)")
    return total
