# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D رحلة: peta رحلة seorang alim. Mahasiswa menulis NAMA tempat saja; koordinatnya dari gazetir al-Thurayya
(`thurayya.tsv`, CC BY 4.0) dan daratannya dari Natural Earth (`daratan.json`, domain publik), keduanya dibawa mesin
(tanpa internet). Peta bergaya ukiran lama: laut berarsir garis mendatar, bingkai garis ganda, jalur putus-putus berpanah."""
import difflib, json, math
from functools import cache
from pathlib import Path

import norma
from sisipan import E, Salah, daftar, pisah

NAMA = "رحلة"
URAIAN = ("tempat yang disinggahi berurutan, satu baris tiap tempat: «محطة: nama tempat» (koordinat dari gazetir "
          "al-Thurayya; ejaan lama/baru seperti بخارى/بخارة dikenali); tempat yang tidak ada di gazetir: «محطة: nama | "
          "lintang، bujur»; paling sedikit dua")
KUNCI = {"محطة": "nama tempat | lintang، bujur"}
CONTOH = """#D رحلة | الشكل (15): رحلة الإمام البخاري في طلب الحديث (المسار للتوضيح)
#D محطة: بخارى
#D محطة: مكة
#D محطة: المدينة
#D محطة: البصرة
#D محطة: الكوفة
#D محطة: بغداد
#D محطة: دمشق
#D محطة: مصر
#D محطة: نيسابور"""
GAZETIR = Path(__file__).with_name("thurayya.tsv")
DARATAN = Path(__file__).with_name("daratan.json")
# ejaan yang lazim di bahts -> nama di gazetir (yang memakai ejaan kitab buldan)
ALIAS = {"بخارى": "بخارة", "قرطبة": "قرطوبة", "أصبهان": "إصبهان", "أصفهان": "إصبهان", "مصر": "فسطاط",
         "الفسطاط": "فسطاط", "القدس": "بيت المقدس", "المدينة المنورة": "المدينة", "مكة المكرمة": "مكة"}


def _kunci(nama):
    """Nama tempat tanpa «ال» dan tanpa alif/ya/ta marbuthah di ujung kata: «بخارى» = «بخارة», «الفسطاط» = «فسطاط»."""
    kata = []
    for k in norma.norm(nama).split():
        k = k[2:] if k.startswith("ال") and len(k) > 4 else k
        kata.append(k[:-1] if len(k) > 3 and k[-1] in "ايه" else k)
    return " ".join(kata)


@cache
def _gazetir():
    nama, kunci = {}, {}
    for baris in GAZETIR.read_text(encoding="utf8").splitlines():
        if baris.startswith("#"):
            continue
        n, la, lo = baris.split("\t")
        nama[n] = (float(la), float(lo))
        kunci.setdefault(_kunci(n), n)
    return nama, kunci


def cari(teks):
    """(nama di gazetir, (lintang, bujur)) atau None."""
    nama, kunci = _gazetir()
    for calon in (teks, ALIAS.get(teks, teks), kunci.get(_kunci(ALIAS.get(teks, teks)))):
        if calon in nama:
            return calon, nama[calon]
    return None


