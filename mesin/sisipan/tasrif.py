# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D تصريف: tabel tasrif satu fi'il (14 dhamir × الماضي، المضارع، الأمر، dan majhul keduanya), dihitung Qutrub
(libqutrub, GPL; termasuk fi'il mu'tal dan mudha'af). Bab fi'il tsulatsi dihitung dari harakat 'ain maadhi dan mudhari'."""
import re

from sisipan import E, Salah, impor, pisah, satu

NAMA = "تصريف"
PUSTAKA = ("libqutrub",)
URAIAN = ("«فعل: maadhi berharakat | harakat 'ain mudhari' (ضمة/فتحة/كسرة) | لازم» (harakat wajib untuk tsulatsi "
          "mujarrad; «لازم» pilihan: tanpa kolom majhul); dihitung Qutrub")
KUNCI = {"فعل": "maadhi | ضمة/فتحة/كسرة | لازم"}
CONTOH = """#D تصريف | الشكل (13): تصريف الفعل «كَتَبَ»
#D فعل: كَتَبَ | ضمة"""
HARAKAT = {"ضمة": "ُ", "فتحة": "َ", "كسرة": "ِ"}
DHAMIR = (("هو", "هو"), ("هما", "هما"), ("هم", "هم"), ("هي", "هي"), ("هما مؤ", "هما <span class=n>(مؤنث)</span>"), ("هن", "هنّ"), ("أنت", "أنتَ"),
          ("أنتما", "أنتما"), ("أنتم", "أنتم"), ("أنتِ", "أنتِ"), ("أنتما مؤ", "أنتما <span class=n>(مؤنث)</span>"), ("أنتن", "أنتنّ"), ("أنا", "أنا"),
          ("نحن", "نحن"))
ZAMAN = (("الماضي المعلوم", "الماضي"), ("المضارع المعلوم", "المضارع"), ("الأمر", "الأمر"),
         ("الماضي المجهول", "الماضي المجهول"), ("المضارع المجهول", "المضارع المجهول"))
BAB = {("َ", "ُ"): "نَصَرَ يَنْصُرُ", ("َ", "ِ"): "ضَرَبَ يَضْرِبُ", ("َ", "َ"): "فَتَحَ يَفْتَحُ",
       ("ِ", "َ"): "عَلِمَ يَعْلَمُ", ("ُ", "ُ"): "كَرُمَ يَكْرُمُ", ("ِ", "ِ"): "حَسِبَ يَحْسِبُ"}
TASYKIL = "ً-ْ"


def bentuk(tabel, zaman, dhamir):
    """Satu sel tasrif dari Qutrub, dengan ejaan baku buku sharaf: mim jamak di akhir kata bersukun (كَتَبْتُمْ); amr =
    mudhari' majzum tanpa huruf mudhara'ah kalau huruf sesudahnya berharakat (Qutrub menulis «نِمْ، خِفْ» untuk «نَمْ، خَفْ»),
    selain itu amr Qutrub dengan hamzah berharakat dhammah/kasrah = hamzah washl (اُكْتُبْ; amr أَفْعِلْ tetap qath')."""
    if zaman == "الأمر" and not dhamir.startswith("أنت"):
        return ""
    kata = tabel[zaman].get(dhamir, "")
    if zaman == "الأمر":
        jazm = re.findall(f"[^{TASYKIL}][{TASYKIL}]*", tabel["المضارع المجزوم"].get(dhamir, ""))
        if len(jazm) > 1 and re.search("[َُِ]", jazm[1]):
            kata = "".join(jazm[1:])
        kata = re.sub("^أ(?=[ُِ])", "ا", kata)
    return kata + "ْ" if kata.endswith("م") else kata


def urai(n_kepala, baris):
    n, v = satu(n_kepala, baris, "فعل")
    bagian = pisah(v)
    fiil = bagian[0]
    madhi = re.findall(f"[^{TASYKIL}ٰ][{TASYKIL}ٰ]*", fiil)  # huruf beserta tandanya
    huruf = "".join(u[0] * (2 if "ّ" in u else 1) for u in madhi)  # مَدَّ = م د د
    if not fiil or len(bagian) > 3 or not re.fullmatch("[ء-ي]{3,6}", huruf):
        raise Salah(n, f"«فعل:» harus berbentuk «{KUNCI['فعل']}», maadhi ditulis berharakat")
    harakat = HARAKAT.get(bagian[1]) if len(bagian) > 1 and bagian[1] else None
    if len(bagian) > 1 and bagian[1] and not harakat:
        raise Salah(n, f"harakat 'ain mudhari' harus ضمة، فتحة، atau كسرة, bukan «{bagian[1]}»")
    lazim = len(bagian) == 3 and bagian[2] == "لازم"
    if len(bagian) == 3 and not lazim:
        raise Salah(n, f"bagian ketiga «فعل:» hanya «لازم», bukan «{bagian[2]}»")
    if len(huruf) == 3 and not harakat:
        raise Salah(n, "fi'il tsulatsi mujarrad butuh harakat 'ain mudhari': «فعل: كَتَبَ | ضمة»")
    impor(n_kepala, "libqutrub")
    from libqutrub import classverb, verb_valid
    if not verb_valid.is_valid_infinitive_verb(fiil):
        raise Salah(n, f"«{fiil}» tidak dikenali Qutrub sebagai fi'il maadhi: tulis maadhi lengkap berharakat")
    f = classverb.VerbClass(fiil, not lazim, harakat or "َ")
    f.conjugate_all_tenses()
    tabel = f.conj_display.tab_conjug
    zaman = ZAMAN[:3] if lazim else ZAMAN
    isi = [[bentuk(tabel, z, d) for z, _ in zaman] for d, _ in DHAMIR]
    ain =madhi[1][1:2] if len(huruf) == 3 and "ّ" not in fiil and huruf[1] not in "اوي" else ""
    return {"fiil": fiil, "mudhari": isi[0][1], "bab": BAB.get((ain, harakat), ""), "lazim": lazim,
            "zaman": [j for _, j in zaman], "isi": isi}


def html(d, angka):
    kepala = "<tr><th>الضمير</th>" + "".join(f"<th>{z}</th>" for z in d["zaman"]) + "</tr>"
    baris = "".join(
        f'<tr{" class=grup" if i in (6, 12) else ""}><td class="tengah"><b>{nama}</b></td>'
        + "".join(f'<td class="tengah">{E(k) or "—"}</td>' for k in kata) + "</tr>"
        for i, ((_, nama), kata) in enumerate(zip(DHAMIR, d["isi"])))
    keterangan = "، ".join(x for x in (f"{d['fiil']} {d['mudhari']}", f"من باب {d['bab']}" if d["bab"] else "",
                                       "لازم" if d["lazim"] else "") if x)
    return f'<div class="tt">{E(keterangan)}</div><table class="tbl">{kepala}{baris}</table>'
