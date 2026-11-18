# SPDX-License-Identifier: AGPL-3.0-or-later
"""Huruf yang dibutuhkan `rakit` di Windows: font mushaf dan huruf profil @format. Ditanya `periksa`, `siapkan`, `rakit`."""
import os
from pathlib import Path

# Font mushaf «KFGQPC HAFS Uthmanic Script» milik مجمع الملك فهد: tidak ikut repo (lihat NOTICE), diunduh oleh `siapkan`.
FONT = "UthmanicHafs_V22.ttf"
FONT_PEMAKAI = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"))
HURUF_SARAN = ("huruf ini ikut terpasang kalau Windows punya papan ketik Arab (Settings > Time & language > Language & region > Add a language > العربية).\n"
               "          Atau lewat PowerShell admin (pemakai cukup klik Yes): Start-Process powershell -Verb RunAs -Wait -ArgumentList "
               "\"Add-WindowsCapability -Online -Name Language.Fonts.Arab~~~und-ARAB~0.0.1.0\"")


def huruf_ada(nama):
    """Huruf `nama` terpasang di Windows, untuk semua akun atau untuk akun ini saja (daftar huruf di registry)."""
    import teks_pdf
    # satu nama terdaftar bisa memuat beberapa huruf: «Cambria & Cambria Math»
    return any(nama.lower() in (x.strip().lower() for x in terdaftar.split("&")) for terdaftar, _ in teks_pdf.huruf_terdaftar())


def font_terpasang():
    return any((d / FONT).exists() for d in (FONT_PEMAKAI, Path(r"C:\Windows\Fonts")))
