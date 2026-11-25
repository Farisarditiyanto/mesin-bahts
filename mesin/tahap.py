# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tahap satu bahts dan langkah berikutnya, di satu tempat (`python mesin/bahts.py tahap <folder>`).

Tahap tidak disimpan di berkas mana pun: tiap kali dibaca ulang dari barang aslinya (`cek` atas naskah.txt, baris
NASKAH_SHA256 di laporan hasil rakit, kunci rakit, penanda folder .rakit-*, cadangan _arsip/rakit-*), jadi tidak bisa
basi. Tiga sumbu:

  naskah  GAGAL ──betulkan ✗──▶ PERHATIAN ──bereskan ! atau «terima»──▶ LOLOS   (dari `cek` + riset.txt; dibaca ulang)
  hasil   BELUM ──rakit──▶ TERKINI ──isi tercetak naskah.txt diubah──▶ USANG ──rakit──▶ TERKINI   (tiap laporan*.txt di folder)
          TIDAK_DIKETAHUI = laporan versi lama tanpa NASKAH_SHA256 ──rakit──▶ TERKINI
  rakit   BEBAS │ JALAN (kunci rakit dipegang; bahts ini atau bahts lain) │ YATIM (rakit.ps1 rakit yang dimatikan)

`rakit` hanya sah dari naskah PERHATIAN atau LOLOS; naskah GAGAL ditolak `rakit` sendiri («Belum dirakit: … galat»).
PERHATIAN menahan langkah pemeriksa: tiap perhatian wajib ditangani, dibereskan di naskah atau diterima dengan alasan
(«terima <kode> <alasan>» di riset.txt, AGENTS.md Alur kerja langkah 4). Menerima tidak mengubah naskah, jadi PDF yang
TERKINI tetap TERKINI; membereskan di naskah membuatnya USANG lalu `rakit`.
Bahts bertahap per فصل (hanya laporan-fasl*.txt): potongan yang terakhir dirakit yang menentukan; potongan lama yang
USANG wajar (sudah dikumpulkan dari naskah lama) dan tidak disuruh rakit ulang.
Keadaan dibaca `baca`; templat .docx dan versi mesin tidak ikut menentukan TERKINI.
Folder .rakit-* punya keadaannya sendiri: rakit.FolderKerja. Satu langkah berikutnya dipilih `berikutnya`."""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import olah
import produk
import shamela
from dasar import perintah
from rakit import PEKERJAAN, FolderKerja, cadangan_tertinggal, lihat_kunci, milik, ps_yatim


class Naskah(Enum):
    GAGAL = "GAGAL"  # `cek` menemukan galat: `rakit` menolak
    PERHATIAN = "PERHATIAN"  # GAGAL 0, ada perhatian yang belum ditangani (dibereskan, atau «terima» beralasan)
    LOLOS = "LOLOS"  # GAGAL 0, perhatian 0


class Hasil(Enum):
    BELUM = "BELUM"  # belum ada PDF + laporan dari `rakit` (atau @berkas diganti sesudahnya)
    TERKINI = "TERKINI"  # PDF dirakit dari naskah.txt versi ini, atau versi yang isi tercetaknya sama (CETAK_SHA256)
    USANG = "USANG"  # PDF dirakit dari naskah.txt versi lain: naskah diubah sesudah `rakit`
    TIDAK_DIKETAHUI = "TIDAK_DIKETAHUI"  # laporan versi lama tanpa NASKAH_SHA256, atau PDF potongan tidak diketahui namanya


class Rakit(Enum):
    BEBAS = "BEBAS"
    JALAN = "JALAN"  # rakit memegang kunci rakit: `rakit` baru antre sendiri; yang jalan jangan dimatikan
    YATIM = "YATIM"  # rakit.ps1 milik rakit yang dimatikan masih jalan: `rakit` baru menunggunya berhenti sendiri


KETERANGAN_HASIL = {
    Hasil.BELUM: "belum dirakit",
    Hasil.TERKINI: "dirakit dari naskah.txt versi ini, atau versi lain yang isi tercetaknya sama (templat .docx dan versi mesin tidak dibandingkan)",
    Hasil.USANG: "dirakit dari naskah.txt versi lain (isi tercetak naskah diubah sesudah `rakit`)",
    Hasil.TIDAK_DIKETAHUI: "sidik versi naskah tidak tercatat atau tidak sah: rakit ulang supaya pasti",
}


def naskah(galat, perhatian):
    return Naskah.GAGAL if galat else Naskah.PERHATIAN if perhatian else Naskah.LOLOS


def _baris(laporan):
    return laporan.read_text(encoding="utf8", errors="replace").splitlines()


def hasil(pdf, laporan, sidik, cetak=None):
    """sidik = NASKAH_SHA256 naskah sekarang; cetak = CETAK_SHA256-nya (olah.sidik_cetak). Naskah yang berubah hanya
    di bagian yang tidak tercetak (mis. @minimal_halaman) tetap TERKINI; laporan tanpa CETAK_SHA256 = naskah saja."""
    if pdf is None:
        return Hasil.TIDAK_DIKETAHUI if laporan.is_file() else Hasil.BELUM
    if not (pdf.is_file() and laporan.is_file()):
        return Hasil.BELUM
    baris_laporan = _baris(laporan)
    tercatat = produk.sidik(baris_laporan)
    if tercatat is None:
        return Hasil.TIDAK_DIKETAHUI
    if tercatat == sidik or (cetak and produk.sidik(baris_laporan, produk.CETAK) == cetak):
        return Hasil.TERKINI
    return Hasil.USANG


@dataclass
class Produk:
    """Satu hasil rakit: seluruh naskah (laporan.txt) atau satu potongan --fasl."""
    laporan: Path
    keadaan: Hasil
    pdf: Path | None  # None = nama PDF potongan tidak diketahui (laporan potongan tanpa baris POTONGAN)
    bendera: str = ""  # "" atau "--fasl n"

    @property
    def kunci(self):
        return "HASIL" if not self.bendera else f"HASIL {self.bendera.removeprefix('--').replace(' ', '')}"


@dataclass
class Keadaan:
    jalur: str  # bahts seperti diketik pemakai, untuk perintah berikutnya
    naskah: Naskah
    galat: int
    perhatian: int  # yang belum ditangani
    tertolak: bool  # ada «teks TIDAK KETEMU di kitab»: `cek --jejak` menunjuk kitab lain
    hasil: list = field(default_factory=list)  # [Produk]: laporan.txt dulu, lalu potongan urut nomornya
    rakit: Rakit = Rakit.BEBAS
    siapa: str = ""  # pemegang kunci rakit (folder, proses, jam mulai), kalau JALAN
    rakit_sini: bool = False  # yang JALAN adalah rakit bahts ini
    kerja: list = field(default_factory=list)  # [(nama folder .rakit-*, FolderKerja.Keadaan)]
    arsip: list = field(default_factory=list)  # [nama folder _arsip/rakit-*]: cadangan hasil lama yang tertinggal
    diterima: int = 0  # perhatian yang diterima lewat «terima» di riset.txt


def hasil_rakit(folder, cek=None, berkas=None):
    """[Produk] hasil `rakit` di folder menurut naskah sekarang (cek = olah.periksa): seluruh naskah dulu, lalu tiap
    potongan --fasl urut nomornya."""
    sidik = cek.sidik_naskah if cek else ""
    cetak = cek.sidik_cetak if cek else ""
    berkas = berkas if berkas is not None else cek.ctx.meta["berkas"]
    pdf, laporan = folder / produk.pdf(berkas), folder / produk.laporan()
    ada = [Produk(laporan, hasil(pdf, laporan, sidik, cetak), pdf)]
    for fasl, laporan in produk.potongan(folder):  # nama yang bukan --fasl sah dilewati: jangan menyarankan perintah palsu
        label = produk.label_potongan(_baris(laporan), fasl)
        pdf = None if label is None else folder / produk.pdf(produk.nama_potongan(berkas, label, fasl))
        ada.append(Produk(laporan, hasil(pdf, laporan, sidik, cetak), pdf, f"--fasl {fasl}"))
    return ada


def terakhir(hasil):
    """Produk yang terakhir dirakit (laporan paling baru), seluruh naskah atau potongan --fasl; belum ada laporan sama
    sekali = seluruh naskah. Dirakit utuh lalu bertahap: potongannya yang menentukan langkah berikutnya."""
    ada = [p for p in hasil if p.laporan.is_file()]
    return max(ada, key=lambda p: p.laporan.stat().st_mtime) if ada else (hasil[0] if hasil else None)


def baca(folder, jalur):
    """Baca naskah, produk, dan kunci rakit tanpa menulis apa pun (folder bahts, bahan `cek`, metadata kunci)."""
    folder = Path(folder)
    pemegang = lihat_kunci(PEKERJAAN)
    rakit = Rakit.JALAN if pemegang is not None else Rakit.YATIM if ps_yatim() else Rakit.BEBAS
    with shamela.baca_saja():
        cek = olah.periksa(folder)
    ctx = cek.ctx
    return Keadaan(jalur=jalur, naskah=naskah(ctx.galat, ctx.perhatian), galat=len(ctx.galat),
                   perhatian=len(ctx.perhatian), diterima=len(ctx.diterima), tertolak=bool(ctx.tertolak),
                   hasil=hasil_rakit(folder, cek), rakit=rakit, siapa=pemegang.kalimat() if pemegang else "",
                   rakit_sini=pemegang is not None and milik(pemegang, folder),
                   kerja=[(x.path.name, x.keadaan()) for x in FolderKerja.semua(folder)],
                   arsip=cadangan_tertinggal(folder))


def berikutnya(k):
    """Satu langkah berikutnya: (apa yang dikerjakan, perintahnya atau None). Urut dari yang menahan semua langkah lain."""
    cek = perintah(f'cek "{k.jalur}"')
    if k.rakit is Rakit.JALAN and k.rakit_sini:
        return (f"rakit bahts ini sedang jalan ({k.siapa or 'pemegang belum tercatat'}): tunggu sampai selesai; jangan "
                "matikan Word, PowerShell, atau Python-nya", None)
    if k.naskah is Naskah.GAGAL:
        return ("betulkan tiap baris «✗» di `cek`" + (", mulai dari petunjuk `--jejak`" if k.tertolak else ""),
                perintah(f'cek "{k.jalur}" --jejak') if k.tertolak else cek)
    p = terakhir(k.hasil)
    keadaan = p.keadaan if p else Hasil.BELUM
    antre = (" (rakit lain sedang jalan: `rakit` antre sendiri)" if k.rakit is Rakit.JALAN else
             " (rakit.ps1 sisa rakit yang dimatikan masih jalan; `rakit` menunggunya berhenti sendiri)"
             if k.rakit is Rakit.YATIM else "")
    rakit = perintah(f'rakit "{k.jalur}"' + (f" {p.bendera}" if p and p.bendera else ""))
    if k.naskah is Naskah.PERHATIAN:
        lalu = "" if keadaan is Hasil.TERKINI else "; lalu rakit"
        return (f"tangani tiap baris «!» di `cek` ({k.perhatian}): bereskan di naskah, atau kalau memang tidak bisa / "
                "salah tangkap tulis «terima <kode> <alasan>» di riset.txt (AGENTS.md Alur kerja langkah 4)" + lalu, cek)
    if keadaan is Hasil.BELUM:
        return "rakit .docx + .pdf" + antre, rakit
    if keadaan is not Hasil.TERKINI:
        return f"rakit ulang: PDF yang ada {KETERANGAN_HASIL[keadaan]}" + antre, rakit
    terima = (f"; pemeriksa juga menilai alasan {k.diterima} baris «terima» di riset.txt" if k.diterima else "")
    return ("PDF sesuai naskah ini. Sebelum lapor selesai: pemeriksa (AGENTS.md Alur kerja langkah 5) membuka bukti "
            "tiap catatan kaki" + terima, perintah(f'bukti "{k.jalur}"'))


def baris(k):
    """Keluaran `tahap`: satu keadaan satu baris «KUNCI=NILAI», supaya agent dan skrip membacanya tanpa menebak."""
    out = [f"NASKAH={k.naskah.value} (GAGAL {k.galat}, perhatian belum ditangani {k.perhatian}, diterima {k.diterima})"]
    for p in k.hasil:
        letak = p.pdf if p.keadaan is not Hasil.BELUM and p.pdf else (p.pdf.name if p.pdf else p.laporan.name)
        ket = KETERANGAN_HASIL[p.keadaan] if p.pdf else "laporan potongan tanpa baris POTONGAN: nama PDF-nya tidak diketahui"
        out.append(f"{p.kunci}={p.keadaan.value}: {letak} {ket}")
    out.append(f"RAKIT={k.rakit.value}" + (f": {k.siapa}" if k.siapa else ""))
    for nama, kk in k.kerja:
        out.append(f"FOLDER_KERJA {nama}={kk.name}: {FolderKerja.KETERANGAN[kk]}")
    for nama in k.arsip:
        out.append(f"ARSIP _arsip/{nama}: cadangan hasil lama yang belum dipulihkan (pemulihan rakit gagal atau rakit "
                   "dimatikan di tengah): selamatkan isinya, lalu hapus sendiri")
    tertahan = [n for n, kk in k.kerja if kk is not FolderKerja.Keadaan.SEMENTARA] + [f"_arsip/{n}" for n in k.arsip]
    if tertahan and not (k.rakit is Rakit.JALAN and k.rakit_sini):  # selama rakit bahts ini jalan, foldernya miliknya
        out.append(f"PERLU PEMAKAI: {', '.join(tertahan)} tidak pernah dibuang mesin; sebut ke pemakai, jangan dihapus sendiri")
    apa, cmd = berikutnya(k)
    out.append(f"BERIKUTNYA: {apa}" + (f"\n  -> {cmd}" if cmd else ""))
    return out
