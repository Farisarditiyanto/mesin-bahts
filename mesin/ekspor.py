# SPDX-License-Identifier: AGPL-3.0-or-later
"""`ekspor`: satu kitab yang sudah diunduh (Shamela atau Waqfeya) jadi satu .docx untuk dibaca di Word.

Kanan-ke-kiri, huruf Traditional Arabic, judul bab dari daftar isi Shamela jadi Heading (Navigation Pane Word),
penanda juz/halaman cetak di awal tiap halaman, حاشية sesudah halamannya. Bukan bahan bahts: `cek` tetap membaca
kitab lokal. .docx ditulis langsung (zip + XML), tanpa Word dan tanpa pustaka tambahan.
"""
import re, zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape

import shamela, waqfeya
from berkas import sementara
from dasar import HORMAT_CETAK
from norma import per_halaman

KONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")  # tidak sah di XML
JUDUL = re.compile(r"""<span\b(?=[^>]*\bdata-type\s*=\s*(?:"title"|'title'))
    (?=[^>]*\bid\s*=\s*["']?toc-(?P<nomor>\d+)\b)[^>]*>(?P<teks>.*?)</span>""", re.S | re.X)
PEMISAH_HTML = frozenset(("br", "p", "div", "li", "tr", "td", "th"))
BARIS = re.compile(r"\r\n?|\n")
ANGKA = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
NAMA_TERLARANG = re.compile(r'[\\/:*?"<>|\x00-\x1f]')  # tidak boleh di nama berkas Windows
TINGKAT_MAKS = 4  # judul yang lebih dalam tetap Heading 4
PEMISAH_HASYIAH = "ـــــــــــــــ"
AKHIR_PARAGRAF = re.compile(r"[.:؟!*»)\]]\s*$")  # baris OCR yang menutup kalimat
# baris judul OCR (pendek, diawali kata judul): tidak disambung ke baris sebelum atau sesudahnya
JUDUL_OCR = re.compile(r"^(?:ال)?(?:باب|فصل|مبحث|مطلب|كتاب|مسألة|تمهيد|مقدمة|خاتمة|فهرس)\b")
KATA_JUDUL_MAKS = 8
KATA_JUDUL_PENDEK = 3  # baris sependek ini yang membuka paragraf baru («كلمة شكر», «الألف») = judul juga
AWAL_HASYIAH = re.compile(r"^\s*\([0-9٠-٩۰-۹]+\)")  # «(١) …»: catatan kaki selalu paragraf baru


class _TeksHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.teks = []

    def handle_data(self, data):
        self.teks.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in PEMISAH_HTML:
            self.teks.append("\n")

    def handle_endtag(self, tag):
        self.handle_starttag(tag, ())


def _html(s):
    p = _TeksHTML()
    p.feed(s)
    p.close()
    return "".join(p.teks)


def _rapi(s):
    return " ".join(KONTROL.sub("", s).translate(HORMAT_CETAK).replace("¬", "").split())


def bersih(s):
    """Teks satu baris kitab untuk dibaca: kalimat hormat untuk ligatur yang tidak ada di huruf, tanpa tag HTML,
    entitas HTML jadi hurufnya («&amp;» -> «&»), tanpa tanda «¬» Shamela di nomor حاشية («(¬١)» -> «(١)»)."""
    return _rapi(_html(s))


def _xml(gaya, teks):
    return (f'<w:p><w:pPr><w:pStyle w:val="{gaya}"/><w:bidi/></w:pPr><w:r><w:rPr><w:rtl/></w:rPr>'
            f'<w:t xml:space="preserve">{escape(teks)}</w:t></w:r></w:p>')


def tanpa_judul_ulang(paragraf):
    """Paragraf biasa yang isinya sama dengan judul tepat sebelum/sesudahnya dibuang: judul daftar isi yang disisipkan
    di awal rekaman bisa bersebelahan dengan baris judul yang sama di teks kitab."""
    judul = lambda i: 0 <= i < len(paragraf) and paragraf[i][0].startswith("Heading")
    return [(g, t) for i, (g, t) in enumerate(paragraf)
            if not (g == "Normal" and any(judul(j) and paragraf[j][1] == t for j in (i - 1, i + 1)))]


