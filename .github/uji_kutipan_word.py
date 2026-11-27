# SPDX-License-Identifier: AGPL-3.0-or-later
"""Kutipan blok `#Q` dan `@anzhur` lewat `rakit` dan Word asli: paragraf #Q menjorok sama di kanan dan kiri
(profil tepi_kutipan), paragraf biasa tidak; `@anzhur: ينظر` mencetak «ينظر:» di tiap catatan kaki nukilan makna
(juga «وانظر:» dan rujukan silang) walau naskah menulis «انظر:»/«راجع:». Kitab CI 11223; runner tanpa Word melaporkan
lewati. Semua bahan di TEMP."""
import re, sys, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from bantu import SAMPUL_UJI, bahts, salin_mesin, tanpa_word

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mesin"))
import olah  # tepi_kutipan bawaan dibaca dari tempatnya (BAWAAN_FORMAT), bukan disalin

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
KUTIPAN = ("غلوا في إثبات قدرة العبد واختياره حتى نفوا أن يكون الله تعالى مشيئة أو اختيار أو خلق فيما يفعله العبد "
           "وزعموا أن العبد مستقل بعمله")
NASKAH = ("@judul: فحص الاقتباس المستقل\n" + SAMPUL_UJI + "@berkas: hasil\n@anzhur: ينظر\n"
          "@tanpa: pustaka, ayat, hadits, maudhuat\n"
          "#K المقدمة\n{A:awal}وهذا تمهيد للفحص.\n"
          "وقال الشيخ في بيان أقسام الناس في القدر:\n"
          f'#Q "{KUTIPAN}"[^رسالة في القضاء والقدر، ابن عثيمين، ص7. <<11223|-|7>>]\n'
          "وخلاصة ذلك أن الشيخ قسم الناس[^انظر: رسالة في القضاء والقدر، ابن عثيمين، ص6؛ وانظر: الكتاب نفسه، ص7. "
          "<<11223|-|6|انقسمت في القدر إلى ثلاثة أقسام>> <<11223|-|7|غلوا في إثبات قدرة العبد>>].\n"
          "وهم ثلاث طوائف[^راجع: رسالة في القضاء والقدر، ابن عثيمين، ص6. <<11223|-|6|انقسمت في القدر إلى ثلاثة أقسام>>].\n"
          "وسبق التمهيد[^انظر: ص{P:awal} من هذا البحث.].\n"
          "#K الخاتمة\nأهم النتائج: انتهى الفحص.\n")


def jorok(p):
    """(kanan, kiri) paragraf dalam twip; Word menulis w:ind start/end atau right/left."""
    ind = p.find(f"{W}pPr/{W}ind")
    if ind is None:
        return 0, 0
    nilai = lambda *k: int(next((ind.get(W + x) for x in k if ind.get(W + x) is not None), 0))
    return nilai("start", "right"), nilai("end", "left")


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji kutipan Word: " + alasan)
        return
    with tempfile.TemporaryDirectory(prefix="bahts-kutipan-word-") as t:
        akar = Path(t)
        salin_mesin(akar, (11223,))
        f = akar / "uji"
        f.mkdir()
        (f / "naskah.txt").write_text(NASKAH, encoding="utf8")
        (f / "riset.txt").write_text("cari القدر | uji\n", encoding="utf8")
        r = bahts(akar, "rakit", "uji", batas=1800)
        assert r.returncode == 0, r.stdout + r.stderr
        with zipfile.ZipFile(f / "hasil.docx") as z:
            doc = ET.fromstring(z.read("word/document.xml"))
            fn = ET.fromstring(z.read("word/footnotes.xml"))
        para = [(p, "".join(p.itertext())) for p in doc.iter(W + "p")]
        q = [p for p, teks in para if KUTIPAN[:20] in teks]
        assert len(q) == 1, [teks[:40] for _, teks in para]
        tepi = round(olah.BAWAAN_FORMAT["tepi_kutipan"] * 567)
        kanan, kiri = jorok(q[0])
        assert abs(kanan - tepi) <= 2 and abs(kiri - tepi) <= 2, f"#Q menjorok {kanan}/{kiri} twip, bukan {tepi}"
        biasa = next(p for p, teks in para if "وهذا تمهيد للفحص" in teks)
        assert jorok(biasa) == (0, 0), f"paragraf biasa ikut menjorok: {jorok(biasa)}"
        catatan = [re.sub(r"^\s*\(\S+\)\s*", "", "".join(n.itertext()))  # «(١)  …»: nomor catatan kaki dibuang
                   for n in fn.findall(W + "footnote") if int(n.get(W + "id", "0")) > 0]
        assert len(catatan) == 4 and catatan[0].lstrip().startswith("رسالة"), catatan  # catatan #Q tanpa kata itu
        makna = catatan[1:]
        assert all(c.lstrip().startswith("ينظر:") for c in makna), makna
        assert all("انظر" not in c and "راجع" not in c for c in makna), makna
        assert any("وينظر:" in c for c in makna), makna
        print(f"lolos kutipan Word: #Q menjorok {kanan}/{kiri} twip, paragraf biasa 0; @anzhur: ينظر di {len(makna)} catatan kaki",
              flush=True)


if __name__ == "__main__":
    utama()
