# SPDX-License-Identifier: AGPL-3.0-or-later
"""Perintah kitab lewat pintu pemakai (`python mesin/bahts.py …`), untuk kerusakan yang diam-diam menyesatkan agent:
- `halaman` tidak mencetak «\\r» mentah Shamela: di konsol atau saat disalin «\\r» hilang, dua kata tersambung
  («نستعينالحمد»), lalu agent menyalinnya ke naskah dan `cek` meloloskannya karena spasi dipadatkan (kitab 11223 ص3);
- argumen atau bendera di luar bentuk perintah ditolak (kode keluar 1, tanpa hasil), bukan ditelan diam-diam:
  `katalog … --mazhab` dulu tidak tersaring, `cari <id> … --kitab` mencari di kitab pertama, `halaman … 8 9` mengabaikan 9.
Kitabnya kitab CI (baris `ambil` di tes.yml)."""
import subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
AKAR = Path(__file__).resolve().parent.parent


def jalankan(*a):
    r = subprocess.run([sys.executable, str(AKAR / "mesin" / "bahts.py"), *a], cwd=AKAR, capture_output=True)
    # «\r\n» = akhir baris konsol Windows; «\r» lain berasal dari teks kitab
    return r.returncode, *(x.decode("utf8").replace("\r\n", "\n") for x in (r.stdout, r.stderr))


gagal = []
kode, out, err = jalankan("halaman", "11223", "-", "3")
if kode or "\r" in out:
    gagal.append(f"halaman 11223 - 3: kode {kode}, «\\r» mentah {out.count(chr(13))}")
if not any(b.startswith("الحمد لله، نحمده") for b in out.split("\n")):
    gagal.append("halaman 11223 - 3: «الحمد لله، نحمده» tidak mulai di baris sendiri (tersambung ke «﷽»)")

for a in (["halaman", "11223", "-", "3", "4"],
          ["katalog", "القضاء والقدر", "--mazhab", "hanbali"],
          ["cari", "11223", "الحمد", "--kitab", "2348"],
          ["kartu", "11223", "2348"],
          ["teks", "11223", "الحمد", "100", "2", "9"]):
    kode, out, err = jalankan(*a)
    if kode != 1 or out.strip() or "berlebih" not in err:
        gagal.append(f"{' '.join(a)}: harus ditolak (kode 1, tanpa hasil); kode {kode}, keluaran {out[:80]!r}, galat {err[:80]!r}")

for g in gagal:
    print("✗ " + g)
print(f"perintah: {len(gagal)} gagal")
sys.exit(1 if gagal else 0)
