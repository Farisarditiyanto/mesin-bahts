# SPDX-License-Identifier: AGPL-3.0-or-later
"""README.en.md dan README.ar.md = terjemahan README.md: judul `##`/`###` sama susunannya, tautan relatifnya sama,
dan tiap berkas menaut dua yang lain (pilihan bahasa).
Penjaga supaya terjemahan tidak tertinggal saat README.md diubah. Pakai: python .github/uji_readme.py [akar]"""
import re
import sys
from pathlib import Path

AKAR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
ASAL = "README.md"
TERJEMAHAN = ("README.en.md", "README.ar.md")
SEMUA = (ASAL, *TERJEMAHAN)
TAUTAN = re.compile(r"\]\((?!https?:|#)([^)\s]+)\)|src=\"(?!https?:)([^\"]+)\"")


def ciri(nama):
    teks = (AKAR / nama).read_text(encoding="utf-8")
    bagian = "".join(str(len(m.group(1))) for m in re.finditer(r"(?m)^(#{2,3}) ", teks))  # mis. «233323»
    tautan = {a or b for a, b in TAUTAN.findall(teks)}
    return bagian, sorted(tautan - set(SEMUA)), tautan & set(SEMUA)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    b1, t1, _ = ciri(ASAL)
    salah = []
    for nama in TERJEMAHAN:
        b2, t2, _ = ciri(nama)
        if b1 != b2:
            salah.append(f"susunan judul (2 = ##, 3 = ###): {ASAL} {b1}, {nama} {b2}")
        if t1 != t2:
            salah.append(f"tautan relatif beda: hanya di {ASAL} {sorted(set(t1) - set(t2))}, "
                         f"hanya di {nama} {sorted(set(t2) - set(t1))}")
    for nama in SEMUA:
        kurang = set(SEMUA) - {nama} - ciri(nama)[2]
        if kurang:
            salah.append(f"{nama} tidak menaut {sorted(kurang)} (pilihan bahasa)")
    for s in salah:
        print("GAGAL", s)
    if salah:
        sys.exit(1)
    print(f"lolos README sejajar ({', '.join(SEMUA)}): {len(b1)} judul ({b1}), {len(t1)} tautan relatif")


if __name__ == "__main__":
    main()
