"""Tes angka lewat pintu pemakai (`bahts.py cek`, lalu bahan yang dibaca rakit.ps1): naskah contoh mengetik
«ص5», «1423هـ», nim «000000000», dan «آية: ٢». Tanpa @angka, semua angka di teks Arab bahan rakit harus ٠-٩
(bug yang pernah terjadi: PDF mencetak «آية: ٢» di samping «ص5» dan «1423هـ»).
Dengan «@angka_ayat: latin», hanya catatan kaki rujukan ayat yang 0-9 (dan ditandai "al" untuk rakit.ps1); sisanya tetap ٠-٩."""
import json, re, shutil, subprocess, sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")  # konsol Windows (cp1252) tidak bisa mencetak huruf Arab


def bahan(nama):
    subprocess.run([sys.executable, str(AKAR / "mesin" / "bahts.py"), "cek", nama], cwd=AKAR, check=True,
                   capture_output=True)
    return json.load(open(AKAR / "mesin" / "_tmp" / f"{nama}.json", encoding="utf-8"))


def teks_latin(b, kecuali=lambda c: False):
    teks = [b["meta"]["nim"], *b["pustaka"]]
    teks += [r["t"] for x in b["blok"] + [c for c in b["catatan"] if not kecuali(c)] for r in x["runs"]
             if "t" in r and not r.get("q")]
    return teks, sorted({t for t in teks if re.search(r"[0-9]", t)})


b = bahan("contoh")
teks, latin = teks_latin(b)
if b["meta"].get("angka") != "hindi" or latin:
    sys.exit(f"angka bawaan bukan ٠-٩: @angka={b['meta'].get('angka')}, masih 0-9 di: {latin}")
print(f"uji angka: {len(teks)} teks, semua angka ٠-٩")

uji = AKAR / "_uji_angka_ayat"  # di dalam folder mesin (syarat `cek`), diabaikan git
uji.mkdir(exist_ok=True)
try:
    naskah = (AKAR / "contoh" / "naskah.txt").read_text(encoding="utf-8")
    (uji / "naskah.txt").write_text("@angka_ayat: latin\n" + naskah, encoding="utf-8")
    b = bahan(uji.name)
    ayat = [c for c in b["catatan"] if "".join(r.get("t", "") for r in c["runs"]).startswith("سورة")]
    salah = ["".join(r.get("t", "") for r in c["runs"]) for c in ayat
             if not c.get("al") or re.search("[٠-٩]", "".join(r.get("t", "") for r in c["runs"]))]
    if not ayat or salah:
        sys.exit(f"@angka_ayat: latin: catatan kaki ayat harus 0-9 dan bertanda al: {salah or 'tidak ada catatan kaki ayat'}")
    teks, latin = teks_latin(b, kecuali=lambda c: c in ayat)
    if latin:
        sys.exit(f"@angka_ayat: latin ikut mengubah selain catatan kaki ayat: {latin}")
    print(f"uji angka_ayat: {len(ayat)} catatan kaki ayat 0-9, {len(teks)} teks lain tetap ٠-٩")
finally:
    shutil.rmtree(uji)
