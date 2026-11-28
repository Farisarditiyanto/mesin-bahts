# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D مراتب: tangga martabat berurutan (mis. مراتب الجرح والتعديل), tiap martabat dengan lafaznya, dan hukum yang
mencakup rentang martabat."""
from sisipan import E, Salah, bilangan, butir, daftar, nomor, pisah

NAMA = "مراتب"
URAIAN = ("martabat urut dari yang tertinggi: «مرتبة: wasf | lafaz، lafaz» (paling sedikit dua); "
          "«حكم: a-b | teks» = hukum martabat a sampai b, pilihan, tidak saling tumpang")
KUNCI = {"مرتبة": "wasf | lafaz، lafaz", "حكم": "a-b | teks"}
CONTOH = """#D مراتب | الشكل (5): مراتب التعديل
#D مرتبة: ما دل على المبالغة | أوثق الناس، أثبت الناس
#D مرتبة: ما أكد بصفة | ثقة ثقة، ثقة حافظ
#D مرتبة: ما عبر بصفة | ثقة، متقن
#D حكم: 1-3 | يحتج بحديثهم"""


def urai(n_kepala, baris):
    maratib, hukm = [], []
    for n, k, v in baris:
        bagian = pisah(v)
        if k == "مرتبة":
            if not bagian[0] or len(bagian) > 2:
                raise Salah(n, f"«مرتبة:» harus berbentuk «{KUNCI['مرتبة']}»")
            maratib.append((bagian[0], daftar(bagian[1]) if len(bagian) > 1 else []))
        elif k == "حكم":
            if len(bagian) != 2 or not all(bagian):
                raise Salah(n, f"«حكم:» harus berbentuk «{KUNCI['حكم']}»")
            a, _, b = bagian[0].partition("-")
            hukm.append((n, bilangan(n, a, "awal rentang «حكم:»"), bilangan(n, b or a, "akhir rentang «حكم:»"), bagian[1]))
    if len(maratib) < 2:
        raise Salah(n_kepala, "مراتب butuh paling sedikit dua baris «#D مرتبة: …»")
    tercakup = set()
    for n, a, b, _ in hukm:
        if not 1 <= a <= b <= len(maratib):
            raise Salah(n, f"rentang «حكم: {a}-{b}» di luar martabat 1-{len(maratib)}")
        if tercakup & set(range(a, b + 1)):
            raise Salah(n, f"rentang «حكم: {a}-{b}» tumpang dengan «حكم:» sebelumnya")
        tercakup |= set(range(a, b + 1))
    return {"maratib": maratib, "hukm": sorted(h[1:] for h in hukm)}


def html(d, angka):
    hukm = {a: (b, t) for a, b, t in d["hukm"]}
    baris = [butir(f"{nomor(i, angka)}<b>{E(wasf)}</b>" + (f': {E("، ".join(lafaz))}' if lafaz else ""))
             for i, (wasf, lafaz) in enumerate(d["maratib"])]
    isi, i = "", 1
    while i <= len(baris):  # martabat yang berhukum dikurung, ujung kurungnya ke hukum itu
        if i in hukm:
            b, t = hukm[i]
            isi += (f'<div class="br balik"><div class="ch">{"".join(baris[i - 1:b])}</div><div class="bs"></div>'
                    f'<div class="lf k">{E(t)}</div></div>')
            i = b + 1
        else:
            isi += f'<div class="ch">{baris[i - 1]}</div>'
            i += 1
    return f'<div class="marateb">{isi}</div>'
