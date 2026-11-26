# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pembantu bersama tes `.github/uji_*.py`: salinan mesin di TEMP, pintu pemakai (`bahts.py`), CLI dalam proses, dan ada-tidaknya Word."""
import contextlib, io, os, runpy, shutil, subprocess, sys
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent


def salin_mesin(akar, kitab=(), huruf=True):
    """Salin `mesin/` (tanpa bahan sementara) dan kitab yang disebut ke `akar`; huruf=False melewatkan font mushaf
    (hanya `rakit` Word asli yang memakainya)."""
    abaikan = ("_tmp", "__pycache__") + (() if huruf else ("*.ttf",))
    shutil.copytree(REPO / "mesin", akar / "mesin", ignore=shutil.ignore_patterns(*abaikan))
    for sid in kitab:
        shutil.copytree(REPO / "kitab" / str(sid), akar / "kitab" / str(sid))


def bahts(akar, *argumen, batas=None):
    """Jalankan `python mesin/bahts.py …` di `akar` seperti pemakai; keluaran dibaca sebagai UTF-8."""
    return subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), *map(str, argumen)], cwd=akar,
                          capture_output=True, encoding="utf8", timeout=batas, env=dict(os.environ, PYTHONIOENCODING="utf8"))


def cli_dalam_proses(akar, *argumen):
    """Jalankan `mesin/bahts.py` di `akar` dalam proses Python ini (untuk tes yang mem-patch modul): (kode, stdout, stderr)."""
    class Keluaran(io.StringIO):
        def reconfigure(self, **kw):
            pass

    out, err = Keluaran(), Keluaran()
    skrip = Path(akar) / "mesin" / "bahts.py"
    with contextlib.chdir(akar), patch.object(sys, "argv", [str(skrip), *map(str, argumen)]), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            runpy.run_path(str(skrip), run_name="__main__")
            kode = 0
        except SystemExit as e:
            if e.code is None:
                kode = 0
            elif isinstance(e.code, int):
                kode = e.code
            else:
                kode = 1
                err.write(str(e.code) + "\n")
    return kode, out.getvalue(), err.getvalue()


def tanpa_word():
    """Alasan tes Word asli dilewati di komputer ini, atau "" kalau Windows + Microsoft Word ada."""
    if os.name != "nt":
        return "perlu Windows + Word asli"
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            return ""
    except FileNotFoundError:
        return "Microsoft Word tidak terpasang"
