# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cara menukil (طرق نقل المعلومات) menurut عبد الوهاب أبو سليمان، كتابة البحث العلمي (Shamela 8350): lafaz kitab ditulis
di antara tanda petik (ص113، 173), nukilan makna ditandai «انظر»/«راجع» (ص114، 173) dan bukan lafaz kitab yang hanya diganti beberapa
katanya (ص113), dan kutipan berukuran wajar (ص123، 219). Kitab itu membolehkan الاختصار memakai kata pengarang (ص114)
dan tidak melarang «انظر» pada kutipan lafaz: batas kata dan larangan itu aturan repo, ditulis begitu di tiap pesan. Semuanya perhatian, tidak pernah GAGAL: `cek` tetap hanya memutus
apakah teks ada di halaman buktinya."""
import functools, re

import norma
from cek_tautsiq import BUKAN_RUJUKAN
from dasar import AYAT_DI_KUTIPAN, MERUJUK_KATA, TAKHRIJ_AWAL
from kitab_lokal import gabung
from cek_sumber import PERANTARA
from petik import diantar_qaul, luar_petik, seragam

# Kata berurutan paling sedikit yang sama persis dengan halaman bukti, di luar tanda petik, supaya disebut salinan lafaz:
# «التغيير البسيط لبعض عبارات المؤلف أو كلماته لا يعني إعادة صياغتها» (ص113; kitab itu tidak memberi angka). Angka di
# sini aturan repo, dari naskah nyata: istilah dan ungkapan baku («لا يجوز بيع ما ليس عنده») jarang lewat 6 kata.
SALIN_MIN = 8
# Kutipan bertanda petik terpanjang di luar nash Quran dan Sunnah (AGENTS.md «Panjang kutipan»): lebih dari empat
# baris dipisah jadi paragraf sendiri (ص219); pedoman risalah Jāmiʿat al-Imām 2022 ص46 memakai batas 60 kata.
KUTIPAN_MAKS = 60
# tanda bahwa penulis mengubah susunan nukilannya: «انظر»، «أنظر»، «انظره في»، «ينظر»، «راجع»، «يراجع»، «بتصرف»
ISYARAT = re.compile(rf"(?<![ء-ي])[وف]?(?:(?:{MERUJUK_KATA})(?:ه|ها)?|بتصرف)(?![ء-ي])")
BUKAN_NUKILAN = BUKAN_RUJUKAN + ("متفق عليه",)  # rujukan ayat dan takhrij: nash yang memang dikutip utuh (ص112)
# deret nama dan sanad («علي بن أبي طالب وعبد الله بن عمرو») tidak bisa ditulis ulang: bukan salinan lafaz
NASAB = frozenset("بن بنت ابو ابي ابا ام عبد".split())


def _kata(teks):
    """[(kata yang disamakan tulisannya, kata aslinya)] teks, tanpa penanda ayat."""
    return [(k, asli) for asli in AYAT_DI_KUTIPAN.sub(" ", teks).split() for k in norma.norm(asli).split()]


@functools.lru_cache(maxsize=512)
def _gram_halaman(sid, juz, p1, p2):
    """Tiap deret SALIN_MIN kata berurutan di halaman bukti (matan dan حاشية); halaman yang bersambung dirangkai,
    jadi salinan yang menyeberang ke halaman berikutnya tetap terbaca."""
    gram = set()
    for r in gabung(int(sid), juz, p1, p2):
        for bagian, _ in norma.BAGIAN:
            kata = [k for k, _ in _kata(norma.PENANDA.sub(" ", r.get(bagian) or ""))]
            gram.update(tuple(kata[i:i + SALIN_MIN]) for i in range(len(kata) - SALIN_MIN + 1))
    return gram


def _nash(isi):
    isi = norma.HARAKAT.sub("", isi).lstrip()
    return bool(TAKHRIJ_AWAL.match(isi)) or isi.startswith(BUKAN_NUKILAN)


def salinan(penggal, mk, isi, terbukti):
    """Perhatian kalau teks penulis sebelum catatan kaki (di luar tanda petik) memuat SALIN_MIN kata atau lebih yang
    berurutan sama persis dengan halaman buktinya, atau None: itu lafaz kitab, bukan إعادة الصياغة."""
    if _nash(isi) or not terbukti:
        return None
    pasangan = _kata(luar_petik(seragam(penggal).replace(mk, " ") if mk else penggal))
    kata = [k for k, _ in pasangan]
    if len(kata) < SALIN_MIN:
        return None
    gram = set().union(*(_gram_halaman(*b) for b in terbukti))
    terpanjang, i = [], 0
    while i <= len(kata) - SALIN_MIN:
        j = i
        while j <= len(kata) - SALIN_MIN and tuple(kata[j:j + SALIN_MIN]) in gram:
            j += 1
        deret = pasangan[i:j + SALIN_MIN - 1] if j > i else []
        nama = sum(k.lstrip("و") in NASAB for k, _ in deret)
        if len(deret) > len(terpanjang) and 4 * nama < len(deret):
            terpanjang = deret
        i = max(j, i + 1)
    if not terpanjang:
        return None
    asli = " ".join(dict.fromkeys(a for _, a in terpanjang[:SALIN_MIN]))
    return (f"{len(terpanjang)} kata berurutan di luar tanda petik sama persis dengan halaman buktinya «{asli}…»: "
            f"beri tanda petik, atau tutup kitabnya lalu tulis ulang dengan kalimat sendiri; mengganti beberapa kata saja "
            f"bukan إعادة الصياغة (أبو سليمان، كتابة البحث العلمي، ص113). الاختصار yang memang memakai kata pengarang "
            f"(ص114) boleh dibiarkan dan disebut di laporan akhir; batas {SALIN_MIN} kata aturan repo  || fn: {isi[:45]}")


def isyarat(penggal, mk, isi, terbukti, kutipan_di_catatan):
    """Perhatian kalau tanda «انظر»/«راجع» tidak sesuai cara menukilnya, atau None. «تشير هذه الكلمة إلى تصرف
    الكاتب في النقل» (ص114): nukilan makna memakainya. Aturan repo dari kalimat itu: kutipan lafaz yang hanya diantar
    «قال …:» tidak memakainya; kalimat yang menggabungkan uraian penulis dengan kutipan lafaz pendek (الجمع، ص115)
    boleh memakai keduanya."""
    if _nash(isi) or not terbukti:
        return None
    bertanda = bool(ISYARAT.search(norma.HARAKAT.sub("", isi)))
    if mk is None:
        if bertanda or kutipan_di_catatan or PERANTARA.search(isi):  # «نقلا عن …» sudah menyebut cara menukilnya
            return None
        return (f"nukilan makna tanpa «انظر:»: catatan kaki untuk kalimat tanpa tanda petik diawali «انظر:» atau «راجع:» "
                f"(أبو سليمان، كتابة البحث العلمي، ص114، 173); kalau itu lafaz kitab, beri tanda petik  || fn: {isi[:45]}")
    s = seragam(penggal)
    if bertanda and ISYARAT.match(norma.HARAKAT.sub("", isi).lstrip()) and mk in s and diantar_qaul(s[:s.rfind(mk) - 1]):
        return (f"kutipan lafaz «{mk[:30]}» dirujuk «انظر:»: kata itu tanda nukilan makna (أبو سليمان، كتابة البحث العلمي، "
                f"ص114، 173); buang «انظر:» dari catatan kakinya (aturan repo)  || fn: {isi[:45]}")
    return None


def panjang(mk, isi):
    """Perhatian kalau kutipan bertanda petik (bukan ayat atau hadits) lebih dari KUTIPAN_MAKS kata, atau None."""
    if mk is None or _nash(isi):
        return None
    n = len(_kata(mk))
    if n <= KUTIPAN_MAKS:
        return None
    return (f"kutipan {n} kata «{mk[:30]}…»: lebih dari {KUTIPAN_MAKS} kata; kutip lafaz kuncinya saja dan ringkas sisanya "
            f"dengan «انظر:», kecuali nash yang memang harus utuh (definisi, nash pokok khilaf, kalimat yang dibantah) "
            f"(أبو سليمان، كتابة البحث العلمي، ص112، 123، 219; batas {KUTIPAN_MAKS} kata aturan repo)  || fn: {isi[:45]}")
