# SPDX-License-Identifier: AGPL-3.0-or-later
"""Huruf Windows: daftar huruf terpasang (registry), font mushaf, dan huruf profil @format. Ditanya `periksa`, `siapkan`,
`rakit`, dan pembetul teks PDF."""
import os, re
from pathlib import Path

# Font mushaf «KFGQPC HAFS Uthmanic Script» milik مجمع الملك فهد: tidak ikut repo (lihat NOTICE), diunduh oleh `siapkan`.
FONT = "UthmanicHafs_V22.ttf"
FONT_NAMA = "KFGQPC HAFS Uthmanic Script (TrueType)"
DAFTAR_HURUF = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"  # kunci registry, sama untuk semua akun dan akun ini
FONT_SISTEM = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
FONT_PEMAKAI = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"))
HURUF_SARAN = ("huruf ini ikut terpasang kalau Windows punya papan ketik Arab (Settings > Time & language > Language & region > Add a language > العربية).\n"
               "          Atau lewat PowerShell admin (pemakai cukup klik Yes): Start-Process powershell -Verb RunAs -Wait -ArgumentList "
               "\"Add-WindowsCapability -Online -Name Language.Fonts.Arab~~~und-ARAB~0.0.1.0\"")


def terdaftar():
    """(nama, berkas) tiap huruf di daftar huruf Windows (registry), semua akun dulu, lalu akun ini. nama = nama
    terdaftar tanpa keterangan jenis, mis. «Traditional Arabic» atau «Cambria & Cambria Math» (dari «… (TrueType)»).
    Daftar yang tidak terbaca dilewati."""
    import winreg
    for akar, folder in ((winreg.HKEY_LOCAL_MACHINE, FONT_SISTEM), (winreg.HKEY_CURRENT_USER, FONT_PEMAKAI)):
        try:
            with winreg.OpenKey(akar, DAFTAR_HURUF) as k:
                daftar = [winreg.EnumValue(k, i)[:2] for i in range(winreg.QueryInfoKey(k)[1])]
        except OSError:
            continue
        for nama, nilai in daftar:
            yield re.sub(r"\s*\(.*\)$", "", nama), Path(nilai) if os.path.isabs(nilai) else folder / nilai


def berkas():
    """{nama huruf tanpa spasi: berkas} dari daftar huruf Windows (semua akun, lalu akun ini)."""
    hasil = {}
    for nama, jalur in terdaftar():
        hasil.setdefault(nama.replace(" ", ""), jalur)
    return hasil


def huruf_ada(nama):
    """Huruf `nama` terpasang di Windows, untuk semua akun atau untuk akun ini saja (daftar huruf di registry)."""
    # satu nama terdaftar bisa memuat beberapa huruf: «Cambria & Cambria Math»
    return any(nama.lower() in (x.strip().lower() for x in satu.split("&")) for satu, _ in terdaftar())


def font_terpasang():
    """Font mushaf terpasang di berkas font Windows dan terdaftar di registry."""
    if os.name != "nt":
        return any((d / FONT).exists() for d in (FONT_PEMAKAI, FONT_SISTEM))
    nama_mushaf = re.sub(r"\s*\(.*\)$", "", FONT_NAMA).casefold()
    return any(
        (jalur.name.casefold() == FONT.casefold() or satu.casefold() == nama_mushaf) and jalur.exists()
        for satu, jalur in terdaftar()
    )


def pasang_font(sumber):
    """Pasang font mushaf dari berkas `sumber` untuk akun ini: sama dengan klik kanan > Install (salin ke folder font
    pemakai + daftarkan), tanpa hak admin."""
    import ctypes, winreg
    FONT_PEMAKAI.mkdir(parents=True, exist_ok=True)
    (FONT_PEMAKAI / FONT).write_bytes(sumber.read_bytes())
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DAFTAR_HURUF) as k:
        winreg.SetValueEx(k, FONT_NAMA, 0, winreg.REG_SZ, str(FONT_PEMAKAI / FONT))
    ctypes.windll.gdi32.AddFontResourceW(str(FONT_PEMAKAI / FONT))
