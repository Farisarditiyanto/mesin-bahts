# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D إعراب: pohon i'rab satu kalimat pendek dari atas ke bawah, kata pertama di kanan: akar = jenis kalimat, tiap kata
(atau rangkaian kata) dengan i'rabnya, rangkaian bercabang ke kata-kata penyusunnya."""
from sisipan import E, Salah, pisah, satu

NAMA = "إعراب"
URAIAN = ("«جملة: jenisnya» sekali (akar pohon); «كلمة: lafaz | i'rabnya» urut kalimat, «كلمة: lafaz | i'rabnya | "
          "induk» = bagian dari rangkaian «induk» yang sudah ditulis; tiap lafaz sekali")
KUNCI = {"جملة": "jenis kalimat", "كلمة": "lafaz | i'rab | induk (pilihan)"}
CONTOH = """#D إعراب | الشكل (12): إعراب «إنما الأعمال بالنيات»
#D جملة: جملة اسمية
#D كلمة: إنما | كافة ومكفوفة، أداة حصر
#D كلمة: الأعمال | مبتدأ مرفوع وعلامة رفعه الضمة
#D كلمة: بالنيات | جار ومجرور متعلق بمحذوف خبر
#D كلمة: الباء | حرف جر | بالنيات
#D كلمة: النيات | اسم مجرور وعلامة جره الكسرة | بالنيات"""


def urai(n_kepala, baris):
    _, akar = satu(n_kepala, baris, "جملة")
    if not akar:
        raise Salah(n_kepala, "«جملة:» kosong")
    irab, anak = {}, {None: []}
    for n, k, v in baris:
        if k != "كلمة":
            continue
        bagian = pisah(v)
        if not 2 <= len(bagian) <= 3 or not all(bagian):
            raise Salah(n, "«كلمة:» harus berbentuk «lafaz | i'rab» atau «lafaz | i'rab | induk»")
        lafaz, induk = bagian[0], bagian[2] if len(bagian) == 3 else None
        if lafaz in irab:
            raise Salah(n, f"«{lafaz}» sudah ditulis: tiap lafaz sekali (bedakan dengan keterangan)")
        if induk is not None and induk not in irab:
            raise Salah(n, f"induk «{induk}» belum ditulis di baris «كلمة:» sebelumnya")
        irab[lafaz] = bagian[1]
        anak[lafaz] = []
        anak[induk].append(lafaz)
    if not anak[None]:
        raise Salah(n_kepala, "baris «#D كلمة: …» belum ada")
    return {"akar": akar, "irab": irab, "anak": anak}


def html(d, angka):
    def simpul(lafaz):
        isi = f'<div class="sp"><b>{E(lafaz)}</b><span class="n susut">{E(d["irab"][lafaz])}</span></div>'
        return f"<li>{isi}{cabang(d['anak'][lafaz])}</li>"

    def cabang(daftar):
        return f'<ul>{"".join(simpul(x) for x in daftar)}</ul>' if daftar else ""

    return f'<ul class="pohon"><li><div class="sp"><div class="cart">{E(d["akar"])}</div></div>{cabang(d["anak"][None])}</li></ul>'
