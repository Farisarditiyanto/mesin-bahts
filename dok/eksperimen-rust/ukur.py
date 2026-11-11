# SPDX-License-Identifier: AGPL-3.0-or-later
"""Differential experiments through the real normalizer, Padat builder and CLI.

Public output contains aggregates only, never manuscript text or its path.
"""
import argparse
import gc
import gzip
import hashlib
import json
import os
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

from jalankan import AKAR, norma, pasang

SEED = 20261111


def sample_books():
    books = sorted((AKAR / "kitab").glob("*/pages.jsonl.gz"))
    if not books:
        raise RuntimeError("No local books; run bahts.py ambil first")
    chosen = books[::max(1, len(books) // 24)]
    texts = []
    for book in chosen:
        with gzip.open(book, "rt", encoding="utf8") as f:
            for i, line in enumerate(f):
                if i >= 1024:
                    break
                if i % 16 == 0:
                    page = json.loads(line)
                    texts.extend(page.get(k) or "" for k, _ in norma.BAGIAN)
    manifest = [{"book_id": p.parent.name, "pages_sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in chosen]
    return texts, len(chosen), manifest


def fuzz(texts):
    rng = random.Random(SEED)
    alphabet = "".join(chr(i) for i in range(0x600, 0x700)) + " <>/b\n\t01239" + "﷽ﷺﷻ﵀﷾﷿ﻻﻹﻷﻵﷲیھکە🦀\x00"
    cases = ["", "شئ شي وشي وبالشي يمشي شيئا ابن ابنه وابن", "رضي الله عنهما صلى الله عليه وآله وسلم"]
    # Exercise every scalar in the presentation ranges, both alone and in context.
    ranges = [(0x675, 0x679), (0xFB50, 0xFDFD), (0xFE70, 0xFEFD)]
    for a, z in ranges:
        for i in range(a, z):
            cases.extend([chr(i), "أَشي " + chr(i) + " ابن ９"])
    for _ in range(12000):
        cases.append("".join(rng.choices(alphabet, k=rng.randrange(0, 100))))
    for _ in range(4000):
        t = rng.choice(texts)
        a = rng.randrange(len(t) + 1)
        cases.append(t[a:a + rng.randrange(0, 500)])
    return cases


def median_run(work, repeats=5):
    samples = []
    for _ in range(repeats):
        gc.collect()
        start = time.perf_counter()
        work()
        samples.append(time.perf_counter() - start)
    return {"median_seconds": statistics.median(samples), "samples_seconds": samples}


def run_cli(mode, library, args):
    command = [sys.executable, str(Path(__file__).with_name("jalankan.py")), "--mode", mode]
    if mode.startswith("rust"):
        command += ["--library", str(library)]
    command += [str(AKAR / "mesin" / "bahts.py"), *args]
    start = time.perf_counter()
    p = subprocess.run(command, cwd=AKAR, capture_output=True, timeout=600)
    return time.perf_counter() - start, (p.returncode, p.stdout, p.stderr)


def cache_lengkap(original, native, source):
    """Real cache entry point, cache absent; OS file cache may still be warm."""
    modes = {"python": original, "rust": native}
    samples = {k: [] for k in modes}
    rng = random.Random(SEED)
    expected = None
    for _ in range(5):
        order = list(modes)
        rng.shuffle(order)
        for mode in order:
            norma.norm, norma.padat = modes[mode]
            with tempfile.TemporaryDirectory(prefix="bahts-rust-cold-") as d:
                folder = Path(d)
                shutil.copyfile(source, folder / "pages.jsonl.gz")
                start = time.perf_counter()
                norma.cache(folder)
                samples[mode].append(time.perf_counter() - start)
                digest = hashlib.sha256((folder / f"padat-{norma.VERSI}.bin").read_bytes()).hexdigest()
                if expected is None:
                    expected = digest
                assert digest == expected, "Full cache bytes differ"
    return {"book_id": int(source.parent.name), "serialized_sha256": expected,
            "serialized_bytes_equal": True, "os_disk_cache": "warm / uncontrolled",
            "modes": {k: {"median_seconds": statistics.median(s), "samples_seconds": s} for k, s in samples.items()}}


def utama():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--folder", type=Path, action="append", default=[])
    args = parser.parse_args()
    for folder in args.folder:
        if not (folder / "naskah.txt").is_file():
            parser.error(f"No naskah.txt in {folder}")
    sys.stdout.reconfigure(encoding="utf8")
    original = norma.norm, norma.padat
    texts, books, manifest = sample_books()
    cases = texts + fuzz(texts)
    expected = [(original[0](s), original[1](s)) for s in cases]
    pasang("rust", args.library)
    native = norma.norm, norma.padat
    mismatches = []
    for i, (s, want) in enumerate(zip(cases, expected)):
        got = native[0](s), native[1](s)
        if got != want:
            mismatches.append(i)
            if len(mismatches) <= 3:
                print(f"DIFFERENCE case {i}: {s!r} -> {got!r} expected {want!r}", flush=True)
    unicode_cases = 0
    for n in range(sys.maxunicode + 1):
        if 0xd800 <= n <= 0xdfff:  # Surrogates are not Unicode scalar values / valid UTF-8 input.
            continue
        s = chr(n) + " ﻻ"  # Force NFKC over the entire string, as the Python implementation does.
        unicode_cases += 1
        if original[0](s) != native[0](s):
            mismatches.append(f"U+{n:04X}")
    result = {
        "seed": SEED, "python": platform.python_version(), "platform": platform.platform(),
        "cpu": platform.processor(), "norma_sha256": hashlib.sha256((AKAR / "mesin" / "norma.py").read_bytes()).hexdigest(),
        "python_unicode": unicodedata.unidata_version,
        "native_source_sha256": hashlib.sha256(Path(__file__).with_name("src").joinpath("lib.rs").read_bytes()).hexdigest(),
        "binary_sha256": hashlib.sha256(args.library.read_bytes()).hexdigest(),
        "corpus": {"books": books, "strings": len(texts), "characters": sum(map(len, texts)), "manifest": manifest},
        "parity": {"cases": len(cases), "functions": 2, "mismatches": len(mismatches)},
        "unicode_scalar_cases": unicode_cases,
        "normalization": {}, "padat_build": {}, "cli": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if mismatches:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8", newline="\n")
        raise SystemExit("Parity failed; no performance claim allowed")
    print(f"parity: {len(cases)} strings × 2 functions, zero differences", flush=True)
    for mode, functions in (("python", original), ("rust", native)):
        norma.norm, norma.padat = functions
        result["normalization"][mode] = {}
        for i, name in enumerate(("norm", "padat")):
            result["normalization"][mode][name] = median_run(lambda: [functions[i](s) for s in texts])
            print("normalization", mode, name, result["normalization"][mode][name]["median_seconds"], flush=True)
    source = AKAR / "kitab" / "1727" / "pages.jsonl.gz"
    pages = list(norma.rekaman(source))
    built = {}
    for mode, functions in (("python", original), ("rust", native)):
        norma.norm, norma.padat = functions
        def build():
            # Fresh records each time: do not time already-populated _padat_ caches.
            built[mode] = norma.Padat.buat([dict(p) for p in pages])
        result["padat_build"][mode] = median_run(build)
        print("padat build", mode, result["padat_build"][mode]["median_seconds"], flush=True)
    with tempfile.TemporaryDirectory(prefix="bahts-rust-cache-") as d:
        contents = []
        for mode, obj in built.items():
            path = Path(d) / mode
            obj.tulis(path, "same-source")
            contents.append(path.read_bytes())
        assert contents[0] == contents[1], "Serialized cache differs"
    result["padat_build"].update(book_id=1727, records=len(pages), serialized_bytes_equal=True)
    result["full_cache"] = cache_lengkap(original, native, source)
    print("full cache", {k: v["median_seconds"] for k, v in result["full_cache"]["modes"].items()}, flush=True)
    workloads = [("example", ["cek", "contoh"]), ("traps", ["cek", "contoh/jebakan"])]
    workloads += [(f"manuscript-{i + 1}", ["cek", str(folder)]) for i, folder in enumerate(args.folder)]
    workloads += [("local-search-miss", ["cari", "11223", "الإخلاص"]),
                  ("local-search-hit", ["cari", "11223", "الربوبية"]),
                  ("page", ["halaman", "11223", "-", "5"])]
    rng = random.Random(SEED)
    for label, command in workloads:
        samples = {m: [] for m in ("python", "rust", "cache", "rust-cache")}
        reference = None
        for _ in range(7):
            order = list(samples)
            rng.shuffle(order)
            for mode in order:
                duration, output = run_cli(mode, args.library, command)
                if reference is None:
                    reference = output
                if output != reference:
                    raise AssertionError(f"CLI output differs: {label}/{mode}")
                samples[mode].append(duration)
        entry = {"workload": label, "output_equal": True, "returncode": reference[0], "modes": {
            m: {"median_seconds": statistics.median(s), "samples_seconds": s} for m, s in samples.items()}}
        result["cli"].append(entry)
        print(label, {m: round(statistics.median(s), 4) for m, s in samples.items()}, flush=True)
    result["binary_bytes"] = args.library.stat().st_size
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8", newline="\n")
    print("saved", args.output, flush=True)


if __name__ == "__main__":
    utama()
