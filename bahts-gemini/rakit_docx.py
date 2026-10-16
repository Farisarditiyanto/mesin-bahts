"""Naskah bahts (tanda mesin bahts) -> berkas Word (.docx) berbentuk pedoman Jamiat al-Imam.

Tanpa internet dan tanpa pustaka tambahan: cukup Python 3.
Pakai: python rakit_docx.py naskah.txt [hasil.docx]
Daftar tanda yang dikenali ada di SKILL.md bagian «Tanda naskah».
"""
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent

# salinan terpaksa profil «imam_ayat16» di mesin/format.json (dicocokkan .github/workflows/tes.yml)
FORMAT = {"huruf": "Traditional Arabic", "matan": 18, "ayat": 16, "catatan": 14, "judul": 20}
# salinan terpaksa bentuk halaman mesin/rakit.ps1: A4, batas atas/bawah/kiri 2,5 cm, kanan 3,5 cm
CM = 567  # twip per cm
BATAS = {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 3.5, "header": 1.25, "footer": 1.25}
SAMPUL_ATAS = ["المملكة العربية السعودية", "وزارة التعليم", "جامعة الإمام محمد بن سعود الإسلامية",
               "معهد العلوم الإسلامية والعربية في جاكرتا", "كلية الشريعة"]
SURAH = json.load(open(HERE / "nama_surah.json", encoding="utf8"))  # salinan terpaksa mesin/nama_surah.json
MERAH = "C00000"
polos_surah = lambda s: re.sub("[أإآءئؤ]", "ا", HARAKAT.sub("", s.strip()))
LATIN = re.compile(r"[A-Za-zÀ-ɏḀ-ỿ][A-Za-zÀ-ɏḀ-ỿ0-9 .,:;/_\-?=&%#@+()]*[A-Za-zÀ-ɏḀ-ỿ0-9/]|[A-Za-zÀ-ɏḀ-ỿ]")

KUAT = re.compile(r"[^\W\d_]|[،؛؟]")
HURUF_LATIN = "A-Za-zÀ-ɏḀ-ỿ"
AD = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
ANGKA_LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)
HARAKAT = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
SURAH_POLOS = {polos_surah(n): n for n in SURAH}


def hindi(s):
    """Angka 0-9 -> ٠-٩, kecuali angka di dekat huruf Latin (tautan, DOI, judul Latin); sama dengan mesin/olah.py."""
    def ganti(m):
        kiri = KUAT.findall(s[:m.start()])
        c = kiri[-1] if kiri else next(iter(KUAT.findall(s[m.end():])), "")
        return m.group() if re.match(f"[{HURUF_LATIN}]", c) else m.group().translate(AD)
    return re.sub(r"[0-9]+", ganti, s)


def kunci_urut(s):
    """Urutan abjad المصادر dan فهرس الأحاديث; sama dengan mesin/olah.py."""
    s = HARAKAT.sub("", s)
    if not s.startswith("الله"):
        s = re.sub(r"^ال", "", s)
    return re.sub("[إأآ]", "ا", s)


class Galat(Exception):
    pass


# ---------- membaca naskah ----------

KUNCI = {"judul", "jenis", "nama", "nim", "fasl", "musyrif", "jabatan", "thalibah", "angka", "tanpa", "berkas"}
SISA = re.compile(r"\[\^|\*\*|\{H2?:|\{P:|<<|>>|\(\(|\)\)")  # tanda yang tertinggal = salah tulis


