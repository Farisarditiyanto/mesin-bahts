# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D تعارض: urutan langkah دفع التعارض tiap manhaj berdampingan; langkah berikutnya ditempuh kalau yang sebelumnya tidak bisa."""
from sisipan import E, Salah, pisah, satu

NAMA = "تعارض"
URAIAN = ("urutan langkah tiap manhaj berdampingan: «منهج: nama | langkah | langkah …» (paling sedikit dua langkah); "
          "«مبدأ: teks» = kotak di atasnya, pilihan")
KUNCI = {"منهج": "nama | langkah | langkah …", "مبدأ": "teks"}
CONTOH = """#D تعارض | الشكل (4): طرق دفع التعارض بين الأدلة
#D مبدأ: تعارض ظاهري بين دليلين
#D منهج: الجمهور | الجمع | الترجيح | النسخ | التساقط
#D منهج: الحنفية | النسخ | الترجيح | الجمع | التساقط"""


def urai(n_kepala, baris):
    manahij = []
    for n, k, v in baris:
        if k == "منهج":
            bagian = pisah(v)
            if len(bagian) < 3 or not all(bagian):
                raise Salah(n, f"«منهج:» harus berbentuk «{KUNCI['منهج']}», paling sedikit dua langkah")
            manahij.append((bagian[0], bagian[1:]))
    if not manahij:
        raise Salah(n_kepala, "baris «#D منهج: …» belum ada")
    mabda = satu(n_kepala, baris, "مبدأ", wajib=False)
    return {"manahij": manahij, "mabda": mabda[1] if mabda else ""}


def html(d, angka):
    manahij = d["manahij"]
    kepala = "<tr><th>الرتبة</th>" + "".join(f"<th>منهج {E(nama)}</th>" for nama, _ in manahij) + "</tr>"
    baris = "".join(
        f'<tr><td class="no">{angka(i + 1)}</td>'
        + "".join(f'<td class="tengah">{E(langkah[i]) if i < len(langkah) else "—"}</td>' for _, langkah in manahij) + "</tr>"
        for i in range(max(len(langkah) for _, langkah in manahij)))
    judul = f'<div class="tt">{E(d["mabda"])}</div>' if d["mabda"] else ""
    return f'{judul}<table class="tbl">{kepala}{baris}</table>'
