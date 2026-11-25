# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pengujian perintah `pratinjau <folder> [halaman]` lewat CLI asli pada PDF contoh (tanpa Word)."""
import importlib.util, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "mesin"))
import olah
from bantu import salin_mesin

sys.stdout.reconfigure(encoding="utf8")


def utama():
    if not importlib.util.find_spec("pymupdf"):
        print("lewati uji pratinjau: pymupdf belum terpasang")
        return
    dibuat = []
    with tempfile.TemporaryDirectory(prefix="bahts-uji-pratinjau-") as t:
        akar = Path(t)
        salin_mesin(akar, (), huruf=False)
        f = akar / "uji"
        f.mkdir()
        (f / "naskah.txt").write_text("@judul: اختبار\n@berkas: hasil\n", encoding="utf8")
        pdf = AKAR / "contoh" / "jebakan" / "sumber_word.pdf"
        shutil.copyfile(pdf, f / "hasil.pdf")

        def jalankan(*arg):
            return subprocess.run(
                [sys.executable, str(akar / "mesin" / "bahts.py"), "pratinjau", "uji", *arg],
                cwd=akar, capture_output=True, encoding="utf8", timeout=60,
            )

        try:
            # Folder sementara lama (>1 jam) dibersihkan; folder baru (sesi bersamaan) tetap utuh
            lama = Path(tempfile.mkdtemp(prefix="bahts-pratinjau-uji-"))
            baru = Path(tempfile.mkdtemp(prefix="bahts-pratinjau-uji-"))
            dibuat.append(baru)
            lalu = time.time() - 7200
            os.utime(lama, (lalu, lalu))

            # Semua halaman -> grid 2×2 PNG sah di TEMP (folder bahts tetap bersih)
            r = jalankan()
            assert r.returncode == 0, r.stdout + r.stderr
            assert not lama.exists(), "folder pratinjau lama (>1 jam) tidak dibersihkan"
            assert baru.exists(), "folder pratinjau aktif (<1 jam) ikut terhapus"
            baris = [x for x in r.stdout.splitlines() if ": " in x]
            assert len(baris) >= 2 and baris[0].startswith("grid 1 (hal 1-4):"), r.stdout
            for b in baris:
                p = Path(b.split(": ", 1)[1].strip())
                dibuat.append(p.parent)
                assert p.is_file() and olah.ukuran_gambar(p) is not None, p
                assert not p.is_relative_to(f), f"pratinjau mengotori folder bahts: {p}"

            # Satu halaman -> gambar tunggal resolusi penuh
            r1 = jalankan("1")
            assert r1.returncode == 0 and r1.stdout.startswith("hal 1: "), r1.stdout + r1.stderr
            p1 = Path(r1.stdout.strip().split(": ", 1)[1])
            dibuat.append(p1.parent)
            assert p1.is_file() and olah.ukuran_gambar(p1) is not None, p1

            # Rentang halaman
            r2 = jalankan("2-3")
            assert r2.returncode == 0 and "grid 1 (hal 2-3):" in r2.stdout, r2.stdout + r2.stderr
            dibuat.append(Path(r2.stdout.strip().split(": ", 1)[1]).parent)

            # Baca-saja tanpa memeriksa kitab Shamela / membuat cache meski naskah merujuk kitab yang belum ada
            (f / "naskah.txt").write_text(
                "@judul: اختبار\n@berkas: hasil\n#K المقدمة\nنص[^مرجع، ص5. <<999999|-|5>>].\n", encoding="utf8"
            )
            rk = jalankan("1")
            assert rk.returncode == 0 and rk.stdout.startswith("hal 1: "), rk.stdout + rk.stderr
            dibuat.append(Path(rk.stdout.strip().split(": ", 1)[1]).parent)
            assert not (akar / "kitab").exists(), "pratinjau menyentuh kitab/cache"

            # Rentang salah & PDF tidak ada ditolak dengan pesan jelas
            for salah in ("0", "4-2", "999", "abc"):
                rs = jalankan(salah)
                assert rs.returncode != 0 and "Traceback" not in rs.stderr, (salah, rs.stdout + rs.stderr)
            (f / "hasil.pdf").unlink()
            rm = jalankan()
            assert rm.returncode != 0 and "belum ada" in (rm.stdout + rm.stderr), rm.stdout + rm.stderr
        finally:
            for d in dict.fromkeys(dibuat):
                shutil.rmtree(d, ignore_errors=True)

    print("lolos uji pratinjau (grid 2×2 + 1 halaman + rentang + bersihkan lama + baca-saja + galat)")


if __name__ == "__main__":
    utama()
