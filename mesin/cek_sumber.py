# SPDX-License-Identifier: AGPL-3.0-or-later
"""«Standar sumber»: pendapat mazhab dari kitab mu'tamad mazhab itu, ijmak dari kitab ulama yang menukilnya, dan
urutan sumber di catatan kaki «انظر:» dari pengarang yang lebih dulu wafat."""
import functools, re

import norma
from dasar import HERE, MERUJUK_KATA
from kitab_lokal import bagian_kitab, kitab_meta
from petik import luar_petik, seragam

# Standar sumber (AGENTS.md «Standar sumber»; dasar: عبد الوهاب أبو سليمان، كتابة البحث العلمي، ص70-73 dan 162-163):
# pendapat mazhab diambil dari kitab mazhab itu, ijmak/kesepakatan dari kitab ulama yang menukilnya, bukan dari kitab
# modern (مرجع). Perantara boleh hanya kalau asalnya tidak bisa didapat, dan catatan kakinya menyebut «مقتبس من» / «نقلا عن».
MAZHAB = {  # mazhab -> (kategori Shamela, pola penyebutannya di kalimat)
    "حنفي": (14, r"الحنفية|الحنفي|الأحناف|أبي حنيفة|أبو حنيفة|أبا حنيفة"),
    "مالكي": (15, r"المالكية|المالكي|الإمام مالك|مذهب مالك|قول مالك|قال مالك|وقال مالك"),
    "شافعي": (16, r"الشافعية|الشافعي"),
    "حنبلي": (17, r"الحنابلة|الحنبلي|الإمام أحمد|أحمد بن حنبل|مذهب أحمد|قول أحمد|قال أحمد|رواية عن أحمد"),
}
IJMAK = re.compile(r"أجمع|الإجماع على|بالإجماع|إجماع العلماء|إجماع الفقهاء|اتفق|باتفاق|بالاتفاق|لا خلاف|بلا خلاف|الجمهور|جمهور")
KATA = r"(?<![ء-ي])(?:{})(?![ء-ي])"  # kata utuh Arab (bukan potongan: «ذكر» bukan bagian «الذكر»)
# perantara yang disebut di catatan kaki: «مقتبس من …» (istilah kitab 8350) atau «نقلا عن …», diikuti nama sumbernya,
# bukan sekadar nama mazhab atau «غيره» («نقلا عن الحنفية» tidak menyebut kitab perantara mana pun)
PERANTARA = re.compile(r"(?:نقلا|نقلًا) عن|مقتبس من")
BUKAN_PERANTARA = re.compile(r"^\s*(?:ال)?(?:حنفية|مالكية|شافعية|حنابلة|أحناف|غيره|غيرها|غيرهم)(?![ء-ي])")
# kalimat yang menyebut mazhab tanpa menisbatkan pendapat kepadanya: penulis sendiri sudah menyebut perantaranya di matan
# («ذكر ابن قدامة أن أبا حنيفة…»، «نقل…»), atau sedang membantah/menilai dalilnya («ونوقش استدلال الحنفية…»)
SEBUT = re.compile(KATA.format(r"[وف]?(?:ذكر|ذكره|ذكرهما|نقل|نقله|حكى|حكاه|عزا|عزاه|نسبه|علل|نوقش|يناقش|اعترض|أجيب|أجاب)"))
KONTEMPORER = re.compile(KATA.format(r"مجمع الفقه|المجمع الفقهي|قرار المجمع|[وف]?(?:ال)?قرار(?:ات)?|هيئة كبار|اللجنة الدائمة"
                                     r"|المؤتمر|الندوة"))
FIKIH = {12, 14, 15, 16, 17, 18, 19, 20, 22}  # kategori fikih Shamela (mazhab, الفقه العام, masail, qadha, fatwa, qawaid)
USUL = {11}  # ijmak/jumhur juga dijaga di أصول الفقه
MODERN = 1350  # wafat sesudah tahun ini, atau tidak tercatat (99999: hidup, kolektif, tak diketahui) = kitab modern


@functools.cache
def mutamad():
    """{mazhab: {nomor kitab}} dari tabel ringkas dok/mutamad.md; kosong kalau berkasnya tidak ada."""
    f = HERE.parent / "dok" / "mutamad.md"
    hasil = {}
    if f.exists():
        for m in re.finditer(r"^\| (\S+) \| `\[([\d, ]+)\]` \|", f.read_text(encoding="utf8"), re.M):
            hasil[m.group(1)] = {int(x) for x in m.group(2).split(",")}
    return hasil


def _kitab_mazhab(mz, sid, v):
    """Bukti dari kitab mazhab mz: kitab daftar mu'tamad, atau kitab lama (wafat < MODERN) di kategori mazhab itu."""
    return int(sid) in mutamad().get(mz, ()) or (v["kategori"] == MAZHAB[mz][0] and v["wafat"] < MODERN)


