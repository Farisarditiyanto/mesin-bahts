# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tanda petik di teks naskah: kutipan bertanda petik, kutipan terakhir sebelum catatan kaki, kutipan yang diantar
«قال …:», dan teks di luar kutipan."""
import re, unicodedata

from dasar import HURUF_LATIN, QAUL

# tanda petik miring dari Word/HP dan bentuk jarang (❝…❞ 〝…〞 ‟…” ❮…❯ ❛…❜) dibaca seperti " « » ‘; tanda yang tidak dikenal
# membuat kutipannya tidak dicek sama sekali
PETIK = str.maketrans("“”„＂‹›﹁﹂「」‚‛❝❞〝〞〟‟⹂❮❯❛❜", '""""«»«»«»‘‘' + '"' * 7 + "«»‘‘")
# petik tunggal ‘…’ ’…‘ '…' yang isinya huruf Arab dibaca seperti «…». Apostrof transliterasi (Qur'an, 'Uthaymin,
# ‘Abduh) bukan tanda petik: petik yang menempel huruf Latin di sisi mana pun tidak dihitung
TUNGGAL = re.compile(rf"(?<![{HURUF_LATIN}])[‘’'](?![{HURUF_LATIN}])([^‘’'\n«»\"]*[ء-ي][^‘’'\n«»\"]*)(?<![{HURUF_LATIN}])[‘’'](?![{HURUF_LATIN}])")


def seragam(teks):
    """Semua bentuk tanda petik jadi " atau «» (panjang teks tetap)."""
    return TUNGGAL.sub(lambda m: f"«{m.group(1)}»", teks.translate(PETIK))


def luar_petik(teks):
    """Teks tanpa kutipan-kutipannya (pasangan «…» dan "…" dibuang, dari yang terdalam); yang tersisa: teks penulis
    dan tanda petik yang tidak berpasangan."""
    teks, lama = seragam(teks), None
    while teks != lama:
        teks, lama = re.sub(r'«[^«»]*»|"[^"«»]*"', " ", teks), teks
    return teks


AKHIR_NUKILAN = re.compile(r'(?<=["»])[\s.،؛]*(?:اهـ|انتهى(?:\s+كلامه)?)[\s.]*$')  # «"…". اهـ» = akhir nukilan, kutipannya tetap dicek


def kutipan_semua(teks):
    """Isi tiap kutipan teratas "..." atau «...» di teks, urut dari depan; kutipan di dalam kutipan ikut induknya.
    Pembuka yang tidak tertutup tidak menghentikan pencarian: dulu satu «« nyasar membuat kutipan sesudahnya tidak dicek."""
    teks, out, i = seragam(teks), [], 0
    while i < len(teks):
        if teks[i] == "«":
            d, j = 1, i + 1
            while d and j < len(teks):
                d += (teks[j] == "«") - (teks[j] == "»"); j += 1
        elif teks[i] == '"':
            d, j = 0, teks.find('"', i + 1) + 1
        else:
            i += 1; continue
        if d or j <= i:  # pembuka tanpa penutup: lewati tanda itu saja, kutipan sesudahnya tetap dicek
            i += 1; continue
        out.append(teks[i + 1:j - 1]); i = j
    return out


TAK_TERLIHAT = "\u200b\u200c\u200d\u200e\u200f\u061c\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff"


def kutipan_akhir(teks):
    """Isi kutipan "..." atau «...» yang menutup teks (tanda baca sesudahnya boleh), termasuk kutipan di dalamnya:
    «قال: "…" ثم سكت» -> seluruh isi «…». None kalau teks tidak berakhir dengan kutipan."""
    # kurung lafaz matn «((…))» dan tanda arah tak terlihat (RLM, ZWNJ, …) sesudah tanda petik ikut dibuang
    teks = seragam(teks)
    # Tanda baca Latin/Unicode sesudah petik tidak memutus hubungan nukilan dengan catatan kakinya.
    # Berhenti pada petik: ia diperlukan parser, termasuk pembuka yang tidak berpasangan.
    for _ in range(2):  # juga «…». اهـ, dan «…» انتهى كلامه؛
        while teks and (teks[-1].isspace() or teks[-1] in TAK_TERLIHAT or
                        unicodedata.category(teks[-1]).startswith("P") and teks[-1] not in '\"«»‘’\''):
            teks = teks[:-1]
        teks = AKHIR_NUKILAN.sub("", teks)
    tunggu = []  # tanda pembuka yang dicari, dari belakang
    for i in range(len(teks) - 1, -1, -1):
        c = teks[i]
        if c == "»" or (c == '"' and tunggu[-1:] != ['"']):
            tunggu.append("«" if c == "»" else '"')
        elif tunggu and c == tunggu[-1]:
            tunggu.pop()
        elif c == "«" and "«" in tunggu:  # " yang tidak berpasangan di dalam «…» diabaikan
            del tunggu[len(tunggu) - 1 - tunggu[::-1].index("«"):]
        elif not tunggu:
            return None
        if not tunggu:
            return teks[i + 1:-1]
    return None


def diantar_qaul(sebelum):
    """Teks sebelum kutipan berakhir dengan pengantar ucapan «قال الشيخ:» / «قال X» (klausa terakhirnya), bukan
    «قال في كتابه/بحثه …» (itu judul). Kutipan yang diantar begini = nukilan, berapa pun panjangnya."""
    pengantar = re.split(r'[.،؛"«»]', seragam(sebelum))[-1]
    return bool(QAUL.search(pengantar)) and not re.search(r"كتاب|بحث|رسال|عنوان|مقال|مجل", pengantar)


def kutipan_pendek_diantar(teks, k):
    """Kutipan k (≤3 kata) di teks diantar «قال …:»? Tanpa pengantar, kutipan sependek itu biasanya istilah («"الإيمان"»),
    begitu juga lafaz yang dibahas «قال قتادة في قوله تعالى "خلفوا"» / «يقول بدل قوله: "قديم"»."""
    t = seragam(teks)
    i = min((j for j in (t.find(f'"{k}"'), t.find(f"«{k}»")) if j >= 0), default=-1)
    sebelum = t[:i].rstrip()
    lafaz = re.search(r"(?:^|\s)[وفب]?قول(?:ه|هم|ها)?(?![ء-ي])|لفظ|كلمة", re.split(r'[.،؛"«»]', sebelum)[-1])
    return i >= 0 and diantar_qaul(sebelum) and not lafaz


def kurung_akhir(polos, seg, matn, h_pos):
    """Isi (…) yang menutup polos[seg:] bila kurung itu kutipan: diantar «قال …:» / «ﷺ:», atau tepat sesudah {H:}
    (h_pos = letak {H:} terakhir di polos). None selain itu: kurung juga dipakai untuk tahun, nomor, penjelasan pendek,
    dan nama; lafaz matn ((…)) (letak kurung bukanya di matn) sudah punya arti sendiri."""
    t = polos.rstrip(" .،,؛;" + TAK_TERLIHAT)
    if not t.endswith(")"):
        return None
    d, i = 0, len(t) - 1
    while i >= seg:
        d += (t[i] == ")") - (t[i] == "(")
        if not d:
            break
        i -= 1
    if i < seg or i in matn or not re.search(r"[ء-ي]", t[i + 1:-1]):
        return None
    sebelum = polos[seg:i].rstrip()
    sesudah_h = h_pos is not None and seg <= h_pos <= i and not polos[h_pos:i].strip()
    if sesudah_h or sebelum.endswith(":") and (diantar_qaul(sebelum) or "ﷺ" in sebelum[-4:]):
        return t[i + 1:-1]
    return None
