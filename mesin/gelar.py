# SPDX-License-Identifier: AGPL-3.0-or-later
"""Gelar ilmiah/jabatan di depan nama: dikenali `cek` (perhatian bentuk rujukan) dan dibuang `kartu`."""
import re

from norma import HARAKAT

# Gelar ilmiah/jabatan di depan nama: «إلغاء الألقاب -سواء كانت علمية، أو وظيفية- لدى ذكر أسماء المؤلفين» (أبو سليمان،
# كتابة البحث العلمي، ص175-176). Satu tempat untuk `cek` (perhatian) dan `kartu` (data cetak tanpa gelar), supaya data
# yang disalin dari `kartu` tidak ditandai lagi. Gelar hanya dikenali di awal nama: di awal teks, sesudah «: ، ؛ - /», atau
# sesudah «و» («ود. عبد الفتاح»). Di tengah nama ia bagian nama («راجعه: يوسف الشيخ محمد البقاعي», kartu 11825), dan di
# judul kitab didahului spasi biasa («مجموع فتاوى ورسائل فضيلة الشيخ …»). «الأستاذ المساعد/المشارك» = jabatan di belakang
# nama, bukan gelar (kartu 2, 22793).
# «د.ت»/«د.ط»/«د.ن»/«د.م» (دون تاريخ/طبعة/ناشر/مكان) di data cetak bukan gelar «د.»
# «د» tanpa titik di depan nama («المؤلف: د خالد بن عبد الرحمن الجريسي», kartu 1497; «أ د خالد», kartu 1262; «و د صالح»,
# kartu 14474) juga gelar; huruf tunggal sesudahnya («د ت») tetap singkatan data cetak, dan «ود» rapat adalah kata
# («كان كل واحد منهم ود أن أخاه كفاه»).
# Gelar yang tidak pernah jadi awal judul kitab (singkatan dan sebutan akademik/profesi) dinilai di awal nama mana pun;
# gelar yang juga awal judul («الشيخ محمد بن عبد الوهاب عقيدته السلفية»، «سماحة الإسلام»، «معالي الهمم») hanya di tempat
# nama, lihat GELAR_NAMA.
_D_POLOS = r"(?=\s+[ء-ي]{2})"
_PASTI = (r"(?:أ\s*\.\s*د\s*[./]|د\s*[./](?!\s*[تطنم](?![ء-ي]))|"
          rf"أ\s*\.?\s*د{_D_POLOS}|(?<!و)د{_D_POLOS}|(?<=و)\s+د{_D_POLOS}|"
          r"(?:الدكتور[ةه]?|الأستاذ[ةه]?(?!\s+(?:ال)?(?:مساعد|مشارك))|المحامي)(?![ء-ي]))")
_RAGU = r"(?:(?:الشيخ|العلام[ةه]|فضيل[ةه]|سماح[ةه]|معالي)(?![ء-ي]))"
_GELAR_KATA = rf"(?:{_PASTI}|{_RAGU})\s*/?\s*"
_AWAL = r"(^\s*|[،,؛;:/\-–]\s*|\s(?=و))(و?)"
GELAR = re.compile(_AWAL + r"(?P<gelar>(?:" + _GELAR_KATA + r")+)")
GELAR_PASTI = re.compile(_AWAL + r"(?P<gelar>" + _PASTI + r"\s*/?\s*(?:" + _GELAR_KATA + r")*)")
KUNCI_NAMA = re.compile(r"^([^:\n]{1,40}):")  # baris data cetak `kartu` «kunci: nilai»; «الكتاب:» = judul, tidak disentuh
# Tempat nama di rujukan yang ditulis (catatan kaki, #R): sesudah «،» (pengarang/penerbit sesudah judul) atau sesudah
# peran «تحقيق: …»; awal rujukan, «؛», «انظر:», dan titik dua lain («وفي المثل: …») juga tempat judul.
_PERAN = (r"(?<![ء-ي])(?:تحقيق|حقق|المحقق|المحققون|تعليق|علق|راجعه|مراجع[ةه]|ضبط|إشراف|أشرف|تقديم|قدم|إعداد|أعد|"
          r"جمع|ترجم[ةه]|اعتنى|عناي[ةت]|بعناي[ةت]|صور|تأليف|المؤلف|بقلم|شرح|خرج|تخريج|دراس[ةه])[^:،؛\n]{0,15}:\s*")
_GELAR_NAMA = r"(?P<gelar>(?:" + _GELAR_KATA + r")+)"
GELAR_NAMA = re.compile(r"(?:[،,/\-–]\s*|" + _PERAN + r"|\s(?=و))(?:و?)" + _GELAR_NAMA)
GELAR_NAMA_AWAL = re.compile(r"(?:^\s*|[،,/\-–]\s*|" + _PERAN + r"|\s(?=و))(?:و?)" + _GELAR_NAMA)
# Di catatan kaki, sumber bisa ditulis pengarang dulu («؛ الشيخ ابن عثيمين، الشرح الممتع»): di tempat judul gelar ragu
# tetap dinilai kalau langsung disusul nama bernasab («ابن/أبو …» atau «… بن …» sebelum «،»).
GELAR_NASAB = re.compile(r"(?:^\s*|[؛;:]\s*)(?:و?)" + _GELAR_NAMA +
                         r"(?=(?:ابن|أبو|أبي|أبا)\s|[^،؛:\n]{0,30}\sبن\s)")


def nama_bergelar(teks, awal_nama=False, catatan_kaki=False):
    """Gelar pertama di awal sebuah nama di rujukan `teks` (tanpa harakat dan tanda **/__), atau None.
    `awal_nama` = rujukan ini diawali nama pengarang (#R @pustaka_gaya: muallif, «**pengarang** …»);
    `catatan_kaki` = sumber di dalamnya boleh ditulis pengarang dulu (GELAR_NASAB)."""
    teks = HARAKAT.sub("", teks.replace("**", "").replace("__", ""))
    pola = [GELAR_PASTI, GELAR_NAMA_AWAL if awal_nama else GELAR_NAMA] + ([GELAR_NASAB] if catatan_kaki else [])
    g = [m for m in (p.search(teks) for p in pola) if m]
    return min(g, key=lambda m: m.start("gelar"))["gelar"].strip() if g else None


def buang_gelar(baris):
    """Satu baris data cetak tanpa gelar di awal nama: «المحقق: الدكتور عبد الله …، الدكتور …» -> tanpa «الدكتور».
    Baris judul («الكتاب:») dan baris tanpa «kunci:» dibiarkan."""
    m = KUNCI_NAMA.match(baris)
    if not m or HARAKAT.sub("", m[1]).strip() == "الكتاب":
        return baris
    nilai = baris[m.end():]
    asal = [i for i, c in enumerate(nilai) if not HARAKAT.fullmatch(c)]
    polos = "".join(nilai[i] for i in asal)
    # Cari di tulisan tanpa harakat, tetapi cabut hanya rentang gelarnya dari tulisan asli. Harakat nama tetap
    # utuh; `kartu` dan `cek` mengenali gelar yang sama meskipun sumber menulis «الدُّكْتُور».
    for g in reversed(list(GELAR.finditer(polos))):
        awal, akhir = g.span("gelar")
        nilai = nilai[:asal[awal]] + nilai[asal[akhir] if akhir < len(asal) else len(nilai):]
    return baris[:m.end()] + nilai
