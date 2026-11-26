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


def _tulis_docx(tujuan, badan, headers):
    ov = "".join(
        f'<Override PartName="/word/{nama}" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
        for _, nama, _ in headers
    )
    rels = "".join(
        f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="{nama}"/>'
        for rid, nama, _ in headers
    )
    with zipfile.ZipFile(tujuan, "w") as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   f'{ov}</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                   '</Relationships>')
        z.writestr("word/_rels/document.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'{rels}</Relationships>')
        z.writestr("word/document.xml", f'<?xml version="1.0" encoding="UTF-8"?><w:document {W}><w:body>{badan}</w:body></w:document>')
        for _, nama, isi in headers:
            z.writestr(f"word/{nama}", isi)


def templat(tujuan, baris_sampul):
    """Word templat: `baris_sampul` paragraf sampul berhuruf 16 pt (plus judul dan baris akhir), pemisah halaman, satu
    halaman contoh; kepala halaman = «(عنوان البحث)»."""
    sampul = paragraf(JUDUL) + "".join(paragraf(f"سطر الغلاف {i}") for i in range(baris_sampul)) + paragraf(AKHIR_SAMPUL)
    badan = (sampul + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' + paragraf(CONTOH)
             + '<w:sectPr><w:headerReference w:type="default" r:id="rIdK"/><w:pgSz w:w="11906" w:h="16838"/>'
               '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>'
               '<w:bidi/></w:sectPr>')
    _tulis_docx(tujuan, badan, [("rIdK", "header1.xml", f'<?xml version="1.0" encoding="UTF-8"?><w:hdr {W}>{paragraf("(عنوان البحث)", 24)}</w:hdr>')])


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
        multi_dan_judul_panjang(akar)


def multi_dan_judul_panjang(akar):
    import os, subprocess
    from xml.etree import ElementTree as ET
    judul_panjang = " ".join(["دراسة فقهية تحليلية مقارنة"] * 12)
    assert len(judul_panjang) > 255
    f = akar / "multi"
    f.mkdir()
    tpl = f / "templat.docx"
    ps = (
        "$ErrorActionPreference = 'Stop'\n"
        "$w = New-Object -ComObject Word.Application\n"
        "$w.Visible = $false\n"
        "try {\n"
        "    $d = $w.Documents.Add()\n"
        "    $d.Content.Text = $env:UJI_JUDUL_PANJANG\n"
        "    $d.Content.Font.Size = 10; $d.Content.Font.SizeBi = 10\n"
        "    $d.Content.InsertBreak(2)\n"
        f"    $d.Sections(2).Range.Text = '{CONTOH}'\n"
        "    $h2 = $d.Sections(2).Headers(1); $h2.LinkToPrevious = $false\n"
        "    $h2.Range.Text = '(عنوان البحث)'\n"
        "    $s1 = $h2.Shapes.AddTextbox(1, 50, 20, 60, 24)\n"
        "    [void]$s1.TextFrame.TextRange.Fields.Add($s1.TextFrame.TextRange, 33)\n"
        "    $s2 = $h2.Shapes.AddTextbox(1, 200, 20, 80, 24)\n"
        "    $s2.TextFrame.TextRange.Text = 'HeaderNote'\n"
        "    $d.SaveAs2($env:UJI_TPL_PATH, 16)\n"
        "    $d.Close(0)\n"
        "} finally {\n"
        "    try { $w.Quit([ref]0) } catch {}\n"
        "}\n"
    )
    env = dict(os.environ, UJI_JUDUL_PANJANG=judul_panjang, UJI_TPL_PATH=str(tpl))
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, env=env)
    (f / "naskah.txt").write_text(KEPALA.replace(JUDUL, judul_panjang), encoding="utf8")
    r = bahts(akar, "rakit", "multi", batas=1800)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PERINGATAN: kepala halaman" not in r.stdout, r.stdout
    w_ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    txbx_page, txbx_note = [], []
    with zipfile.ZipFile(f / "uji.docx") as z:
        kepala_xmls = [z.read(n).decode("utf8") for n in z.namelist() if re.fullmatch(r"word/header\d+\.xml", n)]
        for x in kepala_xmls:
            for bx in ET.fromstring(x).findall(".//w:txbxContent", w_ns):
                isi = "".join(bx.itertext())
                ada_rtl = bool(bx.findall(".//w:rtl", w_ns))
                if "HeaderNote" in isi:
                    txbx_note.append(ada_rtl)
                elif bx.findall(".//w:instrText", w_ns) or bx.findall(".//w:fldSimple", w_ns):
                    txbx_page.append(ada_rtl)
    kepala_teks = " ".join("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", x)) for x in kepala_xmls)
    assert judul_panjang in kepala_teks and "عنوان البحث" not in kepala_teks, kepala_teks
    assert txbx_page and all(txbx_page), txbx_page
    assert txbx_note and not any(txbx_note), txbx_note
    with pymupdf.open(f / "uji.pdf") as doc:
        hal = [h.get_text() for h in doc]
    assert not any(CONTOH in h for h in hal), hal
    print(f"ok: @templat multi-section + @judul {len(judul_panjang)} aksara + RtlRun hanya pada kotak PAGE")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    utama()
