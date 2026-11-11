# SPDX-License-Identifier: AGPL-3.0-or-later
"""Opt-in experiment. Never changes mesin/, its rules, or the installed Python."""
import argparse
import functools
import importlib
import importlib.util
import runpy
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "mesin"))
import norma


def pasang(mode, library=None):
    if mode == "python":
        return
    if mode == "cache":
        norma.norm = functools.lru_cache(maxsize=4096)(norma.norm)
        norma.padat = functools.lru_cache(maxsize=4096)(norma.padat)
        return
    if library is None:
        module = importlib.import_module("_bahts_rust")
    else:
        spec = importlib.util.spec_from_file_location("_bahts_rust", library)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    names = ("TAGS", "HARAKAT", "HORMAT", "LIGATUR_HORMAT", "PRESENTASI", "SYAI", "SYAI_TANPA_HAMZAH", "IBNU", "BUKAN_HURUF", "BUKAN_ABJAD")
    native = module.Normalizer({k: getattr(norma, k).pattern for k in names}, norma.SAMA, norma.EJAAN, norma.unicodedata.normalize)
    norma.norm, norma.padat = native.norm, native.padat
    if mode == "rust-cache":
        norma.norm = functools.lru_cache(maxsize=4096)(norma.norm)
        norma.padat = functools.lru_cache(maxsize=4096)(norma.padat)


def utama():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("python", "cache", "rust", "rust-cache"), required=True)
    parser.add_argument("--library", type=Path)
    parser.add_argument("script", type=Path)
    args, rest = parser.parse_known_args()
    pasang(args.mode, args.library)
    sys.argv = [str(args.script), *rest]
    sys.path.insert(0, str(args.script.resolve().parent))
    runpy.run_path(str(args.script), run_name="__main__")


if __name__ == "__main__":
    utama()
