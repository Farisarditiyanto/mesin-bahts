# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D قياس: empat rukun qiyas. Illat menghubungkan asal dan furu'; hukum asal berpindah ke furu' (تعدية الحكم)."""
from sisipan import E, Salah, butir, kurung, nomor, pisah, satu

NAMA = "قياس"
URAIAN = "empat rukun qiyas: أصل dan فرع (nama | keterangan), علة, حكم (hukum asal yang berpindah ke فرع); masing-masing sekali"
KUNCI = {"أصل": "nama | keterangan", "فرع": "nama | keterangan", "علة": "teks", "حكم": "teks"}
CONTOH = """#D قياس | الشكل (1): أركان القياس في تحريم النبيذ
#D أصل: الخمر | ثبت تحريمه بالنص
#D فرع: النبيذ | لم يرد فيه نص بعينه
#D علة: الإسكار
#D حكم: التحريم"""


def urai(n_kepala, baris):
    data = {}
    for k in KUNCI:
        n, v = satu(n_kepala, baris, k)
        bagian = pisah(v)
        if not bagian[0] or len(bagian) > (2 if KUNCI[k].startswith("nama") else 1):
            raise Salah(n, f"«{k}:» harus berbentuk «{KUNCI[k]}»")
        data[k] = bagian
    return data


def html(d, angka):
    def rukun(nama, x):
        return f"<b>{E(x[0])}</b>" + (f'، <span class="n">{E(x[1])}</span>' if len(x) > 1 else "")

    hukm = E(d["حكم"][0])
    baris = [f'<b>الأصل</b> (المقيس عليه): {rukun("أصل", d["أصل"])}.', f'<b>الفرع</b> (المقيس): {rukun("فرع", d["فرع"])}.',
             f"<b>حكم الأصل: {hukm}</b>.", f'<b>العلة الجامعة: {E(d["علة"][0])}</b>.']
    return (kurung('<div class="cart">أركان القياس</div>', [butir(nomor(i, angka) + t) for i, t in enumerate(baris)])
            + f'<div class="res">الحكم الثابت للفرع (ثمرة القياس): <b>{hukm}</b>، بتعدية الحكم بالعلة.</div>')
