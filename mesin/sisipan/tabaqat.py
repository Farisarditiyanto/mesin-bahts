# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D طبقات: طبقات الرواة berurutan dari yang tertua, tiap طبقة dengan contoh rawinya (dan rentang wafat, pilihan)."""
from sisipan import E, Salah, daftar, pisah

NAMA = "طبقات"
URAIAN = ("طبقة urut dari yang tertua: «طبقة: nama | راو، راو | الوفيات» (bagian ketiga pilihan; kolomnya tercetak "
          "kalau ada yang mengisinya); paling sedikit dua طبقة")
KUNCI = {"طبقة": "nama | راو، راو | الوفيات"}
CONTOH = """#D طبقات | الشكل (10): طبقات الرواة عند ابن حجر في التقريب (نماذج)
#D طبقة: الصحابة | عمر بن الخطاب، أبو هريرة | قبل المائة
#D طبقة: كبار التابعين | سعيد بن المسيب | قبل المائة
#D طبقة: الوسطى من التابعين | الحسن البصري، محمد بن سيرين | بعد المائة
#D طبقة: التي تليها | الزهري، قتادة | بعد المائة"""


def urai(n_kepala, baris):
    tabaqat = []
    for n, _, v in baris:
        bagian = pisah(v)
        if not 2 <= len(bagian) <= 3 or not bagian[0] or not daftar(bagian[1]):
            raise Salah(n, f"«طبقة:» harus berbentuk «{KUNCI['طبقة']}»")
        tabaqat.append((bagian[0], daftar(bagian[1]), bagian[2] if len(bagian) == 3 else ""))
    if len(tabaqat) < 2:
        raise Salah(n_kepala, "طبقات butuh paling sedikit dua baris «#D طبقة: …»")
    return tabaqat


def html(d, angka):
    wafat = any(w for _, _, w in d)
    kepala = "<tr><th>م</th><th>الطبقة</th><th>من رجالها</th>" + ("<th>الوفيات</th>" if wafat else "") + "</tr>"
    baris = "".join(f'<tr><td class="no">{angka(i + 1)}</td><td class="k">{E(nama)}</td><td>{E("، ".join(rijal))}</td>'
                    + (f'<td class="tengah">{E(angka(w)) or "—"}</td>' if wafat else "") + "</tr>"
                    for i, (nama, rijal, w) in enumerate(d))
    return f'<table class="tbl">{kepala}{baris}</table>'
