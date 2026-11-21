# SPDX-License-Identifier: AGPL-3.0-or-later
"""`pustaka <folder>`: susun draf baris `#R` (المصادر والمراجع) siap tempel langsung dari metadata `kartu` kitab lokal
yang benar-benar berbukti di catatan kaki naskah (tanpa internet, tidak mengubah berkas), sekaligus menampilkan
kitab yang belum masuk `#R` dan baris `#R` yang tidak terhubung ke bukti catatan kaki."""
import re

import gelar
import norma
import shamela
import waqfeya
from cek_seluruh import cocok_sid_pustaka, kumpul_bukti_pustaka
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


def cetak(folder):
    """Cetak draf `#R` dari kitab berbukti di catatan kaki + status kecocokannya dengan `#R` saat ini."""
    h = periksa(folder)
    ctx = h.ctx
    gaya = ctx.meta.get("pustaka_gaya", "judul")
    muallif = gaya == "muallif"
    sids, wids = kumpul_bukti_pustaka(ctx.penunjuk)
    non_mushaf = [(n, teks) for n, teks in ctx.pustaka_baris if not _mushaf(teks)]
    ada_mushaf = any(_mushaf(teks) for _, teks in ctx.pustaka_baris)
    terhubung = set()
    entri = []  # [(baris_draf, status_label, catatan_tambahan)]
    for sid in sorted(sids):
        try:
            m = shamela.info(sid)
        except (LookupError, OSError, ValueError, SystemExit):
            entri.append((f"[kitab {sid} belum diunduh]", "BELUM DIUNDUH", ""))
            continue
        cocok = [i for i, (_, teks) in enumerate(non_mushaf) if cocok_sid_pustaka(sid, teks)]
        terhubung.update(cocok)
        baris = format_baris(_ekstrak_kartu(m), gaya=gaya)
        entri.append((baris, "SUDAH DI #R" if cocok else "BELUM DI #R", f"kitab {sid}"))
    for w in sorted(wids):
        if not waqfeya.ada(w):
            entri.append((f"[kitab {w} belum diunduh]", "BELUM DIUNDUH", ""))
            continue
        cocok = [i for i, (_, teks) in enumerate(non_mushaf) if waqfeya.judul_disebut(w, teks)]
        terhubung.update(cocok)
        d = waqfeya.data(w)
        baris = format_baris({"judul": d["judul"], "pengarang": d.get("pengarang") or "", "wafat": "",
                              "muhaqqiq": "", "penerbit": "", "cetakan": "", "tahun": ""}, gaya=gaya)
        entri.append((baris, "SUDAH DI #R" if cocok else "BELUM DI #R", f"{w}; lengkapi data cetak dari scan: kartu {w}"))
    entri.sort(key=lambda x: kunci_urut(x[0], muallif))
    belum = sum(1 for _, st, _ in entri if st == "BELUM DI #R")
    print(f"Draf #R المصادر والمراجع (gaya: {gaya}; {len(entri)} kitab berbukti, {belum} belum ada di #R):")
    if ctx.ayat_idx:
        st_q = "SUDAH DI #R" if ada_mushaf else "BELUM DI #R"
        print(f"  [{st_q}] القرآن الكريم.")
    for baris, st, ket in entri:
        print(f"  [{st}] {baris}" + (f"  # {ket}" if ket else ""))
    if not entri and not ctx.ayat_idx:
        print("  (belum ada kitab berbukti Shamela/Waqfeya atau ayat {Q:} di naskah ini)")
    sisa = [(n, teks) for i, (n, teks) in enumerate(non_mushaf) if i not in terhubung]
    if sisa:
        print(f"\nBaris #R saat ini yang tidak terhubung ke bukti Shamela/Waqfeya ({len(sisa)} — bisa sumber luar/PDF, atau tidak dirujuk):")
        for n, teks in sisa:
            print(f"  baris {n}: {teks}")
