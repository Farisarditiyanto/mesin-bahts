# SPDX-License-Identifier: AGPL-3.0-or-later
"""Jalankan di komputer sendiri semua tes yang dijalankan CI (`.github/workflows/tes.yml`), urut dan sama persis.

Daftarnya dibaca dari tes.yml, jadi tes baru di sana otomatis ikut dan tidak ada yang terlewat. Langkah persiapan (pip, siapkan, periksa, ambil) dilewati: kitabnya sudah
ada di komputer ini. Langkah «if: runner.os == 'Windows'» hanya jalan di Windows. Kode keluar 1 kalau ada yang gagal.
uji_halaman memakai kitab CI secara tetap; `--penuh` secara eksplisit membandingkan seluruh pustaka lokal.
Jumlah kitab pemakai dan perubahan cabang tidak mengubah cakupan tes rutin."""
import os, re, subprocess, sys, time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
PERSIAPAN = re.compile(r"^(pip install|python mesin/bahts\.py (siapkan|periksa|ambil)\b)")


def kitab_ci():
    """Nomor kitab tes dari baris `ambil` workflow; dipakai tes halaman dan salinan tes perintah."""
    yml = (AKAR / ".github" / "workflows" / "tes.yml").read_text(encoding="utf8")
    nomor = sorted({int(x) for m in re.finditer(r"bahts\.py ambil ([\d ]+)", yml) for x in m.group(1).split()})
    if not nomor:
        raise RuntimeError("Daftar kitab CI tidak terbaca dari tes.yml")
    return nomor


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
    os.environ["UJI_HALAMAN"] = "penuh" if "--penuh" in sys.argv[1:] else "ci"
    print(f"uji_halaman: mode {os.environ['UJI_HALAMAN']}", flush=True)
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
