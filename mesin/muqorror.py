# SPDX-License-Identifier: AGPL-3.0-or-later
"""Susun ulang kitab muqorror bergaya klasik dengan anotasi catatan mahasiswa menjadi satu PDF."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

import diagram
from berkas import sementara

FONT = Path(__file__).with_name("font_muqorror")

JENIS_BAGIAN = ("kitab", "lembar")
WARNA_CATATAN = ("biru", "merah", "hijau")
WARNA_DIAGRAM = ("biru", "hijau", "merah", "ungu")
GAYA_BAIT = ("alfiyah", "syahid")
TIPE_DIAGRAM = ("pohon", "alur", "tabel")

PALET = {
    "biru": ("#184a8c", "#2764b3", "#f0f5fc", "#dce9f9"),
    "merah": ("#8f1d28", "#b8323e", "#fdf2f3", "#f8dce0"),
    "hijau": ("#165541", "#267a5e", "#eff8f4", "#d5efe4"),
    "ungu": ("#53297a", "#7645a3", "#f6f1fb", "#e8dcf5"),
}

ANGKA_ARAB = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
POLA_ANOTASI = re.compile(r"\{(hl2|hl|ul|ur|o|b|fn):([^{}]+)\}")
HARAKAT = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")

TAG_ANOTASI = {
    "hl": lambda isi: f'<mark class="hl">{isi}</mark>',
    "hl2": lambda isi: f'<mark class="hl2">{isi}</mark>',
    "ul": lambda isi: f'<span class="ul">{isi}</span>',
    "ur": lambda isi: f'<span class="ur">{isi}</span>',
    "o": lambda isi: f'<span class="o">{isi}</span>',
    "b": lambda isi: f"<strong>{isi}</strong>",
    "fn": lambda isi: f'<sup class="fn">({isi[1:-1] if isi.startswith("(") and isi.endswith(")") else isi})</sup>',
}


@dataclass(frozen=True)
class Sumber:
    id: str
    judul: str
    tautan: str = ""


@dataclass(frozen=True)
class Catatan:
    isi: str
    label: str = ""
    warna: str = "biru"
    sumber: tuple[str, ...] = ()


@dataclass(frozen=True)
class BlokHal:
    nomor: str


@dataclass(frozen=True)
class BlokSubjudul:
    teks: str
    sumber: tuple[str, ...] = ()


@dataclass(frozen=True)
class BlokBait:
    kanan: str
    kiri: str
    nomor: str = ""
    gaya: str = "alfiyah"
    catatan: tuple[Catatan, ...] = ()


@dataclass(frozen=True)
class BlokMatan:
    teks: str
    catatan: tuple[Catatan, ...] = ()


@dataclass(frozen=True)
class BlokSela:
    label: str = ""
    warna: str = "biru"
    sumber: tuple[str, ...] = ()
    isi: str = ""
    butir: tuple[str, ...] = ()
    catatan: tuple[Catatan, ...] = ()


@dataclass(frozen=True)
class ButirHasyiah:
    nomor: str
    teks: str


@dataclass(frozen=True)
class BlokHasyiah:
    butir: tuple[ButirHasyiah, ...]
    catatan_pangkas: str = ""


@dataclass(frozen=True)
class CabangPohon:
    judul: str
    isi: tuple[str, ...]
    warna: str = "biru"


@dataclass(frozen=True)
class LangkahAlur:
    judul: str
    isi: str = ""
    warna: str = "biru"


@dataclass(frozen=True)
class DiagramPohon:
    akar: str
    cabang: tuple[CabangPohon, ...]


@dataclass(frozen=True)
class DiagramAlur:
    langkah: tuple[LangkahAlur, ...]


@dataclass(frozen=True)
class DiagramTabel:
    kolom: tuple[str, ...]
    baris: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class BlokDiagram:
    judul: str
    isi: DiagramPohon | DiagramAlur | DiagramTabel
    sumber: tuple[str, ...] = ()
    catatan: tuple[Catatan, ...] = ()


@dataclass(frozen=True)
class BlokHalamanBaru:
    pass


Blok = BlokHal | BlokSubjudul | BlokBait | BlokMatan | BlokSela | BlokHasyiah | BlokDiagram | BlokHalamanBaru


@dataclass(frozen=True)
class Bagian:
    judul: str
    jenis: str
    hal_kitab: str
    catatan_pangkas: str
    sumber: tuple[str, ...]
    blok: tuple[Blok, ...]


@dataclass(frozen=True)
class Rencana:
    judul: str
    subjudul: str
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


def _cek_kontrol(nilai, letak):
    if any(unicodedata.category(c) in ("Cc", "Cs") and c not in "\t\r\n" for c in nilai):
        raise ValueError(f"{letak} memuat karakter kontrol")


def _teks(nilai, letak):
    if not isinstance(nilai, str) or not nilai.strip():
        raise ValueError(f"{letak} harus berisi teks")
    _cek_kontrol(nilai, letak)
    return nilai.strip()


def _teks_opsional(data, kunci, letak):
    if kunci not in data:
        return ""
    nilai = data[kunci]
    if not isinstance(nilai, str):
        raise ValueError(f"{letak}.{kunci} harus berupa teks")
    _cek_kontrol(nilai, f"{letak}.{kunci}")
    return nilai.strip()


def _daftar(nilai, letak):
    if not isinstance(nilai, list):
        raise ValueError(f"{letak} harus berupa daftar")
    return nilai


def _pilihan(nilai, sah, letak):
    teks = _teks(nilai, letak)
    if teks not in sah:
        raise ValueError(f"{letak} harus salah satu dari {', '.join(sah)}, bukan «{teks}»")
    return teks


def _kode_sumber(data, sumber, letak):
    if "sumber" not in data:
        return ()
    kode = tuple(dict.fromkeys(_teks(k, f"{letak}.sumber") for k in _daftar(data["sumber"], f"{letak}.sumber")))
    for k in kode:
        if k not in sumber:
            raise ValueError(f"{letak} menunjuk sumber yang belum didaftar: {k}")
    return kode


def _urai_catatan_satu(nilai, sumber, letak):
    data = _objek(nilai, letak, ("isi",), ("label", "warna", "sumber"))
    isi = _teks(data["isi"], f"{letak}.isi")
    label = _teks_opsional(data, "label", letak)
    warna = _pilihan(data["warna"], WARNA_CATATAN, f"{letak}.warna") if "warna" in data else "biru"
    kode = _kode_sumber(data, sumber, letak)
    return Catatan(isi=isi, label=label, warna=warna, sumber=kode)


def _urai_catatan(data, sumber, letak):
    if "catatan" not in data:
        return ()
    nilai = data["catatan"]
    if isinstance(nilai, dict):
        return (_urai_catatan_satu(nilai, sumber, f"{letak}.catatan"),)
    if isinstance(nilai, list):
        return tuple(_urai_catatan_satu(m, sumber, f"{letak}.catatan {i}") for i, m in enumerate(nilai, 1))
    raise ValueError(f"{letak}.catatan harus berupa objek atau daftar objek")


def _urai_sumber(daftar):
    sumber: dict[str, Sumber] = {}
    for i, item in enumerate(_daftar(daftar, "sumber"), 1):
        letak = f"sumber {i}"
        data = _objek(item, letak, ("id", "judul"), ("tautan",))
        kode = _teks(data["id"], f"{letak}.id")
        judul = _teks(data["judul"], f"{letak}.judul")
        tautan = _teks_opsional(data, "tautan", letak)
        if tautan:
            pecah = urlsplit(tautan)
            if pecah.scheme not in ("http", "https") or not pecah.hostname:
                raise ValueError(f"{letak}.tautan harus berupa URL HTTP atau HTTPS")
        if kode in sumber:
            raise ValueError(f"ID sumber duplikat: {kode}")
        sumber[kode] = Sumber(id=kode, judul=judul, tautan=tautan)
    return sumber


def _urai_hal(data, _sumber, letak):
    _objek(data, letak, ("jenis", "nomor"))
    return BlokHal(nomor=_teks(data["nomor"], f"{letak}.nomor"))


def _urai_subjudul(data, sumber, letak):
    _objek(data, letak, ("jenis", "teks"), ("sumber",))
    return BlokSubjudul(teks=_teks(data["teks"], f"{letak}.teks"), sumber=_kode_sumber(data, sumber, letak))


def _urai_bait(data, sumber, letak):
    _objek(data, letak, ("jenis", "kanan", "kiri"), ("nomor", "gaya", "catatan"))
    kanan = _teks(data["kanan"], f"{letak}.kanan")
    kiri = _teks(data["kiri"], f"{letak}.kiri")
    nomor = _teks_opsional(data, "nomor", letak)
    gaya = _pilihan(data["gaya"], GAYA_BAIT, f"{letak}.gaya") if "gaya" in data else "alfiyah"
    return BlokBait(kanan=kanan, kiri=kiri, nomor=nomor, gaya=gaya, catatan=_urai_catatan(data, sumber, letak))


def _urai_matan(data, sumber, letak):
    _objek(data, letak, ("jenis", "teks"), ("catatan",))
    return BlokMatan(teks=_teks(data["teks"], f"{letak}.teks"), catatan=_urai_catatan(data, sumber, letak))


def _urai_sela(data, sumber, letak):
    _objek(data, letak, ("jenis",), ("label", "warna", "sumber", "isi", "butir", "catatan"))
    label = _teks_opsional(data, "label", letak)
    warna = _pilihan(data["warna"], WARNA_CATATAN, f"{letak}.warna") if "warna" in data else "biru"
    kode = _kode_sumber(data, sumber, letak)
    isi = _teks_opsional(data, "isi", letak)
    butir = tuple(_teks(b, f"{letak}.butir {i}") for i, b in enumerate(_daftar(data["butir"], f"{letak}.butir"), 1)) if "butir" in data else ()
    if not isi and not butir:
        raise ValueError(f"{letak} harus mengisi isi atau butir")
    return BlokSela(label=label, warna=warna, sumber=kode, isi=isi, butir=butir, catatan=_urai_catatan(data, sumber, letak))


def _urai_hasyiah(data, _sumber, letak):
    _objek(data, letak, ("jenis", "butir"), ("catatan_pangkas",))
    mentah = _daftar(data["butir"], f"{letak}.butir")
    if not mentah:
        raise ValueError(f"{letak}.butir tidak boleh kosong")
    butir = []
    for i, item in enumerate(mentah, 1):
        b = _objek(item, f"{letak}.butir {i}", ("nomor", "teks"))
        butir.append(ButirHasyiah(nomor=_teks(b["nomor"], f"{letak}.butir {i}.nomor"),
                                  teks=_teks(b["teks"], f"{letak}.butir {i}.teks")))
    return BlokHasyiah(butir=tuple(butir), catatan_pangkas=_teks_opsional(data, "catatan_pangkas", letak))


def _urai_diagram_pohon(data, letak):
    _objek(data, letak, ("jenis", "judul", "tipe", "akar", "cabang"), ("sumber", "catatan"))
    akar = _teks(data["akar"], f"{letak}.akar")
    mentah = _daftar(data["cabang"], f"{letak}.cabang")
    if not 2 <= len(mentah) <= 4:
        raise ValueError(f"{letak}.cabang harus berisi 2 sampai 4 cabang")
    cabang = []
    for i, item in enumerate(mentah):
        nama = f"{letak}.cabang {i + 1}"
        c = _objek(item, nama, ("judul", "isi"), ("warna",))
        judul = _teks(c["judul"], f"{nama}.judul")
        isi = tuple(_teks(x, f"{nama}.isi {j}") for j, x in enumerate(_daftar(c["isi"], f"{nama}.isi"), 1))
        warna = _pilihan(c["warna"], WARNA_DIAGRAM, f"{nama}.warna") if "warna" in c else WARNA_DIAGRAM[i % len(WARNA_DIAGRAM)]
        cabang.append(CabangPohon(judul=judul, isi=isi, warna=warna))
    return DiagramPohon(akar=akar, cabang=tuple(cabang))


def _urai_diagram_alur(data, letak):
    _objek(data, letak, ("jenis", "judul", "tipe", "langkah"), ("sumber", "catatan"))
    mentah = _daftar(data["langkah"], f"{letak}.langkah")
    if not 2 <= len(mentah) <= 5:
        raise ValueError(f"{letak}.langkah harus berisi 2 sampai 5 langkah")
    langkah = []
    for i, item in enumerate(mentah):
        nama = f"{letak}.langkah {i + 1}"
        lk = _objek(item, nama, ("judul",), ("isi", "warna"))
        judul = _teks(lk["judul"], f"{nama}.judul")
        isi = _teks_opsional(lk, "isi", nama)
        warna = _pilihan(lk["warna"], WARNA_DIAGRAM, f"{nama}.warna") if "warna" in lk else WARNA_DIAGRAM[i % len(WARNA_DIAGRAM)]
        langkah.append(LangkahAlur(judul=judul, isi=isi, warna=warna))
    return DiagramAlur(langkah=tuple(langkah))


def _urai_diagram_tabel(data, letak):
    _objek(data, letak, ("jenis", "judul", "tipe", "kolom", "baris"), ("sumber", "catatan"))
    kolom = tuple(_teks(k, f"{letak}.kolom {i}") for i, k in enumerate(_daftar(data["kolom"], f"{letak}.kolom"), 1))
    if not 2 <= len(kolom) <= 5:
        raise ValueError(f"{letak}.kolom harus berisi 2 sampai 5 kolom")
    mentah = _daftar(data["baris"], f"{letak}.baris")
    if not mentah:
        raise ValueError(f"{letak}.baris tidak boleh kosong")
    baris = []
    for i, row in enumerate(mentah, 1):
        sel_mentah = _daftar(row, f"{letak}.baris {i}")
        if len(sel_mentah) != len(kolom):
            raise ValueError(f"{letak}.baris {i} harus memiliki {len(kolom)} sel sesuai jumlah kolom")
        sel = []
        for j, s in enumerate(sel_mentah, 1):
            if not isinstance(s, str):
                raise ValueError(f"{letak}.baris {i} kolom {j} harus berupa teks")
            _cek_kontrol(s, f"{letak}.baris {i} kolom {j}")
            sel.append(s.strip())
        baris.append(tuple(sel))
    return DiagramTabel(kolom=kolom, baris=tuple(baris))


PENGURAI_DIAGRAM = {
    "pohon": _urai_diagram_pohon,
    "alur": _urai_diagram_alur,
    "tabel": _urai_diagram_tabel,
}


def _urai_diagram(data, sumber, letak):
    if "tipe" not in data:
        raise ValueError(f"{letak} harus memiliki kolom tipe ({', '.join(TIPE_DIAGRAM)})")
    tipe = _pilihan(data["tipe"], TIPE_DIAGRAM, f"{letak}.tipe")
    isi = PENGURAI_DIAGRAM[tipe](data, letak)
    judul = _teks(data["judul"], f"{letak}.judul")
    return BlokDiagram(judul=judul, isi=isi, sumber=_kode_sumber(data, sumber, letak), catatan=_urai_catatan(data, sumber, letak))


def _urai_halaman_baru(data, _sumber, letak):
    _objek(data, letak, ("jenis",))
    return BlokHalamanBaru()


PENGURAI_BLOK = {
    "hal": _urai_hal,
    "subjudul": _urai_subjudul,
    "bait": _urai_bait,
    "matan": _urai_matan,
    "sela": _urai_sela,
    "hasyiah": _urai_hasyiah,
    "diagram": _urai_diagram,
    "halaman_baru": _urai_halaman_baru,
}


def _urai_blok(daftar, sumber, letak):
    mentah = _daftar(daftar, f"{letak}.blok")
    if not mentah:
        raise ValueError(f"{letak}.blok harus berisi sedikitnya satu blok")
    hasil = []
    for i, item in enumerate(mentah, 1):
        nama = f"{letak}.blok {i}"
        if not isinstance(item, dict):
            raise ValueError(f"{nama} harus berupa objek JSON")
        if "jenis" not in item:
            raise ValueError(f"{nama} harus memiliki kolom jenis")
        jenis = _pilihan(item["jenis"], tuple(PENGURAI_BLOK), f"{nama}.jenis")
        hasil.append(PENGURAI_BLOK[jenis](item, sumber, nama))
    return tuple(hasil)


def _urai_bagian(daftar, sumber):
    mentah = _daftar(daftar, "bagian")
    if not mentah:
        raise ValueError("bagian harus berisi sedikitnya satu bagian")
    hasil = []
    for i, item in enumerate(mentah, 1):
        letak = f"bagian {i}"
        data = _objek(item, letak, ("judul", "blok"), ("jenis", "hal_kitab", "catatan_pangkas", "sumber"))
        judul = _teks(data["judul"], f"{letak}.judul")
        jenis = _pilihan(data["jenis"], JENIS_BAGIAN, f"{letak}.jenis") if "jenis" in data else "kitab"
        hal_kitab = _teks_opsional(data, "hal_kitab", letak)
        catatan_pangkas = _teks_opsional(data, "catatan_pangkas", letak)
        kode = _kode_sumber(data, sumber, letak)
        blok = _urai_blok(data["blok"], sumber, letak)
        hasil.append(Bagian(judul=judul, jenis=jenis, hal_kitab=hal_kitab, catatan_pangkas=catatan_pangkas,
                            sumber=kode, blok=blok))
    return tuple(hasil)


def _baca(jalur: Path) -> Rencana:
    try:
        mentah = json.loads(jalur.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"berkas rencana JSON tidak sah: {e}") from e
    data = _objek(mentah, "rencana", ("judul", "sumber", "bagian"), ("subjudul", "keterangan"))
    judul = _teks(data["judul"], "judul")
    subjudul = _teks_opsional(data, "subjudul", "rencana")
    keterangan = _teks_opsional(data, "keterangan", "rencana")
    sumber = _urai_sumber(data["sumber"])
    bagian = _urai_bagian(data["bagian"], sumber)
    return Rencana(judul=judul, subjudul=subjudul, keterangan=keterangan, sumber=sumber, bagian=bagian)


def _angka_arab(n: int) -> str:
    return str(n).translate(ANGKA_ARAB)


def _css_str(teks: str) -> str:
    return (
        teks.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("<", "\\3c ")
        .replace(">", "\\3e ")
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("\f", " ")
    )


def _format_teks(teks: str) -> str:
    hasil = escape(teks.replace("\r\n", "\n").replace("\r", "\n"))
    for _ in range(5):
        baru = POLA_ANOTASI.sub(lambda m: TAG_ANOTASI[m.group(1)](m.group(2)), hasil)
        if baru == hasil:
            break
        hasil = baru
    return hasil.replace("\n", "<br>")


def _tautan_sumber(kode: tuple[str, ...], jangkar_sumber: dict[str, str], kelas: str = "src-chip") -> str:
    if not kode:
        return ""
    butir = " ".join(f'<a class="{kelas}" href="#{jangkar_sumber[k]}">{escape(k)}</a>' for k in kode)
    return f'<span class="src-list">{butir}</span>'


def _panjang_visual(teks: str) -> int:
    return len(HARAKAT.sub("", teks))


def _gugus_karakter(kata: str) -> list[str]:
    gugus: list[str] = []
    for c in kata:
        if HARAKAT.match(c) and gugus:
            gugus[-1] += c
        else:
            gugus.append(c)
    return gugus


def _pecah_kata_panjang(kata: str, maks_kar: int) -> list[str]:
    if _panjang_visual(kata) <= maks_kar:
        return [kata]
    gugus = _gugus_karakter(kata)
    potongan = []
    for i in range(0, len(gugus), max(1, maks_kar)):
        potongan.append("".join(gugus[i : i + max(1, maks_kar)]))
    return potongan


def _urai_segmen(teks: str) -> list[tuple[str, str]]:
    hasil: list[tuple[str, str]] = []
    pos = 0
    for m in POLA_ANOTASI.finditer(teks):
        if m.start() > pos:
            hasil.append((teks[pos : m.start()], ""))
        tag, isi = m.group(1), m.group(2)
        if tag == "fn":
            isi = f"({isi[1:-1] if isi.startswith('(') and isi.endswith(')') else isi})"
        hasil.append((isi, tag))
        pos = m.end()
    if pos < len(teks):
        hasil.append((teks[pos:], ""))
    return hasil or [(teks, "")]


def _bungkus_segmen(teks: str, maks_kar: int, awalan: str = "") -> list[list[tuple[str, str]]]:
    baris_semua: list[list[tuple[str, str]]] = []
    pertama = True
    for paragraf in teks.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        token_list: list[tuple[str, str]] = []
        if awalan and pertama:
            token_list.append((awalan, ""))
            pertama = False
        for seg, tag in _urai_segmen(paragraf):
            for kata in seg.split():
                for potong in _pecah_kata_panjang(kata, maks_kar):
                    token_list.append((potong, tag))
        if not token_list:
            continue
        baris_ini: list[tuple[str, str]] = []
        lebar_ini = 0
        for kata, tag in token_list:
            lk = _panjang_visual(kata)
            tambahan = lk + (1 if baris_ini else 0)
            if baris_ini and lebar_ini + tambahan > maks_kar:
                baris_semua.append(baris_ini)
                baris_ini = [(kata, tag)]
                lebar_ini = lk
            else:
                if baris_ini:
                    baris_ini.append((" ", ""))
                    lebar_ini += 1
                baris_ini.append((kata, tag))
                lebar_ini += lk
        if baris_ini:
            baris_semua.append(baris_ini)
    return baris_semua or [[(awalan + teks if awalan else teks, "")]]


def _render_tspan(segmen: list[tuple[str, str]]) -> str:
    bagian = []
    for teks, tag in segmen:
        aman = escape(teks)
        if tag == "hl":
            bagian.append(f'<tspan fill="#8a5a00" font-weight="600">{aman}</tspan>')
        elif tag == "hl2":
            bagian.append(f'<tspan fill="#165541" font-weight="600">{aman}</tspan>')
        elif tag == "ul":
            bagian.append(f'<tspan fill="#184a8c" text-decoration="underline">{aman}</tspan>')
        elif tag == "ur":
            bagian.append(f'<tspan fill="#8f1d28" text-decoration="underline">{aman}</tspan>')
        elif tag in ("o", "b"):
            bagian.append(f'<tspan font-weight="600">{aman}</tspan>')
        elif tag == "fn":
            bagian.append(f'<tspan fill="#9e2932" font-weight="600" font-size="0.8em">{aman}</tspan>')
        else:
            bagian.append(aman)
    return "".join(bagian)


def _svg_pohon(pohon: DiagramPohon, id_prefix: str) -> str:
    lebar = 700
    n = len(pohon.cabang)
    pad_x = 8
    gap = 14
    box_w = (lebar - 2 * pad_x - (n - 1) * gap) / n

    akar_fs = 16.5
    akar_polos = POLA_ANOTASI.sub(r"\2", pohon.akar)
    akar_w = min(540, max(250, int(_panjang_visual(akar_polos) * 11.2) + 58))
    akar_maks = max(16, int((akar_w - 36) / 11.0))
    akar_baris = _bungkus_segmen(pohon.akar, akar_maks)
    akar_lh = 24
    akar_h = 22 + len(akar_baris) * akar_lh
    akar_x = (lebar - akar_w) / 2
    akar_y = 10

    judul_fs = 15.0 if n <= 3 else 13.6
    isi_fs = 13.8 if n <= 3 else 12.8
    judul_lh = 22 if n <= 3 else 20
    isi_lh = 21.5 if n <= 3 else 19.5
    judul_maks = max(9, int((box_w - 22) / (judul_fs * 0.72)))
    isi_maks = max(9, int((box_w - 24) / (isi_fs * 0.72)))

    susunan = []
    for c in pohon.cabang:
        j_baris = _bungkus_segmen(c.judul, judul_maks)
        b_baris: list[list[tuple[str, str]]] = []
        for item in c.isi:
            b_baris.extend(_bungkus_segmen(item, isi_maks, awalan="•"))
        kepala_h = 15 + len(j_baris) * judul_lh
        badan_h = (13 + len(b_baris) * isi_lh + 9) if b_baris else 10
        susunan.append((c, j_baris, b_baris, kepala_h, kepala_h + badan_h))

    cabang_y = akar_y + akar_h + 40
    cabang_h = max(x[4] for x in susunan)
    tinggi = int(cabang_y + cabang_h + 12)

    defs = []
    panah = []
    kotak = []
    rx, ry = lebar / 2, akar_y + akar_h
    mid_y = ry + 20

    for idx, (c, j_baris, b_baris, kepala_h, _tinggi_c) in enumerate(susunan):
        tinta, tepi, latar, kepala_bg = PALET[c.warna]
        bx = lebar - pad_x - (idx + 1) * box_w - idx * gap
        cx = bx + box_w / 2
        m_id = f"arr-{id_prefix}-{idx}"
        defs.append(
            f'<marker id="{m_id}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">'
            f'<path d="M 1 1 L 8 5 L 1 9 z" fill="{tepi}"/></marker>'
        )
        panah.append(
            f'<path d="M {rx:.1f} {ry:.1f} C {rx:.1f} {mid_y:.1f}, {cx:.1f} {mid_y:.1f}, {cx:.1f} {cabang_y - 3:.1f}" '
            f'fill="none" stroke="{tepi}" stroke-width="1.7" marker-end="url(#{m_id})"/>'
        )
        r = 8
        kepala_path = (
            f"M {bx:.1f} {cabang_y + r:.1f} Q {bx:.1f} {cabang_y:.1f} {bx + r:.1f} {cabang_y:.1f} "
            f"L {bx + box_w - r:.1f} {cabang_y:.1f} Q {bx + box_w:.1f} {cabang_y:.1f} {bx + box_w:.1f} {cabang_y + r:.1f} "
            f"L {bx + box_w:.1f} {cabang_y + kepala_h:.1f} L {bx:.1f} {cabang_y + kepala_h:.1f} Z"
        )
        elemen = [
            f'<rect x="{bx:.1f}" y="{cabang_y:.1f}" width="{box_w:.1f}" height="{cabang_h:.1f}" rx="{r}" '
            f'fill="{latar}" stroke="{tepi}" stroke-width="1.4"/>',
            f'<path d="{kepala_path}" fill="{kepala_bg}"/>',
            f'<line x1="{bx:.1f}" y1="{cabang_y + kepala_h:.1f}" x2="{bx + box_w:.1f}" y2="{cabang_y + kepala_h:.1f}" '
            f'stroke="{tepi}" stroke-width="1.0" stroke-opacity="0.55"/>',
        ]
        for li, seg_j in enumerate(j_baris):
            ty = cabang_y + 22 + li * judul_lh
            elemen.append(
                f'<text x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle" direction="rtl" '
                f'font-family="Playpen Sans Arabic" font-weight="600" font-size="{judul_fs}" fill="{tinta}">'
                f"{_render_tspan(seg_j)}</text>"
            )
        teks_x = bx + box_w - 11
        for li, seg_b in enumerate(b_baris):
            ty = cabang_y + kepala_h + 22 + li * isi_lh
            elemen.append(
                f'<text x="{teks_x:.1f}" y="{ty:.1f}" text-anchor="start" direction="rtl" '
                f'font-family="Playpen Sans Arabic" font-weight="400" font-size="{isi_fs}" fill="#1f2328">'
                f"{_render_tspan(seg_b)}</text>"
            )
        kotak.append("".join(elemen))

    akar_teks = []
    for li, seg_a in enumerate(akar_baris):
        ty = akar_y + 27 + li * akar_lh
        akar_teks.append(
            f'<text x="{rx:.1f}" y="{ty:.1f}" text-anchor="middle" direction="rtl" '
            f'font-family="Playpen Sans Arabic" font-weight="600" font-size="{akar_fs}" fill="#9e2932">'
            f"{_render_tspan(seg_a)}</text>"
        )

    return (
        f'<svg class="svg-pohon" viewBox="0 0 {lebar} {tinggi}" xmlns="http://www.w3.org/2000/svg">'
        f"<defs>{''.join(defs)}</defs>"
        f"{''.join(panah)}"
        f'<rect x="{akar_x:.1f}" y="{akar_y:.1f}" width="{akar_w:.1f}" height="{akar_h:.1f}" rx="9" '
        f'fill="#faf3d8" stroke="#9e2932" stroke-width="1.7"/>'
        f"{''.join(akar_teks)}"
        f"{''.join(kotak)}"
        "</svg>"
    )


def _html_alur(alur: DiagramAlur, _id_prefix: str) -> str:
    padat = len(alur.langkah) >= 5
    panah_w = 16 if padat else 22
    potongan = []
    for i, lk in enumerate(alur.langkah, 1):
        tinta, tepi, latar, kepala_bg = PALET[lk.warna]
        if i > 1:
            potongan.append(
                '<div class="alur-panah" aria-hidden="true">'
                f'<svg viewBox="0 0 24 16" width="{panah_w}" height="15" xmlns="http://www.w3.org/2000/svg">'
                '<line x1="22" y1="8" x2="5" y2="8" stroke="#6b5e50" stroke-width="1.8"/>'
                '<path d="M 9 3 L 2 8 L 9 13" fill="none" stroke="#6b5e50" stroke-width="1.8" '
                'stroke-linecap="round" stroke-linejoin="round"/>'
                "</svg></div>"
            )
        isi_html = f'<div class="alur-isi">{_format_teks(lk.isi)}</div>' if lk.isi else ""
        potongan.append(
            f'<div class="alur-langkah" style="background:{latar};border-color:{tepi}">'
            f'<div class="alur-kepala" style="background:{kepala_bg};color:{tinta}">'
            f'<span class="alur-no" style="background:{tepi}">{_angka_arab(i)}</span>'
            f'<span class="alur-judul">{_format_teks(lk.judul)}</span></div>'
            f"{isi_html}</div>"
        )
    kelas = "alur-wadah alur-padat" if padat else "alur-wadah"
    return f'<div class="{kelas}">{"".join(potongan)}</div>'


def _html_tabel(tabel: DiagramTabel, _id_prefix: str) -> str:
    kepala = "".join(f"<th>{_format_teks(k)}</th>" for k in tabel.kolom)
    badan = "".join(
        "<tr>" + "".join(f"<td>{_format_teks(s)}</td>" for s in baris) + "</tr>"
        for baris in tabel.baris
    )
    return f'<table class="diag-tabel"><thead><tr>{kepala}</tr></thead><tbody>{badan}</tbody></table>'


PERENDER_DIAGRAM = {
    DiagramPohon: _svg_pohon,
    DiagramAlur: _html_alur,
    DiagramTabel: _html_tabel,
}


def _format_blok_catatan(teks: str) -> str:
    baris_list = [b.strip() for b in teks.replace("\r\n", "\n").replace("\r", "\n").split("\n") if b.strip()]
    bagian: list[str] = []
    butir_aktif: list[str] = []

    def tutup_butir() -> None:
        if butir_aktif:
            isi = "".join(f"<li>{_format_teks(x)}</li>" for x in butir_aktif)
            bagian.append(f'<ul class="catatan-butir">{isi}</ul>')
            butir_aktif.clear()

    for b in baris_list:
        if b.startswith(("• ", "- ", "– ")):
            butir_aktif.append(b[2:].strip())
        else:
            tutup_butir()
            bagian.append(f'<p class="catatan-p">{_format_teks(b)}</p>')
    tutup_butir()
    return "".join(bagian)


def _render_catatan(daftar: tuple[Catatan, ...], jangkar_sumber: dict[str, str]) -> str:
    if not daftar:
        return ""
    kartu = []
    for c in daftar:
        src = _tautan_sumber(c.sumber, jangkar_sumber, "src-chip src-mini")
        if c.label or src:
            label_html = f'<span class="catatan-label">{escape(c.label)}</span>' if c.label else "<span></span>"
            kepala = f'<div class="catatan-kepala">{label_html}{src}</div>'
        else:
            kepala = ""
        kartu.append(
            f'<aside class="catatan-kartu warna-{c.warna}">'
            f"{kepala}"
            f'<div class="catatan-isi">{_format_blok_catatan(c.isi)}</div>'
            "</aside>"
        )
    tata = "catatan-ganda" if len(daftar) >= 2 else "catatan-tunggal"
    return f'<div class="catatan-bawah {tata}">{"".join(kartu)}</div>'


def _bungkus_baris(utama_html: str, catatan: tuple[Catatan, ...], jangkar_sumber: dict[str, str],
                   ekstra_kelas: str = "") -> str:
    catatan_html = _render_catatan(catatan, jangkar_sumber)
    kelas = f"baris {ekstra_kelas}".strip()
    return f'<div class="{kelas}">{utama_html}{catatan_html}</div>'


def _render_hal(blok: BlokHal, ctx: dict) -> str:
    utama = f'<div class="hal-penanda"><span>ص {escape(blok.nomor)}</span></div>'
    return _bungkus_baris(utama, (), ctx["jangkar_sumber"], "tahan-sesudah")


def _render_subjudul(blok: BlokSubjudul, ctx: dict) -> str:
    sub_id = ctx["sub_id"]()
    ctx["tanda"].append((sub_id, blok.teks))
    src = _tautan_sumber(blok.sumber, ctx["jangkar_sumber"])
    utama = f'<h3 class="subjudul" id="{sub_id}"><span>{_format_teks(blok.teks)}</span>{src}</h3>'
    return _bungkus_baris(utama, (), ctx["jangkar_sumber"], "tahan-sesudah")


def _render_bait(blok: BlokBait, ctx: dict) -> str:
    nomor = f'<span class="bait-no">{escape(blok.nomor)}</span>' if blok.nomor else '<span class="bait-no"></span>'
    utama = (
        f'<div class="bait bait-{blok.gaya}">'
        f"{nomor}"
        f'<span class="syatr-kanan">{_format_teks(blok.kanan)}</span>'
        f'<span class="syatr-kiri">{_format_teks(blok.kiri)}</span>'
        "</div>"
    )
    kelas = "tahan-dalam tahan-sesudah" if blok.gaya == "alfiyah" else "tahan-dalam"
    return _bungkus_baris(utama, blok.catatan, ctx["jangkar_sumber"], kelas)


def _render_matan(blok: BlokMatan, ctx: dict) -> str:
    kelas_p = "matan" if ctx["mode_kitab"] else "matan-lembar"
    utama = f'<p class="{kelas_p}">{_format_teks(blok.teks)}</p>'
    tahan = "tahan-dalam" if blok.catatan and len(blok.teks) < 420 else ""
    return _bungkus_baris(utama, blok.catatan, ctx["jangkar_sumber"], tahan)


def _render_sela(blok: BlokSela, ctx: dict) -> str:
    src = _tautan_sumber(blok.sumber, ctx["jangkar_sumber"])
    kepala = ""
    if blok.label or src:
        label_html = f'<span class="sela-label">{escape(blok.label)}</span>' if blok.label else "<span></span>"
        kepala = f'<div class="sela-kepala">{label_html}{src}</div>'
    isi_html = f'<p class="sela-isi">{_format_teks(blok.isi)}</p>' if blok.isi else ""
    butir_html = ""
    if blok.butir:
        item = "".join(f"<li>{_format_teks(b)}</li>" for b in blok.butir)
        butir_html = f'<ul class="sela-butir">{item}</ul>'
    utama = f'<div class="sela warna-{blok.warna}">{kepala}{isi_html}{butir_html}</div>'
    return _bungkus_baris(utama, blok.catatan, ctx["jangkar_sumber"], "tahan-dalam")


def _render_hasyiah(blok: BlokHasyiah, ctx: dict) -> str:
    item = "".join(
        f'<p class="hasyiah-item"><span class="hasyiah-no">({escape(b.nomor)})</span> {_format_teks(b.teks)}</p>'
        for b in blok.butir
    )
    pangkas = f'<p class="hasyiah-pangkas">{_format_teks(blok.catatan_pangkas)}</p>' if blok.catatan_pangkas else ""
    utama = f'<div class="hasyiah"><div class="hasyiah-garis"></div>{item}{pangkas}</div>'
    return _bungkus_baris(utama, (), ctx["jangkar_sumber"], "tahan-dalam")


def _render_diagram(blok: BlokDiagram, ctx: dict) -> str:
    sub_id = ctx["sub_id"]()
    ctx["tanda"].append((sub_id, blok.judul))
    src = _tautan_sumber(blok.sumber, ctx["jangkar_sumber"])
    badan = PERENDER_DIAGRAM[type(blok.isi)](blok.isi, sub_id)
    utama = (
        f'<figure class="diagram-kartu" id="{sub_id}">'
        f'<figcaption class="diagram-kepala"><span>{_format_teks(blok.judul)}</span>{src}</figcaption>'
        f'<div class="diagram-isi">{badan}</div>'
        "</figure>"
    )
    return _bungkus_baris(utama, blok.catatan, ctx["jangkar_sumber"], "tahan-dalam")


def _render_halaman_baru(_blok: BlokHalamanBaru, _ctx: dict) -> str:
    return '<div class="halaman-baru" aria-hidden="true"></div>'


PERENDER_BLOK = {
    BlokHal: _render_hal,
    BlokSubjudul: _render_subjudul,
    BlokBait: _render_bait,
    BlokMatan: _render_matan,
    BlokSela: _render_sela,
    BlokHasyiah: _render_hasyiah,
    BlokDiagram: _render_diagram,
    BlokHalamanBaru: _render_halaman_baru,
}


def _css_font() -> str:
    amiri_r = (FONT / "Amiri-Regular.ttf").resolve().as_uri()
    amiri_b = (FONT / "Amiri-Bold.ttf").resolve().as_uri()
    playpen_r = (FONT / "PlaypenSansArabic-Regular.ttf").resolve().as_uri()
    playpen_s = (FONT / "PlaypenSansArabic-SemiBold.ttf").resolve().as_uri()
    return f"""