def baca(teks):
    teks = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufeff]", "", teks)  # karakter kontrol membuat .docx tidak terbuka
    if "{Q:" in teks:
        raise Galat("{Q:..} tidak dikenali di sini: tulis ayat sebagai ﴿نص الآية﴾ dari connector quran, lalu catatan kaki «سورة …، آية: n.».")
    meta, blok, pustaka, di_r = {}, [], [], False
    for n, baris in enumerate(teks.splitlines(), 1):
        b = baris.strip()
        if not b:
            continue
        m = re.match(r"@(\w+):\s*(.*)$", b)
        if m and blok:
            raise Galat(f"baris {n}: @{m.group(1)} harus di awal naskah, sebelum judul pertama.")
        if m:
            if m.group(1) not in KUNCI:
                raise Galat(f"baris {n}: @{m.group(1)} tidak dikenali di versi Gemini (yang ada: {', '.join(sorted(KUNCI))}).")
            meta[m.group(1)] = m.group(2).strip()
            continue
        if re.fullmatch(r"#[KFBMSTR]", b):
            raise Galat(f"baris {n}: {b} tanpa judul.")
        m = re.match(r"#([KFBMSTR])\s+(.*)$", b)
        if m and m.group(1) != "T" and SISA.search(m.group(2)):
            raise Galat(f"baris {n}: judul tidak boleh memuat catatan kaki [^, bukti <<, tanda {{H: atau **: pindahkan ke paragraf sesudahnya.")
        if m and m.group(1) == "R":
            blok.append(("R", m.group(2).strip(), n)); di_r = True
        elif m and m.group(1) == "T":
            blok.append(("T", m.group(2).strip(), n))
        elif m:
            blok.append((m.group(1), m.group(2).strip(), n))
        elif di_r:
            pustaka.append(b)
        else:
            blok.append(("P", b, n))
    for k in ("judul", "jenis", "nama", "nim", "fasl"):
        if not meta.get(k):
            raise Galat(f"@{k} belum diisi di awal naskah.")
    if not any(k == "R" for k, _, _ in blok) and "pustaka" not in tanpa(meta):
        raise Galat("#R المصادر والمراجع belum ada (atau tulis «@tanpa: pustaka»).")
    if any(k == "R" for k, _, _ in blok) and not pustaka:
        raise Galat("المصادر والمراجع masih kosong: tulis satu kitab per baris sesudah #R.")
    return meta, blok, pustaka


def tanpa(meta):
    return {x.strip() for x in re.split(r"[,،]", meta.get("tanpa", "")) if x.strip()}


TOKEN = re.compile(r"\[\^((?:[^\[\]]|\[[^\]]*\])*)\]|\{H:([^|}]+)\|([^|}]+)\|([a-z]+)\}|\{H2:([a-z]+)\}|\*\*(.+?)\*\*"
                   r"|\(\((.+?)\)\)|﴿([^﴾]+)﴾")


def runs(s, baris):
    """Teks satu paragraf -> potongan: ('t', teks, tebal, merah) ('fn', isi) ('h', tharaf, rawi, kunci) ('h2', kunci) ('ay', teks)."""
    out, i = [], 0
    for m in TOKEN.finditer(s):
        if m.start() > i:
            out.append(("t", s[i:m.start()], False, False))
        if m.group(1) is not None:
            isi = re.sub(r"\s*<<[^>]*>>", "", m.group(1)).strip()
            if not isi:
                raise Galat(f"baris {baris}: catatan kaki kosong sesudah bukti <<…>> dibuang.")
            out.append(("fn", isi))
        elif m.group(2):
            out.append(("h", m.group(2).strip(), m.group(3).strip(), m.group(4)))
        elif m.group(5):
            out.append(("h2", m.group(5)))
        elif m.group(6):
            out.append(("t", m.group(6), True, False))
        elif m.group(7):
            out.append(("t", "(" + m.group(7) + ")", True, True))
        else:
            out.append(("ay", m.group(8)))
        i = m.end()
    if i < len(s):
        out.append(("t", s[i:], False, False))
    for x in out:
        isi = x[1] if x[0] in ("t", "fn") else ""
        if "{P:" in isi:
            raise Galat(f"baris {baris}: {{P:..}} tidak bisa di versi Gemini (Word tidak mengisi nomor halaman di catatan kaki): tulis «سبق تخريجه.» saja.")
        sisa = SISA.search(re.sub(r"\*\*.+?\*\*|\(\(.+?\)\)", "", isi) if x[0] == "fn" else isi)
        if sisa:
            raise Galat(f"baris {baris}: tanda «{sisa.group()}» salah tulis atau bersarang (catatan kaki di dalam ** atau di dalam catatan kaki, "
                        f"kunci hadits bukan huruf kecil a-z, kurung tanpa pasangan): «{isi[:60]}».")
    return out


# ---------- menulis XML Word ----------

