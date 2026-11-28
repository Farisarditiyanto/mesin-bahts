# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D خط زمني: garis waktu Hijriah pada pita tahun bergaris dua, yang tertua di kanan. Wafat = titik hitam, peristiwa =
garis tegak; jarak sebanding tahun; label bergantian di bawah dan di atas pita, bertingkat sendiri (gambar.js) supaya
tidak bertumpuk."""
from sisipan import E, Salah, bilangan, pisah

NAMA = "خط زمني"
URAIAN = ("garis waktu Hijriah, tertua di kanan: «وفاة: tahun | nama» (titik, «ت ١٧٩هـ») dan «حدث: tahun | teks» "
          "(garis tegak); paling sedikit dua baris, urutan tulis bebas")
KUNCI = {"وفاة": "tahun | nama", "حدث": "tahun | teks"}
CONTOH = """#D خط زمني | الشكل (12): وفيات الأئمة الأربعة والشيخين
#D وفاة: 150 | أبو حنيفة
#D وفاة: 179 | مالك بن أنس
#D وفاة: 204 | الشافعي
#D وفاة: 241 | أحمد بن حنبل
#D وفاة: 256 | البخاري
#D وفاة: 261 | مسلم
#D حدث: 132 | قيام الدولة العباسية"""
LANGKAH = (10, 20, 25, 50, 100, 200, 250, 500)  # jarak tanda tahun: yang memberi 4-8 tanda
POROS_PX, HURUF_PX = 480, 7  # taksiran lebar poros (piksel CSS, .zaman) dan lebar rata-rata satu huruf label


def urai(n_kepala, baris):
    titik = []
    for n, k, v in baris:
        bagian = pisah(v)
        if len(bagian) != 2 or not bagian[1]:
            raise Salah(n, f"«{k}:» harus berbentuk «{KUNCI[k]}»")
        titik.append((bilangan(n, bagian[0], "tahun"), k, bagian[1]))
    if len(titik) < 2:
        raise Salah(n_kepala, "خط زمني butuh paling sedikit dua baris «#D وفاة: …» atau «#D حدث: …»")
    return sorted(titik)


def html(d, angka):
    awal, akhir = d[0][0], d[-1][0]
    langkah = next((s for s in LANGKAH if (akhir - awal) / s <= 7), LANGKAH[-1])
    a, b = awal // langkah * langkah, -(-akhir // langkah) * langkah
    if a == b:
        b = a + langkah
    # label mulai dari garis penunjuknya ke kiri: ujung kiri poros diperpanjang sampai label terkiri kira-kira muat
    # (lebar huruf ditaksir; gambar.js tetap menjepit label yang meleset ke dalam poros)
    while any((b - t) / (b - a) * POROS_PX < len(teks) * HURUF_PX + 60 for t, _, teks in d):
        b += langkah
    x = lambda t: (t - a) / (b - a)
    tanda = "".join(f'<div class="ruas-t" style="right:{x(t) * 100:.4f}%"><span>{angka(t)}</span></div>'
                    for t in range(a, b + 1, langkah))
    label, titik = "", ""
    for i, (t, k, teks) in enumerate(d):  # label bergantian di bawah dan di atas pita, supaya rapat
        sisi = "ba"[i % 2]
        label += (f'<div class="tanda" data-x="{x(t):.4f}" data-sisi="{sisi}">'
                  + (f'{E(teks)} <span class="n">(ت {angka(t)}هـ)</span>' if k == "وفاة"
                     else f'<span class="n">{angka(t)}هـ:</span> {E(teks)}') + "</div>")
        titik += f'<div class="{"bulat" if k == "وفاة" else "garis-t"} {sisi}" style="right:{x(t) * 100:.4f}%"></div>'
    return f'<div class="lajur bendera zaman"><div class="poros">{tanda}{titik}</div>{label}</div>'
