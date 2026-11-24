# SPDX-License-Identifier: AGPL-3.0-or-later
"""Susun halaman kitab dan catatan kelas menjadi satu PDF."""

import io
import json
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from html import escape
from inspect import signature
from pathlib import Path
from urllib.parse import urlsplit

FONT = Path(__file__).with_name("font_muqorror")
ARAB = re.compile(r"([\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]+"
                  r"(?:[ \t]+[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]+)*)")

CSS = """
@font-face { font-family: Kalam; src: url(Kalam-Regular.ttf); }
@font-face { font-family: Aref; src: url(ArefRuqaa-Regular.ttf); }
body { margin: 0; color: #263b64; font-family: Kalam; font-size: 14pt; line-height: 1.46; }
.arab { font-family: Aref; }
.label { font-family: sans-serif; color: #6b5950; font-size: 9pt; letter-spacing: 1pt; }
h1, h2, h3 { font-weight: normal; line-height: 1.2; }
h1 { color: #1d2639; font-size: 31pt; margin: 10pt 0 14pt; }
h2 { color: #1d2639; font-size: 20pt; margin: 14pt 0 7pt; }
h3 { color: #26516a; font-size: 17pt; margin: 20pt 0 1pt; page-break-after: avoid; }
p { margin: 0 0 7pt; }
.sumber { color: #6b5950; font-family: sans-serif; font-size: 10pt; margin: 0 0 8pt; page-break-after: avoid; }
.kanan { text-align: right; }
.butir { margin: 0 0 8pt; padding-left: 13pt; border-left: 1pt solid #ccdfdc; }
.butir-rtl { padding-left: 0; border-left: none; padding-right: 13pt; border-right: 1pt solid #ccdfdc; }
.baris { margin: 0 0 10pt; padding-bottom: 5pt; border-bottom: 0.5pt solid #dfd7c8; }
"""


@dataclass(frozen=True)
class Sumber:
    judul: str
    tautan: str


@dataclass(frozen=True)
class Catatan:
    judul: str
    sumber: tuple[str, ...]
    butir: tuple[str, ...]


@dataclass(frozen=True)
class Bagian:
    judul: str
    halaman: tuple[tuple[int, int], ...]
    catatan: tuple[Catatan, ...]


@dataclass(frozen=True)
class Rencana:
    judul: str
    kitab: Path
    kitab_label: str
    keterangan: str
    sumber: dict[str, Sumber]
    bagian: tuple[Bagian, ...]


def _objek(nilai, letak, wajib, opsional=()):
    if not isinstance(nilai, dict):
        raise ValueError(f"{letak} harus berupa objek JSON")
    kurang = set(wajib) - nilai.keys()
    lebih = nilai.keys() - set(wajib) - set(opsional)
    if kurang or lebih:
        raise ValueError(f"{letak} memiliki kolom kurang {sorted(kurang)} atau asing {sorted(lebih)}")
    return nilai


def _teks(nilai, letak):
    if not isinstance(nilai, str) or not nilai.strip():
        raise ValueError(f"{letak} harus berisi teks")
    if any(unicodedata.category(c) in ("Cc", "Cs") and c not in "\t\r\n" for c in nilai):
        raise ValueError(f"{letak} memuat karakter kontrol")
    return nilai.strip()


def _daftar(nilai, letak):
    if not isinstance(nilai, list):
        raise ValueError(f"{letak} harus berupa daftar")
    return nilai


def _sumber(daftar):
    sumber = {}
    for i, data in enumerate(_daftar(daftar, "sumber"), 1):
        letak = f"sumber {i}"
        data = _objek(data, letak, ("id", "judul"), ("tautan",))
        kode = _teks(data["id"], f"{letak}.id")
        judul = _teks(data["judul"], f"{letak}.judul")
        tautan = _teks(data["tautan"], f"{letak}.tautan") if "tautan" in data else ""
        pecah = urlsplit(tautan)
        if tautan and (pecah.scheme not in ("http", "https") or not pecah.hostname):
            raise ValueError(f"{letak}.tautan harus berupa URL HTTP atau HTTPS")
        if kode in sumber:
            raise ValueError(f"ID sumber duplikat: {kode}")
        sumber[kode] = Sumber(judul, tautan)
    return sumber


