# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bentuk فهرس pilihan dan فهرس tambahan lewat `rakit` dan Word asli, dibaca dari .docx hasilnya:
bawaan `@fihris_ayat: terbuka` dan `@fihris_hadits: terbuka` (tanpa garis tegak; hadits berkolom الراوي),
`@fihris_alam: nomor` (kolom م), dan `@maudhuat: titik`; `@fihris_ayat: baris_surah` (baris surat selebar tabel) dan
`tabel` (bergaris penuh), `@fihris_hadits: titik` dan `huruf` (tanpa tabel, kelompok «حرف …»), `@fihris_alam: tabel`
(tanpa kolom م), `@maudhuat: tabel`, atsar {AT:} di فهرس الآثار sendiri,
{B:}/{QB:}/{G:} bertitik-titik, dan {V:} di فهرس الأشعار urut حرف الروي. Tiap nomor halaman terisi (bukan «٠٠»).
Runner tanpa Word melaporkan lewati. Semua bahan di TEMP."""
import re, sys, tempfile, zipfile
from pathlib import Path

from bantu import SAMPUL_UJI, bahts, salin_mesin, tanpa_word

KEPALA = "@judul: اختبار الفهارس\n@berkas: uji\n@tanpa: pustaka\n" + SAMPUL_UJI
ISI = ("#K المقدمة\n"
       "قال الله تعالى: {Q:2:286:1-6}[^سورة البقرة، آية: ٢٨٦.]، وقال: {Q:39:53:1-6}[^سورة الزمر، آية: ٥٣.].\n"
       "وفي الحديث {H:إن الله يبسط يده بالليل|أبو موسى الأشعري|basth}بيان سعة الرحمة.\n"
       "وفي معناه {H:لولا أنكم تذنبون|أبو أيوب الأنصاري|lawla}ما يدل على فضل الاستغفار.\n"
       "ومن الآثار {AT:التوبة النصوح أن يتوب ثم لا يعود|عمر بن الخطاب|nasuh}وهو تفسير لها، وذكره {N:ابن كثير}ابن كثير.\n"
       "ونزلوا {B:مصر}مصر، وذكر {QB:اليهود}اليهود، و{G:الإصر}الإصر هو العهد الثقيل.\n"
       "#V ولما قسا قلبي وضاقت مذاهبي ... جعلت الرجا مني لعفوك سُلَّمَا{V:الشافعي}\n"
       "#V قفا نبك من ذكرى حبيب ومنزل ... بسقط اللوى بين الدخول فحوملِ{V:امرؤ القيس}\n"
       "#K الخاتمة\nهذا آخر البحث.\n")
JUDUL = ("فهرس الآيات", "فهرس الأحاديث", "فهرس أطراف", "فهرس الآثار", "فهرس الأعلام", "فهرس الأماكن", "فهرس القبائل",
         "فهرس الغريب", "فهرس الأشعار", "فهرس الموضوعات")


def teks(p):
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))


def rakit(akar, nama, kunci):
    f = akar / nama
    f.mkdir()
    (f / "naskah.txt").write_text(KEPALA + kunci + ISI, encoding="utf8")
    r = bahts(akar, "rakit", nama, batas=1800)
    assert r.returncode == 0, r.stdout + r.stderr
    with zipfile.ZipFile(f / "uji.docx") as z:
        xml = z.read("word/document.xml").decode("utf8")
    awal = xml.find("فهرس الآيات")
    assert awal > 0, "judul فهرس الآيات tidak ada"
    penuh, xml = xml, xml[awal:]
    # tiap فهرس = dari judulnya sampai judul فهرس berikutnya; kemunculan pertama = judulnya (فهرس الموضوعات di akhir)
    letak = sorted((xml.find(j), j) for j in JUDUL if xml.find(j) >= 0)
    bagian = {j: xml[i:(letak[k + 1][0] if k + 1 < len(letak) else len(xml))] for k, (i, j) in enumerate(letak)}
    assert "٠٠" not in teks(xml[:letak[-1][0]]), f"{nama}: nomor halaman فهرس belum terisi (masih ٠٠)"
    bagian["_xml"] = penuh   # seluruh document.xml: paragraf judul (sebelum teksnya) ada di situ
    return bagian


def paragraf(x):
    """Paragraf bertulisan di `x`; `x` diawali di tengah paragraf judulnya, jadi judul itu tidak ikut."""
    return [p for p in re.findall(r"<w:p[ >].*?</w:p>", x, re.S) if teks(p).strip()]


ABU = re.compile(r'<w:shd [^>]*w:fill="D9D9D9"')  # latar abu-abu muda kepala tabel (fihris.ps1 Kepala-Abu)


def garis(x):
    """Sisi tabel bergaris tunggal di `x` (w:tblBorders/w:tcBorders/w:trPr)."""
    return re.findall(r"<w:(top|bottom|left|right|start|end|insideV|insideH) w:val=\"single\"", x)


def titik(x, nama):
    """فهرس tanpa tabel: tiap barisnya bertitik-titik ke nomor halaman."""
    assert "<w:tbl>" not in x, f"{nama} masih tabel"
    baris = [p for p in paragraf(x) if "<w:tab/>" in p]
    assert baris and all('w:leader="dot"' in p for p in baris), f"{nama}: baris tanpa titik-titik"
    return [teks(p) for p in baris]


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji bentuk فهرس Word: " + alasan)
        return
    with tempfile.TemporaryDirectory(prefix="bahts-fihris-word-") as t:
        akar = Path(t)
        salin_mesin(akar)
        b = rakit(akar, "satu", "@fihris_ayat: baris_surah\n@fihris_hadits: titik\n@fihris_alam: nomor\n")
        ay = b["فهرس الآيات"]
        assert ay.count('w:gridSpan w:val="3"') == 2 and "٢- سورة البقرة" in teks(ay) and "٣٩- سورة الزمر" in teks(ay), \
            "@fihris_ayat: baris_surah: baris surat tidak selebar tabel"
        print("lolos @fihris_ayat: baris_surah: tiap surat satu baris penuh di dalam tabel")
        hd = titik(b["فهرس أطراف"], "@fihris_hadits: titik")
        assert len(hd) == 2 and "الأشعري" not in "".join(hd) and "التوبة النصوح" not in "".join(hd), hd
        at = titik(b["فهرس الآثار"], "فهرس الآثار")
        assert len(at) == 1 and "(عمر بن الخطاب)" in at[0], at
        print("lolos @fihris_hadits: titik dan فهرس الآثار terpisah (القائل dalam kurung)")
        al = b["فهرس الأعلام"]
        assert "<w:tbl>" in al and teks(paragraf(al)[0]).strip() == "م", "@fihris_alam: nomor tanpa kolom م"
        for j in ("فهرس الأماكن", "فهرس القبائل", "فهرس الغريب"):
            assert len(titik(b[j], j)) == 1
        sy = [teks(p) for p in paragraf(b["فهرس الأشعار"])]
        assert "صدر البيت" in sy and sy.index("فحوملِ") < sy.index("سُلَّمَا"), f"فهرس الأشعار tidak urut حرف الروي: {sy}"
        print("lolos @fihris_alam: nomor, فهرس الأماكن/القبائل/الغريب bertitik, فهرس الأشعار urut حرف الروي")
        b = rakit(akar, "dua", "")   # bawaan
        for j in ("فهرس الآيات", "فهرس الأحاديث"):
            assert "<w:tbl>" in b[j] and set(garis(b[j])) == {"top", "bottom"}, f"{j} bawaan (terbuka) bergaris {garis(b[j])}"
        kolom = [teks(p).strip() for p in paragraf(b["فهرس الأحاديث"])[:3]]
        assert kolom == ["طرف الحديث", "الراوي", "الصفحة"], f"kolom فهرس الأحاديث terbuka: {kolom}"
        al = b["فهرس الأعلام"]
        assert "<w:tbl>" in al and teks(paragraf(al)[0]).strip() == "م", "@fihris_alam bawaan (nomor) tanpa kolom م"
        titik(b["فهرس الموضوعات"], "@maudhuat bawaan (titik)")
        assert not ABU.search(b["فهرس الآيات"]) and not ABU.search(b["فهرس الأحاديث"]), "tabel terbuka berlatar abu-abu"
        # judul المصادر dan tiap فهرس berjarak ±14 pt (280 twip) dari tabel/daftar di bawahnya
        for j in ("فهرس الآيات", "فهرس الأحاديث", "فهرس الأعلام", "فهرس الموضوعات"):
            judul = re.search(r"<w:p[ >](?:(?!</w:p>).)*?" + j, b["_xml"], re.S)[0]
            after = re.search(r'w:after="(\d+)"', judul)
            assert after and int(after[1]) >= 280, f"judul {j} menempel ke isinya: {after}"
        print("lolos bawaan: فهرس الآيات/الأحاديث terbuka (garis mendatar saja), فهرس الأعلام bernomor, الموضوعات bertitik; "
              "judul فهرس berjarak 14 pt")
        b = rakit(akar, "tiga", "@fihris_ayat: tabel\n@fihris_hadits: huruf\n@fihris_alam: tabel\n@maudhuat: tabel\n")
        assert {"insideV", "insideH"} <= set(garis(b["فهرس الآيات"])), "@fihris_ayat: tabel tidak bergaris penuh"
        assert teks(paragraf(b["فهرس الأعلام"])[0]).strip() != "م", "@fihris_alam: tabel masih berkolom م"
        assert "<w:tbl>" in b["فهرس الموضوعات"], "@maudhuat: tabel tanpa tabel"
        # tabel bergaris penuh: kepala abu-abu muda seperti @fihris_alam: nomor; tabel terbuka tanpa latar
        for j in ("فهرس الآيات", "فهرس الأعلام", "فهرس الأشعار", "فهرس الموضوعات"):
            assert ABU.search(b[j]), f"{j} bergaris penuh tanpa kepala abu-abu"
        hd = b["فهرس الأحاديث"]
        isi = [teks(p).strip() for p in paragraf(hd)]
        assert "حرف الهمزة" in isi and "حرف اللام" in isi, isi
        assert any("(أبو موسى الأشعري)" in s for s in titik(hd, "@fihris_hadits: huruf")), isi
        print("lolos bentuk lama: @fihris_ayat/@fihris_alam/@maudhuat: tabel dan @fihris_hadits: huruf (حرف الهمزة …, "
              "الراوي dalam kurung)")


if __name__ == "__main__":
    utama()
