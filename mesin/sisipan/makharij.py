# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D مخارج: tujuh belas makhraj dalam lima maudhi' menurut ابن الجزري (المقدمة الجزرية), dua tabel berdampingan; huruf
yang dibahas bisa dilingkari."""
import re

from sisipan import E, Salah, satu

NAMA = "مخارج"
URAIAN = ("17 makhraj dalam 5 maudhi' menurut ابن الجزري (isinya tetap); «أبرز: huruf huruf» = huruf yang dilingkari, "
          "pilihan")
KUNCI = {"أبرز": "huruf dipisah spasi (ق ك)"}
CONTOH = """#D مخارج | الشكل (8): مخارج الحروف عند ابن الجزري
#D أبرز: ق ك"""
MAKHARIJ = (  # (maudhi', [(makhraj, huruf)])
    ("الجوف", [("الجوف (حروف المد)", "ا و ي")]),
    ("الحلق", [("أقصى الحلق", "ء هـ"), ("وسط الحلق", "ع ح"), ("أدنى الحلق", "غ خ")]),
    ("اللسان", [("أقصى اللسان مع ما فوقه من الحنك", "ق"), ("أسفل من مخرج القاف قليلًا", "ك"), ("وسط اللسان", "ج ش ي"),
                ("إحدى حافتي اللسان مع الأضراس", "ض"), ("أدنى الحافة إلى منتهى طرف اللسان", "ل"),
                ("طرف اللسان تحت مخرج اللام", "ن"), ("طرف اللسان مع ظهره قريبًا من النون", "ر"),
                ("طرف اللسان مع أصول الثنايا العليا", "ط د ت"), ("طرف اللسان مع أطراف الثنايا العليا", "ظ ذ ث"),
                ("طرف اللسان فويق الثنايا السفلى", "ص ز س")]),
    ("الشفتان", [("باطن الشفة السفلى مع أطراف الثنايا العليا", "ف"), ("الشفتان معًا", "و ب م")]),
    ("الخيشوم", [("الخيشوم", "الغنة")]),
)
SAMA = str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء", "ؤ": "ء", "ئ": "ء", "ه": "هـ", "ى": "ي"})
HURUF = {h for _, ms in MAKHARIJ for _, hs in ms for h in hs.split() if h != "الغنة"}


def urai(n_kepala, baris):
    x = satu(n_kepala, baris, "أبرز", wajib=False)
    if not x:
        return {"abraz": []}
    n, v = x
    abraz = [re.sub(r"[ً-ْـ]", "", h).translate(SAMA) for h in v.split()]
    if not abraz or (salah := [h for h in abraz if h not in HURUF]):
        raise Salah(n, f"«أبرز:» harus huruf hijaiyah tunggal dipisah spasi, bukan «{'، '.join(salah) if abraz else v}»")
    return {"abraz": abraz}


def html(d, angka):
    baris, k = [], 0  # [(maudhi' atau None, isi baris)] urut; dibelah dua tabel sesudah baris ke-separuh
    for maudhi, ms in MAKHARIJ:
        baris.append((maudhi, f'<tr class="kp"><th colspan="3">{maudhi} ({angka(len(ms))})</th></tr>'))
        for makhraj, hs in ms:
            k += 1
            huruf = " ".join(f'<span class="lingkar">{h}</span>' if h in d["abraz"] else h for h in hs.split())
            baris.append((None, f'<tr><td class="no">{angka(k)}</td><td>{makhraj}</td><td class="hr">{huruf}</td></tr>'))
    tengah = (len(baris) + 1) // 2
    induk = next(m for m, _ in reversed(baris[:tengah + 1]) if m)
    kiri = [r for _, r in baris[tengah:]]
    if baris[tengah][0] is None:  # maudhi' terbelah: kepalanya diulang di tabel kedua
        kiri.insert(0, f'<tr class="kp"><th colspan="3">تابع {induk}</th></tr>')
    tabel = (f'<table class="tbl">{"".join(r for _, r in baris[:tengah])}</table>', f'<table class="tbl">{"".join(kiri)}</table>')
    return f'<div class="duo atas">{tabel[0]}{tabel[1]}</div><div class="res n">{E("سبعة عشر مخرجًا في خمسة مواضع، على مذهب ابن الجزري")}</div>'