@font-face {{ font-family: 'Amiri'; src: url('{amiri_r}') format('truetype'); font-weight: 400; font-style: normal; }}
@font-face {{ font-family: 'Amiri'; src: url('{amiri_b}') format('truetype'); font-weight: 700; font-style: normal; }}
@font-face {{ font-family: 'Playpen Sans Arabic'; src: url('{playpen_r}') format('truetype'); font-weight: 400; font-style: normal; }}
@font-face {{ font-family: 'Playpen Sans Arabic'; src: url('{playpen_s}') format('truetype'); font-weight: 600; font-style: normal; }}
"""


def _css_halaman(rencana: Rencana) -> str:
    sub_bawah = _css_str(rencana.subjudul or rencana.judul)
    aturan = [
        """
@page {
  size: A4;
  margin: 22.5mm 15.5mm 18.5mm 15.5mm;
}
@page fihris {
  margin: 18mm 16mm 18mm 16mm;
  @bottom-center {
    content: counter(page, arabic-indic);
    font-family: 'Amiri';
    font-size: 10pt;
    color: #9e2932;
  }
}
@page sumber {
  @top-right {
    content: "مصادر المحاضرات";
    font-family: 'Amiri';
    font-weight: 700;
    font-size: 11.5pt;
    color: #9e2932;
    vertical-align: bottom;
    padding-bottom: 11pt;
  }
  @top-left {
    content: counter(page, arabic-indic);
    font-family: 'Amiri';
    font-weight: 700;
    font-size: 10.5pt;
    color: #9e2932;
    vertical-align: bottom;
    padding-bottom: 11pt;
    padding-left: 8pt;
  }
  @bottom-right {
    content: \"""" + sub_bawah + """\";
    font-family: 'Amiri';
    font-size: 8.8pt;
    color: #6b5e50;
  }
}
"""
    ]
    for i, bag in enumerate(rencana.bagian, 1):
        judul_css = _css_str(bag.judul)
        if bag.jenis == "kitab":
            hal_bawah = _css_str(f"الأصل: ص {bag.hal_kitab}") if bag.hal_kitab else ""
            aturan.append(f"""
