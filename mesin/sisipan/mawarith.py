# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D مواريث: mahasiswa menulis ahli waris (dan harta), mesin MENGHITUNG bagiannya sendiri: فروض، تعصيب، حجب، عول، رد،
العمريتان، تصحيح. Hasil = جدول المسألة (أصل المسألة، العول/الرد، التصحيح، سهام tiap waris) + batang sebanding.

Aturan = pendapat jumhur yang diajarkan di kitab faraid (mis. الرحبية): الأب يحجب الجدة لأب (`JUMHUR`), إخوة yang
terhalang tetap mengurangi bagian ibu, رد ke ashab al-furudh selain suami/istri. Masalah yang jawabannya khilaf tanpa
pendapat bawaan yang jelas (الجد مع الإخوة، المشتركة، harta sisa yang hanya ada suami/istri) = `BelumDidukung`, bukan
jawaban yang mungkin salah. `hitung` murni (tanpa HTML), dipakai juga `#D حجب`."""
from dataclasses import dataclass
from fractions import Fraction as F
from math import lcm

import norma
from sisipan import E, Salah, bilangan, pisah

NAMA = "مواريث"
URAIAN = ("ahli waris, satu baris tiap jenis: «وارث: nama | jumlah» (jumlah pilihan, bawaan 1); «تركة: angka» pilihan "
          "(kolom bagian harta). Mesin menghitung فروض، تعصيب، حجب، عول، رد، العمريتان dan تصحيح; الجد مع الإخوة "
          "dan المشتركة belum didukung (GAGAL)")
KUNCI = {"وارث": "nama | jumlah", "تركة": "angka"}
CONTOH = """#D مواريث | الشكل (7): قسمة تركة عن زوجة وبنت وأم وعم شقيق
#D وارث: زوجة
#D وارث: بنت
#D وارث: أم
#D وارث: عم شقيق
#D تركة: 240000"""

# kunci -> (nama cetak, laki-laki, jumlah paling banyak)
WARATHA = {
    "زوج": ("الزوج", True, 1), "زوجة": ("الزوجة", False, 4),
    "أب": ("الأب", True, 1), "أم": ("الأم", False, 1), "جد": ("الجد", True, 1),
    "جدة لأب": ("الجدة لأب", False, 1), "جدة لأم": ("الجدة لأم", False, 1),
    "ابن": ("الابن", True, 0), "بنت": ("البنت", False, 0),
    "ابن ابن": ("ابن الابن", True, 0), "بنت ابن": ("بنت الابن", False, 0),
    "أخ شقيق": ("الأخ الشقيق", True, 0), "أخت شقيقة": ("الأخت الشقيقة", False, 0),
    "أخ لأب": ("الأخ لأب", True, 0), "أخت لأب": ("الأخت لأب", False, 0),
    "أخ لأم": ("الأخ لأم", True, 0), "أخت لأم": ("الأخت لأم", False, 0),
    "ابن أخ شقيق": ("ابن الأخ الشقيق", True, 0), "ابن أخ لأب": ("ابن الأخ لأب", True, 0),
    "عم شقيق": ("العم الشقيق", True, 0), "عم لأب": ("العم لأب", True, 0),
    "ابن عم شقيق": ("ابن العم الشقيق", True, 0), "ابن عم لأب": ("ابن العم لأب", True, 0),
}
# العصبة بالنفس, urut dari yang terdekat: yang ada paling atas mengambil sisa dan menghalangi yang di bawahnya
# (kecuali الأب/الجد di bawah الابن/ابن الابن: keduanya tetap mendapat ١/٦)
ASABAH = ("ابن", "ابن ابن", "أب", "جد", "أخ شقيق", "أخ لأب", "ابن أخ شقيق", "ابن أخ لأب",
          "عم شقيق", "عم لأب", "ابن عم شقيق", "ابن عم لأب")
PASANGAN = {"ابن": "بنت", "ابن ابن": "بنت ابن", "أخ شقيق": "أخت شقيقة", "أخ لأب": "أخت لأب"}  # للذكر مثل حظ الأنثيين
FAR = ("ابن", "بنت", "ابن ابن", "بنت ابن")  # الفرع الوارث
IKHWA = ("أخ شقيق", "أخت شقيقة", "أخ لأب", "أخت لأب", "أخ لأم", "أخت لأم")
JUMHUR = {("جدة لأب", "أب")}  # (المحجوب، الحاجب) yang khilaf; hasilnya pendapat jumhur
GANDA = {"بنتان": ("بنت", 2), "بنتا ابن": ("بنت ابن", 2), "أختان شقيقتان": ("أخت شقيقة", 2), "أختان لأب": ("أخت لأب", 2),
         "أخوان لأم": ("أخ لأم", 2), "أخوان شقيقان": ("أخ شقيق", 2)}
