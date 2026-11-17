# SPDX-License-Identifier: AGPL-3.0-or-later
"""`ekspor` lewat pintu pemakai (`python mesin/bahts.py ekspor … --ke <folder>`), untuk kerusakan yang tidak terlihat
sampai .docx-nya dibuka di Word:
- ligatur hormat Unicode 14 (﵁ ﷿ …) tidak ada di huruf Word: harus tercetak sebagai kalimatnya, bukan kotak (11223);
- tag HTML, entitas HTML («&amp;», 711), dan tanda «¬» Shamela di nomor حاشية («(¬١)», 2348) tidak ikut tercetak;
- judul bab: tiap judul daftar isi tepat satu Heading dan tidak tercetak lagi sebagai paragraf biasa, juga di kitab
  yang tanda judulnya berkutip tunggal (1726), dan baris judul di teks yang bersebelahan dengan judul daftar isi yang
  sama (di kitab non-CI, mis. 7861; dicek langsung ke `tanpa_judul_ulang`);
- OCR Waqfeya: baris sisa kalimat disambung, tapi judul («الباب الأول») dan catatan kaki «(١)» tetap paragraf sendiri
  (dicek langsung ke `paragraf_ocr`: CI tidak mengunduh kitab Waqfeya);
- penanda halaman tidak berulang di kitab yang tiap haditsnya satu rekaman (1726);
- .docx terbaca sebagai XML yang sah dan tiap paragrafnya kanan-ke-kiri.
Kitabnya kitab CI (baris `ambil` di tes.yml). `ekspor` hanya membaca kitab/, jadi dijalankan di repo ini."""
import gzip, re, subprocess, sys, tempfile, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
KITAB = ("11223", "2348", "1726", "711")
LIGATUR = re.compile(r"[﵀-﵏﷾﷿]")


def paragraf(docx):
    """[(gaya, teks, kanan-ke-kiri)] tiap paragraf document.xml."""
    akar = ET.fromstring(zipfile.ZipFile(docx).read("word/document.xml"))
    out = []
    for p in akar.iter(W + "p"):
        gaya = p.find(f"{W}pPr/{W}pStyle")
        out.append((gaya.get(W + "val") if gaya is not None else "", "".join(t.text or "" for t in p.iter(W + "t")),
                    p.find(f"{W}pPr/{W}bidi") is not None))
    return out


sys.path.insert(0, str(REPO / "mesin"))
from ekspor import paragraf_ocr, tanpa_judul_ulang  # noqa: E402

gagal = []
for urut in ([("Normal", "باب"), ("Heading2", "باب"), ("Normal", "نص")], [("Heading2", "باب"), ("Normal", "باب"), ("Normal", "نص")]):
    if (h := tanpa_judul_ulang(urut)) != [("Heading2", "باب"), ("Normal", "نص")]:
        gagal.append(f"tanpa_judul_ulang {urut} -> {h}")
OCR = chr(10).join(["كذلك لم يذكر شيئا عن", "من بعده", "الباب الأول", "ابن معطى", "(١) معجم البلدان", "البحر المتوسط ."])
if (h := paragraf_ocr(OCR)) != ["كذلك لم يذكر شيئا عن من بعده", "الباب الأول", "ابن معطى", "(١) معجم البلدان البحر المتوسط ."]:
    gagal.append(f"paragraf_ocr: {h}")
with tempfile.TemporaryDirectory(prefix="bahts-ekspor-") as ke:
    r = subprocess.run([sys.executable, str(REPO / "mesin" / "bahts.py"), "ekspor", *KITAB, "--ke", ke],
                       cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    hasil = dict(b.split("\t") for b in r.stdout.splitlines() if "\t" in b)
    if r.returncode or set(hasil) != set(KITAB):
        sys.exit(f"ekspor {' '.join(KITAB)}: kode {r.returncode}, hasil {hasil}\n{r.stderr}")
    for sid, docx in hasil.items():
        ps = paragraf(docx)
        teks = "\n".join(t for _, t, _ in ps)
        if n := len(LIGATUR.findall(teks)):
            gagal.append(f"{sid}: {n} ligatur hormat tercetak sebagai lambang (kotak di Word)")
        if sisa := re.findall(r"<[^>]*>|¬|&(?:amp|quot|lt|gt|nbsp|#\d+);", teks):
            gagal.append(f"{sid}: tag/tanda Shamela tertinggal: {sisa[:3]}")
        if kiri := sum(not rtl for _, _, rtl in ps):
            gagal.append(f"{sid}: {kiri} paragraf tidak kanan-ke-kiri")
        if ulang := [t for (g, t, _), (g2, t2, _) in zip(ps, ps[1:])
                     if t == t2 and {g[:7], g2[:7]} == {"Heading", "Normal"}]:
            gagal.append(f"{sid}: {len(ulang)} judul tercetak lagi sebagai paragraf biasa: {ulang[:2]}")
        penanda = [t for g, t, _ in ps if g == "Halaman"]
        if dobel := [a for a, b in zip(penanda, penanda[1:]) if a == b]:
            gagal.append(f"{sid}: penanda halaman berulang berturut-turut: {dobel[:3]}")
    with gzip.open(REPO / "kitab" / "1726" / "toc.jsonl.gz", "rt", encoding="utf8") as f:
        toc = sum(1 for _ in f)
    judul = sum(g.startswith("Heading") for g, _, _ in paragraf(hasil["1726"])) - 1  # minus judul kitab
    if judul != toc:
        gagal.append(f"1726: {judul} judul Heading, daftar isi {toc} (dobel atau hilang)")

if gagal:
    sys.exit("GAGAL\n" + "\n".join(gagal))
print(f"ekspor: {', '.join(KITAB)} lolos")
