# SPDX-License-Identifier: AGPL-3.0-or-later
"""README.en.md dan README.ar.md = terjemahan README.md: judul `##`/`###` sama susunannya, tautan relatifnya sama,
baris pilihan bahasa di kepala tiap berkas menaut dua yang lain, dan tiap tautan jangkar `(#…)` menunjuk judul yang ada.
Penjaga supaya terjemahan tidak tertinggal saat README.md diubah. Pakai: python .github/uji_readme.py [akar]"""
import re
import sys
from pathlib import Path

AKAR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
ASAL = "README.md"
TERJEMAHAN = ("README.en.md", "README.ar.md")
SEMUA = (ASAL, *TERJEMAHAN)
TAUTAN = re.compile(r"\]\((?!https?:|#)([^)\s]+)\)|src=\"(?!https?:)([^\"]+)\"")
KEPALA = 5  # baris pilihan bahasa ada di sini; tautan antar-README di bagian bawah tidak dihitung


def jangkar(judul):
    """Id judul buatan GitHub: huruf kecil, tanda baca dibuang, spasi jadi «-»."""
    return re.sub(r"[^\w\- ]", "", judul.strip().lower()).replace(" ", "-")


def ciri(nama):
    teks = (AKAR / nama).read_text(encoding="utf-8")
    judul = re.findall(r"(?m)^(#{1,6}) (.+)$", teks)
    bagian = "".join(str(len(pagar)) for pagar, _ in judul if len(pagar) in (2, 3))  # mis. «233323»
    tautan = {a or b for a, b in TAUTAN.findall(teks)} - set(SEMUA)
    bahasa = {a for a, _ in TAUTAN.findall("\n".join(teks.splitlines()[:KEPALA]))} & set(SEMUA)
    putus = set(re.findall(r"\]\(#([^)\s]+)\)", teks)) - {jangkar(isi) for _, isi in judul}
    return bagian, sorted(tautan), bahasa, sorted(putus)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    b1, t1, _, _ = ciri(ASAL)
    salah = []
    for nama in SEMUA:
        b2, t2, bahasa, putus = ciri(nama)
        if b1 != b2:
            salah.append(f"susunan judul (2 = ##, 3 = ###): {ASAL} {b1}, {nama} {b2}")
        if t1 != t2:
            salah.append(f"tautan relatif beda: hanya di {ASAL} {sorted(set(t1) - set(t2))}, "
                         f"hanya di {nama} {sorted(set(t2) - set(t1))}")
        kurang = set(SEMUA) - {nama} - bahasa
        if kurang:
            salah.append(f"{nama}: {KEPALA} baris pertama tidak menaut {sorted(kurang)} (pilihan bahasa)")
        if putus:
            salah.append(f"{nama}: tautan jangkar tanpa judul {putus}")
    for s in salah:
        print("GAGAL", s)
    if salah:
        sys.exit(1)
    print(f"lolos README sejajar ({', '.join(SEMUA)}): {len(b1)} judul ({b1}), {len(t1)} tautan relatif")


if __name__ == "__main__":
    main()
