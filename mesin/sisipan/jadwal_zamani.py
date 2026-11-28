# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D جدول زمني: الخطة الزمنية للبحث (Gantt) sebagai tabel bergaris: satu baris tiap مرحلة, satu kolom tiap satuan
waktu, sel yang dikerjakan diarsir."""
from sisipan import E, Salah, bilangan, daftar, pisah, satu

NAMA = "جدول زمني"
URAIAN = ("الخطة الزمنية: «مرحلة: nama | 1-3، 5» (satuan ke berapa saja dikerjakan; rentang atau satu angka); "
          "«وحدة: الشهر» pilihan (bawaan الشهر); paling banyak 24 satuan")
KUNCI = {"مرحلة": "nama | 1-3، 5", "وحدة": "الشهر/الأسبوع/…"}
CONTOH = """#D جدول زمني | الشكل (13): الخطة الزمنية للبحث
#D مرحلة: جمع المادة العلمية | 1-2
#D مرحلة: كتابة الفصل الأول | 2-3
#D مرحلة: كتابة الفصل الثاني | 3-5
#D مرحلة: المراجعة والتدقيق | 5-6
#D مرحلة: المناقشة | 6"""
BATAS = 24


def urai(n_kepala, baris):
    marahil = []
    for n, k, v in baris:
        if k != "مرحلة":
            continue
        bagian = pisah(v)
        if len(bagian) != 2 or not bagian[0] or not daftar(bagian[1]):
            raise Salah(n, f"«مرحلة:» harus berbentuk «{KUNCI['مرحلة']}»")
        isi = set()
        for r in daftar(bagian[1]):
            a, _, b = r.partition("-")
            a, b = bilangan(n, a, "awal rentang"), bilangan(n, b or a, "akhir rentang")
            if not 1 <= a <= b <= BATAS:
                raise Salah(n, f"rentang «{r}» harus di antara 1 dan {BATAS}, awal tidak melebihi akhir")
            isi |= set(range(a, b + 1))
        marahil.append((bagian[0], isi))
    if not marahil:
        raise Salah(n_kepala, "baris «#D مرحلة: …» belum ada")
    wahdah = satu(n_kepala, baris, "وحدة", wajib=False)
    return {"marahil": marahil, "wahdah": wahdah[1] if wahdah else "الشهر", "n": max(max(i) for _, i in marahil)}


def html(d, angka):
    n = d["n"]
    kepala = (f'<tr><th>م</th><th>المرحلة / {E(d["wahdah"])}</th>' + "".join(f'<th class="sat">{angka(i)}</th>' for i in range(1, n + 1))
              + "</tr>")
    baris = "".join(f'<tr><td class="no">{angka(j + 1)}</td><td>{E(nama)}</td>'
                    + "".join(f'<td class="{"sat isi" if i in isi else "sat"}"></td>' for i in range(1, n + 1)) + "</tr>"
                    for j, (nama, isi) in enumerate(d["marahil"]))
    return f'<table class="tbl gantt">{kepala}{baris}</table>'