@page kitab-{i} {{
  @top-right {{
    content: "{judul_css}";
    font-family: 'Amiri';
    font-weight: 700;
    font-size: 11.5pt;
    color: #9e2932;
    vertical-align: bottom;
    padding-bottom: 11pt;
  }}
  @top-left {{
    content: counter(page, arabic-indic);
    font-family: 'Amiri';
    font-weight: 700;
    font-size: 10.5pt;
    color: #9e2932;
    vertical-align: bottom;
    padding-bottom: 11pt;
    padding-left: 8pt;
  }}
  @bottom-right {{
    content: "{sub_bawah}";
    font-family: 'Amiri';
    font-size: 8.8pt;
    color: #6b5e50;
  }}
  @bottom-left {{
    content: "{hal_bawah}";
    font-family: 'Amiri';
    font-size: 8.8pt;
    color: #6b5e50;
  }}
}}
""")
        else:
            aturan.append(f"""
@page lembar-{i} {{
  background: #fdfaf2;
  @top-right {{
    content: "{judul_css}";
    font-family: 'Playpen Sans Arabic';
    font-weight: 600;
    font-size: 10.5pt;
    color: #184a8c;
    vertical-align: bottom;
    padding-bottom: 11pt;
  }}
  @top-left {{
    content: counter(page, arabic-indic);
    font-family: 'Playpen Sans Arabic';
    font-weight: 600;
    font-size: 10pt;
    color: #184a8c;
    vertical-align: bottom;
    padding-bottom: 11pt;
    padding-left: 8pt;
  }}
  @bottom-right {{
    content: "{sub_bawah}";
    font-family: 'Amiri';
    font-size: 8.8pt;
    color: #6b5e50;
  }}
}}
""")
    return "".join(aturan)


CSS_UTAMA = """
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  color: #1b1917;
  font-family: 'Amiri', serif;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