def _catatan(daftar, sumber, letak):
    for i, data in enumerate(_daftar(daftar, f"{letak}.catatan"), 1):
        nama = f"{letak}.catatan {i}"
        data = _objek(data, nama, ("judul", "sumber", "butir"))
        judul = _teks(data["judul"], f"{nama}.judul")
        kode = tuple(_teks(k, f"{nama}.sumber") for k in _daftar(data["sumber"], f"{nama}.sumber"))
        for k in kode:
            if k not in sumber:
                raise ValueError(f"{nama} menunjuk sumber yang belum didaftar: {k}")
        butir = tuple(_teks(b, f"{nama}.butir") for b in _daftar(data["butir"], f"{nama}.butir"))
        if not butir:
            raise ValueError(f"{nama}.butir harus berisi sedikitnya satu paragraf")
        yield Catatan(judul, kode, butir)


def _bagian(daftar, sumber):
    akhir = 0
    for i, data in enumerate(_daftar(daftar, "bagian"), 1):
        letak = f"bagian {i}"
        data = _objek(data, letak, ("judul", "halaman", "catatan"))
        judul = _teks(data["judul"], f"{letak}.judul")
        halaman = []
        for rentang in _daftar(data["halaman"], f"{letak}.halaman"):
            if not isinstance(rentang, list) or len(rentang) != 2 or any(type(n) is not int for n in rentang):
                raise ValueError(f"{letak}.halaman harus berisi pasangan [awal, akhir] dalam angka halaman PDF")
            a, z = rentang
            if not 1 <= a <= z or a <= akhir:
                raise ValueError(f"{letak}.halaman {rentang} terbalik, bertumpuk, atau di luar urutan")
            halaman.append((a, z))
            akhir = z
        catatan = tuple(_catatan(data["catatan"], sumber, letak))
        if not halaman and not catatan:
            raise ValueError(f"{letak} harus berisi halaman kitab atau catatan")
        yield Bagian(judul, tuple(halaman), catatan)


def _baca(jalur):
    data = _objek(json.loads(jalur.read_text(encoding="utf-8-sig")), "rencana",
                  ("judul", "kitab", "sumber", "bagian"), ("kitab_label", "keterangan"))
    judul = _teks(data["judul"], "judul")
    kitab = jalur.parent / _teks(data["kitab"], "kitab")
    label = _teks(data.get("kitab_label", kitab.name), "kitab_label")
    keterangan = _teks(data["keterangan"], "keterangan") if "keterangan" in data else ""
    sumber = _sumber(data["sumber"])
    bagian = tuple(_bagian(data["bagian"], sumber))
    if not bagian:
        raise ValueError("bagian harus berisi sedikitnya satu bagian")
    return Rencana(judul, kitab, label, keterangan, sumber, bagian)


def _isi(teks):
    teks = teks.replace("\r\n", "\n").replace("\r", "\n")
    potongan = ARAB.split(teks)
    for i, isi in enumerate(potongan):
        bersih = escape(isi).replace("\n", "<br>")
        potongan[i] = f'<span class="arab">{bersih}</span>' if i % 2 else bersih
    return "".join(potongan)


def _arah(teks):
    for c in teks:
        if unicodedata.bidirectional(c) in ("L", "R", "AL"):
            return ' dir="rtl"' if unicodedata.bidirectional(c) != "L" else ""
    return ""


def _teks_html(tag, teks, atribut=""):
    return f"<{tag}{atribut}{_arah(teks)}>{_isi(teks)}</{tag}>"


def _tautan(tujuan, teks):
    return f'<a href="{escape(tujuan, quote=True)}" style="color:#255b70">{_isi(teks)}</a>'


def _daftar_bagian(rencana):
    hasil = ['<p class="label">MUQORROR</p>', _teks_html("h1", rencana.judul),
             _teks_html("p", rencana.kitab_label)]
    if rencana.keterangan:
        hasil.append(_teks_html("p", rencana.keterangan))
    hasil.append("<h2>Daftar bagian</h2>")
    for i, bagian in enumerate(rencana.bagian, 1):
        judul = _tautan(f"#bagian-{i}", bagian.judul)
        catatan = " · " + _tautan(f"#catatan-{i}-1", "Catatan") if bagian.halaman and bagian.catatan else ""
        hasil.append(f'<p class="baris"{_arah(bagian.judul)}>{judul}{catatan}</p>')
    if rencana.sumber:
        sumber = _tautan("#sumber", "Daftar sumber kelas")
        hasil.append(f"<p>{sumber}</p>")
    return "".join(hasil)


