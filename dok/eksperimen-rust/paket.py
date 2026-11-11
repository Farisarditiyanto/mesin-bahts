# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build an experimental wheel in temp, then install it into a fresh venv."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def worker():
    # This branch executes inside the clean venv: the installed wheel supplies Rust.
    import _bahts_rust
    sys.path.insert(0, str(HERE))
    from jalankan import norma, pasang
    old = norma.norm, norma.padat
    rng = random.Random(20261111)
    alphabet = "".join(chr(i) for i in range(0x600, 0x700)) + "﷽ﷺﻻ ﷲABC09\n<>"
    cases = ["", "شئ شي ابن سماوات", "﷽ صلى الله عليه وسلم", (ROOT / "contoh/naskah.txt").read_text(encoding="utf8")]
    cases += ["".join(rng.choices(alphabet, k=rng.randrange(200))) for _ in range(12000)]
    expected = [(old[0](s), old[1](s)) for s in cases]
    pasang("rust")
    assert [(norma.norm(s), norma.padat(s)) for s in cases] == expected
    scalars = 0
    for n in range(sys.maxunicode + 1):
        if 0xd800 <= n <= 0xdfff:
            continue
        s = chr(n) + " ﻻ"
        assert old[0](s) == norma.norm(s), hex(n)
        scalars += 1
    print(json.dumps({"python": platform.python_version(), "platform": platform.platform(),
                      "arch": platform.machine(), "cases": len(cases), "unicode_scalars": scalars,
                      "mismatches": 0, "installed_module": Path(_bahts_rust.__file__).name}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--interpreter", type=Path, action="append", default=[])
    parser.add_argument("--wheel", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    result = {"platform": platform.platform(), "arch": platform.machine(), "installs": []}
    wheel = args.wheel
    if wheel is None:
        with tempfile.TemporaryDirectory(prefix="bahts-wheel-build-") as d:
            build = Path(d)
            for name in ("Cargo.toml", "Cargo.lock", "pyproject.toml", "src"):
                src, dst = HERE / name, build / name
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copyfile(src, dst)
            # Include the actual repository license without maintaining a second source copy.
            shutil.copyfile(ROOT / "LICENSE", build / "LICENSE")
            env = os.environ.copy()
            env.setdefault("CARGO_TARGET_DIR", str(build / "target"))
            start = time.perf_counter()
            subprocess.run(["maturin", "build", "--release", "--locked", "--interpreter", sys.executable,
                            "--manifest-path", str(build / "Cargo.toml"), "--out", str(args.out.resolve())], env=env, check=True)
            result["build_seconds"] = time.perf_counter() - start
        wheels = list(args.out.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError("Use a fresh output folder containing exactly one wheel")
        wheel = wheels[0]
    result.update(wheel=wheel.name, wheel_bytes=wheel.stat().st_size, wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest())
    with zipfile.ZipFile(wheel) as z:
        license_files = [n for n in z.namelist() if "/licenses/" in n or n.endswith("/LICENSE")]
        assert license_files, "Wheel must include repository license"
        assert any((ROOT / "LICENSE").read_bytes() == z.read(n) for n in license_files), "Wrong license text"
        result["license_included"] = True
    for interpreter in args.interpreter or [Path(sys.executable)]:
        with tempfile.TemporaryDirectory(prefix="bahts-wheel-install-") as d:
            envdir = Path(d) / "venv"
            subprocess.run([str(interpreter), "-m", "venv", str(envdir)], check=True)
            python = envdir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            subprocess.run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel.resolve())], check=True)
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            # Keep the installer independent of toolchain availability.
            env["PATH"] = str(python.parent)
            start = time.perf_counter()
            p = subprocess.run([str(python), str(Path(__file__).resolve()), "--worker"], env=env, capture_output=True, text=True, encoding="utf8")
            if p.returncode:
                raise RuntimeError(f"Clean-venv verification failed: {p.stderr}")
            data = json.loads(p.stdout)
            data["validation_seconds"] = time.perf_counter() - start
            data["no_rust_on_path"] = shutil.which("rustc", path=env["PATH"]) is None
            assert data["no_rust_on_path"]
            result["installs"].append(data)
    (args.out / "paket.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8", newline="\n")
    print(json.dumps(result))


if __name__ == "__main__":
    if sys.argv[1:] == ["--worker"]:
        worker()
    else:
        main()
