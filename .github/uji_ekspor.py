# SPDX-License-Identifier: AGPL-3.0-or-later
"""`ekspor` lewat pintu pemakai (`python mesin/bahts.py ekspor … --ke <folder>`), untuk kerusakan yang tidak terlihat
sampai .docx-nya dibuka di Word:
- ligatur hormat Unicode 14 (﵁ ﷿ …) tidak ada di huruf Word: harus tercetak sebagai kalimatnya, bukan kotak (11223);
- tag HTML, entitas HTML («&amp;», 711), dan tanda «¬» Shamela di nomor حاشية («(¬١)», 2348) tidak ikut tercetak;
- judul bab: tiap judul daftar isi tepat satu Heading dan tidak tercetak lagi sebagai paragraf biasa, juga di kitab
  yang tanda judulnya berkutip tunggal (1726);
- OCR Waqfeya: baris sisa kalimat disambung, tapi judul («الباب الأول», baris pendek «كلمة شكر») dan catatan kaki
  «(١)» tetap paragraf sendiri; aksara lain, angka, huruf tunggal, dan batas paragraf kosong tetap ada;
- penanda halaman tidak berulang di kitab yang tiap haditsnya satu rekaman (1726);
- .docx terbaca sebagai XML yang sah dan tiap paragrafnya kanan-ke-kiri.
Kitabnya kitab CI (baris `ambil` di tes.yml). `ekspor` hanya membaca kitab/, jadi dijalankan di repo ini."""
import gzip, json, re, subprocess, sys, tempfile, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from bantu import salin_mesin

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


gagal = []
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

    # Kitab kecil di salinan mesin: alur pemakai, tanpa mengganti fungsi produk atau mengunduh Waqfeya di CI.
    akar = Path(ke) / "repo"
    salin_mesin(akar)
    for sid in ("1", "2"):
        d = akar / "kitab" / sid
        d.mkdir(parents=True)
        (d / "book_metadata.json").write_text(json.dumps({"title_ar": "عنوان &amp; كتاب\x01", "main_author_name_ar": "مؤلف &#xfd41;"}), encoding="utf8")
        with gzip.open(d / "pages.jsonl.gz", "wt", encoding="utf8") as f:
            f.write(json.dumps({"page_id": 1, "page_num": 1, "part": None,
                                "body": "باب طويل\n<span id='toc-1' class='x' data-type = 'title'>باب\rطويل</span>.\nباب طويل\n"
                                "... لم يحذف النص<br>كلمة أخرى\n&#xfd41; &amp; &#x26;lt;لفظ&#x26;gt;\n"
                                'إذا كان أ < ب وكانت ج > د ثبت المقصود.\nأول <span title="x > y">ثان</span> ثالث',
                                "footnotes": "(¬١) حاشية"}) + "\n")
        with gzip.open(d / "toc.jsonl.gz", "wt", encoding="utf8") as f:
            f.write(json.dumps({"page_id": 1, "title_id": 1, "shamela_title_id": 1, "parent_id": None, "title_text": "باب طويل"}) + "\n")
    w = akar / "kitab" / "waqfeya" / "w0123abcd"
    w.mkdir(parents=True)
    (w / "kitab.json").write_text(json.dumps({"judul": "عنوان كتاب", "pengarang": "مؤلف", "berkas": ["الكتاب"]}), encoding="utf8")
    (w / "1.pdf").write_bytes(b"%PDF-1.4\n")  # ekspor membaca OCR, bukan PDF scan
    with gzip.open(w / "1.txt.gz", "wt", encoding="utf8") as f:
        f.write("كذلك لم يذكر شيئا عن\nمن بعده\nالباب الأول\nابن معطى\n١٢\n(١) معجم البلدان\nالبحر المتوسط .\n"
                "كلمة شكر\nإذا كان من سنة أصحاب الرسائل\n\nفقد بقي معنى جديد\nالكلمة اليونانية λόγος معناها كلمة.\nز\n٣٫١٤\n")
    r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), "ekspor", "1", "2", "w0123abcd", "--ke", str(akar / "out")],
                       cwd=akar, capture_output=True, text=True, encoding="utf8")
    ps = {sid: paragraf(docx) for sid, docx in (b.split("\t") for b in r.stdout.splitlines() if "\t" in b)}
    if r.returncode or set(ps) != {"1", "2", "w0123abcd"}:
        sys.exit(f"ekspor kitab kecil: {r.stdout}\n{r.stderr}")
    for sid in ("1", "2"):
        harus = [("Heading1", "عنوان & كتاب"), ("Pengarang", "مؤلف رضي الله عنه"), ("Halaman", "[ص ١]"),
                 ("Heading1", "باب طويل"), ("Normal", "... لم يحذف النص"), ("Normal", "كلمة أخرى"),
                 ("Normal", "رضي الله عنه & &lt;لفظ&gt;"), ("Normal", "إذا كان أ < ب وكانت ج > د ثبت المقصود."),
                 ("Normal", "أول ثان ثالث"), ("Hasyiah", "ـــــــــــــــ"), ("Hasyiah", "(١) حاشية")]
        if [(g, t) for g, t, _ in ps[sid]] != harus:
            gagal.append(f"{sid}: judul/teks/entitas berubah: {ps[sid]}")
    harus = ["كذلك لم يذكر شيئا عن من بعده", "الباب الأول", "ابن معطى", "١٢", "(١) معجم البلدان البحر المتوسط .",
             "كلمة شكر", "إذا كان من سنة أصحاب الرسائل", "فقد بقي معنى جديد الكلمة اليونانية λόγος معناها كلمة.", "ز", "٣٫١٤"]
    if [t for g, t, _ in ps["w0123abcd"] if g == "Normal"] != harus:
        gagal.append(f"Waqfeya: isi OCR/batas paragraf berubah: {ps['w0123abcd']}")
    for args in (("1", "--ke"), ("1", "--ke", "--salah"), ("1", "--ke", ke, "--ke", ke)):
        r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), "ekspor", *args],
                           cwd=akar, capture_output=True, text=True, encoding="utf8")
        if r.returncode != 1 or r.stdout.strip() or "Traceback" in r.stderr:
            gagal.append(f"ekspor {args}: argumen salah diterima/traceback: {r.stdout} {r.stderr}")

if gagal:
    sys.exit("GAGAL\n" + "\n".join(gagal))
print(f"ekspor: {', '.join(KITAB)} lolos")
