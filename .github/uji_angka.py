"""Tes angka lewat pintu pemakai (`bahts.py cek contoh`, lalu bahan yang dibaca rakit.ps1): naskah contoh mengetik
«ص5», «1423هـ», nim «000000000», dan «آية: ٢». Tanpa @angka, semua angka di teks Arab bahan rakit harus ٠-٩
(bug yang pernah terjadi: PDF mencetak «آية: ٢» di samping «ص5» dan «1423هـ»)."""
import json, re, subprocess, sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")  # konsol Windows (cp1252) tidak bisa mencetak huruf Arab
subprocess.run([sys.executable, str(AKAR / "mesin" / "bahts.py"), "cek", "contoh"], cwd=AKAR, check=True,
               capture_output=True)
bahan = json.load(open(AKAR / "mesin" / "_tmp" / "contoh.json", encoding="utf-8"))
teks = [bahan["meta"]["nim"], *bahan["pustaka"]]
teks += [r["t"] for b in bahan["blok"] + bahan["catatan"] for r in b["runs"] if "t" in r and not r.get("q")]
latin = sorted({t for t in teks if re.search(r"[0-9]", t)})
if bahan["meta"].get("angka") != "hindi" or latin:
    sys.exit(f"angka bawaan bukan ٠-٩: @angka={bahan['meta'].get('angka')}, masih 0-9 di: {latin}")
print(f"uji angka: {len(teks)} teks, semua angka ٠-٩")
