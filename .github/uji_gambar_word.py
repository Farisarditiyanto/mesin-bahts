# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regresi #G dan @malahiq: akhir lewat `rakit` dan Word asli.

Gambar #G harus masuk DOCX dengan keterangannya, dan bagian «#K الملاحق» harus tercetak sesudah المصادر والمراجع
(halaman penanda PUSTAKAMARK < LAMPIRANMARK). Runner tanpa Word melaporkan lewati. Semua bahan tinggal di TEMP.
"""
import os, shutil, struct, subprocess, sys, tempfile, zipfile, zlib
from pathlib import Path

from pypdf import PdfReader

AKAR = Path(__file__).resolve().parent.parent


def png(lebar, tinggi):
    """PNG putih polos (tanpa pustaka gambar)."""
    baris = b"".join(b"\x00" + b"\xff\xff\xff" * lebar for _ in range(tinggi))

    def potong(jenis, isi):
        return struct.pack(">I", len(isi)) + jenis + isi + struct.pack(">I", zlib.crc32(jenis + isi) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + potong(b"IHDR", struct.pack(">IIBBBBB", lebar, tinggi, 8, 2, 0, 0, 0))
            + potong(b"IDAT", zlib.compress(baris)) + potong(b"IEND", b""))


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if os.name != "nt":
        print("lewati uji gambar Word: perlu Windows + Word asli")
        return
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            pass
    except FileNotFoundError:
        print("lewati uji gambar Word: Microsoft Word tidak terpasang")
        return
    with tempfile.TemporaryDirectory(prefix="bahts-gambar-word-") as t:
        akar = Path(t)
        shutil.copytree(AKAR / "mesin", akar / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__"))
        folder = akar / "uji"
        folder.mkdir()
        (folder / "lebar.png").write_bytes(png(3000, 600))   # lebih lebar dari halaman: harus dikecilkan
        (folder / "tinggi.png").write_bytes(png(300, 3000))  # lebih tinggi dari halaman: harus dikecilkan
        teks = ("@bentuk: kitab\n@judul: اختبار\n@berkas: uji\n@angka: latin\n@malahiq: akhir\n"
                "#K المقدمة\nAWALMARK فقرة أولى، والشكل الآتي:\n"
                "#G lebar.png | GAMBARMARK الشكل الأول\n"
                "فقرة بعد الشكل، والشكل الثاني:\n"
                "#G tinggi.png |\n"
                "#K الخاتمة\nAKHIRMARK فقرة الخاتمة.\n"
                "#K الملاحق\nLAMPIRANMARK فقرة الملحق.\n"
                "#R المصادر والمراجع\nPUSTAKAMARK كتاب تجريبي.\n")
        (folder / "naskah.txt").write_text(teks, encoding="utf8")
        r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), "rakit", "uji"], cwd=akar,
                           capture_output=True, encoding="utf8", timeout=1800)
        assert r.returncode == 0 and (folder / "uji.pdf").is_file(), r.stdout + r.stderr
        # pengantar «…الآتي:» yang disusul gambar di halaman yang sama bukan pengantar yang terpisah dari isinya
        assert "berakhir «:»" not in r.stdout, r.stdout
        halaman = {}
        for n, p in enumerate(PdfReader(folder / "uji.pdf").pages, 1):
            isi = p.extract_text()
            for tanda in ("AWALMARK", "GAMBARMARK", "AKHIRMARK", "PUSTAKAMARK", "LAMPIRANMARK"):
                if tanda in isi:
                    halaman.setdefault(tanda, n)
        assert len(halaman) == 5, halaman
        assert halaman["AKHIRMARK"] < halaman["PUSTAKAMARK"] < halaman["LAMPIRANMARK"], f"urutan halaman {halaman}"
        with zipfile.ZipFile(folder / "uji.docx") as z:
            media = [n for n in z.namelist() if n.startswith("word/media/")]
        assert len(media) >= 2, f"gambar di DOCX: {media}"
        print(f"lolos gambar Word: {len(media)} gambar; halaman {halaman}", flush=True)


if __name__ == "__main__":
    utama()