def urai(n_kepala, baris):
    mahattat = []
    for n, _, v in baris:
        bagian = pisah(v)
        if not bagian[0] or len(bagian) > 2:
            raise Salah(n, f"«محطة:» harus berbentuk «{KUNCI['محطة']}»")
        if len(bagian) == 2:
            koor = daftar(bagian[1].translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")))
            try:
                la, lo = (float(x) for x in koor)
            except ValueError:
                raise Salah(n, "koordinat «محطة:» harus «lintang، bujur», mis. «21.42، 39.83»") from None
            if not (-90 <= la <= 90 and -180 <= lo <= 180):
                raise Salah(n, "koordinat di luar bumi (lintang -90..90، bujur -180..180)")
        elif ada := cari(bagian[0]):
            la, lo = ada[1]
        else:
            _, kunci = _gazetir()
            mirip = [kunci[k] for k in difflib.get_close_matches(_kunci(bagian[0]), list(kunci), n=6, cutoff=0.6)]
            raise Salah(n, f"tempat «{bagian[0]}» tidak ada di gazetir al-Thurayya"
                           + (f"; yang mirip: {'، '.join(mirip)}" if mirip else "")
                           + f"; atau tulis koordinatnya: «محطة: {bagian[0]} | lintang، bujur»")
        mahattat.append((bagian[0], la, lo))
    if len(mahattat) < 2:
        raise Salah(n_kepala, "رحلة butuh paling sedikit dua baris «#D محطة: …»")
    return mahattat


W, H_MIN, H_MAKS, HURUF = 540, 240, 440, 14.5  # ukuran peta dan huruf label, piksel CSS


def _bingkai(titik):
    """(bujur0, bujur1, lintang0, lintang1, skala px/derajat bujur, cos) yang memuat semua titik, rasio dibatasi."""
    la = [p[1] for p in titik]
    lo = [p[2] for p in titik]
    pad = max(1.5, 0.15 * max(max(lo) - min(lo), max(la) - min(la)))
    lo0, lo1, la0, la1 = min(lo) - pad, max(lo) + pad, min(la) - pad, max(la) + pad
    cos = math.cos(math.radians((la0 + la1) / 2))
    k = W / ((lo1 - lo0) * cos)
    h = (la1 - la0) * k
    if h > H_MAKS:  # terlalu tinggi: lebarkan bujur
        tambah = ((la1 - la0) * W / H_MAKS / cos - (lo1 - lo0)) / 2
        lo0, lo1 = lo0 - tambah, lo1 + tambah
    elif h < H_MIN:  # terlalu pipih: tinggikan lintang
        tambah = (H_MIN / k - (la1 - la0)) / 2
        la0, la1 = la0 - tambah, la1 + tambah
    return lo0, lo1, la0, la1, W / ((lo1 - lo0) * cos), cos


def html(d, angka):
    lo0, lo1, la0, la1, k, cos = _bingkai(d)
    H = (la1 - la0) * k
    xy = lambda la, lo: ((lo - lo0) * cos * k, (la1 - la) * k)
    darat = []
    for cincin in json.loads(DARATAN.read_text(encoding="utf8"))["cincin"]:
        xs, ys = [p[0] for p in cincin], [p[1] for p in cincin]
        if max(xs) < lo0 or min(xs) > lo1 or max(ys) < la0 or min(ys) > la1:
            continue
        darat.append("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in (xy(la, lo) for lo, la in cincin)) + "Z")
    # titik: tempat yang disinggahi dua kali = satu titik bernomor dua
    tempat = {}
    for i, (nama, la, lo) in enumerate(d):
        tempat.setdefault(nama, [xy(la, lo), []])[1].append(i + 1)
    jalur, lintasan = [], []  # lintasan: titik-titik sepanjang jalur, supaya label menghindarinya
    for (_, la, lo), (_, la2, lo2) in zip(d, d[1:]):
        (x1, y1), (x2, y2) = xy(la, lo), xy(la2, lo2)
        panjang = math.hypot(x2 - x1, y2 - y1)
        if panjang < 1:
            continue
        ux, uy = (x2 - x1) / panjang, (y2 - y1) / panjang
        x1, y1, x2, y2 = x1 + ux * 5, y1 + uy * 5, x2 - ux * 6, y2 - uy * 6  # tidak menutup titik
        cx, cy = (x1 + x2) / 2 - uy * panjang * 0.12, (y1 + y2) / 2 + ux * panjang * 0.12
        jalur.append(f'<path class="jalan" d="M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}" marker-end="url(#panah)"/>')
        for s in range(1, int(panjang / 8)):
            u = s * 8 / panjang
            px, py = (1 - u) ** 2 * x1 + 2 * u * (1 - u) * cx + u * u * x2, (1 - u) ** 2 * y1 + 2 * u * (1 - u) * cy + u * u * y2
            lintasan.append((px - 1, py - 1, px + 1, py + 1))
    # label: dari empat letak, yang tidak menabrak label/titik lain dan tidak keluar bingkai
    terpakai = [(x - 4, y - 4, x + 4, y + 4) for (x, y), _ in tempat.values()]
    label = []
    for nama, ((x, y), nomor) in tempat.items():
        teks = f"{'، '.join(angka(i) for i in nomor)}- {nama}"
        w = len(teks) * HURUF * 0.5
        calon = [(x - 6, y + 5, "start", (x - 6 - w, y - 9, x - 6, y + 6)),  # kiri titik (RTL: ujung kanan teks di x)
                 (x + 6, y + 5, "end", (x + 6, y - 9, x + 6 + w, y + 6)),
                 (x, y - 8, "middle", (x - w / 2, y - 22, x + w / 2, y - 7)),
                 (x, y + 19, "middle", (x - w / 2, y + 6, x + w / 2, y + 21))]

        def nilai(c):
            a = c[3]
            kena = lambda kotak: sum(1 for b in kotak if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3])
            return kena(terpakai) * 10 + kena(lintasan) + (a[0] < 2 or a[2] > W - 2 or a[1] < 2 or a[3] > H - 2) * 20
        tx, ty, anchor, kotak = min(calon, key=nilai)
        terpakai.append(kotak)
        label.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anchor}">{E(teks)}</text>')
    titik = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2"/>' for (x, y), _ in tempat.values())
    defs = ('<defs><pattern id="laut" width="6" height="3.2" patternUnits="userSpaceOnUse">'
            '<line x1="0" y1="1.6" x2="6" y2="1.6"/></pattern>'
            '<marker id="panah" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">'
            '<path d="M0,0.5 L8,4 L0,7.5 Z"/></marker></defs>')
    return (f'<svg class="peta" viewBox="0 0 {W} {H:.0f}" width="{W}" height="{H:.0f}">{defs}'
            f'<rect class="laut" width="{W}" height="{H:.0f}"/><path class="darat" d="{"".join(darat)}"/>'
            f'{"".join(jalur)}{titik}{"".join(label)}</svg>'
            '<div class="n sumber">المواضع من معجم الثريا الجغرافي (<bdi>al-Ṯurayyā, CC BY 4.0</bdi>)</div>')