a { text-decoration: none; color: inherit; }

/* Fihris */
.hal-fihris { page: fihris; }
.fihris-sampul {
  background: linear-gradient(180deg, #faf3d8 0%, #f5ebca 100%);
  border: 1.4px solid #9e8a6b;
  border-radius: 9px;
  padding: 18px 22px;
  text-align: center;
  margin-bottom: 18px;
}
.fihris-judul {
  margin: 0 0 6px;
  font-family: 'Amiri', serif;
  font-size: 22pt;
  font-weight: 700;
  color: #9e2932;
  line-height: 1.35;
}
.fihris-subjudul {
  margin: 0;
  font-size: 13pt;
  color: #4a4036;
  line-height: 1.5;
}
.fihris-ket {
  margin: 0 0 18px;
  padding: 10px 14px;
  background: #f8f5ec;
  border-right: 3px solid #9e2932;
  border-radius: 5px;
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 9.8pt;
  line-height: 1.7;
  color: #3a342e;
}
.fihris-kepala {
  margin: 0 0 10px;
  padding-bottom: 5px;
  border-bottom: 2px double #9e2932;
  font-size: 15pt;
  font-weight: 700;
  color: #9e2932;
}
.fihris-daftar { display: flex; flex-direction: column; gap: 6px; }
.fihris-baris {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 5px;
  background: #fffdf8;
  border: 0.7px solid #ebe2d2;
  break-inside: avoid;
}
.fihris-no {
  font-weight: 700;
  color: #9e2932;
  min-width: 20px;
  text-align: center;
  font-size: 11.5pt;
}
.fihris-ikon {
  display: inline-block;
  width: 7px;
  height: 7px;
  background: #9e2932;
  transform: rotate(45deg);
  vertical-align: middle;
}
.fihris-teks {
  font-size: 12.5pt;
  font-weight: 700;
  color: #1b1917;
}
.fihris-tag {
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 8.2pt;
  padding: 1px 7px;
  border-radius: 10px;
  white-space: nowrap;
}
.fihris-tag-kitab { background: #faf3d8; color: #7c4d12; border: 0.6px solid #d5c198; }
.fihris-tag-lembar { background: #e8f1fb; color: #184a8c; border: 0.6px solid #b5cee9; }
.fihris-tag-sumber { background: #f8e5e7; color: #8f1d28; border: 0.6px solid #dfadb3; }
.fihris-asal {
  font-size: 9.5pt;
  color: #6b5e50;
  white-space: nowrap;
}
.fihris-titik {
  flex: 1;
  min-width: 16px;
  border-bottom: 1.2px dotted #b5a690;
  margin-bottom: 4px;
}
.fihris-hal {
  font-weight: 700;
  font-size: 11.5pt;
  color: #9e2932;
  min-width: 26px;
  text-align: center;
  padding: 0 5px;
  background: #faf3d8;
  border: 0.7px solid #d3bfa0;
  border-radius: 3px;
}

/* Bagian Kitab & Lembar */
.bagian { break-before: page; }
.bab-spanduk {
  background: linear-gradient(180deg, #faf3d8 0%, #f5ebca 100%);
  border: 1.2px solid #9e8a6b;
  border-radius: 7px;
  padding: 10px 18px;
  text-align: center;
  margin: 0 0 10px;
  break-after: avoid;
  break-inside: avoid;
}
.bab-spanduk h1 {
  margin: 0;
  font-family: 'Amiri', serif;
  font-size: 20pt;
  font-weight: 700;
  color: #9e2932;
  line-height: 1.35;
}
.bab-meta {
  margin-top: 5px;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 9.5pt;
  color: #6b5e50;
}
.bab-pangkas {
  margin: 0 0 10px;
  padding: 5px 10px;
  background: #faf7ef;
  border-right: 2.5px solid #9e8a6b;
  border-radius: 4px;
  font-size: 9.5pt;
  color: #5c5145;
  line-height: 1.55;
  break-after: avoid;
}
.lembar-kepala {
  margin: 0 0 12px;
  padding: 10px 14px;
  background: #eef4fc;
  border: 1.1px solid #9eb8d9;
  border-right: 4px solid #184a8c;
  border-radius: 7px;
  break-after: avoid;
  break-inside: avoid;
}
.lembar-kepala h1 {
  margin: 0;
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 16pt;
  font-weight: 600;
  color: #184a8c;
  line-height: 1.45;
}
.lembar-meta {
  margin-top: 4px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 9pt;
  color: #465a73;
}

/* Alur satu kolom penuh selebar kitab asli */
.baris { padding-top: 3pt; margin-bottom: 4pt; }
.tahan-dalam { break-inside: avoid; }
.tahan-sesudah { break-after: avoid; }
.grup-jaga { break-inside: avoid; }
.halaman-baru { break-before: page; height: 0; }

/* Penanda halaman kitab */
.hal-penanda { margin: 4px 0 2px; }
.hal-penanda span {
  display: inline-block;
  font-family: 'Amiri', serif;
  font-size: 9.2pt;
  font-weight: 700;
  color: #7c4d12;
  background: #faf6ec;
  border: 0.8px solid #d8c8b4;
  border-radius: 10px;
  padding: 0 8px;
  line-height: 1.5;
}

/* Subjudul */
.subjudul {
  margin: 8px 0 3px;
  padding-bottom: 2px;
  border-bottom: 1px solid #e4d2c2;
  font-family: 'Amiri', serif;
  font-size: 14.2pt;
  font-weight: 700;
  color: #9e2932;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.bagian-lembar .subjudul {
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 12.5pt;
  font-weight: 600;
  color: #184a8c;
  border-bottom-color: #c2d4eb;
}

/* Bait Alfiyah & Syahid */
.bait {
  display: grid;
  grid-template-columns: auto 1fr 1fr;
  gap: 4px 14px;
  align-items: baseline;
  padding: 5px 10px;
  border-radius: 5px;
  break-inside: avoid;
}
.bait-alfiyah {
  font-family: 'Amiri', serif;
  font-size: 14pt;
  font-weight: 700;
  color: #9e2932;
  background: #fdf9f0;
  border: 0.7px solid #e6d7b9;
}
.bait-syahid {
  font-family: 'Amiri', serif;
  font-size: 12.6pt;
  font-weight: 400;
  color: #222222;
  margin-inline: 18px;
  background: #f9f8f6;
  border-right: 2px solid #9e8a6b;
}
.bait-no {
  font-size: 9.8pt;
  color: #7c6855;
  font-weight: 700;
  white-space: nowrap;
}
.syatr-kanan { text-align: right; }
.syatr-kiri { text-align: left; }

/* Matan + anotasi sebaris */
.matan {
  margin: 0;
  padding-top: 4pt;
  padding-bottom: 2pt;
  font-family: 'Amiri', serif;
  font-size: 14pt;
  line-height: 1.85;
  text-align: justify;
  text-indent: 18px;
  color: #1b1917;
  orphans: 2;
  widows: 2;
}
.matan-lembar {
  margin: 0;
  padding-top: 3pt;
  padding-bottom: 2pt;
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 11.4pt;
  line-height: 1.8;
  color: #1f2328;
  orphans: 2;
  widows: 2;
}
.hl { background: rgba(255, 232, 105, 0.50); padding: 0 2px; border-radius: 2px; }
.hl2 { background: rgba(182, 240, 206, 0.50); padding: 0 2px; border-radius: 2px; }
.ul { text-decoration: underline wavy #1c539e; text-decoration-thickness: 1.2px; text-underline-offset: 4px; }
.ur { text-decoration: underline solid #b22430; text-decoration-thickness: 1.5px; text-underline-offset: 4px; }
.o {
  border: 1.2px solid #1c539e;
  border-radius: 45% 55% 48% 52% / 55% 45% 55% 45%;
  padding: 0 5px;
  display: inline-block;
  line-height: 1.45;
}
.fn { color: #9e2932; font-size: 0.72em; font-weight: 700; vertical-align: super; padding: 0 1px; }

/* Catatan coretan tangan langsung di bawah blok */
.catatan-bawah {
  margin-top: 6px;
}
.catatan-ganda {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  align-items: stretch;
}
.catatan-ganda > .catatan-kartu:last-child:nth-child(odd) {
  grid-column: 1 / -1;
}
.catatan-kartu {
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 10.8pt;
  line-height: 1.7;
  padding: 7px 12px;
  border-radius: 6px;
  border: 0.8px solid transparent;
  border-right-width: 3px;
  break-inside: avoid;
}
.catatan-kepala {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.catatan-label { font-weight: 600; font-size: 11pt; }
.catatan-isi { color: #1f2328; }
.catatan-p { margin: 0 0 3px; }
.catatan-p:last-child { margin-bottom: 0; }
.catatan-butir { margin: 2px 0 3px; padding: 0 17px 0 0; }
.catatan-butir:last-child { margin-bottom: 0; }
.catatan-butir li { margin-bottom: 3px; }
.catatan-butir li:last-child { margin-bottom: 0; }

/* Kotak sela */
.sela {
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 11.2pt;
  line-height: 1.75;
  padding: 9px 13px;
  border-radius: 6px;
  border: 0.9px solid transparent;
  border-right-width: 3.2px;
  break-inside: avoid;
}
.sela-kepala {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.sela-label { font-weight: 600; font-size: 11.6pt; }
.sela-isi { margin: 0; color: #1f2328; }
.sela-butir { margin: 4px 0 0; padding: 0 19px 0 0; color: #1f2328; }
.sela-butir li {
  margin-bottom: 6px;
  padding-bottom: 5px;
  border-bottom: 0.6px dashed rgba(24, 40, 64, 0.12);
}
.sela-butir li:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }

/* Warna catatan */
.warna-biru { background: #f0f5fc; border-color: #c5d9f1; border-right-color: #184a8c; color: #184a8c; }
.warna-biru strong { color: #113463; font-weight: 600; }
.warna-merah { background: #fdf2f3; border-color: #f0c9cd; border-right-color: #8f1d28; color: #8f1d28; }
.warna-merah strong { color: #75151f; font-weight: 600; }
.warna-hijau { background: #eff8f4; border-color: #bfe3d3; border-right-color: #165541; color: #165541; }
.warna-hijau strong { color: #0f4534; font-weight: 600; }

/* Chip sumber */
.src-list { display: inline-flex; flex-wrap: wrap; gap: 4px; }
.src-chip {
  display: inline-block;
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 7.8pt;
  font-weight: 600;
  color: #184a8c;
  background: #e6effa;
  border: 0.6px solid #b5cde8;
  border-radius: 9px;
  padding: 0 6px;
  line-height: 1.5;
  white-space: nowrap;
}
.src-mini { font-size: 7.2pt; padding: 0 5px; }

/* Hasyiah */
.hasyiah {
  margin-top: 4px;
  padding-top: 2px;
  font-family: 'Amiri', serif;
  font-size: 10pt;
  line-height: 1.6;
  color: #3a342e;
  break-inside: avoid;
}
.hasyiah-garis {
  width: 38%;
  border-top: 0.9px solid #9e2932;
  margin-bottom: 4px;
}
.hasyiah-item { margin: 0 0 2px; text-align: justify; }
.hasyiah-no { color: #9e2932; font-weight: 700; margin-left: 2px; }
.hasyiah-pangkas { margin: 3px 0 0; font-size: 9pt; color: #6b5e50; }

/* Diagram */
.diagram-kartu {
  margin: 6px 0;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #d5cfc2;
  border-radius: 8px;
  break-inside: avoid;
}
.diagram-kepala {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  padding-bottom: 5px;
  border-bottom: 0.8px dashed #d5cfc2;
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 11.8pt;
  font-weight: 600;
  color: #184a8c;
}
.svg-pohon { display: block; width: 100%; height: auto; }

/* Diagram Alur */
.alur-wadah {
  display: flex;
  flex-wrap: nowrap;
  align-items: stretch;
  justify-content: center;
  gap: 5px;
}
.alur-langkah {
  flex: 1 1 0;
  min-width: 0;
  border: 1.3px solid;
  border-radius: 7px;
  overflow: hidden;
  font-family: 'Playpen Sans Arabic', sans-serif;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.alur-kepala {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 8px;
  font-size: 10.8pt;
  font-weight: 600;
  line-height: 1.45;
}
.alur-judul {
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.alur-no {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 19px;
  height: 19px;
  margin-top: 2px;
  border-radius: 50%;
  color: #ffffff;
  font-size: 9.2pt;
  flex-shrink: 0;
}
.alur-isi {
  padding: 7px 9px;
  font-size: 10.4pt;
  line-height: 1.6;
  color: #1f2328;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.alur-padat { gap: 3px; }
.alur-padat .alur-kepala { padding: 4px 6px; font-size: 9.8pt; gap: 4px; }
.alur-padat .alur-no { min-width: 17px; height: 17px; font-size: 8.4pt; }
.alur-padat .alur-isi { padding: 5px 7px; font-size: 9.3pt; line-height: 1.52; }
.alur-panah {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

/* Diagram Tabel */
.diag-tabel {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 11pt;
  line-height: 1.65;
  border: 1.1px solid #9eb2c9;
  border-radius: 7px;
  overflow: hidden;
}
.diag-tabel th {
  background: #e8f0fa;
  color: #184a8c;
  font-size: 11.2pt;
  font-weight: 600;
  padding: 7px 11px;
  text-align: right;
  border-bottom: 1.1px solid #9eb2c9;
  border-left: 0.7px solid #c9d8e8;
}
.diag-tabel th:last-child, .diag-tabel td:last-child { border-left: none; }
.diag-tabel td {
  padding: 7px 11px;
  text-align: right;
  color: #1f2328;
  border-bottom: 0.7px dashed #d2dce8;
  border-left: 0.7px solid #dfe7f0;
  vertical-align: top;
}
.diag-tabel tr { break-inside: avoid; }
.diag-tabel tbody tr:nth-child(even) td { background: #f8fbff; }
.diag-tabel tbody tr:last-child td { border-bottom: none; }

/* Sumber (ringkas muat 1 halaman tanpa URL mentah) */
.hal-sumber { page: sumber; break-before: page; }
.sumber-judul {
  margin: 0 0 9px;
  padding-bottom: 4px;
  border-bottom: 2px double #9e2932;
  font-size: 15pt;
  font-weight: 700;
  color: #9e2932;
}
.sumber-daftar { display: flex; flex-direction: column; gap: 4px; }
.sumber-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 4.5px 10px;
  background: #fffdf8;
  border: 0.7px solid #e3dacc;
  border-right: 3px solid #9e2932;
  border-radius: 5px;
  break-inside: avoid;
}
.sumber-kode {
  font-family: 'Playpen Sans Arabic', sans-serif;
  font-size: 8.8pt;
  font-weight: 600;
  color: #9e2932;
  background: #faf3d8;
  border: 0.7px solid #d5c198;
  border-radius: 4px;
  padding: 0 6px;
  min-width: 28px;
  text-align: center;
  white-space: nowrap;
}
.sumber-badan { flex: 1; min-width: 0; }
.sumber-nama { font-size: 11.4pt; font-weight: 700; color: #1b1917; line-height: 1.45; }

/* Probe khusus putaran pertama untuk menangkap halaman semua jangkar */
.probe-jangkar { break-before: page; font-size: 8pt; }
"""


def _render_fihris(rencana: Rencana, nomor_halaman: dict[str, int]) -> str:
    sub = f'<p class="fihris-subjudul">{_format_teks(rencana.subjudul)}</p>' if rencana.subjudul else ""
    ket = f'<div class="fihris-ket">{_format_teks(rencana.keterangan)}</div>' if rencana.keterangan else ""
    baris = []
    for i, bag in enumerate(rencana.bagian, 1):
        kunci = f"bagian-{i}"
        hal = _angka_arab(nomor_halaman[kunci]) if kunci in nomor_halaman else "٠٠"
        tag_kelas = "fihris-tag-kitab" if bag.jenis == "kitab" else "fihris-tag-lembar"
        tag_teks = "نص الكتاب" if bag.jenis == "kitab" else "ملخص وملاحظات"
        asal = f'<span class="fihris-asal">ص {escape(bag.hal_kitab)}</span>' if bag.hal_kitab else ""
        baris.append(
            f'<a class="fihris-baris" href="#{kunci}">'
            f'<span class="fihris-no">{_angka_arab(i)}</span>'
            f'<span class="fihris-teks">{_format_teks(bag.judul)}</span>'
            f'<span class="fihris-tag {tag_kelas}">{tag_teks}</span>'
            f"{asal}"
            '<span class="fihris-titik"></span>'
            f'<span class="fihris-hal">{hal}</span>'
            "</a>"
        )
    if rencana.sumber:
        hal_s = _angka_arab(nomor_halaman["sumber"]) if "sumber" in nomor_halaman else "٠٠"
        baris.append(
            '<a class="fihris-baris" href="#sumber">'
            '<span class="fihris-no"><span class="fihris-ikon"></span></span>'
            '<span class="fihris-teks">مصادر المحاضرات</span>'
            '<span class="fihris-tag fihris-tag-sumber">فهرس المحاضرات</span>'
            '<span class="fihris-titik"></span>'
            f'<span class="fihris-hal">{hal_s}</span>'
            "</a>"
        )
    return (
        '<section class="hal-fihris" id="fihris">'
        f'<header class="fihris-sampul"><h1 class="fihris-judul">{_format_teks(rencana.judul)}</h1>{sub}</header>'
        f"{ket}"
        '<h2 class="fihris-kepala">فهرس المقرر</h2>'
        f'<nav class="fihris-daftar">{"".join(baris)}</nav>'
        "</section>"
    )


def _kepala_menempel(blok: Blok) -> bool:
    return isinstance(blok, (BlokHal, BlokSubjudul)) or (isinstance(blok, BlokBait) and blok.gaya == "alfiyah")


def _kelompokkan_blok(daftar: tuple[Blok, ...]) -> list[tuple[list[Blok], bool]]:
    grup: list[tuple[list[Blok], bool]] = []
    i = 0
    n = len(daftar)
    while i < n:
        if _kepala_menempel(daftar[i]):
            bag: list[Blok] = []
            while i < n and _kepala_menempel(daftar[i]):
                bag.append(daftar[i])
                i += 1
            if i < n and not isinstance(daftar[i], BlokHalamanBaru):
                berikut = daftar[i]
                boleh_gabung = not (isinstance(berikut, BlokMatan) and len(berikut.teks) > 1500)
                if boleh_gabung:
                    bag.append(berikut)
                    i += 1
            grup.append((bag, len(bag) > 1))
        else:
            grup.append(([daftar[i]], False))
            i += 1

    # Tempelkan BlokHasyiah pada blok/grup Matan ber-{fn:...} tepat di atasnya bila ukurannya masih muat satu halaman
    hasil: list[tuple[list[Blok], bool]] = []
    for bag, jaga in grup:
        if (
            len(bag) == 1
            and isinstance(bag[0], BlokHasyiah)
            and hasil
            and isinstance(hasil[-1][0][-1], BlokMatan)
            and "{fn:" in hasil[-1][0][-1].teks
            and sum(len(b.teks) for b in hasil[-1][0] if isinstance(b, BlokMatan)) <= 900
        ):
            hasil[-1][0].append(bag[0])
            hasil[-1] = (hasil[-1][0], True)
        else:
            hasil.append((bag, jaga))
    return hasil


def _render_bagian(bagian: Bagian, urut: int, jangkar_sumber: dict[str, str]) -> tuple[str, list[tuple[str, str]]]:
    mode_kitab = bagian.jenis == "kitab"
    tanda: list[tuple[str, str]] = []
    hitung = 0

    def sub_id() -> str:
        nonlocal hitung
        hitung += 1
        return f"sub-{urut}-{hitung}"

    ctx = {"jangkar_sumber": jangkar_sumber, "mode_kitab": mode_kitab, "sub_id": sub_id, "tanda": tanda}
    src_html = _tautan_sumber(bagian.sumber, jangkar_sumber)
    if mode_kitab:
        meta_bag = []
        if bagian.hal_kitab:
            meta_bag.append(f"<span>الأصل: ص {escape(bagian.hal_kitab)}</span>")
        if src_html:
            meta_bag.append(src_html)
        meta = f'<div class="bab-meta">{"".join(meta_bag)}</div>' if meta_bag else ""
        kepala = f'<header class="bab-spanduk"><h1>{_format_teks(bagian.judul)}</h1>{meta}</header>'
    else:
        meta_bag = []
        if bagian.hal_kitab:
            meta_bag.append(f"<span>مرجع الكتاب: ص {escape(bagian.hal_kitab)}</span>")
        if src_html:
            meta_bag.append(src_html)
        meta = f'<div class="lembar-meta">{"".join(meta_bag)}</div>' if meta_bag else ""
        kepala = f'<header class="lembar-kepala"><h1>{_format_teks(bagian.judul)}</h1>{meta}</header>'

    pangkas = f'<div class="bab-pangkas">{_format_teks(bagian.catatan_pangkas)}</div>' if bagian.catatan_pangkas else ""
    potongan_isi = []
    for bag_blok, jaga in _kelompokkan_blok(bagian.blok):
        html_bag = "".join(PERENDER_BLOK[type(b)](b, ctx) for b in bag_blok)
        potongan_isi.append(f'<div class="grup-jaga">{html_bag}</div>' if jaga else html_bag)
    isi = "".join(potongan_isi)
    halaman_css = f"kitab-{urut}" if mode_kitab else f"lembar-{urut}"
    kelas = "bagian bagian-kitab" if mode_kitab else "bagian bagian-lembar"
    html = f'<section class="{kelas}" id="bagian-{urut}" style="page:{halaman_css}">{kepala}{pangkas}{isi}</section>'
    return html, tanda


def _render_sumber(sumber: dict[str, Sumber], jangkar_sumber: dict[str, str]) -> str:
    if not sumber:
        return ""
    butir = []
    for kode, data in sumber.items():
        if data.tautan:
            tautan_esc = escape(data.tautan, quote=True)
            nama = f'<a class="sumber-nama" href="{tautan_esc}">{_format_teks(data.judul)}</a>'
        else:
            nama = f'<div class="sumber-nama">{_format_teks(data.judul)}</div>'
        butir.append(
            f'<div class="sumber-item" id="{jangkar_sumber[kode]}">'
            f'<span class="sumber-kode">{escape(kode)}</span>'
            f'<div class="sumber-badan">{nama}</div>'
            "</div>"
        )
    return (
        '<section class="hal-sumber" id="sumber">'
        '<h2 class="sumber-judul">مصادر المحاضرات</h2>'
        f'<div class="sumber-daftar">{"".join(butir)}</div>'
        "</section>"
    )


def _bangun_html(rencana: Rencana, nomor_halaman: dict[str, int], sertakan_probe: bool) -> tuple[str, list[list[tuple[str, str]]]]:
    jangkar_sumber = {k: f"sumber-{i}" for i, k in enumerate(rencana.sumber, 1)}
    fihris = _render_fihris(rencana, nomor_halaman)
    bagian_html = []
    semua_tanda: list[list[tuple[str, str]]] = []
    for i, bag in enumerate(rencana.bagian, 1):
        h, tanda = _render_bagian(bag, i, jangkar_sumber)
        bagian_html.append(h)
        semua_tanda.append(tanda)
    sumber_html = _render_sumber(rencana.sumber, jangkar_sumber)

    probe = ""
    if sertakan_probe:
        id_target = [f"bagian-{i}" for i in range(1, len(rencana.bagian) + 1)]
        for tanda_bag in semua_tanda:
            id_target.extend(sid for sid, _ in tanda_bag)
        if rencana.sumber:
            id_target.append("sumber")
        probe = '<div class="probe-jangkar">' + "".join(f'<a href="#{k}">{k}</a> ' for k in id_target) + "</div>"

    dokumen = (
        '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
        f"<title>{escape(rencana.judul)}</title>"
        f"<style>{_css_font()}{_css_halaman(rencana)}{CSS_UTAMA}</style>"
        f"</head><body>{fihris}{''.join(bagian_html)}{sumber_html}{probe}</body></html>"
    )
    return dokumen, semua_tanda


def _cetak_chromium(chrome: str, html: str, kerja: Path, nama: str) -> Path:
    berkas_html = kerja / f"{nama}.html"
    berkas_pdf = kerja / f"{nama}.pdf"
    profil = kerja / f"profil-{nama}"
    berkas_html.write_text(html, encoding="utf-8")
    perintah = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--disable-extensions",
        "--allow-file-access-from-files",
        f"--user-data-dir={profil}",
        f"--print-to-pdf={berkas_pdf}",
        berkas_html.resolve().as_uri(),
    ]
    if os.name != "nt":
        perintah.insert(1, "--no-sandbox")
    hasil = subprocess.run(perintah, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if hasil.returncode or not berkas_pdf.is_file() or not berkas_pdf.stat().st_size:
        pesan = (hasil.stderr or hasil.stdout).strip().splitlines()
        detail = pesan[-1] if pesan else "browser tidak menghasilkan PDF"
        raise ValueError(f"gagal merender PDF muqorror: {detail}")
    return berkas_pdf


def _peta_jangkar(doc) -> dict[str, int]:
    hasil: dict[str, int] = {}
    for nama, info in doc.resolve_names().items():
        if isinstance(info, dict) and "page" in info:
            hasil[nama] = int(info["page"])
    for halaman in doc:
        for tautan in halaman.get_links():
            nama = tautan.get("nameddest")
            if nama and "page" in tautan and nama not in hasil:
                hasil[nama] = int(tautan["page"])
    return hasil


def _nomor_fihris(rencana: Rencana, peta: dict[str, int], jumlah_halaman: int) -> dict[str, int]:
    nomor: dict[str, int] = {}
    for i in range(1, len(rencana.bagian) + 1):
        kunci = f"bagian-{i}"
        if kunci in peta:
            nomor[kunci] = peta[kunci] + 1
    if rencana.sumber and "sumber" in peta:
        nomor["sumber"] = peta["sumber"] + 1
    # Pengaman jika ada jangkar tidak terbaca
    if len(nomor) < len(rencana.bagian) + (1 if rencana.sumber else 0):
        dasar = min(2, jumlah_halaman)
        for i in range(1, len(rencana.bagian) + 1):
            nomor.setdefault(f"bagian-{i}", dasar)
        if rencana.sumber:
            nomor.setdefault("sumber", jumlah_halaman)
    return nomor


def _hiaskan_dan_daftar_isi(doc, rencana: Rencana, semua_tanda: list[list[tuple[str, str]]],
                            peta_p1: dict[str, int], peta_p2: dict[str, int]) -> None:
    jumlah = len(doc)
    mulai_bagian = [peta_p2.get(f"bagian-{i}", peta_p1.get(f"bagian-{i}", 1)) for i in range(1, len(rencana.bagian) + 1)]
    mulai_sumber = peta_p2.get("sumber", peta_p1.get("sumber", jumlah - 1)) if rencana.sumber else jumlah

    jenis_halaman = ["fihris"] * jumlah
    for idx, bag in enumerate(rencana.bagian):
        awal = mulai_bagian[idx]
        akhir = mulai_bagian[idx + 1] if idx + 1 < len(rencana.bagian) else mulai_sumber
        for p in range(max(0, awal), min(jumlah, akhir)):
            jenis_halaman[p] = bag.jenis
    if rencana.sumber:
        for p in range(max(0, mulai_sumber), jumlah):
            jenis_halaman[p] = "sumber"

    marun = (158 / 255, 41 / 255, 50 / 255)
    biru = (39 / 255, 100 / 255, 179 / 255)
    bawah = (201 / 255, 189 / 255, 168 / 255)
    krem = (1.0, 0.992, 0.968)
    margin_x = 43.9  # 15.5mm

    def gambar_kotak_hal(hal, warna_tepi, warna_isi=None):
        zona = hal.rect.__class__(margin_x - 2, 16, margin_x + 70, 56)
        kotak = None
        for b in hal.get_text("dict", clip=zona).get("blocks", ()):
            for ln in b.get("lines", ()):
                r = hal.rect.__class__(ln["bbox"])
                kotak = r if kotak is None else (kotak | r)
        if kotak is not None and not kotak.is_empty:
            lebar_min = max(kotak.width + 14, 24)
            cx = (kotak.x0 + kotak.x1) / 2
            bx0 = max(margin_x, cx - lebar_min / 2)
            bx1 = bx0 + lebar_min
            bingkai = hal.rect.__class__(bx0, kotak.y0 - 1.5, bx1, 52.8)
            hal.draw_rect(bingkai, color=warna_tepi, fill=warna_isi, width=0.95, overlay=warna_isi is None)
            if warna_isi is not None:
                dalam = hal.rect.__class__(bx0 + 1.8, kotak.y0 + 0.3, bx1 - 1.8, 51.0)
                hal.draw_rect(dalam, color=warna_tepi, fill=None, width=0.45, overlay=True)

    for i, halaman in enumerate(doc):
        jenis = jenis_halaman[i]
        if jenis == "fihris":
            continue
        x0, x1 = margin_x, halaman.rect.width - margin_x
        y_bawah = halaman.rect.height - 39.5
        if jenis == "kitab":
            gambar_kotak_hal(halaman, marun, krem)
            halaman.draw_line((x0, 52.8), (x1, 52.8), color=marun, width=1.15)
            halaman.draw_line((x0, 55.2), (x1, 55.2), color=marun, width=0.45)
            halaman.draw_line((x0, y_bawah), (x1, y_bawah), color=bawah, width=0.45)
        elif jenis == "lembar":
            gambar_kotak_hal(halaman, biru)
            halaman.draw_line((x0, 52.8), (x1, 52.8), color=biru, width=0.9)
            halaman.draw_line((x0, y_bawah), (x1, y_bawah), color=(188 / 255, 205 / 255, 224 / 255), width=0.45)
        elif jenis == "sumber":
            gambar_kotak_hal(halaman, marun, krem)
            halaman.draw_line((x0, 52.8), (x1, 52.8), color=marun, width=0.9)
            halaman.draw_line((x0, y_bawah), (x1, y_bawah), color=bawah, width=0.45)

    toc = [[1, "فهرس المقرر", 1]]
    for idx, bag in enumerate(rencana.bagian, 1):
        awal_p2 = mulai_bagian[idx - 1]
        akhir_p2 = (mulai_bagian[idx] if idx < len(rencana.bagian) else mulai_sumber) - 1
        akhir_p2 = max(awal_p2, min(jumlah - 1, akhir_p2))
        toc.append([1, bag.judul, awal_p2 + 1])
        awal_p1 = peta_p1.get(f"bagian-{idx}", awal_p2)
        for sid, judul_tanda in semua_tanda[idx - 1]:
            selisih = max(0, peta_p1.get(sid, awal_p1) - awal_p1)
            hal_tanda = min(awal_p2 + selisih, akhir_p2)
            toc.append([2, judul_tanda, hal_tanda + 1])
    if rencana.sumber:
        toc.append([1, "مصادر المحاضرات", mulai_sumber + 1])
    doc.set_toc(toc)
    doc.set_metadata({"title": rencana.judul, "subject": rencana.subjudul or rencana.judul})


def rakit(jalur: Path, tujuan: Path) -> None:
    try:
        import pymupdf as pdf
    except ImportError:
        pdf = None
    if pdf is None:
        raise ValueError("muqorror butuh pustaka pymupdf. Jalankan python -m pip install -r requirements.txt dari repo")
    chrome = diagram.browser()
    if not chrome:
        raise ValueError(
            f"browser Chromium tidak ditemukan: pasang {diagram.PASANG_BROWSER}, "
            "atau tulis jalur chrome.exe di variabel lingkungan BAHTS_CHROME"
        )
    try:
        rencana = _baca(jalur)
        if tujuan.suffix.lower() != ".pdf":
            raise ValueError("hasil muqorror harus berakhiran .pdf")
        if tujuan.resolve() == jalur.resolve() or (tujuan.exists() and tujuan.samefile(jalur)):
            raise ValueError("hasil muqorror tidak boleh menimpa berkas rencana")

        with tempfile.TemporaryDirectory(prefix="bahts-muqorror-") as t:
            kerja = Path(t)
            html_p1, semua_tanda = _bangun_html(rencana, {}, sertakan_probe=True)
            pdf_p1 = _cetak_chromium(chrome, html_p1, kerja, "pass1")
            with pdf.open(pdf_p1) as doc1:
                peta_p1 = _peta_jangkar(doc1)
                nomor = _nomor_fihris(rencana, peta_p1, max(1, len(doc1) - 1))

            html_p2, _ = _bangun_html(rencana, nomor, sertakan_probe=False)
            pdf_p2 = _cetak_chromium(chrome, html_p2, kerja, "pass2")
            with pdf.open(pdf_p2) as doc2:
                peta_p2 = _peta_jangkar(doc2)
                nomor_baru = _nomor_fihris(rencana, peta_p2, len(doc2))
                if nomor_baru != nomor:
                    html_p3, _ = _bangun_html(rencana, nomor_baru, sertakan_probe=False)
                    pdf_p3 = _cetak_chromium(chrome, html_p3, kerja, "pass3")
                    with pdf.open(pdf_p3) as doc3:
                        peta_p3 = _peta_jangkar(doc3)
                        _hiaskan_dan_daftar_isi(doc3, rencana, semua_tanda, peta_p1, peta_p3)
                        with sementara(tujuan) as part:
                            doc3.save(part, garbage=4, deflate=True)
                        jumlah_hal = len(doc3)
                else:
                    _hiaskan_dan_daftar_isi(doc2, rencana, semua_tanda, peta_p1, peta_p2)
                    with sementara(tujuan) as part:
                        doc2.save(part, garbage=4, deflate=True)
                    jumlah_hal = len(doc2)

        print(f"HALAMAN={jumlah_hal}\nPDF={tujuan.resolve()}")
    except (OSError, subprocess.TimeoutExpired, pdf.FileDataError, pdf.FileNotFoundError) as e:
        pesan = "renderer browser kehabisan waktu" if isinstance(e, subprocess.TimeoutExpired) else str(e)
        raise ValueError(pesan) from e
