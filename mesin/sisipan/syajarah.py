# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D شجرة: pohon umum kanan-ke-kiri (akar di kanan, cabang ke kiri) untuk تقسيم، قواعد، القراء ورواتهم، نسب، طبقات."""
from sisipan import E, Salah, butir, daftar, kurung, nomor, pisah

NAMA = "شجرة"
URAIAN = ("pohon, akar di kanan: «فرع: induk | anak، anak»; induk baris pertama = akar, induk baris berikutnya "
          "harus sudah tertulis sebagai anak; tiap nama sekali")
KUNCI = {"فرع": "induk | anak، anak"}
CONTOH = """#D شجرة | الشكل (6): أقسام الحكم الشرعي
#D فرع: الحكم الشرعي | الحكم التكليفي، الحكم الوضعي
#D فرع: الحكم التكليفي | الواجب، المندوب، المباح، المكروه، المحرم
#D فرع: الحكم الوضعي | السبب، الشرط، المانع"""


def urai(n_kepala, baris):
    anak, akar = {}, None  # nama -> [anak]; urut tulisan
    for n, _, v in baris:
        bagian = pisah(v)
        if len(bagian) != 2 or not bagian[0] or not daftar(bagian[1]):
            raise Salah(n, f"«فرع:» harus berbentuk «{KUNCI['فرع']}»")
        induk, cabang = bagian[0], daftar(bagian[1])
        if akar is None:
            akar = induk
            anak[akar] = []
        elif induk not in anak:
            raise Salah(n, f"induk «{induk}» belum tertulis: tulis dulu sebagai anak di baris «فرع:» sebelumnya")
        for c in cabang:
            if c in anak:
                raise Salah(n, f"«{c}» sudah ada di pohon ini: tiap nama sekali (bedakan dengan keterangan)")
            anak[c] = []
        anak[induk] += cabang
    if akar is None:
        raise Salah(n_kepala, "baris «#D فرع: …» belum ada")
    return {"akar": akar, "anak": anak}


def html(d, angka):
    anak = d["anak"]

    def simpul(nama, i):
        if not anak[nama]:
            return butir(nomor(i, angka) + E(nama))
        return kurung(butir(f"<b>{E(nama)}</b>"), [simpul(c, j) for j, c in enumerate(anak[nama])])

    return kurung(f'<div class="cart">{E(d["akar"])}</div>', [simpul(c, j) for j, c in enumerate(anak[d["akar"]])])
