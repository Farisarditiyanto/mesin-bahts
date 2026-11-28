# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D بياني: رسم بياني hitam-putih bergaya buku statistik lama: أعمدة (batang mendatar, tumbuh dari kanan), نسبة (batang
100% bertumpuk, mis. skala Likert), خط (garis, tahun pertama di kanan). Seri dibedakan arsiran/garis putus, bukan warna."""
import math

from sisipan import E, Salah, pisah, satu

NAMA = "بياني"
URAIAN = ("«نوع: أعمدة/نسبة/خط»; «فئات: seri | seri» (nama seri; wajib untuk نسبة dan untuk lebih dari satu seri); "
          "«صف: label | nilai | nilai» satu baris tiap kategori, jumlah nilai = jumlah seri; «وحدة: ٪» pilihan")
KUNCI = {"نوع": "أعمدة/نسبة/خط", "فئات": "seri | seri", "صف": "label | nilai | nilai", "وحدة": "teks sesudah angka"}
CONTOH = """#D بياني | الشكل (14): آراء أفراد العينة في محاور الاستبانة (بيانات افتراضية للتوضيح)
#D نوع: نسبة
#D فئات: موافق بشدة | موافق | محايد | غير موافق
#D صف: وضوح الأحكام | 45 | 30 | 15 | 10
#D صف: سهولة التطبيق | 25 | 40 | 20 | 15
#D صف: ملاءمة العصر | 35 | 35 | 10 | 20"""
JENIS = ("أعمدة", "نسبة", "خط")
ARSIR = ("a1", "a2", "a3", "a4", "a5", "a6")  # pola isi tiap seri (tema.css), urut
GARIS = ("", "6 3", "1.5 2.5", "8 3 1.5 3", "3 3", "")  # garis putus tiap seri (خط)
TITIK = ("bulat", "kosong", "kotak", "segitiga", "bulat", "kosong")


def _angka(teks, n):
    t = teks.strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")).replace("٪", "").replace("%", "")
    try:
        return float(t)
    except ValueError:
        raise Salah(n, f"nilai «{teks}» bukan angka") from None


def urai(n_kepala, baris):
    n, nau = satu(n_kepala, baris, "نوع")
    if nau.strip() not in JENIS:
        raise Salah(n, f"«نوع:» harus salah satu dari: {'، '.join(JENIS)}")
    fiat = satu(n_kepala, baris, "فئات", wajib=False)
    silsilah = pisah(fiat[1]) if fiat else []
    if fiat and not all(silsilah):
        raise Salah(fiat[0], "«فئات:» berisi nama seri yang kosong")
    shufuf = []
    for n, k, v in baris:
        if k == "صف":
            bagian = pisah(v)
            if len(bagian) < 2 or not bagian[0]:
                raise Salah(n, f"«صف:» harus berbentuk «{KUNCI['صف']}»")
            nilai = [_angka(x, n) for x in bagian[1:]]
            if any(x < 0 for x in nilai):
                raise Salah(n, "nilai negatif belum didukung")
            if silsilah and len(nilai) != len(silsilah):
                raise Salah(n, f"«صف:» memuat {len(nilai)} nilai, padahal «فئات:» menyebut {len(silsilah)} seri")
            if not silsilah and shufuf and len(nilai) != len(shufuf[0][1]):
                raise Salah(n, "jumlah nilai tiap «صف:» harus sama")
            shufuf.append((bagian[0], nilai))
    if len(shufuf) < 2:
        raise Salah(n_kepala, "بياني butuh paling sedikit dua baris «#D صف: …»")
    jumlah = len(shufuf[0][1])
    if jumlah > len(ARSIR):
        raise Salah(n_kepala, f"paling banyak {len(ARSIR)} seri")
    if (nau.strip() == "نسبة" or jumlah > 1) and not silsilah:
        raise Salah(n_kepala, "baris «#D فئات: seri | seri» belum ada (nama tiap seri untuk keterangan)")
    if nau.strip() == "نسبة" and any(not sum(v) for _, v in shufuf):
        raise Salah(n_kepala, "baris «صف:» نسبة yang jumlahnya nol")
    wahdah = satu(n_kepala, baris, "وحدة", wajib=False)
    return {"nau": nau.strip(), "silsilah": silsilah, "shufuf": shufuf, "wahdah": wahdah[1] if wahdah else ""}


def _skala(maks):
    """(langkah, puncak) tanda sumbu yang rapi: langkah 1/2/2,5/5 × 10^k, 3-6 tanda."""
    if maks <= 0:
        return 1, 1
    pangkat = 10 ** math.floor(math.log10(maks / 5))
    langkah = next(s * pangkat for s in (1, 2, 2.5, 5, 10, 20) if maks / (s * pangkat) <= 6)
    return langkah, math.ceil(maks / langkah - 1e-9) * langkah


def _tulis(angka):
    def tulis(x):
        s = f"{x:.2f}".rstrip("0").rstrip(".")
        return angka(s).replace(".", "٫") if angka("1") != "1" else s
    return tulis


def _ket(silsilah, tanda):
    return '<div class="ket">' + "".join(f'<span>{tanda(i)} {E(s)}</span>' for i, s in enumerate(silsilah)) + "</div>"