SINONIM = {"ابنة": "بنت", "لأبوين": "شقيق"}


class BelumDidukung(Exception):
    """Masalah yang jawabannya khilaf tanpa pendapat bawaan: mesin tidak menebak."""


def _kunci_nama(teks):
    """Nama waris tanpa «ال» di tiap kata, ejaan disamakan: «بنت الابن» = «بنت ابن», «الأخت الشقيقة» = «أخت شقيقة»."""
    kata = [k[2:] if k.startswith("ال") and len(k) > 3 else k for k in norma.norm(teks).split()]
    return " ".join(norma.norm(SINONIM.get(k, k)) for k in kata)


_DIKENAL = {_kunci_nama(k): k for k in WARATHA} | {_kunci_nama(k): v for k, v in GANDA.items()}


def nama_waris(n, teks):
    """«بنت الابن» -> "بنت ابن"; «البنتان» -> ("بنت", 2); nama yang tidak dikenal = Salah yang menyebut daftarnya."""
    if (k := _DIKENAL.get(_kunci_nama(teks))) is None:
        raise Salah(n, f"ahli waris «{teks}» tidak dikenal (yang ada: {'، '.join(WARATHA)})")
    return k


@dataclass(frozen=True)
class Baris:
    kunci: str
    jumlah: int
    label: str  # الفرض (angka Latin): «1/2», «الباقي تعصيبًا», «1/6 والباقي», «ثلث الباقي», «محجوب»
    bagian: F  # bagian seluruh kelompok dari harta (sesudah عول/رد)
    hajib: str = ""  # kunci yang menghalanginya


@dataclass(frozen=True)
class Hasil:
    baris: tuple
    asl: int  # أصل المسألة
    akhir: int  # sesudah عول/رد (= asl kalau tidak ada)
    hal: str  # "" | "عول" | "رد"
    tashih: int  # pengali التصحيح (1 = tidak perlu)
    kelompok: tuple = ()  # عصبة laki-laki dan perempuan yang berbagi sisa (2:1); sahamnya di أصل المسألة satu

    @property
    def pokok(self):
        return self.akhir * self.tashih

    def saham(self, b):
        return b.bagian * self.pokok


