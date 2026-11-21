# SPDX-License-Identifier: AGPL-3.0-or-later
"""`pustaka <folder>`: susun draf baris `#R` (المصادر والمراجع) siap tempel langsung dari metadata `kartu` kitab lokal
yang benar-benar berbukti di catatan kaki naskah (tanpa internet, tidak mengubah berkas), sekaligus menampilkan
kitab yang belum masuk `#R` dan baris `#R` yang tidak terhubung ke bukti catatan kaki."""
import re
from collections import Counter

import gelar
import norma
import shamela
import waqfeya
from dasar import ANGKA_LATIN, WAQFEYA_BUKTI
from olah import _mushaf, kunci_urut, periksa

_BIDANG = (
    ("judul", re.compile(r"^الكتاب$")),
    ("pengarang", re.compile(r"^(?:المؤلف|المؤلفون)$")),
    ("muhaqqiq", re.compile(r"^(?:المحقق|تحقيق|تحقيق وتخريج|حققه|دراسة وتحقيق|اعتنى به|أشرف على طبعه)$")),
    ("penerbit", re.compile(r"^(?:الناشر|دار النشر|مطبعة)$")),
    ("cetakan", re.compile(r"^الطبعة$")),
    ("tahun", re.compile(r"^(?:سنة النشر|عام النشر|تاريخ النشر|النشر)$")),
)
_TITIK_DUA = re.compile(r"[:：]")
_H = r"[\u064b-\u065f\u0670\u0640]*"
_WAFAT = re.compile(
    rf"\s*\(?\s*(?:ال{_H}م{_H}ت{_H}و{_H}ف{_H}[ىي]{_H}|ت{_H})\s*[:：]?\s*([0-9٠-٩]{{1,4}})\s*(?:ه{_H})?\s*\)?"
)


def _ekstrak_kartu(m):
    """Ambil (judul, pengarang, wafat, muhaqqiq, penerbit, cetakan, tahun) bersih tanpa gelar dari metadata Shamela."""
    data = {}
    for baris in (m.get("betaka_text") or "").replace("\r", "\n").splitlines():
        m_col = _TITIK_DUA.search(baris)
        if not m_col:
            continue
        kunci_teks = baris[:m_col.start()].strip()
        nilai_mentah = baris[m_col.end():].strip()
        if not nilai_mentah:
            continue
        kunci_polos = norma.HARAKAT.sub("", kunci_teks)
        for kunci, pola in _BIDANG:
            if kunci not in data and pola.match(kunci_polos):
                # `gelar.buang_gelar` hanya mengenali «:» ASCII; kirim dengan «:» agar label ber-«：» tetap bersih dari gelar
                nilai = nilai_mentah if kunci == "judul" else gelar.buang_gelar(f"{kunci_teks}: {nilai_mentah}").partition(":")[2].strip()
                if nilai:
                    data[kunci] = nilai
                break
    judul = data.get("judul") or (m.get("title_ar") or "").split(" - ")[0].strip()
    pengarang = data.get("pengarang") or gelar.buang_gelar("المؤلف: " + (m.get("main_author_name_ar") or "")).partition(":")[2].strip()
    wafat = ""
    if pengarang and (mw := _WAFAT.search(pengarang)):
        wafat = f"{mw.group(1)}هـ"
        pengarang = _WAFAT.sub("", pengarang).strip(" ،,-")
    elif m.get("death_year_hijri"):
        wafat = f"{m['death_year_hijri']}هـ"
    return {
        "judul": judul.rstrip(" .،"),
        "pengarang": pengarang.rstrip(" .،"),
        "wafat": wafat,
        "muhaqqiq": (data.get("muhaqqiq") or "").rstrip(" .،"),
        "penerbit": (data.get("penerbit") or "").rstrip(" .،"),
        "cetakan": (data.get("cetakan") or "").rstrip(" .،"),
        "tahun": (data.get("tahun") or "").rstrip(" .،"),
    }


def format_baris(info_kartu, gaya="judul"):
    """Susun satu baris `#R` siap tempel dari kamus `_ekstrak_kartu` sesuai `@pustaka_gaya` (`judul` atau `muallif`)."""
    rinci = []
    if info_kartu["muhaqqiq"]:
        rinci.append(f"تحقيق: {info_kartu['muhaqqiq']}")
    if info_kartu["penerbit"]:
        rinci.append(info_kartu["penerbit"])
    if info_kartu["cetakan"]:
        c = info_kartu["cetakan"]
        butuh_prefix = not c.startswith(("ط", "الطبعة")) and not re.match(r"^[\d٠-٩]{3,4}\s*(?:هـ|م)", c)
        rinci.append(f"الطبعة {c}" if butuh_prefix else c)
    if info_kartu["tahun"] and info_kartu["tahun"] not in (info_kartu["cetakan"] or ""):
        rinci.append(info_kartu["tahun"])
    ekor_data = "، ".join(rinci)
    if gaya == "muallif":
        nama = f"**{info_kartu['pengarang']}**" if info_kartu["pengarang"] else ""
        if nama and info_kartu["wafat"]:
            nama += f" (ت {info_kartu['wafat']})"
        bagian = [x for x in (nama, f"__{info_kartu['judul']}__", ekor_data) if x]
        return ". ".join(bagian) + "."
    bagian = [x for x in (info_kartu["judul"], info_kartu["pengarang"], ekor_data) if x]
    return "، ".join(bagian) + "."


