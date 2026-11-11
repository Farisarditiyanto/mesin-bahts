# SPDX-License-Identifier: AGPL-3.0-or-later
"""README.ar.md = terjemahan README.md: judul `##`/`###` sama susunannya dan tautan relatifnya sama.
Penjaga supaya terjemahan tidak tertinggal saat README.md diubah. Pakai: python .github/uji_readme.py [akar]"""
import re
import sys
from pathlib import Path

AKAR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
PASANGAN = ("README.md", "README.ar.md")
TAUTAN = re.compile(r"\]\((?!https?:|#)([^)\s]+)\)|src=\"(?!https?:)([^\"]+)\"")


def ciri(nama):
    teks = (AKAR / nama).read_text(encoding="utf-8")
    bagian = "".join(str(len(m.group(1))) for m in re.finditer(r"(?m)^(#{2,3}) ", teks))  # mis. «233323»
    tautan = {a or b for a, b in TAUTAN.findall(teks)} - set(PASANGAN)
    return bagian, sorted(tautan)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    (b1, t1), (b2, t2) = ciri(PASANGAN[0]), ciri(PASANGAN[1])
    salah = []
    if b1 != b2:
        salah.append(f"susunan judul (2 = ##, 3 = ###): {PASANGAN[0]} {b1}, {PASANGAN[1]} {b2}")
    if t1 != t2:
        salah.append(f"tautan relatif beda: hanya di {PASANGAN[0]} {sorted(set(t1) - set(t2))}, "
                     f"hanya di {PASANGAN[1]} {sorted(set(t2) - set(t1))}")
    for nama in PASANGAN:
        lain = PASANGAN[1] if nama == PASANGAN[0] else PASANGAN[0]
        if f"]({lain})" not in (AKAR / nama).read_text(encoding="utf-8"):
            salah.append(f"{nama} tidak menaut {lain} (pilihan bahasa)")
    for s in salah:
        print("GAGAL", s)
    if salah:
        sys.exit(1)
    print(f"lolos README sejajar: {len(b1)} judul ({b1}), {len(t1)} tautan relatif")


if __name__ == "__main__":
    main()
