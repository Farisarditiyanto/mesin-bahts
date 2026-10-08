"""Rakit <folder>/<berkas>.docx dari build.json (hasil olah.py) TANPA Word, lalu .pdf kalau ada LibreOffice.
Untuk tempat yang tidak punya Word (Linux, kotak kerja Claude web). Dipanggil oleh bahts.py; jangan dijalankan langsung.

Bentuk halaman, huruf, tabel, dan فهارس mengikuti rakit.ps1. Bedanya:
- sampul netral (tidak memakai sampul.doc milik dosen); kepala sampul dari @lembaga;
- nomor halaman di فهارس dan {P:..} berupa field PAGEREF: dihitung oleh program yang membuka berkasnya,
  jadi tetap benar walaupun huruf (dan jumlah halaman) di sana berbeda.
"""
import json, os, re, shutil, signal, subprocess, tempfile, zipfile
from pathlib import Path
from xml.sax.saxutils import escape

QF = "KFGQPC HAFS Uthmanic Script"
KUNCI_FONT = "{6B2F8A31-4C5D-4E7A-9B1C-2D3E4F5A6B7C}"
CM = 567  # twips per cm
W = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
     'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
KEPALA = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
HALAMAN = (f'<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="{round(2.5 * CM)}" w:right="{round(3.5 * CM)}" '
           f'w:bottom="{round(2.5 * CM)}" w:left="{round(2.5 * CM)}" w:header="{round(1.25 * CM)}" w:footer="{round(1.25 * CM)}" w:gutter="0"/>')


def rpr(font, ukuran, tebal=False, atas=False):
    h = round(ukuran * 2)
    return (f'<w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>' + ('<w:b/><w:bCs/>' if tebal else '')
            + f'<w:sz w:val="{h}"/><w:szCs w:val="{h}"/>' + ('<w:vertAlign w:val="superscript"/>' if atas else '') + '<w:rtl/></w:rPr>')


def run(t, font, ukuran, tebal=False, atas=False):
    return f'<w:r>{rpr(font, ukuran, tebal, atas)}<w:t xml:space="preserve">{escape(t)}</w:t></w:r>' if t else ''


def par(isi, rata="both", sebelum=0, menjorok=0, lekat=False, hal_baru=False, masuk=0, gaya="", ekor=""):
    return ('<w:p><w:pPr>' + gaya + ('<w:keepNext/>' if lekat else '') + ('<w:pageBreakBefore/>' if hal_baru else '')
            + f'<w:widowControl/><w:bidi/><w:spacing w:before="{round(sebelum * 20)}" w:after="0" w:line="240" w:lineRule="auto"/>'
            + f'<w:ind w:left="{round(masuk * CM)}" w:right="0" w:firstLine="{round(menjorok * CM)}"/><w:jc w:val="{rata}"/>{ekor}</w:pPr>{isi}</w:p>')


def field(perintah, font, ukuran):
    """Field Word (PAGE / PAGEREF), ditandai «dirty»: Word menghitungnya saat mencetak/Save As PDF, atau Ctrl+A lalu F9.
    (updateFields di settings.xml tidak dipakai: memunculkan dialog tiap berkas dibuka.)"""
    p = rpr(font, ukuran)
    return (f'<w:r>{p}<w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r><w:r>{p}<w:instrText xml:space="preserve"> {perintah} </w:instrText></w:r>'
            f'<w:r>{p}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{p}<w:t>0</w:t></w:r><w:r>{p}<w:fldChar w:fldCharType="end"/></w:r>')


def tabel(baris, lebar_cm, garis):
    """baris = [[isi sel (xml paragraf), ...], ...]; kolom pertama di kanan."""
    w = [round(x * CM) for x in lebar_cm]
    tepi = ''.join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="000000"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    x = (f'<w:tbl><w:tblPr><w:bidiVisual/><w:tblW w:w="{sum(w)}" w:type="dxa"/><w:jc w:val="center"/>'
         + (f'<w:tblBorders>{tepi}</w:tblBorders>' if garis else '') + '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="108" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>'
         + ''.join(f'<w:gridCol w:w="{n}"/>' for n in w) + '</w:tblGrid>')
    for b in baris:
        x += '<w:tr>' + ''.join(f'<w:tc><w:tcPr><w:tcW w:w="{n}" w:type="dxa"/></w:tcPr>{s}</w:tc>' for n, s in zip(w, b)) + '</w:tr>'
    return x + '</w:tbl>'


