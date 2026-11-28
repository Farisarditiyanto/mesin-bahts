# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D إسناد: شجرة الإسناد. Tiap طريق ditulis dari مخرج sampai ujungnya; nama yang sama = satu simpul, jadi jalur-jalur
bertemu sendiri. Ujung di atas, مخرج di bawah; مدار الإسناد (simpul bersama terbawah tempat jalur bercabang) dihitung
dan ditandai. Garis antarsimpul digambar gambar.js."""
from sisipan import E, Salah, pisah

NAMA = "إسناد"
URAIAN = ("jalur sanad dari مخرج ke atas: «طريق: مخرج | راو | … | الصحابي | النبي ﷺ» (paling sedikit dua nama), "
          "satu baris tiap jalur; nama yang sama ditulis sama persis; semua jalur berujung di nama yang sama; "
          "مدار الإسناد ditandai sendiri")
KUNCI = {"طريق": "مخرج | راو | … | ujung"}
CONTOH = """#D إسناد | الشكل (9): مدار حديث «إنما الأعمال بالنيات»
#D طريق: البخاري | الحميدي | سفيان بن عيينة | يحيى بن سعيد الأنصاري | محمد بن إبراهيم التيمي | علقمة بن وقاص | عمر بن الخطاب | النبي ﷺ
#D طريق: البخاري | عبد الله بن مسلمة | مالك بن أنس | يحيى بن سعيد الأنصاري
#D طريق: البخاري | محمد بن كثير | سفيان الثوري | يحيى بن سعيد الأنصاري"""


def urai(n_kepala, baris):
    jalur = []
    for n, _, v in baris:
        nama = pisah(v)
        if len(nama) < 2 or not all(nama):
            raise Salah(n, f"«طريق:» harus berbentuk «{KUNCI['طريق']}», paling sedikit dua nama")
        if len(set(nama)) != len(nama):
            raise Salah(n, "nama yang sama dua kali dalam satu طريق")
        jalur.append((n, nama))
    if not jalur:
        raise Salah(n_kepala, "baris «#D طريق: …» belum ada")
    # jalur sesudah yang pertama boleh berhenti di simpul yang sudah ada (mis. di المدار): sisanya sama dengan jalur itu
    induk = {}  # murid -> {syaikh}
    for nama in (j for _, j in jalur):
        for murid, syaikh in zip(nama, nama[1:]):
            if syaikh not in induk.setdefault(murid, []):
                induk[murid].append(syaikh)
        induk.setdefault(nama[-1], [])
    ujung = [k for k, v in induk.items() if not v]
    if not ujung:
        raise Salah(n_kepala, "jalur sanad berputar (nama yang sama di atas dan di bawah)")
    if len(ujung) != 1:
        n = next(n for n, j in jalur if j[-1] != jalur[0][1][-1])
        raise Salah(n, f"semua طريق harus berujung di nama yang sama (ada: {'، '.join(ujung)}); "
                       "jalur yang bertemu di tengah cukup ditulis sampai nama pertemuannya")
    # tingkat = jarak terjauh dari ujung; urutan dalam tingkat = urutan tulisan
    tingkat, urut = {ujung[0]: 0}, list(dict.fromkeys(x for _, j in jalur for x in reversed(j)))
    berubah = True
    while berubah:
        berubah = False
        for murid, syaikh in induk.items():
            if syaikh and all(s in tingkat for s in syaikh):
                t = max(tingkat[s] for s in syaikh) + 1
                if tingkat.get(murid) != t:
                    tingkat[murid], berubah = t, True
    if len(tingkat) != len(induk):
        raise Salah(n_kepala, "jalur sanad berputar (nama yang sama di atas dan di bawah)")
    murid_dari = {}
    for m, ss in induk.items():
        for s in ss:
            murid_dari.setdefault(s, []).append(m)
    madar = max((k for k, v in murid_dari.items() if len(v) > 1), key=lambda k: tingkat[k], default="")
    baris_t = [[] for _ in range(max(tingkat.values()) + 1)]
    for k in urut:
        baris_t[tingkat[k]].append(k)
    return {"baris": baris_t, "induk": induk, "madar": madar}


def html(d, angka):
    id_ = {k: str(i) for i, k in enumerate(k for b in d["baris"] for k in b)}

    def simpul(k):
        ke = " ".join(id_[s] for s in d["induk"][k])
        kelas = "simpul madar" if k == d["madar"] else "simpul"
        # ﷺ ditulis lengkap: huruf yang tidak memuat ligatur itu (mis. di Linux) mencetak ruang kosong setinggi baris
        isi = E(k).replace("ﷺ", "صلى الله عليه وسلم") + ('<span class="n">مدار الإسناد</span>' if k == d["madar"] else "")
        return f'<div class="{kelas}" data-id="{id_[k]}"' + (f' data-ke="{ke}"' if ke else "") + f">{isi}</div>"

    return "".join(f'<div class="tingkat">{"".join(simpul(k) for k in b)}</div>' for b in d["baris"])