def _lembar_catatan(bagian, urut, jangkar_sumber):
    arah = _arah(bagian.judul)
    hasil = [f'<p class="label"{arah}>CATATAN KELAS</p>', _teks_html("h2", bagian.judul)]
    for i, catatan in enumerate(bagian.catatan, 1):
        hasil.append(_teks_html("h3", catatan.judul, f' id="catatan-{urut}-{i}"'))
        sumber = ", ".join(_tautan(f"#{jangkar_sumber[k]}", k) for k in catatan.sumber)
        atribusi = f"Sumber kelas · {sumber}" if sumber else "Catatan penyusun"
        sisi = " kanan" if _arah(catatan.judul) else ""
        hasil.append(f'<p class="sumber{sisi}">{atribusi}</p>')
        for butir in catatan.butir:
            kelas = ' class="butir butir-rtl"' if _arah(butir) else ' class="butir"'
            hasil.append(_teks_html("p", butir, kelas))
    return "".join(hasil)


def _daftar_sumber(sumber, jangkar_sumber):
    hasil = ['<p class="label">RUJUKAN REKAMAN</p>', '<h2 id="sumber">Daftar sumber kelas</h2>']
    for kode, data in sumber.items():
        tujuan = data.tautan
        judul = _tautan(tujuan, data.judul) if tujuan else _isi(data.judul)
        hasil.append(f'<p class="baris" id="{jangkar_sumber[kode]}">{_isi(kode)} · {judul}</p>')
    return "".join(hasil)


class _Perakit:
    def __init__(self, pdf, hasil):
        self.pdf = pdf
        self.hasil = hasil
        self.jangkar = {}
        self.tautan = []
        self.daftar = []
        self.arsip = pdf.Archive(str(FONT))

    def lembar(self, html, label):
        halaman = self.pdf.paper_rect("a4")
        badan = self.pdf.Rect(58, 75, halaman.width - 54, halaman.height - 65)
        awal = len(self.hasil)

        def posisi(p):
            kotak = self.pdf.Rect(p.rect)
            if p.id and p.open_close & 1:
                self.jangkar.setdefault(p.id, (nomor, kotak.tl))
            if p.href and not kotak.is_empty:
                self.tautan.append((nomor, kotak, p.href))

        stream = io.BytesIO()
        cerita = self.pdf.Story(html, CSS, archive=self.arsip)
        batas = self.pdf.mupdf.FZ_PLACE_STORY_FLAG_NO_OVERFLOW
        with self.pdf.DocumentWriter(stream) as penulis:
            nomor = awal
            lanjut = True
            while lanjut:
                lanjut, _terisi = cerita.place(badan, batas)
                if lanjut == self.pdf.mupdf.FZ_PLACE_STORY_RETURN_OVERFLOW_WIDTH:
                    raise ValueError(f"teks {label.lower()} terlalu lebar untuk satu baris")
                cerita.element_positions(posisi)
                cerita.draw(penulis.begin_page(halaman))
                penulis.end_page()
                nomor += 1
        with self.pdf.open(stream=stream.getvalue(), filetype="pdf") as lembar:
            self.hasil.insert_pdf(lembar)
        for nomor in range(awal, len(self.hasil)):
            p = self.hasil[nomor]
            p.draw_rect(halaman, color=None, fill=(1, 0.987, 0.956), overlay=False)
            p.draw_line((58, 56), (halaman.width - 54, 55), color=(0.41, 0.56, 0.56), width=0.85)
            p.insert_text((58, halaman.height - 37), label, fontsize=9, color=(0.36, 0.34, 0.32))
            p.insert_textbox((halaman.width - 96, halaman.height - 47, halaman.width - 54, halaman.height - 31),
                             str(nomor + 1), fontsize=9, align=self.pdf.TEXT_ALIGN_RIGHT,
                             color=(0.36, 0.34, 0.32))

    def tandai(self, tingkat, judul, nomor):
        self.daftar.append((tingkat, judul, nomor + 1))

    def sambungkan(self):
        for nomor, kotak, tujuan in self.tautan:
            if tujuan.startswith("#"):
                halaman, titik = self.jangkar[tujuan[1:]]
                tautan = {"kind": self.pdf.LINK_GOTO, "page": halaman, "to": titik}
            else:
                tautan = {"kind": self.pdf.LINK_URI, "uri": tujuan}
            self.hasil[nomor].insert_link({"from": kotak, **tautan})
        self.hasil.set_toc(self.daftar)


