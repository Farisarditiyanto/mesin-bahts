# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tahap satu bahts dan langkah berikutnya, di satu tempat (`python mesin/bahts.py tahap <folder>`).

Tahap tidak disimpan di berkas mana pun: tiap kali dibaca ulang dari barang aslinya (`cek` atas naskah.txt, baris
NASKAH_SHA256 di laporan hasil rakit, kunci rakit, penanda folder .rakit-*, cadangan _arsip/rakit-*), jadi tidak bisa
basi. Tiga sumbu:

  naskah  GAGAL ──betulkan ✗──▶ PERHATIAN ──bereskan !──▶ LOLOS            (dari `cek`; naskah diubah = dibaca ulang)
  hasil   BELUM ──rakit──▶ TERKINI ──naskah.txt diubah──▶ USANG ──rakit──▶ TERKINI      (tiap laporan*.txt di folder)
          TIDAK_DIKETAHUI = laporan versi lama tanpa NASKAH_SHA256 ──rakit──▶ TERKINI
  rakit   BEBAS │ JALAN (kunci rakit dipegang; bahts ini atau bahts lain) │ YATIM (rakit.ps1 rakit yang dimatikan)

`rakit` hanya sah dari naskah PERHATIAN atau LOLOS; naskah GAGAL ditolak `rakit` sendiri («Belum dirakit: … galat»).
PERHATIAN bukan keadaan akhir yang menahan: perhatian yang memang tidak bisa dibereskan disebut di laporan akhir
(AGENTS.md Alur kerja langkah 4), jadi PERHATIAN + hasil TERKINI = lanjut ke pemeriksa, sama dengan LOLOS.
Bahts bertahap per فصل (hanya laporan-fasl*.txt): potongan yang terakhir dirakit yang menentukan; potongan lama yang
USANG wajar (sudah dikumpulkan dari naskah lama) dan tidak disuruh rakit ulang.
Folder .rakit-* punya keadaannya sendiri: berkas.FolderKerja. Satu langkah berikutnya dipilih `berikutnya`."""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from berkas import FolderKerja
from shamela import perintah


class Naskah(Enum):
    GAGAL = "GAGAL"  # `cek` menemukan galat: `rakit` menolak
    PERHATIAN = "PERHATIAN"  # GAGAL 0, ada perhatian: dibereskan, atau yang tidak bisa disebut di laporan akhir
    LOLOS = "LOLOS"  # GAGAL 0, perhatian 0


class Hasil(Enum):
    BELUM = "BELUM"  # belum ada PDF + laporan dari `rakit` (atau @berkas diganti sesudahnya)
    TERKINI = "TERKINI"  # PDF dirakit dari naskah.txt versi ini (NASKAH_SHA256 laporan = naskah sekarang)
    USANG = "USANG"  # PDF dirakit dari naskah.txt versi lain: naskah diubah sesudah `rakit`
    TIDAK_DIKETAHUI = "TIDAK_DIKETAHUI"  # laporan versi lama tanpa NASKAH_SHA256, atau PDF potongan tidak diketahui namanya


class Rakit(Enum):
    BEBAS = "BEBAS"
    JALAN = "JALAN"  # rakit memegang kunci rakit: `rakit` baru antre sendiri; yang jalan jangan dimatikan
    YATIM = "YATIM"  # rakit.ps1 milik rakit yang dimatikan masih jalan: `rakit` baru menunggunya berhenti sendiri


KETERANGAN_HASIL = {
    Hasil.BELUM: "belum dirakit",
    Hasil.TERKINI: "dirakit dari naskah.txt versi ini (templat .docx dan versi mesin tidak dibandingkan)",
    Hasil.USANG: "dirakit dari naskah.txt versi lain (naskah diubah sesudah `rakit`)",
    Hasil.TIDAK_DIKETAHUI: "versi naskahnya tidak tercatat (laporan dari mesin versi lama): rakit ulang supaya pasti",
}


def naskah(galat, perhatian):
    return Naskah.GAGAL if galat else Naskah.PERHATIAN if perhatian else Naskah.LOLOS


def sidik_laporan(laporan):
    """NASKAH_SHA256 yang tercatat di laporan hasil rakit; None = tidak tercatat (laporan versi lama)."""
    for b in laporan.read_text(encoding="utf8", errors="replace").splitlines():
        if b.startswith("NASKAH_SHA256="):
            return b.split("=", 1)[1].strip()
    return None


def hasil(pdf, laporan, sidik):
    if pdf is None:
        return Hasil.TIDAK_DIKETAHUI if laporan.is_file() else Hasil.BELUM
    if not (pdf.is_file() and laporan.is_file()):
        return Hasil.BELUM
    tercatat = sidik_laporan(laporan)
    if tercatat is None:
        return Hasil.TIDAK_DIKETAHUI
    return Hasil.TERKINI if tercatat == sidik else Hasil.USANG


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
    perhatian: int
    tertolak: bool  # ada «teks TIDAK KETEMU di kitab»: `cek --jejak` menunjuk kitab lain
    hasil: list = field(default_factory=list)  # [Produk]: laporan.txt dulu, lalu potongan urut nomornya
    rakit: Rakit = Rakit.BEBAS
    siapa: str = ""  # pemegang kunci rakit (folder, proses, jam mulai), kalau JALAN
    rakit_sini: bool = False  # yang JALAN adalah rakit bahts ini
    kerja: list = field(default_factory=list)  # [(nama folder .rakit-*, FolderKerja.Keadaan)]
    arsip: list = field(default_factory=list)  # [nama folder _arsip/rakit-*]: cadangan hasil lama yang tertinggal


def penentu(k):
    """Hasil yang menentukan langkah berikutnya: yang terakhir dirakit (laporan paling baru), seluruh naskah atau
    potongan --fasl; belum ada laporan sama sekali = seluruh naskah. Dirakit utuh lalu bertahap: potongannya yang
    menentukan."""
    ada = [p for p in k.hasil if p.laporan.is_file()]
    return max(ada, key=lambda p: p.laporan.stat().st_mtime) if ada else (k.hasil[0] if k.hasil else None)


def berikutnya(k):
    """Satu langkah berikutnya: (apa yang dikerjakan, perintahnya atau None). Urut dari yang menahan semua langkah lain."""
    cek = perintah(f'cek "{k.jalur}"')
    if k.rakit is Rakit.JALAN and k.rakit_sini:
        return (f"rakit bahts ini sedang jalan ({k.siapa or 'pemegang belum tercatat'}): tunggu sampai selesai; jangan "
                "matikan Word, PowerShell, atau Python-nya", None)
    if k.naskah is Naskah.GAGAL:
        return ("betulkan tiap baris «✗» di `cek`" + (", mulai dari petunjuk `--jejak`" if k.tertolak else ""),
                perintah(f'cek "{k.jalur}" --jejak') if k.tertolak else cek)
    p = penentu(k)
    keadaan = p.keadaan if p else Hasil.BELUM
    antre = (" (rakit lain sedang jalan: `rakit` antre sendiri)" if k.rakit is Rakit.JALAN else
             " (rakit.ps1 sisa rakit yang dimatikan masih jalan; `rakit` menunggunya berhenti sendiri)"
             if k.rakit is Rakit.YATIM else "")
    rakit = perintah(f'rakit "{k.jalur}"' + (f" {p.bendera}" if p and p.bendera else ""))
    if keadaan is not Hasil.TERKINI and k.naskah is Naskah.PERHATIAN:  # perintahnya `rakit`: perhatian bisa abadi
        return (f"bereskan dulu tiap baris «!» di `cek` yang bisa dibereskan ({cek}; AGENTS.md Alur kerja langkah 4), "
                "yang tidak bisa disebut di laporan akhir; lalu rakit" + antre, rakit)
    if keadaan is Hasil.BELUM:
        return "rakit .docx + .pdf" + antre, rakit
    if keadaan is not Hasil.TERKINI:
        return f"rakit ulang: PDF yang ada {KETERANGAN_HASIL[keadaan]}" + antre, rakit
    sisa = (f"; {k.perhatian} perhatian yang tersisa: bereskan lalu rakit ulang, atau sebut di laporan akhir"
            if k.naskah is Naskah.PERHATIAN else "")
    return ("PDF sesuai naskah ini" + sisa + ". Sebelum lapor selesai: pemeriksa (AGENTS.md Alur kerja langkah 5) "
            "membuka bukti tiap catatan kaki", perintah(f'bukti "{k.jalur}"'))


def baris(k):
    """Keluaran `tahap`: satu keadaan satu baris «KUNCI=NILAI», supaya agent dan skrip membacanya tanpa menebak."""
    out = [f"NASKAH={k.naskah.value} (GAGAL {k.galat}, perhatian {k.perhatian})"]
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