def standar_sumber(penggal, isi, sid_bukti):
    """Catatan standar sumber satu catatan kaki (dinilai per bagian oleh standar_baris), atau None kalau data kitabnya tak
    terbaca. Takhrij/ayat, perantara yang disebut («مقتبس من …»، «نقلا عن …»), dan masalah kontemporer tidak dinilai, tetapi
    bukti kitab mazhabnya tetap dihitung untuk bagian itu."""
    if not sid_bukti:
        return None
    meta = {sid: kitab_meta(int(sid)) for sid in sid_bukti}
    if any(v is None for v in meta.values()):
        return None
    ada = {mz for mz in MAZHAB for sid, v in meta.items() if _kitab_mazhab(mz, sid, v)}
    teks = norma.HARAKAT.sub("", penggal)
    perantara = any(not BUKAN_PERANTARA.match(isi[m.end():]) for m in PERANTARA.finditer(isi))
    if perantara or isi.startswith(("أخرجه", "رواه", "سورة")) or KONTEMPORER.search(teks):
        # tidak dinilai (takhrij: nama imam = mukharrij), tetapi bukti kitab mazhabnya tetap dihitung untuk bagian itu
        return {"isi": isi, "disebut": set(), "ada": ada, "ijmak": False, "judul": "", "n": None}
    judul = "، ".join(dict.fromkeys(v["judul"] for v in meta.values()))
    # kategori usul, akhlak, tafsir… tidak dibagi per mazhab di Shamela: di sana mesin tidak bisa menilai kitab mazhabnya
    fikih = any(v["kategori"] in FIKIH for v in meta.values())
    # mazhab yang disebut di dalam kutipan kitab lama adalah ucapan pengarang kitab itu, bukan penisbatan penulis bahts;
    # kutipan dari kitab modern («وهو مذهب الحنفية…» dari sebuah ensiklopedi) tetap dihitung
    modern = any(v["wafat"] >= MODERN for v in meta.values())
    nilai = teks if modern else luar_petik(seragam(teks))
    disebut = ({mz for mz, (_, pola) in MAZHAB.items() if re.search(pola, nilai)}
               if fikih and not SEBUT.search(luar_petik(seragam(teks))) else set())
    # ijmak tidak dibebaskan SEBUT: «نقلت الموسوعة عن ابن رجب … بالاتفاق» tetap diminta dari kitab penukil tertuanya
    ijmak = (IJMAK.search(teks) and any(v["kategori"] in FIKIH | USUL for v in meta.values())
             and all(v["wafat"] >= MODERN for v in meta.values()))
    return {"isi": isi, "disebut": disebut, "ada": ada, "ijmak": bool(ijmak), "judul": judul, "n": None}


MERUJUK = re.compile(rf"^(?:{MERUJUK_KATA})(?![ء-ي])")  # nukilan makna: beberapa sumber untuk satu hal


def urutan_sumber(isi, bukti):
    """Perhatian kalau catatan kaki «انظر: …» menyebut beberapa kitab tidak urut dari pengarang yang lebih dulu wafat
    (أبو سليمان، كتابة البحث العلمي، ص73), atau None. Urutannya dibaca dari letak judul/pengarang tiap kitab di catatan
    kaki (bagian_kitab); yang letaknya tidak dikenali, perantara («مقتبس من …»، «نقلا عن …»), dan kitab yang tahun
    wafat pengarangnya tidak tercatat tidak dinilai. Kutipan lafaz tidak dinilai: kitab yang lafaznya dikutip boleh di depan."""
    # label «في …:» = sumber dibagi per hal («انظر في الحديث: …، وفي الأثر: …»), bukan beberapa sumber untuk satu hal;
    # «تحقيق:» dan «انظر:» bukan label
    if (not MERUJUK.match(isi) or PERANTARA.search(isi) or len({b[0] for b in bukti}) < 2
            or re.search(r"(?<![ء-ي])و?في\s+[^:،؛.]{1,40}:", isi)):
        return None
    urut = [bb[0][0] for _, bb in bagian_kitab(isi, bukti)]
    if len(urut) < 2:
        return None
    meta = [(sid, kitab_meta(int(sid))) for sid in urut]
    meta = [(sid, v) for sid, v in meta if v and v["wafat"] < 99999]
    for (a, va), (b, vb) in zip(meta, meta[1:]):
        if va["wafat"] > vb["wafat"]:
            return (f"urutan sumber: «{va['judul']}» (pengarangnya wafat {va['wafat']}هـ) disebut sebelum «{vb['judul']}» "
                    f"(wafat {vb['wafat']}هـ); beberapa sumber untuk satu hal diurutkan dari pengarang yang lebih dulu wafat "
                    f"(أبو سليمان، كتابة البحث العلمي، ص73)  || fn: {isi[:45]}")
    return None


def standar_baris(catat):
    """Perhatian standar sumber satu bagian naskah (sampai judul atau «القول/الرأي/المذهب …» berikutnya). Pendapat mazhab
    dinilai sebagian: «القول الأول: … وبه قال المالكية والحنابلة» lalu baris «قال الدسوقي: "…"[bukti مالكي]» dan «قال
    المرداوي: "…"[bukti حنبلي]» tidak ditandai, karena tiap mazhab yang disebut punya bukti dari kitabnya di bagian itu.
    Ijmak dinilai per catatan kaki."""
    ada = set().union(*(c["ada"] for c in catat)) if catat else set()
    hasil, sudah = [], set()
    for c in catat:
        kurang = [mz for mz in MAZHAB if mz in c["disebut"] and mz not in ada and (c["n"], mz) not in sudah]
        sudah.update((c["n"], mz) for mz in kurang)  # satu baris naskah: tiap mazhab disebut sekali
        alasan = []
        if kurang:
            alasan.append(f"pendapat {'، '.join(kurang)} dibuktikan dari {c['judul']}, bukan kitab mazhab itu: ambil dari "
                          f"kitab mu'tamad-nya (dok/mutamad.md, `shamela_search_phrase` dengan scope.book_ids)")
        if c["ijmak"]:
            alasan.append(f"klaim ijmak/kesepakatan/jumhur hanya dari kitab modern {c['judul']} (مرجع، bukan مصدر): ambil "
                          f"dari kitab ulama yang menukilnya")
        if alasan:
            hasil.append(f"baris {c['n']}: standar sumber: " + "; ".join(alasan) + "; asalnya memang tidak bisa didapat → tulis «مقتبس من …» "
                         f"atau «نقلا عن …» di catatan kaki  || fn: {c['isi'][:45]}")
    return hasil