def hitung(w):
    """{kunci waris: jumlah} -> Hasil. Satu-satunya tempat aturan faraid mesin ini."""
    ada = lambda *k: any(w.get(x, 0) for x in k)
    hajb = {}  # kunci -> kunci penghalang

    def halangi(k, oleh):
        if w.get(k) and k not in hajb:
            hajb[k] = oleh

    # حجب الحرمان bukan karena urutan ashabah
    for k in ("ابن ابن", "بنت ابن"):
        if ada("ابن"):
            halangi(k, "ابن")
    if w.get("بنت", 0) >= 2 and not ada("ابن ابن"):
        halangi("بنت ابن", "بنت")
    halangi("جد", "أب") if ada("أب") else None
    if ada("أم"):
        halangi("جدة لأب", "أم")
        halangi("جدة لأم", "أم")
    if ada("أب"):
        halangi("جدة لأب", "أب")
    hidup = lambda k: w.get(k, 0) and k not in hajb
    far = [k for k in FAR if hidup(k)]
    for k in ("أخ لأم", "أخت لأم"):
        for oleh in far + [x for x in ("أب", "جد") if hidup(x)]:
            halangi(k, oleh)
    if hidup("جد") and not ada("ابن", "ابن ابن") and ada("أخ شقيق", "أخت شقيقة", "أخ لأب", "أخت لأب"):
        raise BelumDidukung("مسألة الجد مع الإخوة (khilaf: الجد يحجب الإخوة atau المقاسمة)")
    # urutan ashabah: saudari bersama anak perempuan (عصبة مع الغير) menempati tingkat saudara sekandungnya
    for i, k in enumerate(ASABAH):
        if not hidup(k):
            continue
        for bawah in ASABAH[i + 1:]:
            if not (k in ("ابن", "ابن ابن") and bawah in ("أب", "جد")):
                halangi(bawah, k)
                halangi(PASANGAN.get(bawah, ""), k)
        if k in ("ابن", "ابن ابن", "أب"):
            halangi("أخت شقيقة", k)
            halangi("أخت لأب", k)
    if w.get("أخت شقيقة", 0) >= 2 and not ada("أخ لأب"):
        halangi("أخت لأب", "أخت شقيقة")
    ada_bint = any(hidup(k) for k in ("بنت", "بنت ابن"))
    ghair = ""  # saudari yang menjadi عصبة مع الغير
    if hidup("أخت شقيقة") and not ada("أخ شقيق") and ada_bint:
        ghair = "أخت شقيقة"
    elif hidup("أخت لأب") and not ada("أخ لأب") and ada_bint:
        ghair = "أخت لأب"
    if ghair:  # menghalangi seperti saudara laki-laki setingkatnya
        setara = "أخ شقيق" if ghair == "أخت شقيقة" else "أخ لأب"
        for bawah in ASABAH[ASABAH.index(setara) + 1:]:
            halangi(bawah, ghair)
            halangi(PASANGAN.get(bawah, ""), ghair)

    far = [k for k in FAR if hidup(k)]
    far_l = any(k in far for k in ("ابن", "ابن ابن"))
    jml_ikhwa = sum(w.get(k, 0) for k in IKHWA)  # yang terhalang pun mengurangi bagian ibu
    fard, label = {}, {}

    def beri(k, bagian, teks=""):
        fard[k] = F(bagian)
        label[k] = teks or _pecahan(bagian)

    if hidup("زوج"):
        beri("زوج", F(1, 4) if far else F(1, 2))
    if hidup("زوجة"):
        beri("زوجة", F(1, 8) if far else F(1, 4))
    ushul = [k for k in ("أب", "جد") if hidup(k)]
    for k in ushul:
        if far:
            beri(k, F(1, 6), "" if far_l else "1/6 والباقي")
    if hidup("أم"):
        if far or jml_ikhwa >= 2:
            beri("أم", F(1, 6))
        elif ada("زوج", "زوجة") and hidup("أب"):  # العمريتان
            beri("أم", F(1, 3) * (1 - fard.get("زوج", fard.get("زوجة", 0))), "ثلث الباقي")
        else:
            beri("أم", F(1, 3))
    jaddat = [k for k in ("جدة لأب", "جدة لأم") if hidup(k)]
    for k in jaddat:
        beri(k, F(1, 6) / len(jaddat), "1/6" + (" بالاشتراك" if len(jaddat) > 1 else ""))
    if hidup("بنت") and not hidup("ابن"):
        beri("بنت", F(1, 2) if w["بنت"] == 1 else F(2, 3))
    if hidup("بنت ابن") and not hidup("ابن ابن") and not hidup("ابن"):
        if not hidup("بنت"):
            beri("بنت ابن", F(1, 2) if w["بنت ابن"] == 1 else F(2, 3))
        else:
            beri("بنت ابن", F(1, 6), "1/6 تكملة للثلثين")
    if hidup("أخت شقيقة") and not ada("أخ شقيق") and ghair != "أخت شقيقة":
        beri("أخت شقيقة", F(1, 2) if w["أخت شقيقة"] == 1 else F(2, 3))
    if hidup("أخت لأب") and not ada("أخ لأب") and ghair != "أخت لأب":
        if "أخت شقيقة" in fard:
            beri("أخت لأب", F(1, 6), "1/6 تكملة للثلثين")
        else:
            beri("أخت لأب", F(1, 2) if w["أخت لأب"] == 1 else F(2, 3))
    umm = [k for k in ("أخ لأم", "أخت لأم") if hidup(k)]
    jml_umm = sum(w[k] for k in umm)
    for k in umm:  # الذكر كالأنثى
        beri(k, (F(1, 6) if jml_umm == 1 else F(1, 3)) * w[k] / jml_umm,
             ("1/6" if jml_umm == 1 else "1/3") + (" بالاشتراك" if len(umm) > 1 else ""))

    # العصبة: yang terdekat, beserta saudarinya (2:1); atau saudari مع الغير; atau الأب/الجد bersama anak perempuan
    asib = next((k for k in ASABAH if hidup(k) and not (k in ushul and far_l)), "")
    kelompok = []
    if ghair and (not asib or ASABAH.index(asib) > ASABAH.index("أخ شقيق" if ghair == "أخت شقيقة" else "أخ لأب")):
        kelompok = [ghair]
    elif asib:
        kelompok = [asib] + ([PASANGAN[asib]] if hidup(PASANGAN.get(asib, "")) else [])
    jumlah = sum(fard.values(), F(0))
    sisa = 1 - jumlah
    hal = ""
    bagian = dict(fard)
    if kelompok:
        if sisa > 0:
            kepala = {k: w[k] * (2 if WARATHA[k][1] and len(kelompok) > 1 else 1) for k in kelompok}
            for k in kelompok:
                bagian[k] = bagian.get(k, 0) + sisa * kepala[k] / sum(kepala.values())
        elif umm and "أخ شقيق" in kelompok and ada("زوج"):
            raise BelumDidukung("المسألة المشتركة (khilaf: الإخوة الأشقاء يشاركون الإخوة لأم atau tidak mendapat apa-apa)")
        for k in kelompok:
            label.setdefault(k, "الباقي تعصيبًا" if k != ghair else "الباقي (عصبة مع الغير)")
    if jumlah > 1:
        hal = "عول"
        bagian = {k: v / jumlah for k, v in bagian.items()}
    elif sisa > 0 and not kelompok:
        penerima = [k for k in fard if k not in ("زوج", "زوجة")]
        if not penerima:
            raise BelumDidukung("sisa harta yang hanya ada suami/istri (khilaf: الرد على الزوجين atau بيت المال)")
        hal = "رد"
        tetap = sum(v for k, v in fard.items() if k in ("زوج", "زوجة"))
        jml_rad = sum(fard[k] for k in penerima)
        for k in penerima:
            bagian[k] = (1 - tetap) * fard[k] / jml_rad
    for k in w:
        if k in hajb:
            label[k], bagian[k] = "محجوب", F(0)
        elif k not in bagian:
            label[k], bagian[k] = "لم يبق له شيء", F(0)  # عاصب yang tidak kebagian sisa
    asl = lcm(*(v.denominator for v in (list(fard.values()) + ([sisa] if kelompok and sisa > 0 else []))))
    akhir = asl
    if hal == "رد":  # tanpa suami/istri: jumlah saham ashab al-furudh; bersamanya: penyebut bagian akhir
        akhir = (lcm(*(v.denominator for v in bagian.values() if v)) if ada("زوج", "زوجة")
                 else sum(int(v * asl) for v in fard.values()))
    if hal == "عول":
        akhir = sum(int(v * asl) for v in fard.values())
    # التصحيح: pengali terkecil yang membuat saham tiap orang utuh
    tashih = lcm(*((v * akhir / w[k]).denominator for k, v in bagian.items() if v))
    urut = [k for k in WARATHA if k in w]
    return Hasil(tuple(Baris(k, w[k], label[k], bagian[k], hajb.get(k, "")) for k in urut), asl, akhir, hal, tashih,
                 tuple(k for k in urut if k in kelompok) if len(kelompok) > 1 else ())