def _ejaan(teks):
    return norma.norm(teks.translate(ANGKA_LATIN))


def _termuat(bagian, teks):
    return bool(bagian) and f" {bagian} " in f" {teks} "


def _buku(penunjuk):
    shamela_id, waqfeya_id = set(), set()
    for p in penunjuk:
        for bukti in p.get("bukti", ()):
            if m := WAQFEYA_BUKTI.fullmatch(bukti):
                waqfeya_id.add(m[1])
            else:
                sid = bukti.split("|", 1)[0].strip()
                if sid.isdecimal():
                    shamela_id.add(int(sid))
    return sorted(shamela_id), sorted(waqfeya_id)


def _cocok(data, judul, nama_katalog, pustaka):
    """Nomor baris dengan judul sepadan, dan subset yang memuat data cetak dari kartu."""
    judul = {_ejaan(j) for j in judul}
    nama = {_ejaan(data["pengarang"]), _ejaan(nama_katalog or "")}
    penerbitan = {_ejaan(data[k]) for k in ("muhaqqiq", "penerbit") if data[k]}
    cetak = (penerbitan | {_ejaan(data["cetakan"]), _ejaan(data["tahun"])}) - {""}
    # Tahun yang sudah disebut dalam label satu cetakan bukan petunjuk yang kedua.
    mandiri = {d for d in cetak if not any(d != lain and _termuat(d, lain) for lain in cetak)}
    calon, cocok = set(), set()
    for n, teks in pustaka.items():
        if not any(_termuat(j, teks) for j in judul):
            continue
        calon.add(n)
        if (len(mandiri) >= 2 and penerbitan and all(_termuat(d, teks) for d in cetak)
                and any(_termuat(p, teks) for p in nama)):
            cocok.add(n)
    return calon, cocok


def cetak(folder):
    """Cetak blok #R yang bisa ditempel, lalu petunjuk per kitab untuk mencocokkannya dengan daftar saat ini."""
    ctx = periksa(folder).ctx
    gaya = ctx.meta.get("pustaka_gaya", "judul")
    sids, wids = _buku(ctx.penunjuk)
    baris_r = {n: teks for n, teks in ctx.pustaka_baris if not _mushaf(teks)}
    pustaka = {n: _ejaan(teks) for n, teks in baris_r.items()}
    draf, sid_cocok, catatan, terlihat = [], {}, {}, set()
    for sid in sids:
        try:
            m = shamela.info(sid)
        except (LookupError, OSError, ValueError, SystemExit):
            catatan[sid] = "kartu lokal belum terbaca"
            continue
        data = _ekstrak_kartu(m)
        alias = shamela.judul_pokok(m["title_ar"]) + shamela.judul_pokok(data["judul"])
        calon, cocok = _cocok(data, alias, m.get("main_author_name_ar"), pustaka)
        terlihat.update(calon)
        sid_cocok[sid] = calon, cocok
        draf.append(format_baris(data, gaya=gaya))
    pemilik = Counter(n for _, cocok in sid_cocok.values() for n in cocok)
    for sid, (calon, cocok) in sid_cocok.items():
        if sah := sorted(n for n in cocok if pemilik[n] == 1):
            catatan[sid] = "data cetak cocok di #R baris " + ", ".join(map(str, sah))
        elif calon:
            catatan[sid] = "judul ditemukan, edisi perlu dicek di #R baris " + ", ".join(map(str, sorted(calon)))
        else:
            catatan[sid] = "judul belum ditemukan di #R"
    for wid in wids:
        if not waqfeya.ada(wid):
            catatan[wid] = "scan belum diunduh"
            continue
        d = waqfeya.data(wid)
        calon = {n for n, teks in baris_r.items() if waqfeya.judul_disebut(wid, teks)}
        terlihat.update(calon)
        catatan[wid] = f"salin data cetak dari scan: kartu {wid}"
        if calon:
            catatan[wid] += " (judul ditemukan di #R baris " + ", ".join(map(str, sorted(calon))) + ")"
        draf.append(format_baris(dict(judul=d["judul"], pengarang=d["pengarang"] or "", wafat="", muhaqqiq="",
                                      penerbit="", cetakan="", tahun=""), gaya=gaya))
    if draf or ctx.ayat_idx:
        print("Draf kitab berbukti. Periksa data cetak dan gabungkan dengan rujukan lain di #R.")
        print("#R المصادر والمراجع")
        if ctx.ayat_idx:
            print("القرآن الكريم.")
        for baris in sorted(draf, key=lambda b: kunci_urut(b, gaya == "muallif")):
            print(baris)
    else:
        print("Belum ada kartu kitab berbukti atau ayat {Q:} untuk menyusun draf.")
    if catatan:
        print("\nPemeriksaan #R:")
        for sid, pesan in catatan.items():
            print(f"  {sid}: {pesan}")
    if sisa := sorted(baris_r.keys() - terlihat):
        print("\nBaris #R di luar padanan kitab berbukti; periksa sumber lain/PDF:")
        for n in sisa:
            print(f"  baris {n}: {baris_r[n]}")
