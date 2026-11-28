# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D تقطيع: taqthi' 'arudhi satu bait, dihitung pyarud (MIT): bahr, tulisan 'arudhi tiap taf'ilah (huruf bertasydid
dipecah dua, tanwin jadi nun, isyba' di akhir paruh), lambang «/» mutaharrik dan «٥» sakin, nama taf'ilah sesudah
zihafnya, dan zihafnya."""
import difflib, re

from sisipan import E, Salah, impor, satu

NAMA = "تقطيع"
PUSTAKA = ("pyarud",)
URAIAN = "satu bait berharakat lengkap: «بيت: صدر ... عجز» (pemisah « ... » seperti #V); bahr dan taqthi'-nya dihitung pyarud"
KUNCI = {"بيت": "صدر ... عجز"}
CONTOH = """#D تقطيع | الشكل (14): تقطيع مطلع معلقة امرئ القيس
#D بيت: قِفَا نَبْكِ مِنْ ذِكْرَى حَبِيبٍ وَمَنْزِلِ ... بِسِقْطِ اللِّوَى بَيْنَ الدَّخُولِ فَحَوْمَلِ"""
SUKUN, SYADDAH = "ْ", "ّ"
HARAKAT = "َُِ"
TANWIN = {"ً": "َ", "ٌ": "ُ", "ٍ": "ِ"}
ISYBA = {"ِ": "ي", "ُ": "و", "َ": "ا"}


def satuan(teks):
    """Tulisan 'arudhi berharakat: [(huruf, harakat)] dengan " " di antara kata; mad tanpa harakat = sakin, syaddah =
    sakin + mutaharrik, tanwin = harakat + nun sakin, akhir paruh yang berharakat diisyba'kan."""
    hasil = []
    for t in re.findall(r"\s+|.[ً-ْٰ]*", teks.strip()):
        if t.isspace():
            hasil.append((" ", ""))
            continue
        huruf, tanda = t[0], t[1:]
        harakat = next((m for m in tanda if m in HARAKAT), "")
        tanwin = next((TANWIN[m] for m in tanda if m in TANWIN), "")
        if SYADDAH in tanda:
            hasil.append((huruf, SUKUN))
        hasil += [(huruf, tanwin), ("ن", SUKUN)] if tanwin else [(huruf, harakat or SUKUN)]
    akhir = max(i for i, (h, _) in enumerate(hasil) if h != " ")
    if mad := ISYBA.get(hasil[akhir][1]):
        hasil.insert(akhir + 1, (mad, SUKUN))
    return hasil


def taqthi(n, paruh, analisis, pyarud):
    """[(tulisan 'arudhi, lambang, taf'ilah, zihaf)] tiap taf'ilah satu paruh. Huruf dan sakin/mutaharrik-nya dari pyarud
    (yang membuang hamzah washl dan lam syamsiyah); harakat tiap huruf dari huruf yang sama di teks asal."""
    from pyarud.processor import TAFEELA_VARIATION_MAP
    polos, pola = pyarud.ArudiConverter().prepare_text(paruh)
    polos = polos.replace("ةن", "تن")
    if len(polos.replace(" ", "")) == len(pola) + 1 and polos[-1] == polos[-2]:
        polos = polos[:-1]  # pyarud mengisyba'kan huruf mad di akhir paruh sekali lagi («تعرفنيي»), polanya tidak
    asal = [x for x in satuan(paruh) if x[0] != " "]
    huruf = [h for h in polos if h != " "]
    if len(huruf) != len(pola):
        raise Salah(n, f"tulisan 'arudhi «{paruh}» tidak bisa diselaraskan dengan hitungan pyarud: periksa harakatnya")
    harakat = {}
    for blok in difflib.SequenceMatcher(None, [h for h, _ in asal], huruf, autojunk=False).get_matching_blocks():
        harakat.update((blok.b + j, asal[blok.a + j][1]) for j in range(blok.size))
    u, k = [], 0  # (huruf, tanda) dengan " " di antara kata
    for h in polos:
        if h == " ":
            u.append((" ", ""))
            continue
        m = harakat.get(k, "")
        u.append((h, SUKUN if pola[k] == "0" else (m if m in HARAKAT else "")))
        k += 1
    salim = {v[0]: k[0] for k, v in TAFEELA_VARIATION_MAP.items() if k[0] == k[1]}  # taf'ilah salim -> polanya
    hasil, i = [], 0
    for kaki in analisis.feet:
        sisa, tulis = len(kaki.actual_segment), ""
        while sisa:
            h, m = u[i]
            tulis += h if h == " " or (m == SUKUN and h in "اى") else h + m
            sisa -= h != " "
            i += 1
        while i < len(u) and u[i][0] == " ":
            tulis, i = tulis + " ", i + 1
        nama = TAFEELA_VARIATION_MAP.get((salim.get(kaki.base_tafeela), kaki.actual_segment), (0, kaki.actual_tafeela))[1]
        hasil.append((tulis.strip(), "".join("/" if b == "1" else "٥" for b in kaki.actual_segment), nama,
                      kaki.zihaf_name_ar.split(" (")[0]))
    return hasil


def urai(n_kepala, baris):
    n, v = satu(n_kepala, baris, "بيت")
    paruh = [x.strip() for x in v.split("...")]
    if len(paruh) != 2 or not all(paruh):
        raise Salah(n, "«بيت:» harus dua paruh dipisah « ... »: صدر ... عجز")
    if not re.search("[َ-ْ]", v):
        raise Salah(n, "bait harus berharakat lengkap: pyarud menghitung dari harakatnya")
    pyarud = impor(n_kepala, "pyarud")
    r = pyarud.analyze_verse(*paruh)
    if not r.meter_name_ar or not r.is_valid:
        raise Salah(n, f"bait ini tidak cocok dengan bahr mana pun menurut pyarud ({'؛ '.join(map(str, r.errors)) or 'tanpa pesan'}): "
                       "periksa harakatnya")
    return {"bahr": re.sub("^بحر ", "البحر ", r.meter_name_ar), "paruh": paruh,
            "kaki": [taqthi(n, p, a, pyarud) for p, a in zip(paruh, (r.sadr, r.ajuz))]}


def html(d, angka):
    def satu_paruh(nama, kaki):
        sel = (("الكتابة العروضية", 0), ("الرموز", 1), ("التفعيلات", 2), ("الزحاف", 3))
        return "".join(f'<tr{" class=grup" if j == 0 and nama == "العجز" else ""}><th>{nama if j == 0 else ""}</th>'
                       f'<td class="kecil">{label}</td>'
                       + "".join(f'<td class="tengah{" rumuz" if k == 1 else ""}">{E(x[k])}</td>' for x in kaki) + "</tr>"
                       for j, (label, k) in enumerate(sel))
    bait = f'<div class="bait"><span>{E(d["paruh"][0])}</span><span>{E(d["paruh"][1])}</span></div>'
    return (f'<div class="tt">{E(d["bahr"])}</div>{bait}'
            f'<table class="tbl">{satu_paruh("الصدر", d["kaki"][0])}{satu_paruh("العجز", d["kaki"][1])}</table>')
