# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D حجب: شجرة حجب الحرمان (tiap حاجب dengan yang dihalanginya) dan جدول حجب النقصان. Isinya DIHITUNG penghitung
faraid `#D مواريث` (satu aturan, satu tempat): X menghalangi Y kalau Y terhalang di masalah yang hanya berisi X dan Y."""
from sisipan import E, Salah, butir, daftar, kurung, nomor, satu
from sisipan.mawarith import JUMHUR, WARATHA, BelumDidukung, hitung, nama_waris

NAMA = "حجب"
URAIAN = ("dihitung penghitung faraid: «حاجب: waris، waris» = pohon حجب الحرمان tiap waris itu (bentuk ganda seperti "
          "«البنتان» boleh); «نقصان: waris، waris» = tabel حجب النقصان. Paling sedikit salah satunya; pendapat jumhur ditandai *")
KUNCI = {"حاجب": "waris، waris", "نقصان": "waris، waris"}
CONTOH = """#D حجب | الشكل (8): الحجب في المواريث
#D حاجب: الابن، الأب، الأم، البنتان
#D نقصان: الزوج، الزوجة، الأم، بنت الابن"""

# yang dikurangi -> (waris yang mengurangi dalam hitungan, uraian الحاجب)
NUQSAN = {
    "زوج": ("ابن", "الفرع الوارث"), "زوجة": ("ابن", "الفرع الوارث"),
    "أم": ("ابن", "الفرع الوارث، أو اثنان فأكثر من الإخوة"), "أب": ("ابن", "الفرع الوارث الذكر"),
    "جد": ("ابن", "الفرع الوارث الذكر"), "بنت ابن": ("بنت", "البنت الواحدة"),
    "أخت لأب": ("أخت شقيقة", "الأخت الشقيقة الواحدة"),
}
PEMBANDING = "عم شقيق"  # pengambil sisa di masalah ujinya, supaya bagian yang diuji tidak berubah karena رد


def _label(w, k):
    return next(b.label for b in hitung(w).baris if b.kunci == k)


def urai(n_kepala, baris):
    hajib, nuqsan = [], []
    for kunci, simpan in (("حاجب", hajib), ("نقصان", nuqsan)):
        if ada := satu(n_kepala, baris, kunci, wajib=False):
            n, v = ada
            for teks in daftar(v):
                nama = nama_waris(n, teks)
                k, jumlah = nama if isinstance(nama, tuple) else (nama, 1)
                if kunci == "نقصان" and k not in NUQSAN:
                    raise Salah(n, f"«{teks}» tidak berkurang bagiannya karena حجب النقصان (yang ada: {'، '.join(NUQSAN)})")
                simpan.append((teks, k, jumlah))
    if not (hajib or nuqsan):
        raise Salah(n_kepala, "baris «#D حاجب: …» atau «#D نقصان: …» belum ada")
    pohon = []
    for teks, k, jumlah in hajib:
        terhalang, khilaf = [], []
        for y in WARATHA:
            if y == k or {k, y} == {"زوج", "زوجة"}:
                continue
            try:
                b = next(b for b in hitung({k: jumlah, y: 1}).baris if b.kunci == y)
            except BelumDidukung:
                khilaf.append(y)
                continue
            if b.hajib == k:
                terhalang.append((y, (y, k) in JUMHUR))
        pohon.append((teks, terhalang, khilaf))
    tabel = [(k, _label({k: 1, PEMBANDING: 1}, k), _label({k: 1, NUQSAN[k][0]: 1, PEMBANDING: 1}, k), NUQSAN[k][1])
             for _, k, _ in nuqsan]
    return {"pohon": pohon, "tabel": tabel}


def html(d, angka):
    bagian = []
    if d["pohon"]:
        cabang = []
        for teks, terhalang, khilaf in d["pohon"]:
            anak = [butir(nomor(i, angka) + E(WARATHA[y][0]) + ("*" if j else "")) for i, (y, j) in enumerate(terhalang)]
            if khilaf:
                anak.append(butir(f'<span class="n">{E("، ".join(WARATHA[y][0] for y in khilaf))}: فيه خلاف</span>'))
            induk = butir(f"<b>{E(teks)}</b>")
            if len(anak) > 6:  # daftar panjang dua kolom (urut ke bawah), supaya tidak tinggi dan kosong di sampingnya
                cabang.append(f'<div class="br dua" style="--baris:{-(-len(anak) // 2)}">{induk}<div class="bs"></div>'
                              f'<div class="ch">{"".join(anak)}</div></div>')
            else:
                cabang.append(kurung(induk, anak or [butir("—")]))
        bagian.append(kurung('<div class="cart">حجب الحرمان</div>', cabang))
        if any(j for _, t, _ in d["pohon"] for _, j in t):
            bagian.append('<div class="n">* عند الجمهور.</div>')
    if d["tabel"]:
        baris = "".join(f'<tr><td>{E(WARATHA[k][0])}</td><td class="tengah">{E(angka(a))}</td>'
                        f'<td class="tengah">{E(angka(b))}</td><td>{E(oleh)}</td></tr>' for k, a, b, oleh in d["tabel"])
        bagian.append('<div class="tt">حجب النقصان</div><table class="tbl"><tr><th>الوارث</th><th>فرضه</th>'
                      f'<th>ينقص إلى</th><th>الحاجب</th></tr>{baris}</table>')
    return "".join(f'<div class="blok">{b}</div>' for b in bagian)