def _gaya(nama, ukuran, tambah_ppr="", tambah_rpr="", judul=None):
    ppr = f"<w:pPr>{tambah_ppr}</w:pPr>" if tambah_ppr else ""
    jenis = '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>' if nama != "Normal" else ""
    nama_tampil = f"heading {judul}" if judul else nama
    bawaan = ' w:default="1"' if nama == "Normal" else ""
    return (f'<w:style w:type="paragraph" w:styleId="{nama}"{bawaan}>'
            f'<w:name w:val="{nama_tampil}"/>{jenis}{ppr}<w:rPr>{tambah_rpr}'
            f'<w:sz w:val="{ukuran * 2}"/><w:szCs w:val="{ukuran * 2}"/></w:rPr></w:style>')


HURUF = "Traditional Arabic"
GAYA = "".join([
    _gaya("Normal", 16, '<w:bidi/><w:jc w:val="both"/><w:spacing w:after="60" w:line="240" w:lineRule="auto"/>'),
    _gaya("Pengarang", 18, '<w:jc w:val="center"/><w:spacing w:after="360"/>'),
    _gaya("Halaman", 11, '<w:jc w:val="center"/><w:spacing w:before="120"/>', '<w:color w:val="808080"/>'),
    _gaya("Hasyiah", 12, '<w:spacing w:after="0"/>'),
    *(_gaya(f"Heading{n}", 22 - 2 * n, f'<w:keepNext/><w:spacing w:before="240" w:after="120"/>'
            f'<w:jc w:val="{"center" if n == 1 else "right"}"/><w:outlineLvl w:val="{n - 1}"/>',
            '<w:b/><w:bCs/><w:color w:val="1F3864"/>', judul=n) for n in range(1, TINGKAT_MAKS + 1)),
])
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/package/2006/relationships"
OD = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
BAGIAN_DOCX = {
    "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    "</Types>",
    "_rels/.rels": f'<Relationships xmlns="{R}"><Relationship Id="rId1" Type="{OD}/officeDocument" Target="word/document.xml"/></Relationships>',
    "word/_rels/document.xml.rels": f'<Relationships xmlns="{R}"><Relationship Id="rId1" Type="{OD}/styles" Target="styles.xml"/></Relationships>',
    "word/styles.xml": f'<w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{HURUF}" '
    f'w:hAnsi="{HURUF}" w:cs="{HURUF}"/><w:lang w:bidi="ar-SA"/></w:rPr></w:rPrDefault></w:docDefaults>{GAYA}</w:styles>',
}
# A4, tepi 2 cm
HALAMAN_A4 = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" '
              'w:left="1134" w:header="567" w:footer="567" w:gutter="0"/><w:bidi/></w:sectPr>')


def tulis(tujuan, paragraf):
    """[(gaya, teks)] -> berkas .docx (ditulis lewat nama sementara: yang ada = utuh)."""
    with sementara(tujuan) as tmp, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for nama, isi in BAGIAN_DOCX.items():
            z.writestr(nama, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + isi)
        z.writestr("word/document.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}">'
                   f'<w:body>{"".join(_xml(*p) for p in tanpa_judul_ulang(paragraf))}{HALAMAN_A4}</w:body></w:document>')


def _judul(teks, tingkat):
    return f"Heading{min(tingkat, TINGKAT_MAKS)}", teks


def _baris_body(teks, tingkat):
    """Paragraf matan satu halaman: judul bertanda di body jadi Heading, titik yang tertinggal sesudah judul
    («</span>.») dibuang."""
    out = []
    teks = JUDUL.sub(lambda m: f"\n\x01{m['nomor']}\x02{escape(bersih(m['teks']))}\n", teks)
    for b in BARIS.split(_html(teks)):
        if b.startswith("\x01"):
            n, t = b[1:].split("\x02", 1)
            if t := _rapi(t):
                out.append(_judul(t, tingkat.get(int(n), TINGKAT_MAKS)))
        elif (t := _rapi(b)) and not (not t.strip(".") and out and out[-1][0].startswith("Heading")):
            out.append(("Normal", t))
    return out