def _amdah(d, tulis):
    langkah, puncak = _skala(max(max(v) for _, v in d["shufuf"]))
    w = d["wahdah"]
    baris = "".join(
        f'<div class="lb">{E(label)}</div><div class="bidang">'
        + "".join(f'<div class="bb"><div class="bar {ARSIR[i]}" style="width:{x / puncak * 100:.3f}%"></div>'
                  f'<span class="nilai">{tulis(x)}{E(w)}</span></div>' for i, x in enumerate(nilai))
        + "</div>" for label, nilai in d["shufuf"])
    skala = "".join(f'<span style="right:{t / puncak * 100:.3f}%">{tulis(t)}</span>'
                    for t in (langkah * i for i in range(round(puncak / langkah) + 1)))
    ket = _ket(d["silsilah"], lambda i: f'<i class="kotak {ARSIR[i]}"></i>') if len(d["silsilah"]) > 1 else ""
    # ruang kiri secukupnya untuk angka di ujung batang terpanjang (taksiran 5 px per huruf, bidang 9 cm = 340 px)
    ruang = max(len(tulis(x) + w) * 5 + 4 - (1 - x / puncak) * 340 for _, v in d["shufuf"] for x in v)
    return f'<div class="amdah" style="padding-left:{max(ruang, 0):.0f}px">{baris}<div></div><div class="skala">{skala}</div></div>{ket}'


def _nisbah(d, tulis):
    baris = ""
    for label, nilai in d["shufuf"]:
        jumlah = sum(nilai)
        ruas = "".join(f'<div class="ruas {ARSIR[i]}" style="width:{x / jumlah * 100:.3f}%">'
                       + (f"<span>{tulis(round(x / jumlah * 100))}٪</span>" if x / jumlah >= 0.08 else "") + "</div>"
                       for i, x in enumerate(nilai) if x)
        baris += f'<div class="lb">{E(label)}</div><div class="batang">{ruas}</div>'
    return f'<div class="nisbah100">{baris}</div>' + _ket(d["silsilah"], lambda i: f'<i class="kotak {ARSIR[i]}"></i>')


def _khatt(d, tulis):
    W, H, kanan, kiri, atas, bawah = 440, 166, 28, 4, 7, 24
    shufuf = d["shufuf"]
    langkah, puncak = _skala(max(max(v) for _, v in shufuf))
    lebar, tinggi = W - kanan - kiri, H - atas - bawah
    x = lambda i: W - kanan - 16 - i * (lebar - 40) / max(1, len(shufuf) - 1)  # kategori pertama di kanan
    y = lambda v: atas + tinggi - v / puncak * tinggi
    s = [f'<line x1="{W - kanan}" y1="{atas}" x2="{W - kanan}" y2="{atas + tinggi}"/>',
         f'<line x1="{kiri}" y1="{atas + tinggi}" x2="{W - kanan}" y2="{atas + tinggi}"/>']
    for i in range(round(puncak / langkah) + 1):
        v = langkah * i
        s.append(f'<line x1="{W - kanan}" y1="{y(v):.2f}" x2="{W - kanan + 4}" y2="{y(v):.2f}"/>'
                 f'<text x="{W - kanan + 7}" y="{y(v) + 5:.2f}" class="kiri">{tulis(v)}</text>')
    for i, (label, _) in enumerate(shufuf):
        s.append(f'<line x1="{x(i):.2f}" y1="{atas + tinggi}" x2="{x(i):.2f}" y2="{atas + tinggi + 4}"/>'
                 f'<text x="{x(i):.2f}" y="{atas + tinggi + 20}">{E(label)}</text>')

    def titik(j, px, py):
        if TITIK[j] == "kotak":
            return f'<rect x="{px - 3:.2f}" y="{py - 3:.2f}" width="6" height="6" class="isi"/>'
        if TITIK[j] == "segitiga":
            return f'<path d="M{px:.2f},{py - 4:.2f} L{px + 4:.2f},{py + 3:.2f} L{px - 4:.2f},{py + 3:.2f} Z" class="isi"/>'
        return f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3" class="{"isi" if TITIK[j] == "bulat" else "kosong"}"/>'

    for j in range(len(shufuf[0][1])):
        titik_j = [(x(i), y(v[j])) for i, (_, v) in enumerate(shufuf)]
        s.append(f'<polyline points="{" ".join(f"{a:.2f},{b:.2f}" for a, b in titik_j)}"'
                 + (f' stroke-dasharray="{GARIS[j]}"' if GARIS[j] else "") + "/>")
        s += [titik(j, a, b) for a, b in titik_j]
    contoh = lambda j: ('<svg class="contoh" viewBox="0 0 28 10" width="28" height="10"><line x1="1" y1="5" x2="27" y2="5"'
                        + (f' stroke-dasharray="{GARIS[j]}"' if GARIS[j] else "") + f"/>{titik(j, 14, 5)}</svg>")
    ket = _ket(d["silsilah"], contoh) if len(d["silsilah"]) > 1 else ""
    return f'<svg class="khatt" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(s)}</svg>{ket}'


def html(d, angka):
    tulis = _tulis(angka)
    w = d["wahdah"]
    # angka di nama seri dan label kategori (mis. tahun) mengikuti @angka; satuan ditulis berspasi kecuali tanda persen
    d = {**d, "silsilah": [angka(s) for s in d["silsilah"]], "shufuf": [(angka(lb), v) for lb, v in d["shufuf"]],
         "wahdah": w if w in ("", "٪", "%") else f" {w}"}
    return {"أعمدة": _amdah, "نسبة": _nisbah, "خط": _khatt}[d["nau"]](d, tulis)