class Docx:
    def __init__(self, meta):
        self.meta = meta
        self.hindi = meta.get("angka", "hindi") != "latin"
        self.fn = []          # isi XML tiap catatan kaki
        self.bm = 0
        self.ayat = []        # (surah, nomor, teks, bookmark)
        self.hadits = {}      # kunci -> [tharaf, rawi, [bookmark]]
        self.toc = []         # (judul, tingkat, bookmark)

    def angka(self, s):
        return hindi(s) if self.hindi else s.translate(ANGKA_LATIN)

    def r(self, teks, size, bold=False, merah=False, sup=False, font=None):
        teks = self.angka(teks)
        if LATIN.search(teks):
            xml, i = "", 0
            for m in LATIN.finditer(teks):
                xml += self.r1(teks[i:m.start()], size, bold, merah, sup, font) + self.r1(m.group(), size, bold, merah, sup, font, latin=True)
                i = m.end()
            return xml + self.r1(teks[i:], size, bold, merah, sup, font)
        return self.r1(teks, size, bold, merah, sup, font)

    def r1(self, teks, size, bold=False, merah=False, sup=False, font=None, latin=False):
        if not teks:
            return ""
        f = font or FORMAT["huruf"]
        pr = (f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}"/>' + ("<w:b/><w:bCs/>" if bold else "")
              + (f'<w:color w:val="{MERAH}"/>' if merah else "") + f'<w:sz w:val="{size * 2}"/><w:szCs w:val="{size * 2}"/>'
              + ('<w:vertAlign w:val="superscript"/>' if sup else "") + ('<w:lang w:val="en-US"/>' if latin else '<w:rtl/><w:lang w:bidi="ar-SA"/>'))
        return f'<w:r><w:rPr>{pr}</w:rPr><w:t xml:space="preserve">{escape(teks)}</w:t></w:r>'

    def p(self, isi, jc="both", before=0, indent=0, pb=False, keep=False, kotak=False, after=0):
        pr = ("<w:keepNext/>" if keep else "") + ("<w:pageBreakBefore/>" if pb else "")
        if kotak:
            g = f'w:val="single" w:sz="4" w:space="4" w:color="{MERAH}"'
            pr += f"<w:pBdr><w:top {g}/><w:left {g}/><w:bottom {g}/><w:right {g}/></w:pBdr>"
        pr += (f'<w:spacing w:before="{before * 20}" w:after="{after * 20}" w:line="240" w:lineRule="auto"/>'
               + (f'<w:ind w:firstLine="{indent}"/>' if indent else "") + f'<w:bidi/><w:jc w:val="{jc}"/>')
        return f"<w:p><w:pPr>{pr}</w:pPr>{isi}</w:p>"

    def bookmark(self, nama):
        self.bm += 1
        return f'<w:bookmarkStart w:id="{self.bm}" w:name="{nama}"/><w:bookmarkEnd w:id="{self.bm}"/>'

    def pageref(self, nama, size):
        rp = f'<w:rPr><w:rFonts w:cs="{FORMAT["huruf"]}"/><w:sz w:val="{size * 2}"/><w:szCs w:val="{size * 2}"/><w:rtl/></w:rPr>'
        return (f'<w:r>{rp}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{rp}<w:instrText xml:space="preserve"> PAGEREF {nama} \\h </w:instrText></w:r>'
                f'<w:r>{rp}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{rp}<w:t>؟</w:t></w:r><w:r>{rp}<w:fldChar w:fldCharType="end"/></w:r>')

    def catatan(self, isi, baris):
        no = len(self.fn) + 1
        sz = FORMAT["catatan"]
        xml = ""
        for t in re.split(r"(\*\*.+?\*\*|\(\(.+?\)\))", isi):
            if t.startswith("**"):
                xml += self.r(t[2:-2], sz, bold=True)
            elif t.startswith("(("):
                xml += self.r("(" + t[2:-2] + ")", sz, bold=True, merah=True)
            elif t:
                xml += self.r(t, sz)
        rp = f'<w:rPr><w:rStyle w:val="FootnoteReference"/><w:rFonts w:cs="{FORMAT["huruf"]}"/><w:sz w:val="{sz * 2}"/><w:szCs w:val="{sz * 2}"/><w:vertAlign w:val="baseline"/><w:rtl/></w:rPr>'
        tanda = f'{self.r("(", sz)}<w:r>{rp}<w:footnoteRef/></w:r>{self.r(") ", sz)}'
        self.fn.append(f'<w:footnote w:id="{no}"><w:p><w:pPr><w:pStyle w:val="FootnoteText"/><w:bidi/><w:jc w:val="both"/></w:pPr>{tanda}{xml}</w:p></w:footnote>')
        u = FORMAT["matan"]
        ref = f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:rFonts w:cs="{FORMAT["huruf"]}"/><w:sz w:val="{u * 2}"/><w:szCs w:val="{u * 2}"/><w:rtl/></w:rPr><w:footnoteReference w:id="{no}"/></w:r>'
        return self.r("(", u, sup=True) + ref + self.r(")", u, sup=True)

    def isi(self, potongan, baris, merah=False):
        xml, u = "", FORMAT["matan"]
        for k, x in enumerate(potongan):
            if x[0] == "t":
                xml += self.r(x[1], u, bold=x[2], merah=x[3] or merah)
            elif x[0] == "ay":
                nxt = potongan[k + 1] if k + 1 < len(potongan) else None
                m = re.match(r"سورة\s+(.+?)\s*،\s*(?:الآية|آية)\s*:?\s*([0-9٠-٩\-–]+)", nxt[1]) if nxt and nxt[0] == "fn" else None
                if not m:
                    raise Galat(f"baris {baris}: ayat ﴿…﴾ harus langsung diikuti catatan kaki «سورة …، آية: n.».")
                surah = SURAH_POLOS.get(polos_surah(m.group(1)))
                if not surah:
                    raise Galat(f"baris {baris}: «سورة {m.group(1).strip()}» tidak ada di daftar nama surah (nama_surah.json); salin namanya dari sana.")
                nama = f"a_{len(self.ayat) + 1}"
                self.ayat.append((surah, m.group(2).translate(ANGKA_LATIN), x[1], nama))
                xml += self.bookmark(nama) + self.r("﴿" + x[1] + "﴾", FORMAT["ayat"], merah=merah)
            elif x[0] == "fn":
                xml += self.catatan(x[1], baris)
            elif x[0] == "h":
                if x[3] in self.hadits:
                    raise Galat(f"baris {baris}: kunci hadits «{x[3]}» dipakai dua kali; hadits yang sama di tempat lain: {{H2:{x[3]}}}.")
                self.hadits[x[3]] = [x[1], x[2], [f"h_{x[3]}_1"]]
                xml += self.bookmark(f"h_{x[3]}_1")
            elif x[0] == "h2":
                if x[1] not in self.hadits:
                    raise Galat(f"baris {baris}: {{H2:{x[1]}}} sebelum {{H:…|{x[1]}}}.")
                nama = f"h_{x[1]}_{len(self.hadits[x[1]][2]) + 1}"
                self.hadits[x[1]][2].append(nama)
                xml += self.bookmark(nama)
        return xml

    def judul(self, teks, pb, tingkat, ke_toc=True):
        nama = f"t_{len(self.toc) + 1}"
        if ke_toc:
            self.toc.append((teks, tingkat, nama))
        return self.p(self.bookmark(nama) + self.r(teks, FORMAT["judul"], bold=True), jc="center", before=0 if pb else 6, pb=pb, keep=True)

    def tabel(self, lebar_cm, baris, garis=True):
        g = '<w:top w:val="single" w:sz="4"/><w:left w:val="single" w:sz="4"/><w:bottom w:val="single" w:sz="4"/><w:right w:val="single" w:sz="4"/><w:insideH w:val="single" w:sz="4"/><w:insideV w:val="single" w:sz="4"/>' if garis else ""
        xml = (f'<w:tbl><w:tblPr><w:bidiVisual/><w:tblW w:w="{int(sum(lebar_cm) * CM)}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{g}</w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>'
               + "".join(f'<w:gridCol w:w="{int(w * CM)}"/>' for w in lebar_cm) + "</w:tblGrid>")
        for sel in baris:
            xml += "<w:tr>" + "".join(f'<w:tc><w:tcPr><w:tcW w:w="{int(w * CM)}" w:type="dxa"/></w:tcPr>{c}</w:tc>' for w, c in zip(lebar_cm, sel)) + "</w:tr>"
        return xml + "</w:tbl>" + self.p("")

    def sel(self, isi_xml, jc="center", indent_kanan=0):
        ind = f'<w:ind w:right="{indent_kanan}"/>' if indent_kanan else ""
        return f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/>{ind}<w:bidi/><w:jc w:val="{jc}"/></w:pPr>{isi_xml}</w:p>'

    def halaman(self, nama_nama):
        u, xml = FORMAT["matan"], ""
        for i, n in enumerate(nama_nama):
            xml += (self.r("، ", u) if i else "") + self.pageref(n, u)
        return xml


