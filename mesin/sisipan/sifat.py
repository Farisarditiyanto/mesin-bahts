# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D صفات: صفات الحروف menurut ابن الجزري: lima pasang ذوات الأضداد (الشدة/التوسط/الرخاوة bertiga) beserta kalimat
hafalannya, dan tujuh صفة yang tidak berlawan dalam satu tabel; «حرف:» = صفات satu huruf dihitung dari tabel itu."""
import re

from sisipan import E, Salah, butir, kurung, nomor, satu

NAMA = "صفات"
URAIAN = "صفات الحروف menurut ابن الجزري (isinya tetap); «حرف: huruf» = baris صفات huruf itu di bawahnya, pilihan"
KUNCI = {"حرف": "satu huruf (ق)"}
CONTOH = """#D صفات | الشكل (9): صفات الحروف
#D حرف: ق"""
# ذوات الأضداد: tiap kelompok = [(صفة, huruf, kalimat hafalan)]; huruf kosong = ما عدا huruf kelompok itu
ADDAD = (
    (("الهمس", "ف ح ث هـ ش خ ص س ك ت", "فحثه شخص سكت"), ("الجهر", "", "")),
    (("الشدة", "ء ج د ق ط ب ك ت", "أجد قط بكت"), ("التوسط", "ل ن ع م ر", "لن عمر"), ("الرخاوة", "", "")),
    (("الاستعلاء", "خ ص ض غ ط ق ظ", "خص ضغط قظ"), ("الاستفال", "", "")),
    (("الإطباق", "ص ض ط ظ", ""), ("الانفتاح", "", "")),
    (("الإذلاق", "ف ر م ن ل ب", "فر من لب"), ("الإصمات", "", "")),
)
MUFRADA = (("الصفير", "ص ز س"), ("القلقلة", "ق ط ب ج د"), ("اللين", "و ي"), ("الانحراف", "ل ر"), ("التكرير", "ر"),
           ("التفشي", "ش"), ("الاستطالة", "ض"))
SYARAT = {"اللين": "اللين إذا سكنتا بعد فتح"}
HURUF = "ء ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن هـ و ي".split()
SAMA = str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء", "ؤ": "ء", "ئ": "ء", "ه": "هـ", "ى": "ي"})
NAMA_HURUF = dict(zip(HURUF, ("الهمزة", "الباء", "التاء", "الثاء", "الجيم", "الحاء", "الخاء", "الدال", "الذال", "الراء",
                              "الزاي", "السين", "الشين", "الصاد", "الضاد", "الطاء", "الظاء", "العين", "الغين", "الفاء",
                              "القاف", "الكاف", "اللام", "الميم", "النون", "الهاء", "الواو", "الياء")))


def sifat(h):
    """صفات huruf h: satu dari tiap kelompok ذوات الأضداد, lalu yang tidak berlawan."""
    hasil = [next((s for s, hs, _ in g if h in hs.split()), g[-1][0]) for g in ADDAD]
    return hasil + [SYARAT.get(s, s) for s, hs in MUFRADA if h in hs.split()]


def urai(n_kepala, baris):
    x = satu(n_kepala, baris, "حرف", wajib=False)
    if not x:
        return {"harf": ""}
    h = re.sub(r"[ً-ْـ]", "", x[1]).translate(SAMA)
    if h not in HURUF:
        raise Salah(x[0], f"«حرف:» harus satu huruf hijaiyah selain alif mad, bukan «{x[1]}»")
    return {"harf": h}


def html(d, angka):
    def satu_kelompok(i, g):
        bagian = []
        for j, (s, hs, hafalan) in enumerate(g):
            huruf = f"«{hafalan or hs}»" if hs else ""
            if j == 0:
                bagian.append(f"<b>{s}</b> {huruf}")
            elif hs:
                bagian.append(f"و<b>{s}</b> {huruf}")
            else:
                bagian.append(f"وضد{'هما' if len(g) > 2 else 'ه'} <b>{s}</b>")
        return butir(nomor(i, angka) + "، ".join(bagian))

    addad = kurung('<div class="cart">ذوات الأضداد</div>', [satu_kelompok(i, g) for i, g in enumerate(ADDAD)], "lebar")
    mufrada = (f'<div class="tt">الصفات التي لا ضد لها</div><table class="tbl"><tr>{"".join(f"<th>{s}</th>" for s, _ in MUFRADA)}</tr>'
               f'<tr>{"".join(f"<td class=tengah>{hs}</td>" for _, hs in MUFRADA)}</tr></table>')
    harf = (f'<div class="res">صفات {NAMA_HURUF[d["harf"]]}: <b>{E("، ".join(sifat(d["harf"])))}</b>.</div>'
            if d["harf"] else "")
    return f"{addad}{mufrada}{harf}"
