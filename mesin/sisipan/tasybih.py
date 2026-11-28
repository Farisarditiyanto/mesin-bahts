# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D تشبيه: kalimat tasybih dengan tiap rukun bernomor di bawahnya, empat rukunnya, dan qism yang berlaku (dihitung dari
rukun yang disebut: ada أداة = مرسل, tidak = مؤكد; ada وجه = مفصل, tidak = مجمل; keduanya tidak ada = بليغ)."""
from sisipan import E, Salah, butir, kurung, nomor, satu

NAMA = "تشبيه"
URAIAN = ("rukun tasybih menurut urutan di kalimat: «مشبه:» dan «مشبه به:» wajib, «أداة:» dan «وجه:» pilihan "
          "(tidak ditulis = محذوف); masing-masing sekali. Qism-nya dihitung mesin")
KUNCI = {"مشبه": "lafaz", "أداة": "lafaz (huruf yang bersambung: كَـ)", "مشبه به": "lafaz", "وجه": "lafaz"}
CONTOH = """#D تشبيه | الشكل (7): أركان التشبيه في «العلم كالنور في الهداية»
#D مشبه: العلمُ
#D أداة: كَـ
#D مشبه به: النورِ
#D وجه: في الهداية"""
RUKN = {"مشبه": "المشبَّه", "أداة": "أداة التشبيه", "مشبه به": "المشبَّه به", "وجه": "وجه الشبه"}


def urai(n_kepala, baris):
    ada = {k: satu(n_kepala, baris, k, wajib=k in ("مشبه", "مشبه به")) for k in KUNCI}
    for k, x in ada.items():
        if x and not x[1]:
            raise Salah(x[0], f"«{k}:» kosong: rukun yang محذوف tidak ditulis")
    urut = sorted((x[0], k, x[1]) for k, x in ada.items() if x)  # urutan di kalimat = urutan baris
    return {"kalimat": [(k, v) for _, k, v in urut], "adat": bool(ada["أداة"]), "wajh": bool(ada["وجه"])}


def html(d, angka):
    ada = dict(d["kalimat"])
    no = {k: i for i, k in enumerate(RUKN)}
    kata = "".join(f'<span class="rk"><span class="w">{E(v)}</span><span class="no">{angka(no[k] + 1)}</span></span>'
                   + ("" if v.endswith("ـ") else " ") for k, v in d["kalimat"])
    arkan = [butir(f"{nomor(i, angka)}<b>{nama}</b>: " + (E(ada[k].rstrip("ـ")) if k in ada else '<span class="n">(محذوف)</span>'))
             for i, (k, nama) in enumerate(RUKN.items())]
    berlaku = {"المرسل": d["adat"], "المؤكد": not d["adat"], "المجمل": not d["wajh"], "المفصل": d["wajh"],
               "البليغ": not (d["adat"] or d["wajh"])}

    def qism(nama, takrif):
        return butir(f"<b>{nama}: {takrif}</b>" if berlaku[nama] else f'{nama}: <span class="n">{takrif}</span>')

    aqsam = [kurung(butir("باعتبار الأداة"), [qism("المرسل", "ما ذُكرت فيه الأداة"), qism("المؤكد", "ما حُذفت منه الأداة")]),
             kurung(butir("باعتبار الوجه"), [qism("المجمل", "ما حُذف منه وجه الشبه"), qism("المفصل", "ما ذُكر فيه وجه الشبه")]),
             qism("البليغ", "ما حُذفت منه الأداة ووجه الشبه")]
    jenis = "بليغ" if berlaku["البليغ"] else ("مرسل" if d["adat"] else "مؤكد") + " " + ("مفصل" if d["wajh"] else "مجمل")
    return (f'<div class="jumla">{kata.strip()}</div>'
            f'<div class="duo">{kurung("<div class=cart>أركانه</div>", arkan)}{kurung("<div class=cart>أقسامه</div>", aqsam)}</div>'
            f'<div class="res">فهو تشبيه <b>{jenis}</b>.</div>')
