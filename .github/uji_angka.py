# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tes angka lewat pintu pemakai (`bahts.py cek`, lalu bahan yang dibaca rakit.ps1): naskah contoh mengetik
«ص5», «1423هـ», nim «123456789» (contoh sendiri «-»: tidak tercetak), dan «آية: ٢». Tanpa @angka, semua angka di teks Arab bahan rakit harus ٠-٩
(bug yang pernah terjadi: PDF mencetak «آية: ٢» di samping «ص5» dan «1423هـ»).
Dengan «@angka_ayat: latin», hanya catatan kaki rujukan ayat yang 0-9 (dan ditandai "al" untuk rakit.ps1); sisanya tetap ٠-٩.
Dengan «@angka: latin», semua angka di teks Arab bahan rakit 0-9 (mesin/olah.py, _format_dan_angka: ubah = latin).
Tautan/DOI di catatan kaki tetap 0-9 dan titiknya tetap, juga DOI tanpa huruf di depannya, dan pola "tautan" bahan
(dipakai rakit.ps1 untuk mencetaknya kiri-ke-kanan) menangkap seluruhnya tanpa titik penutup kalimat (bug yang pernah
terjadi: PDF mencetak «doi.org/١٠,٢١٦٠٨/jasis.٢٠٢١,١٨٣١٣١»)."""
import json, re, shutil, subprocess, sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "mesin"))
from berkas import bahan as alamat_bahan
sys.stdout.reconfigure(encoding="utf-8")  # konsol Windows (cp1252) tidak bisa mencetak huruf Arab


def bahan(nama):
    subprocess.run([sys.executable, str(AKAR / "mesin" / "bahts.py"), "cek", nama], cwd=AKAR, check=True,
                   capture_output=True)
    return json.loads(alamat_bahan(AKAR / nama).read_text(encoding="utf8"))


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

uji = AKAR / "_uji_angka_ayat"  # akar repo = parent.parent uji_angka.py (folder bahts; syarat `cek`), diabaikan git
uji.mkdir(exist_ok=True)
try:
    naskah = (AKAR / "contoh" / "naskah.txt").read_text(encoding="utf-8").replace("@nim: -", "@nim: 123456789")
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

uji = AKAR / "_uji_angka"  # folder bahts baru; diabaikan git
uji.mkdir(exist_ok=True)
try:
    naskah = (AKAR / "contoh" / "naskah.txt").read_text(encoding="utf-8").replace("@nim: -", "@nim: 123456789")
    (uji / "naskah.txt").write_text("@angka: latin\n" + naskah, encoding="utf-8")
    b = bahan(uji.name)
    if b["meta"].get("angka") != "latin":
        sys.exit(f"@angka: latin: meta.angka={b['meta'].get('angka')}, bukan latin")
    teks = [b["meta"]["nim"], *b["pustaka"]]
    teks += [r["t"] for x in b["blok"] + b["catatan"] for r in x["runs"] if "t" in r and not r.get("q")]
    hindi = [t for t in teks if re.search(r"[٠-٩]", t)]
    if hindi:
        sys.exit(f"@angka: latin: masih ada angka hindi ٠-٩ di: {hindi}")
    latin = sorted({t for t in teks if re.search(r"[0-9]", t)})
    if not latin:
        sys.exit("@angka: latin: tidak ada satu pun angka 0-9 di teks hasil (terlalu longgar?)")
    print(f"uji angka: {len(latin)} teks berangka 0-9, ٠-٩ tidak ada")
finally:
    shutil.rmtree(uji)

uji = AKAR / "_uji_tautan"  # folder bahts baru; diabaikan git
uji.mkdir(exist_ok=True)
try:
    tautan = ["doi.org/10.21608/jasis.2021.183131", "10.1016/j.cell.2020.05.012", "https://dorar.net/aqadia/1234",
              "https://dorar.net/aqadia/5678", "10.1016/S0140-6736(20)30183-5"]  # DOI berkurung di dalam kurung kalimat
    naskah = (AKAR / "contoh" / "naskah.txt").read_text(encoding="utf-8").replace(
        "#K الخاتمة\n", f"#K الخاتمة\nوانظر[^انظر ملخص البحث في موقع المجلة، {tautan[0]}.]، وانظر أيضًا[^انظر: {tautan[1]}، "
                        f"ص 12.]، والموقع[^موقع الدرر السنية، {tautan[2]}، 1445هـ.]، وغيره[^انظر: {tautan[3]}وانظر ص 13.]، "
                        f"والدراسة[^انظر: ({tautan[4]})، ص 14.].\n")
    (uji / "naskah.txt").write_text(naskah, encoding="utf-8")
    b = bahan(uji.name)
    teks = ["".join(r.get("t", "") for r in c["runs"]) for c in b["catatan"]]
    teks = [t for t in teks if "ص ١٢" in t or "ص ١٣" in t or "ص ١٤" in t or "١٤٤٥" in t or "المجلة" in t]
    dapat = sorted(m.group() for t in teks for m in re.finditer(b["tautan"], t))
    if len(teks) != len(tautan) or dapat != sorted(tautan):
        sys.exit(f"tautan/DOI di catatan kaki harus tetap 0-9 dan tertangkap utuh {tautan}: dapat {dapat} dari {teks}")
    print(f"uji tautan: {len(dapat)} tautan/DOI di catatan kaki tetap 0-9, angka lain ٠-٩")
finally:
    shutil.rmtree(uji)
