# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D خلاف: aqwal satu masalah khilafiyah berdampingan, tiap qaul dengan pemiliknya, dan qaul yang dirajihkan."""
from sisipan import E, Salah, bilangan, butir, daftar, kurung, pisah, satu, urutan

NAMA = "خلاف"
URAIAN = "aqwal satu masalah (paling sedikit dua): «قول: isi | pemilik، pemilik»; «راجح: nomor qaul» pilihan"
KUNCI = {"قول": "isi | pemilik، pemilik", "راجح": "nomor qaul (1 = القول الأول)"}
CONTOH = """#D خلاف | الشكل (2): حكم النية في الوضوء
#D قول: شرط لصحة الوضوء | المالكية، الشافعية، الحنابلة
#D قول: سنة لا تتوقف عليها الصحة | الحنفية
#D راجح: 1"""


def urai(n_kepala, baris):
    aqwal = []
    for n, k, v in baris:
        if k == "قول":
            bagian = pisah(v)
            if len(bagian) != 2 or not all(bagian) or not daftar(bagian[1]):
                raise Salah(n, f"«قول:» harus berbentuk «{KUNCI['قول']}»")
            aqwal.append((bagian[0], daftar(bagian[1])))
    if len(aqwal) < 2:
        raise Salah(n_kepala, "khilaf butuh paling sedikit dua baris «#D قول: …»")
    rajih = satu(n_kepala, baris, "راجح", wajib=False)
    nomor = bilangan(rajih[0], rajih[1], "«راجح:»") if rajih else 0
    if rajih and not 1 <= nomor <= len(aqwal):
        raise Salah(rajih[0], f"«راجح: {rajih[1]}» tidak menunjuk qaul (ada {len(aqwal)} qaul)")
    return {"aqwal": aqwal, "rajih": nomor}


def html(d, angka):
    aqwal = [kurung(butir(f'<b>القول {urutan(i)}{" (الراجح)" if i + 1 == d["rajih"] else ""}</b>'),
                    [butir(E(isi)), butir(f'<span class="n">وبه قال: {E("، ".join(siapa))}</span>')])
             for i, (isi, siapa) in enumerate(d["aqwal"])]
    return kurung('<div class="cart">الأقوال في المسألة</div>', aqwal)
