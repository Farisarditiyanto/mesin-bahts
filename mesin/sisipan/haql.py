# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D حقل: الحقل الدلالي, lafaz umum (الكلمة الغطاء) di kanan, kelompok maknanya bercabang ke kiri, tiap kelompok dengan
kata-katanya dalam satu baris."""
from sisipan import E, Salah, butir, daftar, kurung, nomor, pisah, satu

NAMA = "حقل"
URAIAN = ("الحقل الدلالي: «عام: lafaz umum» sekali; «مجموعة: nama | kata، kata» paling sedikit dua, tiap nama "
          "kelompok sekali")
KUNCI = {"عام": "lafaz", "مجموعة": "nama | kata، kata"}
CONTOH = """#D حقل | الشكل (10): الحقل الدلالي لألفاظ الألوان
#D عام: الألوان
#D مجموعة: الألوان الأصلية | أبيض، أسود، أحمر، أخضر، أصفر، أزرق
#D مجموعة: درجات السواد | حالك، فاحم، أسحم، أدهم
#D مجموعة: درجات البياض | ناصع، يَقَق، أشهب"""


def urai(n_kepala, baris):
    _, am = satu(n_kepala, baris, "عام")
    kelompok = {}
    for n, k, v in baris:
        if k != "مجموعة":
            continue
        bagian = pisah(v)
        if len(bagian) != 2 or not bagian[0] or not daftar(bagian[1]):
            raise Salah(n, f"«مجموعة:» harus berbentuk «{KUNCI['مجموعة']}»")
        if bagian[0] in kelompok:
            raise Salah(n, f"kelompok «{bagian[0]}» sudah ditulis")
        kelompok[bagian[0]] = daftar(bagian[1])
    if len(kelompok) < 2:
        raise Salah(n_kepala, "حقل butuh paling sedikit dua baris «#D مجموعة: …»")
    if not am:
        raise Salah(n_kepala, "«عام:» kosong")
    return {"am": am, "kelompok": list(kelompok.items())}


def html(d, angka):
    cabang = [butir(f"{nomor(i, angka)}<b>{E(nama)}</b>: {E('، '.join(kata))}.") for i, (nama, kata) in enumerate(d["kelompok"])]
    return kurung(f'<div class="cart"><span class="n">حقل</span> {E(d["am"])}</div>', cabang, "lebar")