def font_tersamar(ttf):
    """Font mushaf ditanam di .docx (cara Word: 32 byte pertama di-XOR dengan kunci) supaya ayat tampil di komputer mana pun."""
    kunci = bytes.fromhex(re.sub(r"[^0-9A-Fa-f]", "", KUNCI_FONT))[::-1]
    d = bytearray(Path(ttf).read_bytes())
    for i in range(32):
        d[i] ^= kunci[i % 16]
    return bytes(d)


def rakit(build, folder, ttf):
    """Tulis .docx (+ .pdf) ke `folder`; kembalikan baris laporan untuk dicetak."""
    data = json.load(open(build, encoding="utf8"))
    m, fmt = data["meta"], data["format"]
    ta, u_matan, u_catatan, u_judul = fmt["huruf"], fmt["matan"], fmt["catatan"], fmt["judul"]
    u_ayat = fmt.get("ayat", u_matan)
    nomor = iter(range(1, 10 ** 6))
    blok_bm = {}  # bookmark -> nomor blok tempatnya (dua bookmark di paragraf yang sama = halaman yang sama)

    def tanda(k, i=-1):
        blok_bm[k] = i
        n = next(nomor)
        return f'<w:bookmarkStart w:id="{n}" w:name="{k}"/><w:bookmarkEnd w:id="{n}"/>'

    def hal(kunci_bm):
        """Nomor halaman beberapa bookmark, dipisah «، »; yang separagraf cukup sekali."""
        unik = {blok_bm[k]: k for k in reversed(kunci_bm)}
        return run("، ", ta, u_matan).join(field(f"PAGEREF {k}", ta, u_matan) for k in kunci_bm if unik[blok_bm[k]] == k)

    catatan = []

    def runs(rs, ukuran, i, di_catatan=False):
        x = ""
        for r in rs:
            if "fn" in r:
                n = len(catatan) + 2  # 0 dan 1 = garis pemisah
                c = data["catatan"][r["fn"]]
                catatan.append(f'<w:footnote w:id="{n}">' + par(
                    run("(", ta, u_catatan) + f'<w:r>{rpr(ta, u_catatan)}<w:footnoteRef/></w:r>' + run(") ", ta, u_catatan)
                    + runs(c["runs"], u_catatan, i, True), gaya='<w:pStyle w:val="FootnoteText"/>') + '</w:footnote>')
                x += run("(", ta, u_matan, atas=True) + f'<w:r>{rpr(ta, u_matan, atas=True)}<w:footnoteReference w:id="{n}"/></w:r>' + run(")", ta, u_matan, atas=True)
            elif "bm" in r:
                x += tanda(r["bm"], i)
            elif "pg" in r:
                x += field(f"PAGEREF {r['pg']}", ta, ukuran)
            elif r.get("q"):
                x += run(r["t"], QF, ukuran if di_catatan else u_ayat)
            else:
                x += run(r["t"], ta, ukuran, r.get("b", False))
        return x

    isi_daftar = []  # (judul, bookmark, tingkat) untuk فهرس الموضوعات

    def judul(teks, tingkat, hal_baru):
        bm = f"t_{len(isi_daftar) + 1}"
        isi_daftar.append((teks, bm, tingkat))
        return par(tanda(bm) + run(teks, ta, u_judul, True), "center", 0 if hal_baru else 6, lekat=True, hal_baru=hal_baru)

    def sel(teks, rata="center", tebal=False, masuk=0):
        return par(run(teks, ta, u_matan, tebal), rata, masuk=masuk)

    # ---------- 1. Sampul netral ----------
    def sampul(u_jdl):
        """Baris sampul: (teks, ukuran, jarak di atasnya)."""
        x = [(b.strip(), 20, 0) for b in m.get("lembaga", "").split("|") if b.strip()]
        x += [(m["judul"], u_jdl, 110), (m["jenis"], 20, 40), ("إعداد الطالب:", 20, 70), (m["nama"], 20, 0), ("الرقم الجامعي: " + m["nim"], 20, 0)]
        if m.get("musyrif") not in (None, "", "-"):
            x += [("المشرف على البحث:", 20, 40), (m["musyrif"], 20, 0)]
            if m.get("jabatan") not in (None, "", "-"):
                x.append((m["jabatan"], 20, 0))
        return x + [(m["fasl"], 20, 70)]

    # Sampul harus tetap satu halaman. Taksiran dari ukuran di Word (Traditional Arabic tebal): tinggi baris ±1,55x ukuran huruf,
    # satu baris muat ±1500/ukuran huruf. Bidang tulis 700pt; sisakan 40pt. Kalau teksnya saja tidak muat, huruf judul dikecilkan
    # (36 -> paling kecil 22); sisanya dibagi ke jarak antarbagian.
    def tinggi(x):
        return sum(1.55 * u * -(-len(t) * u // 1500) for t, u, _ in x)
    u_jdl = next((u for u in range(36, 21, -2) if tinggi(sampul(u)) <= 600), 22)
    brs = sampul(u_jdl)
    susut = max(0.0, min(1.0, (660 - tinggi(brs)) / sum(j for _, _, j in brs)))
    badan = "".join(par(run(t, ta, u, True), "center", j * susut,
                        ekor=f'<w:sectPr>{HALAMAN}<w:bidi/></w:sectPr>' if n == len(brs) - 1 else "") for n, (t, u, j) in enumerate(brs))

    # ---------- 2. Isi ----------
    pertama = True
    for i, b in enumerate(data["blok"]):
        if b["k"] == "R":
            break
        if b["k"] in "KFBM":
            badan += judul(b["judul"], {"K": 0, "F": 0, "B": 1, "M": 2}[b["k"]], b["k"] in "KF" and not pertama)
            pertama = False
        elif b["k"] == "S":
            badan += par(run(b["judul"], ta, u_judul, True), "both", 6, lekat=True)
        else:
            badan += par(runs(b["runs"], u_matan, i), menjorok=0.8)

    # ---------- 3. المصادر والمراجع (tabel tanpa garis) ----------
    badan += judul("المصادر والمراجع", 0, True)
    badan += tabel([[sel("-" if n == 0 else f"{n}."), sel(p, "both")] for n, p in enumerate(data["pustaka"])], (1.3, 13.7), False)

    # ---------- 4. الفهارس ----------
    badan += judul("فهرس الآيات القرآنية", 0, True)
    ay = {}
    for a in data["ayat"]:  # ayat yang sama digabung, urut mushaf
        e = ay.setdefault((a["s"], int(a["a"].split("-")[0]), a["a"]), {"t": a["t"], "surah": a["surah"], "bm": []})
        e["bm"].append(a["k"])
        if len(a["t"]) > len(e["t"]):
            e["t"] = a["t"]
    baris = [[sel(t, tebal=True) for t in ("الآية", "السورة", "رقمها", "الصفحة")]]
    for (s, n, a), e in sorted(ay.items()):
        kata = e["t"].split(" ")
        nk = 5 if len(kata) > 5 and len(kata[3]) <= 3 else 4
        # huruf mushaf hanya untuk kata-kata ayat; titik-titik « ...» tetap huruf matan (huruf mushaf tidak punya titik)
        pot = run(" ".join(kata[:nk]), QF, u_ayat) + (run(" ...", ta, u_matan) if len(kata) > nk else "")
        baris.append([par(run("﴿", ta, u_matan) + pot + run("﴾", ta, u_matan)), sel(e["surah"]), sel(a), par(hal(e["bm"]), "center")])
    badan += tabel(baris, (7.9, 2.6, 2.5, 2.0), True)

    badan += judul("فهرس الأحاديث والآثار", 0, True)
    baris = [[sel(t, tebal=True) for t in ("طرف الحديث أو الأثر", "الراوي", "الصفحة")]]
    baris += [[sel(f"«{h['t']}»", "both"), sel(h["r"]), par(hal([h["k"]] + h.get("lagi", [])), "center")] for h in data["hadits"]]
    badan += tabel(baris, (8.6, 4.4, 2.0), True)

    badan += judul("فهرس الموضوعات", 0, True)
    baris = [[sel("الموضوع", tebal=True), sel("الصفحة", tebal=True)]]
    baris += [[sel(t, "both", tingkat == 0, 0.7 * tingkat), par(hal([bm]), "center")] for t, bm, tingkat in isi_daftar]
    badan += tabel(baris, (13.0, 2.0), True)
    ulang = '<w:numRestart w:val="eachPage"/>' if fmt.get("catatan_ulang_tiap_halaman") else ''
    badan += ('<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/></w:pPr></w:p>'
              f'<w:sectPr><w:footerReference w:type="default" r:id="rId5"/><w:footnotePr>{ulang}</w:footnotePr>{HALAMAN}<w:pgNumType w:start="1"/><w:bidi/></w:sectPr>')

    # ---------- 5. Bungkus .docx ----------
    pemisah = ''.join(f'<w:footnote w:type="{t}" w:id="{n}"><w:p><w:pPr><w:bidi/><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:{t}/></w:r></w:p></w:footnote>'
                      for n, t in enumerate(("separator", "continuationSeparator")))
    huruf_dasar = f'<w:rFonts w:ascii="{ta}" w:hAnsi="{ta}" w:cs="{ta}"/>'
    berkas = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="odttf" ContentType="application/vnd.openxmlformats-officedocument.obfuscatedFont"/>'
            + ''.join(f'<Override PartName="/word/{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.{t}+xml"/>'
                      for n, t in (("document", "document.main"), ("styles", "styles"), ("settings", "settings"), ("footnotes", "footnotes"),
                                   ("footer1", "footer"), ("fontTable", "fontTable"))) + '</Types>',
        "_rels/.rels": f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{REL}/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/_rels/document.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + ''.join(f'<Relationship Id="rId{n}" Type="{REL}/{t}" Target="{f}.xml"/>' for n, (t, f) in enumerate(
                (("styles", "styles"), ("settings", "settings"), ("footnotes", "footnotes"), ("fontTable", "fontTable"), ("footer", "footer1")), 1)) + '</Relationships>',
        "word/_rels/fontTable.xml.rels": f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{REL}/font" Target="fonts/font1.odttf"/></Relationships>',
        "word/document.xml": f'<w:document {W}><w:body>{badan}</w:body></w:document>',
        "word/footnotes.xml": f'<w:footnotes {W}>{pemisah}{"".join(catatan)}</w:footnotes>',
        # pedoman: nomor halaman di tengah bawah, huruf dan ukuran sama dengan matan, dihitung mulai dari المقدمة
        "word/footer1.xml": f'<w:ftr {W}>{par(field("PAGE", ta, u_matan), "center")}</w:ftr>',
        "word/fontTable.xml": f'<w:fonts {W}><w:font w:name="{QF}"><w:embedRegular r:id="rId1" w:fontKey="{KUNCI_FONT}"/></w:font></w:fonts>',
        "word/settings.xml": f'<w:settings {W}><w:embedTrueTypeFonts/><w:footnotePr>{ulang}<w:footnote w:id="0"/><w:footnote w:id="1"/></w:footnotePr>'
            '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>',
        "word/styles.xml": f'<w:styles {W}><w:docDefaults><w:rPrDefault><w:rPr>{huruf_dasar}<w:sz w:val="{round(u_matan * 2)}"/><w:szCs w:val="{round(u_matan * 2)}"/>'
            '<w:lang w:val="en-US" w:bidi="ar-SA"/></w:rPr></w:rPrDefault></w:docDefaults>'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
            f'<w:style w:type="paragraph" w:styleId="FootnoteText"><w:name w:val="footnote text"/><w:basedOn w:val="Normal"/><w:rPr>{huruf_dasar}'
            f'<w:sz w:val="{round(u_catatan * 2)}"/><w:szCs w:val="{round(u_catatan * 2)}"/></w:rPr></w:style></w:styles>',
    }
    keluar = Path(folder) / (m["berkas"] + ".docx")
    with zipfile.ZipFile(keluar, "w", zipfile.ZIP_DEFLATED) as z:
        for nama, x in berkas.items():
            z.writestr(nama, KEPALA + x)
        z.writestr("word/fonts/font1.odttf", font_tersamar(ttf))
    lap = [f"CATATAN_KAKI={len(catatan)}", f"Jadi: {Path(folder).name}/{keluar.name}", buat_pdf(keluar, ta, ttf)]
    if any("pg" in r for c in data["catatan"] for r in c["runs"]):
        lap.append("Ada «سبق تخريجه، ص…»: di Word, klik di dalam salah satu catatan kaki, lalu Ctrl+A dan F9 sekali lagi "
                   "(Ctrl+A di matan tidak menjangkau catatan kaki); tanpa itu nomor halamannya salah.")
    return lap


def _libreoffice(so, docx, batas):
    """Ubah docx jadi pdf di sebelahnya; False kalau gagal atau lewat `batas` detik (LibreOffice bisa berputar tanpa henti)."""
    pdf = docx.with_suffix(".pdf")
    pdf.unlink(missing_ok=True)
    p = subprocess.Popen([so, f"-env:UserInstallation=file://{tempfile.mkdtemp()}", "--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        p.wait(batas)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        return False
    return pdf.exists()


def buat_pdf(docx, huruf, ttf):
    """Ubah .docx jadi .pdf lewat LibreOffice; kembalikan satu baris laporan yang jujur soal bedanya dengan pedoman."""
    resmi = "PDF untuk dikumpulkan: buka .docx di Word, tekan Ctrl+A lalu F9 (mengisi nomor halaman الفهارس), lalu File > Save As > PDF."
    so = shutil.which("soffice") or shutil.which("libreoffice")
    if not so:
        return "PDF TIDAK dibuat: LibreOffice tidak ada di sini. " + resmi
    dipakai = subprocess.run(["fc-match", "-f", "%{family}", huruf], capture_output=True, text=True).stdout
    font = Path.home() / ".fonts"
    font.mkdir(exist_ok=True)
    shutil.copy(ttf, font)
    beda = [] if huruf.lower() in dipakai.lower() else [f"huruf «{huruf}» tidak ada di sini dan diganti «{dipakai}»"]
    if not _libreoffice(so, docx, 180):
        # LibreOffice kadang macet meratakan baris Arab kanan-kiri: coba sekali lagi dengan salinan rata kanan
        salinan = Path(tempfile.mkdtemp()) / docx.name
        with zipfile.ZipFile(docx) as a, zipfile.ZipFile(salinan, "w", zipfile.ZIP_DEFLATED) as b:
            for i in a.infolist():
                b.writestr(i, a.read(i).replace(b'<w:jc w:val="both"/>', b'<w:jc w:val="left"/>'))
        if not _libreoffice(so, salinan, 180):
            return "PDF GAGAL dibuat (LibreOffice macet atau menolak berkasnya). " + resmi
        shutil.move(salinan.with_suffix(".pdf"), docx.with_suffix(".pdf"))
        beda.append("baris tidak diratakan kanan-kiri")
    if beda:
        return f"PDF jadi sebagai PRATINJAU saja ({'; '.join(beda)}): bentuk dan jumlah halamannya tidak sama dengan pedoman. " + resmi
    return f"Jadi: {docx.parent.name}/{docx.with_suffix('.pdf').name} (huruf «{huruf}» tersedia)"
