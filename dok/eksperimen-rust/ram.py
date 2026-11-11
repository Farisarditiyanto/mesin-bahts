# SPDX-License-Identifier: AGPL-3.0-or-later
"""Measure OS process peak RAM; each mode/workload runs in a fresh child."""
import argparse
import contextlib
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import runpy
import statistics
import subprocess
import sys
import tempfile
import time

import psutil
from jalankan import AKAR, norma, pasang


def peak_bytes():
    info = psutil.Process().memory_info()
    if os.name == "nt":
        return info.peak_wset
    import resource
    n = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return n if sys.platform == "darwin" else n * 1024


def worker(job):
    pasang(job["mode"], Path(job["library"]) if job.get("library") else None)
    proc = psutil.Process()
    baseline = proc.memory_info().rss
    start = time.perf_counter()
    digest = hashlib.sha256()
    status = 0
    if job["kind"] == "cli":
        sys.argv = [str(AKAR / "mesin/bahts.py"), "cek", job["folder"]]
        with tempfile.TemporaryFile(mode="w+", encoding="utf8") as out, tempfile.TemporaryFile(mode="w+", encoding="utf8") as err:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    runpy.run_path(sys.argv[0], run_name="__main__")
                except SystemExit as e:
                    if e.code is None or isinstance(e.code, int):
                        status = e.code or 0
                    else:
                        status = 1
                        print(e.code, file=err)
            out.seek(0); err.seek(0)
            # Digest used privately by parent only; never emitted in the public result.
            digest.update((out.read() + "\0" + err.read()).encode("utf8"))
    else:
        text = "هذا نص عربي تجريبي لفحص حجم الذاكرة مع اختلاف المدخلات وتكرارها. "
        length = 8192 if job["kind"] != "unique-small" else 64
        paragraph = (text * (length // len(text) + 1))[:length]
        for i in range(8192):
            s = paragraph if job["kind"] == "repeated-long" else f"{i}:" + paragraph
            for fn in (norma.norm, norma.padat):
                digest.update(fn(s).encode("utf8"))
    duration = time.perf_counter() - start
    gc.collect()
    result = {"baseline_rss_bytes": baseline, "peak_rss_bytes": peak_bytes(),
              "retained_rss_bytes": proc.memory_info().rss, "seconds": duration,
              "status": status, "digest": digest.hexdigest(), "caches": {}}
    for name in ("norm", "padat"):
        fn = getattr(norma, name)
        if hasattr(fn, "cache_info"):
            result["caches"][name] = fn.cache_info()._asdict()
            fn.cache_clear()
    gc.collect()
    result["rss_after_clear_bytes"] = proc.memory_info().rss
    print(json.dumps(result))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--library", type=Path, required=True)
    p.add_argument("--folder", type=Path, action="append", default=[])
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--scope", choices=("all", "synthetic", "cli"), default="all")
    args = p.parse_args()
    if args.scope == "cli" and not args.folder:
        p.error("--scope cli requires at least one --folder")
    for folder in args.folder:
        if not folder.resolve().is_relative_to(AKAR) or not (folder / "naskah.txt").is_file():
            p.error("Every --folder must contain naskah.txt inside the repository")
    modes = ("python", "cache", "rust", "rust-cache")
    jobs = [(name, {"kind": name}) for name in ("unique-small", "unique-long", "repeated-long")] if args.scope != "cli" else []
    if args.scope != "synthetic":
        jobs += [(f"manuscript-{i + 1}", {"kind": "cli", "folder": str(f)}) for i, f in enumerate(args.folder)]
    result = {"platform": platform.platform(), "python": platform.python_version(), "unit": "bytes", "workloads": []}
    rng = random.Random(20261111)
    for label, job in jobs:
        samples = {mode: [] for mode in modes}
        reference = None
        for _ in range(3):
            order = list(modes)
            rng.shuffle(order)
            for mode in order:
                task = dict(job, mode=mode, library=str(args.library.resolve()))
                child = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker"], input=json.dumps(task), capture_output=True, text=True, encoding="utf8")
                if child.returncode:
                    raise RuntimeError(child.stderr)
                data = json.loads(child.stdout)
                if job["kind"] == "cli" and data["status"] != 0:
                    raise RuntimeError(f"CLI workload {label} failed with status {data['status']}; no result published")
                equality = (data.pop("digest"), data["status"])
                if reference is None:
                    reference = equality
                assert equality == reference, f"Outputs differ: {label}/{mode}"
                samples[mode].append(data)
        entry = {"workload": label, "output_equal": True, "modes": {}}
        for mode, values in samples.items():
            entry["modes"][mode] = {"median_peak_rss_bytes": statistics.median(v["peak_rss_bytes"] for v in values), "samples": values}
        result["workloads"].append(entry)
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8", newline="\n")
        print(label, {m: round(v["median_peak_rss_bytes"] / 1048576, 1) for m, v in entry["modes"].items()}, flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["--worker"]:
        worker(json.loads(sys.stdin.read()))
    else:
        main()
