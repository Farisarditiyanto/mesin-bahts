"""Tes skill Gemini lewat pintu pemakainya (`python skill-gemini/rakit_docx.py naskah.txt hasil.docx`):
salinan terpaksa (huruf/ukuran, daftar surah) sama dengan mesin, dan contoh.txt jadi .docx yang terbaca XML-nya
dengan catatan kaki dan فهرس yang lengkap."""
import json, re, subprocess, sys, tempfile, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
SKILL = AKAR / "skill-gemini"
sys.stdout.reconfigure(encoding="utf-8")

baca = lambda p: json.load(open(p, encoding="utf-8"))
if baca(SKILL / "nama_surah.json") != baca(AKAR / "mesin" / "nama_surah.json"):
    sys.exit("skill-gemini/nama_surah.json beda dengan mesin/nama_surah.json")
kode = (SKILL / "rakit_docx.py").read_text(encoding="utf-8")
fmt = json.loads(re.search(r"^FORMAT = (\{.*\})$", kode, re.M).group(1))
profil = baca(AKAR / "mesin" / "format.json")["imam_ayat16"]
if any(profil[k] != v for k, v in fmt.items()):
    sys.exit(f"FORMAT di rakit_docx.py {fmt} beda dengan imam_ayat16 di mesin/format.json")

with tempfile.TemporaryDirectory() as tmp:
    hasil = Path(tmp) / "contoh.docx"
    p = subprocess.run([sys.executable, str(SKILL / "rakit_docx.py"), str(SKILL / "contoh.txt"), str(hasil)],
                       capture_output=True, text=True, encoding="utf-8")
    if p.returncode or not p.stdout.startswith("JADI"):
        sys.exit(f"rakit_docx.py gagal merakit contoh.txt: {p.stdout}{p.stderr}")
    with zipfile.ZipFile(hasil) as z:
        bagian = {n: ET.fromstring(z.read(n)) for n in z.namelist() if n.endswith(".xml") or n.endswith(".rels")}
        dok = z.read("word/document.xml").decode("utf-8")
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    catatan = [f for f in bagian["word/footnotes.xml"] if f.get(W + "type") is None]
    teks = "".join(t.text or "" for t in bagian["word/document.xml"].iter(W + "t"))
    kurang = [s for s in ("فهرس الآيات القرآنية", "فهرس الأحاديث والآثار", "فهرس الموضوعات", "المصادر والمراجع", "٠٠٠٠٠٠٠٠٠") if s not in teks]
    if len(catatan) != 4 or "PAGEREF" not in dok or kurang:
        sys.exit(f"contoh.docx tidak lengkap: catatan kaki {len(catatan)} (harus 4), PAGEREF {'PAGEREF' in dok}, kurang {kurang}")
print(f"uji skill gemini: {p.stdout.strip()}")