def _shamela(sid):
    m = shamela.info(sid)
    judul = shamela.judul_rekaman(sid)
    tingkat = {n: k for daftar in judul.values() for n, _, k in daftar}
    out = [("Heading1", bersih(m["title_ar"])), ("Pengarang", bersih(m.get("main_author_name_ar") or ""))]
    tadi = (object(), -1)  # (juz, halaman) penanda terakhir
    for p in shamela.rekaman(sid):
        juz = p.get("part")
        hasyiah = dict(per_halaman(p, "footnotes")) if p.get("footnotes") else {}
        potong = per_halaman(p)
        bertanda = {int(m["nomor"]) for m in JUDUL.finditer(p.get("body") or "")}
        for k, (hal, teks) in enumerate(potong):
            # satu penanda per halaman cetak: kitab hadits menyimpan tiap hadits sebagai rekaman sendiri, dan rekaman
            # judul bab bisa bernomor halaman yang lebih kecil (mis. سنن أبي داود)
            if isinstance(hal, int) and (juz != tadi[0] or hal > tadi[1]):  # rekaman tanpa nomor halaman: tanpa penanda
                tadi = juz, hal
                out.append(("Halaman", f"[{juz + ' ' if juz and not juz.isdigit() else 'ج' + juz + ' ' if juz else ''}ص {hal}]"
                            .translate(ANGKA)))
            if k == 0:  # judul daftar isi yang tidak bertanda di body: di awal rekamannya
                out += [_judul(t, d) for n, j, d in judul.get(p["page_id"], ()) if n not in bertanda and (t := bersih(j))]
            out += _baris_body(teks, tingkat)
            # حاشية tanpa penanda halaman di rekaman banyak halaman: semuanya sesudah halaman terakhir rekaman itu
            isi = hasyiah.get(hal, "") if len(hasyiah) > 1 else ("".join(hasyiah.values()) if k == len(potong) - 1 else "")
            if baris := [t for b in BARIS.split(isi) if (t := bersih(b))]:
                out += [("Hasyiah", PEMISAH_HASYIAH), *(("Hasyiah", t) for t in baris)]
    return m["title_ar"], out


def _waqfeya(w):
    d = waqfeya.data(w)
    out = [("Heading1", bersih(d["judul"])), ("Pengarang", bersih(d.get("pengarang") or ""))]
    for i, nama in enumerate(d["berkas"], 1):
        if len(d["berkas"]) > 1:
            out.append(("Heading2", bersih(nama)))
        for n, teks in enumerate(waqfeya.ocr(w, i), 1):
            out.append(("Halaman", f"[PDF ص {n}]".translate(ANGKA)))
            out += [("Normal", t) for t in paragraf_ocr(teks)]
    return d["judul"], out


def paragraf_ocr(teks):
    """Baris OCR satu halaman -> paragraf: baris yang tidak menutup kalimat disambung baris berikutnya (sisa kalimat yang
    turun baris), kecuali baris berikutnya awal catatan kaki «(١)»; baris judul («الباب الثاني», atau baris pendek yang membuka paragraf) berdiri sendiri."""
    out, tutup = [], True  # tutup: paragraf terakhir tidak boleh disambung
    for b in teks.splitlines():
        if not (t := bersih(b)):
            tutup = True
            continue
        judul = t.isdecimal() or JUDUL_OCR.match(t) is not None and len(t.split()) <= KATA_JUDUL_MAKS
        if out and not tutup and not judul and not AWAL_HASYIAH.match(t):
            out[-1] += " " + t
        else:
            out.append(t)
            judul = judul or (len(t.split()) <= KATA_JUDUL_PENDEK and not AWAL_HASYIAH.match(t))
        tutup = judul or AKHIR_PARAGRAF.search(out[-1]) is not None
    return out


def ekspor(kitab, ke):
    """Tiap kitab (nomor Shamela atau w…) -> <ke>/<judul> (<nomor>).docx; yang belum diunduh diunduh dulu. Nomor di nama
    berkas: kitab lain yang judulnya sama tidak tertimpa. Kembalikan jalurnya."""
    kitab = list(dict.fromkeys(map(str, kitab)))
    ke = Path(ke).expanduser()
    ke.mkdir(parents=True, exist_ok=True)
    ww = [x for x in kitab if str(x).startswith("w")]
    gagal = (shamela.ambil(*[x for x in kitab if x not in ww]) if len(ww) < len(kitab) else []) + (waqfeya.ambil(*ww) if ww else [])
    if gagal:
        raise SystemExit(f"Belum terunduh: {', '.join(map(str, gagal))} (lihat pesan di atas).")
    hasil = []
    for x in kitab:
        judul, paragraf = _waqfeya(x) if x in ww else _shamela(x)
        tujuan = ke / f"{NAMA_TERLARANG.sub(' ', judul).strip()[:120]} ({x}).docx"
        try:
            tulis(tujuan, paragraf)
        except PermissionError:  # Windows: berkas yang sedang dibuka Word tidak bisa diganti
            raise SystemExit(f"{tujuan} sedang dibuka (mis. di Word): tutup dulu, lalu ulangi.") from None
        print(f"{x}\t{tujuan}")
        hasil.append(tujuan)
    return hasil