def _pecahan(f):
    return f"{F(f).numerator}/{F(f).denominator}"


def urai(n_kepala, baris):
    waris, tirkah = {}, None
    for n, k, v in baris:
        if k == "وارث":
            bagian = pisah(v)
            if len(bagian) > 2 or not bagian[0]:
                raise Salah(n, f"«وارث:» harus berbentuk «{KUNCI['وارث']}»")
            nama = nama_waris(n, bagian[0])
            kunci, jumlah = nama if isinstance(nama, tuple) else (nama, 1)
            if len(bagian) == 2:
                jumlah = bilangan(n, bagian[1], "jumlah waris")
            if kunci in waris:
                raise Salah(n, f"«{WARATHA[kunci][0]}» ditulis dua kali: tulis jumlahnya «وارث: {kunci} | 2»")
            batas = WARATHA[kunci][2]
            if not 1 <= jumlah or (batas and jumlah > batas):
                raise Salah(n, f"jumlah «{WARATHA[kunci][0]}» harus 1" + (f"-{batas}" if batas > 1 else ""))
            if {"زوج", "زوجة"} <= set(waris) | {kunci}:
                raise Salah(n, "الزوج dan الزوجة tidak berkumpul dalam satu masalah")
            waris[kunci] = jumlah
        elif k == "تركة":
            if tirkah is not None:
                raise Salah(n, "«تركة:» ditulis dua kali")
            t = v.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")).replace(",", "").replace("،", "").strip()
            try:
                tirkah = F(t)
            except ValueError:
                raise Salah(n, f"«تركة:» harus angka, bukan «{v}»") from None
    if not waris:
        raise Salah(n_kepala, "baris «#D وارث: …» belum ada")
    try:
        hasil = hitung(waris)
    except BelumDidukung as e:
        raise Salah(n_kepala, f"{e} belum didukung: tulis pembagiannya sebagai tabel #J") from None
    return {"hasil": hasil, "tirkah": tirkah}


