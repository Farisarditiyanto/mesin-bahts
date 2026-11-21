# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sampul dan kepala halaman `@templat` lewat `rakit` dan Word asli. Runner tanpa Word melaporkan lewati.

Templat Word dibuat di tes ini (tanpa berkas kampus): sampul, pemisah halaman, satu halaman contoh, dan kepala halaman
berisi penanda «(عنوان البحث)» seperti templat kampus yang belum diisi. Yang dijaga:
- penanda di kepala halaman diganti @judul (bukan tercetak di tiap halaman isi);
- sampul yang meluap di kertas A4 tidak dipotong diam-diam: baris akhirnya tetap tercetak dan `rakit` memberi PERINGATAN;
- sampul yang muat satu halaman tanpa PERINGATAN itu, dan halaman contoh sesudah pemisah halaman tidak ikut dicetak.
Semua bahan di TEMP."""
import re, sys, tempfile, zipfile
from pathlib import Path

import pymupdf

from bantu import bahts, salin_mesin, tanpa_word

JUDUL = "اختبار القالب"
KEPALA = (f"@judul: {JUDUL}\n@nama: طالب\n@berkas: uji\n@templat: templat.docx\n@tanpa: ayat, hadits, maudhuat, pustaka\n"
          "@minimal_halaman: 0\n#K المقدمة\nهذا نص المقدمة.\n#K الخاتمة\nهذا نص الخاتمة.\n")
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' \
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
AKHIR_SAMPUL = "AKHIR SAMPUL"   # baris terakhir sampul; Latin supaya terbaca pasti di teks PDF
CONTOH = "HALAMAN CONTOH"       # isi templat sesudah pemisah halaman: bukan sampul


def paragraf(teks, ukuran=32):
    return (f'<w:p><w:pPr><w:bidi/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rtl/><w:sz w:val="{ukuran}"/>'
            f'<w:szCs w:val="{ukuran}"/></w:rPr><w:t xml:space="preserve">{teks}</w:t></w:r></w:p>')


def templat(tujuan, baris_sampul):
    """Word templat: `baris_sampul` paragraf sampul berhuruf 16 pt (plus judul dan baris akhir), pemisah halaman, satu
    halaman contoh; kepala halaman = «(عنوان البحث)»."""
    sampul = paragraf(JUDUL) + "".join(paragraf(f"سطر الغلاف {i}") for i in range(baris_sampul)) + paragraf(AKHIR_SAMPUL)
    badan = (sampul + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' + paragraf(CONTOH)
             + '<w:sectPr><w:headerReference w:type="default" r:id="rIdK"/><w:pgSz w:w="11906" w:h="16838"/>'
               '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>'
               '<w:bidi/></w:sectPr>')
    with zipfile.ZipFile(tujuan, "w") as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
                   '</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                   '</Relationships>')
        z.writestr("word/_rels/document.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rIdK" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>'
                   '</Relationships>')
        z.writestr("word/document.xml", f'<?xml version="1.0" encoding="UTF-8"?><w:document {W}><w:body>{badan}</w:body></w:document>')
        z.writestr("word/header1.xml", f'<?xml version="1.0" encoding="UTF-8"?><w:hdr {W}>{paragraf("(عنوان البحث)", 24)}</w:hdr>')


def rakit(akar, nama, baris_sampul):
    f = akar / nama
    f.mkdir()
    templat(f / "templat.docx", baris_sampul)
    (f / "naskah.txt").write_text(KEPALA, encoding="utf8")
    r = bahts(akar, "rakit", nama, batas=1800)
    assert r.returncode == 0, r.stdout + r.stderr
    with zipfile.ZipFile(f / "uji.docx") as z:
        kepala = " ".join("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", z.read(n).decode("utf8")))
                          for n in z.namelist() if re.fullmatch(r"word/header\d+\.xml", n))
    doc = pymupdf.open(f / "uji.pdf")
    return r.stdout, kepala, [h.get_text() for h in doc]


def utama():
    if alasan := tanpa_word():
        print(f"uji_templat_word: lewati ({alasan})")
        return
    with tempfile.TemporaryDirectory(prefix="bahts-templat-") as t:
        akar = Path(t)
        salin_mesin(akar)
        # sampul muat satu halaman
        out, kepala, hal = rakit(akar, "pas", 3)
        assert "عنوان البحث" not in kepala and JUDUL in kepala, f"penanda kepala halaman tidak diganti @judul: {kepala!r}"
        assert "PERINGATAN: sampul dari @templat" not in out and "PERINGATAN: kepala halaman" not in out, out
        assert AKHIR_SAMPUL in hal[0], f"baris akhir sampul tidak di halaman 1: {hal[0]!r}"
        assert not any(CONTOH in h for h in hal), "halaman contoh templat sesudah pemisah halaman ikut dicetak"
        print("ok: penanda kepala halaman @templat diganti @judul; sampul satu halaman tanpa PERINGATAN")
        # sampul meluap: 60 baris 16 pt tidak muat satu halaman A4
        out, kepala, hal = rakit(akar, "luap", 60)
        assert re.search(r"PERINGATAN: sampul dari @templat jadi [2-9] halaman", out), out
        assert any(AKHIR_SAMPUL in h for h in hal[:3]), "baris akhir sampul yang meluap hilang dari PDF"
        assert not any(CONTOH in h for h in hal), "halaman contoh templat ikut dicetak"
        print("ok: sampul @templat yang meluap tetap utuh di PDF dan diberi PERINGATAN")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    utama()
