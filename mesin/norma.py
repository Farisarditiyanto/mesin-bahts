"""Penyamaan tulisan Arab (`norm`, `padat`) dan cache teks `padat` tiap kitab. Dipakai lewat shamela.py.

Hanya berkas ini yang menentukan isi cache: sidiknya (VERSI) jadi nama berkas cache. Aturan penyamaan yang diubah di
sini membuat cache baru; perubahan di berkas lain tidak. Modul berkas hanya menangani penulisan, bukan isi normalisasi.
"""
import gzip, hashlib, json, re, unicodedata
from pathlib import Path
from berkas import sementara

HARAKAT = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")  # harakat, tanda mushaf, tatwil (ditulis sebagai kode: penyunting teks bisa menukar urutan harakat)
TAGS = re.compile(r"<[^>]+>")
HORMAT = re.compile(
    r"صل[يى] الله عليه(?: وعل[يى] [آا]له| و[آا]له)?(?: وصحبه)? وسلم|رض[يى] الله(?: تعال[يى])? عنه(?:ما|م|ا|ن)?"
    r"|علي(?:هما|هم|ها|ه) (?:الصلا[ةه] و)?السلام|رحمه(?:ما|م|ا)? الله(?: تعال[يى])?|عز وجل|جل جلاله"
    r"|سبحانه وتعالى|تبارك وتعالى|صلعم|قدس الله روحه")
# ligatur kalimat hormat tanpa pecahan NFKC (﵀-﵏ dari Unicode 14, ﷾ ﷿): dibuang, bentuk panjangnya dibuang HORMAT
LIGATUR_HORMAT = re.compile(r"[﵀-﵏﷾﷿]")
# bentuk huruf yang disamakan; huruf Persia (ی ک ە ھ) sering terbawa dari PDF/situs
# ؤ/ئ tidak disamakan dengan ء: بئس («seburuk-buruk») ≠ بؤس («kesengsaraan»); kursi hamzah yang beda menurut cetakan
# disamakan per kata di EJAAN
SAMA = (("إ", "ا"), ("أ", "ا"), ("آ", "ا"), ("ٱ", "ا"), ("ٲ", "ا"), ("ٳ", "ا"), ("ى", "ي"), ("ة", "ه"), ("ؤ", "و"), ("ئ", "ي"),
        ("ی", "ي"), ("ے", "ي"), ("ۓ", "ي"), ("ک", "ك"), ("ڪ", "ك"), ("ە", "ه"), ("ھ", "ه"), ("ۀ", "ه"), ("ہ", "ه"), ("ۃ", "ه"),
        ("ں", "ن"), ("ٮ", "ب"))
# ejaan kata yang sama-sama sah dan dipakai bergantian, bahkan dalam satu kitab; hanya pasangan yang tidak mungkin
# menyatukan dua kata berbeda makna («مائة/مئة» tidak: «مائه» juga «airnya»). Dicocokkan sesudah SAMA
# Kursi hamzah ditulis sesudah SAMA (ؤ->و, ئ->ي): مسئول/مسؤول، شئون/شؤون، رءوس/رؤوس، تساءل/تساؤل
EJAAN = (("سماوات", "سموات"), ("اسحاق", "اسحق"), ("داوود", "داود"), ("طاووس", "طاوس"),
         ("مسيول", "مسوول"), ("شيون", "شوون"), ("رءوس", "رووس"), ("تساءل", "تساول"), ("رحمان", "رحمن"))


BUKAN_HURUF = re.compile(r"[^ء-ي0-9]+")
BUKAN_ABJAD = re.compile(r"[^ء-ي]+")
PRESENTASI = re.compile(r"[\u0675-\u0678\ufb50-\ufdfc\ufe70-\ufefc]")  # bentuk presentasi yang dipecah NFKC (﷽ ﷾ ﷿ tidak)
SYAI = re.compile(r"شئ(?![ء-ي])")
SYAI_TANPA_HAMZAH = re.compile(r"(?<![ء-ي])([وفبلك]{0,2}(?:ال)?)شي(?![ء-ي])")  # «شي» = «شيء»; «يمشي», «شيئا» tidak
IBNU = re.compile(r"(?<![ء-ي])ابن(?![ء-ي])")
BAGIAN = (("body", ""), ("footnotes", " [حاشية]"))  # bagian rekaman kitab, dan tandanya di keluaran
PENANDA = re.compile(r"⦗([٠-٩]+)⦘")  # awal halaman cetak berikutnya di dalam satu rekaman