ARSIR = ("a1", "a2", "a3", "a4", "a5", "a6")  # pola arsir batang (tema.css), bergiliran


def _uang(x, angka):
    s = f"{x:,.0f}" if x.denominator == 1 else f"{float(x):,.2f}"
    return angka(s).replace(",", "٬").replace(".", "٫") if angka("1") != "1" else s


def html(d, angka):
    h, tirkah = d["hasil"], d["tirkah"]
    frac = lambda f: angka(f"{f.numerator}/{f.denominator}") if f else "—"
    kolom = [f"أصل المسألة {angka(h.asl)}"]
    if h.hal == "عول":
        kolom = [f"{angka(h.asl)} وعالت إلى {angka(h.akhir)}"]
    elif h.hal == "رد":
        kolom = [f"{angka(h.asl)} وردّت إلى {angka(h.akhir)}"]
    if h.tashih > 1:
        kolom.append(f"التصحيح {angka(h.pokok)}")
    kepala = ("<tr><th>الوارث</th><th>الفرض</th>" + "".join(f"<th>{k}</th>" for k in kolom)
              + "<th>سهام الواحد</th>" + ("<th>النصيب من التركة</th>" if tirkah else "") + "</tr>")
    baris, potong = [], []
    for b in h.baris:
        nama = WARATHA[b.kunci][0] + (f" ({angka(b.jumlah)})" if b.jumlah > 1 else "")
        catatan = f'<br><span class="n">ب{WARATHA[b.hajib][0]}{"*" if (b.kunci, b.hajib) in JUMHUR else ""}</span>' if b.hajib else ""
        sel = [f"{E(nama)}", f'{E(angka(b.label))}{catatan}']
        if b.kunci in h.kelompok:  # satu saham bersama di أصل المسألة, sel kedua menyambung sel pertama
            sel.append(angka(sum(x.bagian for x in h.baris if x.kunci in h.kelompok) * h.akhir)
                       if b.kunci == h.kelompok[0] else "")
        else:
            sel.append(angka(b.bagian * h.akhir) if b.bagian else "—")
        if h.tashih > 1:
            sel.append(angka(h.saham(b)) if b.bagian else "—")
        sel.append(angka(h.saham(b) / b.jumlah) if b.jumlah > 1 and b.bagian else "—")
        if tirkah:
            sel.append(_uang(b.bagian * tirkah, angka) if b.bagian else "—")
        gabung = {h.kelompok[0]: " atas", h.kelompok[-1]: " sambung"}.get(b.kunci, "") if h.kelompok else ""
        baris.append(f'<tr><td>{sel[0]}</td>' + "".join(f'<td class="tengah{gabung if j == 1 else ""}">{s}</td>'
                                                       for j, s in enumerate(sel[1:])) + "</tr>")
        if b.bagian:
            potong.append((b, len(potong)))
    if tirkah:
        baris.append(f'<tr class="jumlah"><td>المجموع</td><td class="tengah">—</td><td class="tengah">{angka(h.akhir)}</td>'
                     + (f'<td class="tengah">{angka(h.pokok)}</td>' if h.tashih > 1 else "")
                     + f'<td class="tengah">—</td><td class="tengah">{_uang(tirkah, angka)}</td></tr>')
    # batang sebanding: tiap waris sebidang selebar bagiannya, namanya di bawah (gambar.js menyusun lajurnya)
    batang, tanda, kiri = "", "", F(0)
    for b, i in potong:
        lebar = float(b.bagian) * 100
        batang += (f'<div class="ruas {ARSIR[i % len(ARSIR)]}" style="width:{lebar:.4f}%">'
                   + (f'<span>{frac(b.bagian)}</span>' if lebar >= 9 else "") + "</div>")
        tanda += f'<div class="tanda" data-x="{float(kiri + b.bagian / 2):.4f}" data-sisi="b">{E(WARATHA[b.kunci][0])}' \
                 + (f" {frac(b.bagian)}" if lebar < 9 else "") + "</div>"
        kiri += b.bagian
    jumhur = any((b.kunci, b.hajib) in JUMHUR for b in h.baris)
    return (f'<table class="tbl">{kepala}{"".join(baris)}</table>'
            + ('<div class="n">* عند الجمهور.</div>' if jumhur else "")
            + f'<div class="lajur bagi"><div class="batang">{batang}</div>{tanda}</div>')
