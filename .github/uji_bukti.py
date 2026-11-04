# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tes `bukti` lewat pintu pemakai (`bahts.py bukti contoh`): penunjuk untuk pemeriksa langkah 5.

Yang diuji (kalau rusak, pemeriksa membaca teks yang salah tanpa sadar):
- teks kitab yang dicetak memang dari halaman yang dirujuk bukti, dan memuat kutipannya;
- bukti yang menunjuk halaman lain: dikatakan «TIDAK ketemu» dan yang dicetak awal halaman yang dirujuk itu,
  bukan halaman lain tempat kutipannya berada;
- ayat {Q:} dicetak persis teks mushaf mesin;
- `bukti contoh <baris>` hanya mencetak baris itu, dan tiap baris keluaran diawali «baris n».
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # konsol Windows (cp1252) tidak bisa mencetak huruf Arab
sys.stderr.reconfigure(encoding="utf-8")  # pesan assert juga memuat huruf Arab

REPO = Path(__file__).resolve().parent.parent
AKAR = Path(tempfile.mkdtemp(prefix="bahts-uji-bukti-"))
shutil.copytree(REPO / "mesin", AKAR / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__"))
for sid in ("_meta", "11223"):
    shutil.copytree(REPO / "kitab" / sid, AKAR / "kitab" / sid)
shutil.copytree(REPO / "contoh", AKAR / "contoh", ignore=shutil.ignore_patterns("*.docx", "*.pdf", "laporan.txt", "jebakan"))
sys.path.insert(0, str(AKAR / "mesin"))
from shamela import padat  # bentuk yang dicocokkan `cek`

KUTIPAN = "توحيد الربوبية وهو إفراد الله تعالى بالخلق والملك والتدبير"  # contoh/naskah.txt baris 15, <<11223|-|5>>
QURAN = json.loads((AKAR / "mesin" / "quran_hafs_v22.json").read_text(encoding="utf8"))


def jalan(*argumen):
    r = subprocess.run([sys.executable, str(AKAR / "mesin" / "bahts.py"), *argumen], cwd=AKAR,
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    return r.returncode, r.stdout + r.stderr


def teks_kitab(keluar, hal):
    """Teks kitab yang dicetak `bukti` untuk halaman itu (tanpa «…» dan penanda ⦗n⦘)."""
    baris = [b for b in keluar.splitlines() if f" ج- ص{hal}: " in b]
    assert len(baris) == 1, keluar
    return baris[0].split(f" ج- ص{hal}: ", 1)[1]


try:
    kode, keluar = jalan("bukti", "contoh")
    print(keluar)
    assert kode == 0, kode
    assert all(b.startswith("baris ") for b in keluar.splitlines()), "ada baris keluaran tanpa «baris n»"
    _, halaman5 = jalan("halaman", "11223", "-", "5")
    teks = teks_kitab(keluar, 5)
    assert padat(KUTIPAN) in padat(teks), "kutipan tidak ada di teks yang dicetak"
    assert padat(teks) in padat(halaman5), "teks yang dicetak bukan dari halaman 5"
    assert f"baris 14 ayat {{Q:1:2}}: ﴿{QURAN['1:2']}﴾" in keluar.splitlines(), "teks ayat tidak persis mushaf"
    print("lolos: teks dari halaman yang dirujuk, ayat persis")

    for b, tidak in ((14, 15), (15, 14)):
        kode, keluar = jalan("bukti", "contoh", str(b))
        assert kode == 0 and keluar.strip(), keluar
        assert all(x.startswith(f"baris {b} ") for x in keluar.splitlines()), f"bukti contoh {b}:\n{keluar}"
        assert f"baris {tidak} " not in keluar
    kode, keluar = jalan("bukti", "contoh", "16-30")
    assert kode == 1 and "baris 15" not in keluar, keluar
    print("lolos: hanya baris yang diminta")

    naskah = AKAR / "contoh" / "naskah.txt"
    naskah.write_text(naskah.read_text(encoding="utf-8-sig").replace("<<11223|-|5>>", "<<11223|-|6>>"), encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh", "15")
    print(keluar)
    _, halaman6 = jalan("halaman", "11223", "-", "6")
    teks = teks_kitab(keluar, 6)
    assert "TIDAK ketemu" in teks, teks
    assert padat(KUTIPAN) not in padat(teks), "halaman lain tempat kutipan berada ikut dicetak"
    assert padat(teks.split("awal halaman: ", 1)[1])[:200] == padat(halaman6)[:200], "yang dicetak bukan awal halaman 6"
    print("lolos: halaman yang salah dikatakan, tidak diganti halaman lain")
finally:
    print("arsip uji:", AKAR)

print("uji bukti: semua sesuai")
