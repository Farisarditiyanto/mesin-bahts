# SPDX-License-Identifier: AGPL-3.0-or-later
"""Produk `rakit` di folder bahts: nama berkas hasil dan baris «KUNCI=nilai» laporannya, di satu tempat.
Laporan = baris `cek` (olah), lalu baris yang ditambahkan rakit.ps1 (HALAMAN, HALAMAN_ISI, KHULASAH); dibaca `rakit` dan
`tahap`."""
import re

from dasar import TandaRusak

LAPORAN = "laporan.txt"  # laporan rakit seluruh naskah
LAPORAN_FASL = "laporan-fasl"  # awal nama laporan potongan --fasl
HALAMAN, KHULASAH, NASKAH, CETAK = "HALAMAN", "KHULASAH", "NASKAH_SHA256", "CETAK_SHA256"
HITUNGAN = ("HALAMAN", "CATATAN_KAKI", "KATA")  # awal baris hitungan rakit.ps1 yang dicetak `rakit` sesudah hasil terpasang


def laporan(fasl=None):
    """Nama laporan hasil rakit; potongan --fasl punya laporannya sendiri, jadi laporan seluruh naskah tidak tertimpa."""
    return f"{LAPORAN_FASL}{fasl}.txt" if fasl else LAPORAN


def potongan(folder):
    """[(fasl, laporan)] tiap potongan `rakit --fasl` di folder, urut nomornya. Catatan atau salinan laporan yang
    namanya bukan nomor/rentang sah bukan produk `rakit --fasl`: dilewati."""
    ada = []
    for jalur in folder.glob(f"{LAPORAN_FASL}*.txt"):
        fasl = jalur.stem.removeprefix(LAPORAN_FASL)
        try:
            ada.append((rentang_fasl(fasl), fasl, jalur))
        except TandaRusak:
            continue
    return [(fasl, jalur) for _, fasl, jalur in sorted(ada, key=lambda p: p[0])]


def docx(berkas):
    return f"{berkas}.docx"


def pdf(berkas):
    return f"{berkas}.pdf"


def khulasah(berkas):
    """PDF halaman-halaman khulasah {X} yang distabilo."""
    return f"{berkas} - الخلاصات.pdf"


def nama_potongan(berkas, label, fasl):
    """Nama berkas hasil `rakit --fasl`: «<@berkas> - <label potongan>» (dipakai `potong` dan `tahap`)."""
    nama = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", label).strip(" .")
    return f"{berkas} - {nama or 'fasl' + fasl}"


def rentang_fasl(fasl):
    """Nomor/rentang sah untuk hasil per فصل; dipakai perakit dan pembaca laporan tahap."""
    m = re.fullmatch(r"([1-9][0-9]*)(?:-([1-9][0-9]*))?", fasl)
    if not m or (m[2] and int(m[2]) < int(m[1])):
        raise TandaRusak(f"--fasl «{fasl}»: tulis nomor #F, mis. «--fasl 2», atau rentang dari kecil ke besar, mis. «--fasl 1-2»")
    return int(m[1]), int(m[2] or m[1])


def baris(kunci, nilai):
    return f"{kunci}={nilai}"


def nilai(laporan, kunci):
    """Nilai tiap baris «kunci=…» di baris-baris laporan, urut kemunculannya."""
    return [b.split("=", 1)[1] for b in laporan if b.startswith(kunci + "=")]


def sidik(laporan, kunci=NASKAH):
    """Sidik `kunci` yang sah di baris-baris laporan hasil rakit; None = tidak tercatat (versi lama) atau rusak."""
    tercatat = nilai(laporan, kunci)
    if not tercatat:
        return None
    pertama = tercatat[0].strip()
    return pertama if re.fullmatch(r"[0-9a-f]{64}", pertama) else None


def baris_potongan(fasl, label):
    return f"POTONGAN=--fasl {fasl}: {label}"


def label_potongan(laporan, fasl):
    """Label potongan --fasl itu dari baris-baris laporannya; None = laporan tanpa baris POTONGAN."""
    awal = baris_potongan(fasl, "")
    return next((b.removeprefix(awal) for b in laporan if b.startswith(awal)), None)