def norm(s):
    """Samakan tulisan Arab: buang harakat/tatwil dan kalimat hormat, satukan bentuk alif/ya/ta marbuthah."""
    # NFKC paling awal: memecah ﻻ dan bentuk presentasi lain (ﷺ/ﷻ jadi kalimat hormat, yang lalu dibuang HORMAT).
    # ﷺ dan ﷻ (ada di hampir tiap halaman kitab hadits) langsung dibuang: hasilnya sama, NFKC-nya tidak perlu.
    s = LIGATUR_HORMAT.sub(" ", s.replace("ﷺ", " ").replace("ﷻ", " "))
    if "﷽" in s:  # ligatur basmalah: dijabarkan, bukan dibuang (NFKC tidak memecahnya)
        s = s.replace("﷽", " بسم الله الرحمن الرحيم ")
    if PRESENTASI.search(s):
        s = unicodedata.normalize("NFKC", s)
    s = HORMAT.sub(" ", HARAKAT.sub("", TAGS.sub("", s)))
    if "شئ" in s:  # ejaan lama «شئ» = «شيء»; «شئت» (kehendak) tidak ikut
        s = SYAI.sub("شيء", s)
    if "شي" in s:  # ketikan Shamela tanpa hamzah: «كل شي» = «كل شيء»
        s = SYAI_TANPA_HAMZAH.sub(r"\1شيء", s)
    for dari, ke in SAMA:
        s = s.replace(dari, ke)  # str.replace jauh lebih cepat daripada regex untuk ganti satu huruf
    for dari, ke in EJAAN:
        if dari in s:
            s = s.replace(dari, ke)
    if "ابن" in s:  # «محمد ابن يحيى» = «محمد بن يحيى»: alif «ابن» ditulis atau tidak menurut penyunting
        s = IBNU.sub("بن", s)
    return BUKAN_HURUF.sub(" ", s).strip()


def _potong(p, bagian="body"):
    """Satu rekaman bisa memuat beberapa halaman cetak (penanda ⦗n⦘): pecah jadi [(halaman, teks)].
    Teks sebelum penanda pertama milik page_num."""
    hal, out = p.get("page_num"), []
    for k, b in enumerate(PENANDA.split(p.get(bagian) or "")):
        if k % 2:
            hal = int(b)  # int() membaca angka Arab ٠-٩ juga
        else:
            out.append((hal, b))
    return out


def padat(s):
    """Huruf Arab saja, tanpa spasi dan angka: bentuk yang dicocokkan `cari`, `teks`, `bab`, dan `cek`.
    Spasi diabaikan supaya «و "الإحياء"» tetap ketemu dengan «والإحياء»."""
    return BUKAN_ABJAD.sub("", norm(s))


def _ruas(p, bagian):
    """Teks `padat` satu bagian rekaman dan ruas halamannya [(awal, akhir, hal_awal, hal_akhir)]; dihitung sekali per rekaman.
    حاشية tanpa penanda ⦗n⦘ di rekaman banyak halaman: halaman tiap catatan tidak tercatat, jadi ruasnya = seluruh rekaman."""
    kunci = "_padat_" + bagian
    if kunci not in p:
        potong = _potong(p, bagian)
        if bagian != "body" and len(potong) == 1:
            ruas = [(p.get("page_num"), _potong(p)[-1][0], potong[0][1])]
        else:
            ruas = [(h, h, b) for h, b in potong]
        teks, batas = "", []
        for h1, h2, b in ruas:
            n = padat(b)
            batas.append((len(teks), len(teks) + len(n), h1, h2))
            teks += n
        p[kunci] = teks, batas
    return p[kunci]


# cache teks `padat` tiap kitab (kitab/<id>/padat-<VERSI>.json.gz): menormalisasi seluruh kitab tiap `cari`/`teks`
# makan detik-an untuk kitab besar. VERSI = sidik isi berkas INI (bukan shamela.py): yang menentukan isi cache hanya
# berkas ini, jadi perubahan mesin di luarnya tidak membuat seluruh perpustakaan dihitung ulang (154 kitab: ±2,5 menit).
VERSI = hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:12]


def rekaman(f):
    with gzip.open(f, "rt", encoding="utf8") as g:
        for line in g:
            yield json.loads(line)


def cache(folder):
    """Teks `padat` + ruas halaman tiap rekaman kitab di `folder` ([[body, footnotes], …]); dibuat sekali kalau belum ada.
    Cache yang rusak atau tidak bisa ditulis tidak menghentikan apa pun: dihitung biasa."""
    f = folder / f"padat-{VERSI}.json.gz"
    with open(folder / "pages.jsonl.gz", "rb") as h:
        sumber = hashlib.file_digest(h, "sha256").hexdigest()
    try:
        with gzip.open(f, "rt", encoding="utf8") as g:
            d = json.load(g)
        if (isinstance(d, dict) and d.get("sumber") == sumber and isinstance(d.get("rekaman"), list)
                and all(isinstance(r, list) and len(r) == len(BAGIAN)
                        and all(isinstance(b, list) and len(b) == 2 and isinstance(b[0], str)
                                and isinstance(b[1], list) and all(isinstance(x, list) and len(x) == 4
                                and type(x[0]) is int and type(x[1]) is int and 0 <= x[0] <= x[1] <= len(b[0])
                                for x in b[1]) for b in r) for r in d["rekaman"])):
            return d["rekaman"]
    except (OSError, ValueError, EOFError, TypeError):
        pass
    isi = [[_ruas(p, b) for b, _ in BAGIAN] for p in rekaman(folder / "pages.jsonl.gz")]
    try:
        with sementara(f) as part:
            with gzip.open(part, "wt", encoding="utf8", compresslevel=6) as g:
                json.dump({"sumber": sumber, "rekaman": isi}, g, ensure_ascii=False, separators=(",", ":"))
        for lama in folder.glob("padat-*.json.gz"):  # cache versi norma.py lama tidak terpakai lagi
            if lama != f:
                lama.unlink()
    except OSError:
        pass
    return isi
