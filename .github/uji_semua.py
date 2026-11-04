# SPDX-License-Identifier: AGPL-3.0-or-later
"""Jalankan di komputer sendiri semua tes yang dijalankan CI (`.github/workflows/tes.yml`), urut dan sama persis.

Daftarnya dibaca dari tes.yml, jadi tes baru di sana otomatis ikut dan tidak ada yang terlewat (dulu `uji_word_startup`
lupa dijalankan lokal, lalu CI Windows merah). Langkah persiapan (pip, siapkan, periksa, ambil) dilewati: kitabnya sudah
ada di komputer ini. Langkah «if: runner.os == 'Windows'» hanya jalan di Windows. Kode keluar 1 kalau ada yang gagal.
uji_halaman memeriksa semua kitab yang sudah diunduh (lokal bisa ratusan, ±26 menit) hanya kalau kode yang diujinya
berubah dibanding `main` atau diminta `--penuh`; selain itu kitab CI + sampel acak (`UJI_HALAMAN=sampel`)."""
import os, re, subprocess, sys, time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
PERSIAPAN = re.compile(r"^(pip install|python mesin/bahts\.py (siapkan|periksa|ambil)\b)")
# berkas yang perilakunya dibandingkan uji_halaman per kitab; berubah → semua kitab lokal dibandingkan
PEMICU_HALAMAN = {"mesin/shamela.py", "mesin/norma.py", "mesin/berkas.py", ".github/uji_halaman.py"}


def halaman_penuh():
    """(penuh?, alasan): semua kitab kalau --penuh, kalau berkas PEMICU_HALAMAN berubah (commit sejak main atau belum
    di-commit), atau kalau git tidak bisa menjawab."""
    if "--penuh" in sys.argv[1:]:
        return True, "--penuh"
    ubah = set()
    for perintah in (["git", "diff", "--name-only", "main...HEAD"], ["git", "diff", "--name-only", "HEAD"],
                     ["git", "ls-files", "--others", "--exclude-standard"]):
        try:
            r = subprocess.run(perintah, cwd=AKAR, capture_output=True, text=True, encoding="utf8")
        except OSError:  # git tidak terpasang (repo diunduh sebagai zip)
            return True, "git tidak terpasang"
        if r.returncode:
            return True, "git tidak bisa membandingkan dengan main"
        ubah |= set(r.stdout.split())
    kena = sorted(ubah & PEMICU_HALAMAN)
    return (True, "berubah: " + ", ".join(kena)) if kena else (False, "")


def langkah():
    """(nama, perintah, powershell?, khusus Windows?) tiap langkah `run:` di tes.yml, urut."""
    baris = (AKAR / ".github" / "workflows" / "tes.yml").read_text(encoding="utf8").splitlines()
    hasil, cur, i = [], None, 0
    while i < len(baris):
        b = baris[i]
        m = re.match(r"^(\s*)- (\w+):\s*(.*)$", b) or re.match(r"^(\s*)(\w+):\s*(.*)$", b)
        if m and b.lstrip().startswith("- "):
            cur = {"nama": None, "run": None, "ps": False, "win": False}
            hasil.append(cur)
        if m and cur is not None:
            kunci, nilai = m.group(2), m.group(3)
            if kunci == "name":
                cur["nama"] = nilai
            elif kunci == "shell":
                cur["ps"] = nilai.strip() == "powershell"
            elif kunci == "if":
                cur["win"] = "Windows" in nilai
            elif kunci == "run":
                if nilai.strip() == "|":  # blok: baris-baris yang lebih menjorok dari `run:`
                    tepi, isi = len(b) - len(b.lstrip()), []
                    while i + 1 < len(baris) and (not baris[i + 1].strip() or len(baris[i + 1]) - len(baris[i + 1].lstrip()) > tepi):
                        i += 1
                        isi.append(baris[i].strip())
                    cur["run"] = "\n".join(isi).strip()
                else:
                    cur["run"] = nilai.strip()
        i += 1
    return [(s["nama"] or s["run"], s["run"], s["ps"], s["win"]) for s in hasil
            if s["run"] and not PERSIAPAN.match(s["run"])]


def utama():
    sys.stdout.reconfigure(encoding="utf-8")
    gagal = []
    penuh, alasan = halaman_penuh()
    if penuh:
        os.environ.pop("UJI_HALAMAN", None)
        print(f"uji_halaman: semua kitab lokal ({alasan})", flush=True)
    else:
        os.environ["UJI_HALAMAN"] = "sampel"
    for nama, perintah, ps, win in langkah():
        if win and os.name != "nt":
            print(f"lewati (khusus Windows): {nama}")
            continue
        mulai = time.monotonic()
        if ps:
            r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", perintah], cwd=AKAR)
        else:
            r = subprocess.run(perintah, shell=True, cwd=AKAR)
        detik = time.monotonic() - mulai
        print(f"{'lolos' if r.returncode == 0 else 'GAGAL'} ({detik:.0f} dtk): {nama}", flush=True)
        if r.returncode:
            gagal.append(nama)
    print(f"uji semua: {len(gagal)} gagal" + (": " + "; ".join(gagal) if gagal else ""))
    sys.exit(1 if gagal else 0)


if __name__ == "__main__":
    utama()