def _susun(pdf, hasil, kitab, rencana):
    perakit = _Perakit(pdf, hasil)
    jangkar_sumber = {k: f"sumber-{i}" for i, k in enumerate(rencana.sumber, 1)}
    perakit.tandai(1, "Daftar bagian", 0)
    perakit.lembar(_daftar_bagian(rencana), "Muqorror")
    blok_salin = sum(len(b.halaman) for b in rencana.bagian)
    for i, bagian in enumerate(rencana.bagian, 1):
        awal = len(hasil)
        perakit.jangkar[f"bagian-{i}"] = (awal, pdf.Point(0, 0))
        perakit.tandai(1, bagian.judul, awal)
        for a, z in bagian.halaman:
            blok_salin -= 1
            hasil.insert_pdf(kitab, from_page=a - 1, to_page=z - 1, final=int(blok_salin == 0))
        if bagian.catatan:
            perakit.lembar(_lembar_catatan(bagian, i, jangkar_sumber), "Catatan kelas")
            for j, catatan in enumerate(bagian.catatan, 1):
                halaman, _titik = perakit.jangkar[f"catatan-{i}-{j}"]
                perakit.tandai(2, catatan.judul, halaman)
    if rencana.sumber:
        perakit.tandai(1, "Daftar sumber kelas", len(hasil))
        perakit.lembar(_daftar_sumber(rencana.sumber, jangkar_sumber), "Sumber kelas")
    perakit.sambungkan()
    hasil.set_metadata({"title": rencana.judul, "subject": rencana.kitab_label})


def _simpan(hasil, tujuan):
    with tempfile.NamedTemporaryFile(prefix=".muqorror-", suffix=".pdf", dir=tujuan.parent, delete=False) as f:
        sementara = Path(f.name)
    try:
        hasil.save(sementara, garbage=4, deflate=True)
        sementara.replace(tujuan)
    finally:
        sementara.unlink(missing_ok=True)


def rakit(jalur, tujuan):
    try:
        import pymupdf as pdf
    except ImportError:
        pdf = None
    if pdf is None or "flags" not in signature(pdf.Story.place).parameters:
        raise ValueError("muqorror butuh versi pymupdf di requirements.txt. "
                         "Jalankan python -m pip install -r requirements.txt dari repo")
    try:
        rencana = _baca(jalur)
        if tujuan.suffix.lower() != ".pdf":
            raise ValueError("hasil muqorror harus berakhiran .pdf")
        for asal in (jalur, rencana.kitab):
            if tujuan.resolve() == asal.resolve() or (tujuan.exists() and tujuan.samefile(asal)):
                raise ValueError("hasil muqorror tidak boleh menimpa kitab atau rencana")
        with pdf.open(rencana.kitab) as kitab, pdf.open() as hasil:
            if not kitab.is_pdf or kitab.needs_pass or not len(kitab):
                raise ValueError("kitab harus berupa PDF dengan halaman yang dapat dibuka tanpa kata sandi")
            for bagian in rencana.bagian:
                if bagian.halaman and bagian.halaman[-1][1] > len(kitab):
                    raise ValueError(f"rentang halaman bagian «{bagian.judul}» di luar PDF kitab (1–{len(kitab)})")
            _susun(pdf, hasil, kitab, rencana)
            _simpan(hasil, tujuan)
            print(f"HALAMAN={len(hasil)}\nPDF={tujuan.resolve()}")
    except (OSError, pdf.FileDataError, pdf.FileNotFoundError) as e:
        raise ValueError(str(e)) from e
