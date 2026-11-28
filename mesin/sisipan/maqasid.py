# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D مقاصد: tiga martabat maslahat (الضروريات، الحاجيات، التحسينيات), bercabang dengan kurung, dengan definisi dan contohnya."""
from sisipan import E, Salah, butir, daftar, kurung, nomor, pisah, satu

NAMA = "مقاصد"
URAIAN = "tiga martabat maslahat, masing-masing sekali: «ضروريات: definisi | contoh، contoh», حاجيات, تحسينيات"
KUNCI = {"تحسينيات": "definisi | contoh، contoh", "حاجيات": "definisi | contoh، contoh", "ضروريات": "definisi | contoh، contoh"}
CONTOH = """#D مقاصد | الشكل (3): مراتب المصالح في مقاصد الشريعة
#D ضروريات: ما لا تستقيم الحياة بفقده | حفظ الدين، حفظ النفس، حفظ العقل، حفظ النسل، حفظ المال
#D حاجيات: ما يرفع الحرج والمشقة | الرخص كقصر الصلاة للمسافر
#D تحسينيات: ما يليق بمحاسن العادات | الطهارة، ستر العورة"""


def urai(n_kepala, baris):
    data = {}
    for k in KUNCI:  # urut dari puncak
        n, v = satu(n_kepala, baris, k)
        bagian = pisah(v)
        if not bagian[0] or len(bagian) > 2:
            raise Salah(n, f"«{k}:» harus berbentuk «{KUNCI[k]}»")
        data[k] = (bagian[0], daftar(bagian[1]) if len(bagian) > 1 else [])
    return data


def html(d, angka):
    tingkat = []
    for i, k in enumerate(reversed(KUNCI)):  # dari الضروريات
        definisi, contoh = d[k]
        anak = [butir(E(definisi))]
        pengantar = "وهي:" if k == "ضروريات" else "ومنها:"
        if len(contoh) == 1:
            anak.append(butir(f"{pengantar} {E(contoh[0])}"))
        elif contoh:
            anak.append(kurung(butir(pengantar), [butir(nomor(j, angka) + E(c)) for j, c in enumerate(contoh)]))
        tingkat.append(kurung(butir(f"<b>{nomor(i, angka)}ال{k}</b>"), anak))
    return kurung('<div class="cart">مراتب المصالح</div>', tingkat)