def sampul(d):
    m, u = d.meta, FORMAT["judul"]
    logo = ('<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="936000" cy="1293000"/><wp:docPr id="1" name="logo"/>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="1" name="logo.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            '<pic:blipFill><a:blip r:embed="rLogo"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="936000" cy="1293000"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')
    kanan = "".join(d.sel(d.r(t, 15, bold=True)) for t in SAMPUL_ATAS)
    xml = d.tabel([11.0, 4.0], [[kanan, d.sel(logo, jc="left")]], garis=False)
    tengah = lambda t, s=u, before=0: d.p(d.r(t, s, bold=True), jc="center", before=before)
    xml += tengah(m["judul"], 36, 60) + tengah(m["jenis"], u, 36)
    xml += tengah("اسم الطالبة :" if m.get("thalibah") == "ya" else "اسم الطالب :", u, 24) + tengah(m["nama"]) + tengah("الرقم الجامعي :") + tengah(m["nim"])
    musyrif = m.get("musyrif", "")
    if musyrif and musyrif != "-":
        xml += tengah("المشرف على البحث :", u, 24) + tengah(musyrif)
        if m.get("jabatan", "") not in ("", "-"):
            xml += tengah(m["jabatan"])
    return xml + tengah(m["fasl"], u, 24)


def susun(meta, blok, pustaka):
    d = Docx(meta)
    tak = tanpa(meta)
    body, pertama = "", True
    for k, teks, baris in blok:
        if k in "KFBM":
            pb = k in "KF" and not pertama
            pertama = False
            body += d.judul(teks, pb, {"K": 0, "F": 0, "B": 1, "M": 2}[k])
        elif k == "S":
            body += d.p(d.r(teks, FORMAT["judul"], bold=True), jc="right", before=6, keep=True)
        elif k == "T":
            body += d.p(d.isi(runs(teks, baris), baris, merah=True), before=6, after=6, kotak=True)
        elif k == "P":
            body += d.p(d.isi(runs(teks, baris), baris), indent=int(0.8 * CM))
    u = FORMAT["matan"]
    if "pustaka" not in tak:
        polos = lambda s: HARAKAT.sub("", s)
        quran = [b for b in pustaka if polos(b).startswith("القرآن")]
        lain = sorted((b for b in pustaka if b not in quran), key=kunci_urut)
        body += d.judul("المصادر والمراجع", True, 0)
        rows = [[d.sel(d.r("-", u)), d.sel(d.r(b, u), jc="both")] for b in quran]
        rows += [[d.sel(d.r(f"{i}.", u)), d.sel(d.r(b, u), jc="both")] for i, b in enumerate(lain, 1)]
        body += d.tabel([1.3, 13.7], rows, garis=False)
    if d.ayat and "ayat" not in tak:
        body += d.judul("فهرس الآيات القرآنية", True, 0)
        gabung = {}
        for s, a, t, nama in d.ayat:
            gabung.setdefault((s, a), [t, []])[1].append(nama)
        urut = lambda kv: (SURAH.index(kv[0][0]) if kv[0][0] in SURAH else 999, int(re.match(r"\d+", kv[0][1]).group()))
        rows = [[d.sel(d.r(x, u, bold=True)) for x in ("الآية", "السورة", "رقمها", "الصفحة")]]
        for (s, a), (t, nama) in sorted(gabung.items(), key=urut):
            kata = t.split()
            pot = " ".join(kata[:4]) + " ..." if len(kata) > 4 else t
            rows.append([d.sel(d.r("﴿" + pot + "﴾", FORMAT["ayat"]), jc="right"), d.sel(d.r(s, u)), d.sel(d.r(a, u)), d.sel(d.halaman(nama))])
        body += d.tabel([7.9, 2.6, 2.5, 2.0], rows)
    if d.hadits and "hadits" not in tak:
        body += d.judul("فهرس الأحاديث والآثار", True, 0)
        rows = [[d.sel(d.r(x, u, bold=True)) for x in ("طرف الحديث أو الأثر", "الراوي", "الصفحة")]]
        abjad = sorted(d.hadits.values(), key=lambda h: kunci_urut(h[0]))
        rows += [[d.sel(d.r("«" + t + "»", u), jc="right"), d.sel(d.r(r, u)), d.sel(d.halaman(n))] for t, r, n in abjad]
        body += d.tabel([8.6, 4.4, 2.0], rows)
    if "maudhuat" not in tak:
        body += d.judul("فهرس الموضوعات", True, 0)
        rows = [[d.sel(d.r(x, u, bold=True)) for x in ("الموضوع", "الصفحة")]]
        rows += [[d.sel(d.r(t, u, bold=lvl == 0), jc="right", indent_kanan=int(0.7 * CM * lvl)), d.sel(d.pageref(n, u))] for t, lvl, n in d.toc]
        body += d.tabel([13.0, 2.0], rows)
    return d, body


NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"')


def sect(footer, mulai):
    b = BATAS
    pg = (f'<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="{int(b["top"] * CM)}" w:right="{int(b["right"] * CM)}" w:bottom="{int(b["bottom"] * CM)}" '
          f'w:left="{int(b["left"] * CM)}" w:header="{int(b["header"] * CM)}" w:footer="{int(b["footer"] * CM)}" w:gutter="0"/>')
    f = '<w:footerReference w:type="default" r:id="rFoot"/>' if footer else ""
    return (f'<w:sectPr>{f}<w:footnotePr><w:numRestart w:val="eachPage"/></w:footnotePr><w:type w:val="nextPage"/>{pg}'
            + (f'<w:pgNumType w:start="{mulai}"/>' if footer else "") + "<w:bidi/></w:sectPr>")


def tulis(meta, blok, pustaka, keluar):
    d, body = susun(meta, blok, pustaka)
    u, c, f = FORMAT["matan"], FORMAT["catatan"], FORMAT["huruf"]
    dokumen = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>'
               f'{sampul(d)}<w:p><w:pPr>{sect(False, 1)}</w:pPr></w:p>{body}{sect(True, 1)}</w:body></w:document>')
    sep = ('<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:separator/></w:r></w:p></w:footnote>'
           '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>')
    catatan = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:footnotes {NS}>{sep}{"".join(d.fn)}</w:footnotes>'
    rp = f'<w:rPr><w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}"/><w:sz w:val="{u * 2}"/><w:szCs w:val="{u * 2}"/><w:rtl/></w:rPr>'
    kaki = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {NS}><w:p><w:pPr><w:bidi/><w:jc w:val="center"/></w:pPr>'
            f'<w:r>{rp}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{rp}<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
            f'<w:r>{rp}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{rp}<w:t>1</w:t></w:r><w:r>{rp}<w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')
    gaya = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {NS}><w:docDefaults><w:rPrDefault><w:rPr>'
            f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}"/><w:sz w:val="{u * 2}"/><w:szCs w:val="{u * 2}"/><w:lang w:val="ar-SA" w:bidi="ar-SA"/></w:rPr></w:rPrDefault>'
            '<w:pPrDefault><w:pPr><w:bidi/><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
            f'<w:style w:type="paragraph" w:styleId="FootnoteText"><w:name w:val="footnote text"/><w:basedOn w:val="Normal"/><w:pPr><w:bidi/><w:jc w:val="both"/></w:pPr><w:rPr><w:sz w:val="{c * 2}"/><w:szCs w:val="{c * 2}"/></w:rPr></w:style>'
            '<w:style w:type="character" w:styleId="FootnoteReference"><w:name w:val="footnote reference"/><w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>'
            '</w:styles>')
    setelan = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {NS}>'
               '<w:footnotePr><w:numRestart w:val="eachPage"/><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr>'
               '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')
    rel = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
           '<Relationship Id="rStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
           '<Relationship Id="rSet" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
           '<Relationship Id="rFn" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>'
           '<Relationship Id="rFoot" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
           '<Relationship Id="rLogo" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo.png"/></Relationships>')
    jenis = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
             '<Default Extension="png" ContentType="image/png"/>'
             '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
             '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
             '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
             '<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>'
             '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
    akar = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    with zipfile.ZipFile(keluar, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", jenis); z.writestr("_rels/.rels", akar)
        z.writestr("word/document.xml", dokumen); z.writestr("word/styles.xml", gaya); z.writestr("word/settings.xml", setelan)
        z.writestr("word/footnotes.xml", catatan); z.writestr("word/footer1.xml", kaki)
        z.writestr("word/_rels/document.xml.rels", rel); z.write(HERE / "logo.png", "word/media/logo.png")
    return d


def utama(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    naskah = Path(argv[1])
    try:
        meta, blok, pustaka = baca(naskah.read_text(encoding="utf-8-sig"))
        keluar = Path(argv[2]) if len(argv) > 2 else naskah.with_name((meta.get("berkas") or "bahts") + ".docx")
        d = tulis(meta, blok, pustaka, keluar)
    except Galat as e:
        print(f"GAGAL: {e}"); return 1
    print(f"JADI: {keluar} (catatan kaki {len(d.fn)}, ayat {len(d.ayat)}, hadits {len(d.hadits)}, judul {len(d.toc)})")
    return 0


if __name__ == "__main__":
    sys.exit(utama(sys.argv))
