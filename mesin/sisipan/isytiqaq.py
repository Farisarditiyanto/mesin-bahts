# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D اشتقاق: kata-kata yang dibentuk dari satu akar tsulatsi menurut wazannya (الأفعال، المشتقات، المصادر), dihitung
mesin: huruf ف ع ل wazan diganti huruf akar. Hanya akar shahih salim; akar mu'tal, mahmuz, mudha'af, dan wazan yang
butuh ibdal/idgham (افتعل dengan fa' ت ث د ذ ز ص ض ط ظ, dua huruf sama yang bertemu) = Salah, karena hasil
penggantian polos di situ salah."""
import re

from sisipan import E, Salah, pisah, satu

NAMA = "اشتقاق"
URAIAN = ("akar tsulatsi shahih salim «جذر: ك ت ب»; «أفعال:», «مشتقات:», «مصادر:» = «wazan = keterangan | wazan …» "
          "(keterangan pilihan), paling sedikit satu; kata jadinya dihitung mesin")
KUNCI = {"جذر": "tiga huruf (ك ت ب)", "أفعال": "wazan = keterangan | …", "مشتقات": "wazan = keterangan | …",
         "مصادر": "wazan = keterangan | …"}
CONTOH = """#D اشتقاق | الشكل (11): ما يشتق من الجذر (ك ت ب)
#D جذر: ك ت ب
#D أفعال: فَعَلَ | فَاعَلَ | تَفَاعَلَ | اسْتَفْعَلَ
#D مشتقات: فَاعِل = اسم الفاعل | مَفْعُول = اسم المفعول | مَفْعَل = اسم المكان
#D مصادر: فِعَالَة = مصدر فَعَلَ | مُفَاعَلَة = مصدر فَاعَلَ"""
KELOMPOK = {"أفعال": "الأفعال", "مشتقات": "المشتقات", "مصادر": "المصادر"}
HARAKAT = "ً-ْ"
LEMAH = set("اويىءأإآؤئ")
IBDAL = set("تثدذزصضطظ")  # fa' افتعل yang ta'-nya diganti/diidghamkan


def isi(n, wazan, akar):
    """Kata dari wazan: ف ع ل (dengan harakatnya) diganti huruf akar; Salah kalau wazannya tidak bisa diisi polos."""
    tanpa = re.sub(f"[{HARAKAT}]", "", wazan)
    if [h for h in tanpa if h in "فعل"] != list("فعل"):
        raise Salah(n, f"wazan «{wazan}» harus memuat ف ع ل masing-masing sekali, berurutan")
    if re.search(f"ف[{HARAKAT}]*ت", wazan) and akar[0] in IBDAL:
        raise Salah(n, f"wazan «{wazan}» dengan fa' «{akar[0]}» butuh ibdal (افتعل): belum dihitung mesin; tulis dengan #J")
    kata = re.sub("[فعل]", lambda m: akar["فعل".index(m[0])], wazan)
    satuan = re.findall(f".[{HARAKAT}]*", kata)
    for a, b in zip(satuan, satuan[1:]):
        if a[0] == b[0] and "ْ" in a:
            raise Salah(n, f"«{wazan}» dari akar ini mempertemukan dua «{a[0]}» (idgham): belum dihitung mesin")
    return kata


def urai(n_kepala, baris):
    n, v = satu(n_kepala, baris, "جذر")
    akar = re.sub(f"[{HARAKAT}\\s]", "", v)
    if len(akar) != 3 or not all("ء" <= h <= "ي" for h in akar):
        raise Salah(n, f"«جذر:» harus tiga huruf akar (ك ت ب), bukan «{v}»")
    if lemah := [h for h in akar if h in LEMAH]:
        raise Salah(n, f"akar «{' '.join(akar)}» memuat huruf illat/hamzah «{lemah[0]}»: belum dihitung mesin (hanya akar "
                       "shahih salim); tulis tabelnya dengan #J")
    if akar[1] == akar[2]:
        raise Salah(n, f"akar «{' '.join(akar)}» mudha'af (butuh idgham): belum dihitung mesin; tulis tabelnya dengan #J")
    kelompok = []
    for k, judul in KELOMPOK.items():
        x = satu(n_kepala, baris, k, wajib=False)
        if not x:
            continue
        butir = []
        for b in pisah(x[1]):
            wazan, _, ket = b.partition("=")
            if not wazan.strip():
                raise Salah(x[0], f"«{k}:» harus berbentuk «{KUNCI[k]}»")
            butir.append((isi(x[0], wazan.strip(), akar), wazan.strip(), ket.strip()))
        kelompok.append((judul, butir))
    if not kelompok:
        raise Salah(n_kepala, "tulis paling sedikit satu baris «#D أفعال: …», «#D مشتقات: …», atau «#D مصادر: …»")
    return {"akar": akar, "kelompok": kelompok}


def html(d, angka):
    tinggi = max(len(b) for _, b in d["kelompok"])
    kepala = "<tr>" + "".join(f"<th>{j}</th>" for j, _ in d["kelompok"]) + "</tr>"

    def sel(b, i):
        if i >= len(b):
            return "<td></td>"
        kata, wazan, ket = b[i]
        return f'<td><b>{E(kata)}</b> <span class="n">({E(wazan)}{"، " + E(ket) if ket else ""})</span></td>'

    baris = "".join("<tr>" + "".join(sel(b, i) for _, b in d["kelompok"]) + "</tr>" for i in range(tinggi))
    return f'<div class="tt">الجذر ({" ".join(d["akar"])})</div><table class="tbl">{kepala}{baris}</table>'
