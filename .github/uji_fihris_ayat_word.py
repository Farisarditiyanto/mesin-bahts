# SPDX-License-Identifier: AGPL-3.0-or-later
"""`@fihris_ayat: titik` lewat `rakit` dan Word asli: فهرس الآيات tanpa tabel, nama tiap surat sebagai judul, nomor
ayat dalam huruf mushaf di dalam ﴿…﴾ (digambar huruf itu sebagai bulatan akhir ayat), dan nomor halaman terisi. Bawaan
tanpa kunci itu tetap tabel. Runner tanpa Word melaporkan lewati. Semua bahan di TEMP."""
import re, sys, tempfile, zipfile
from pathlib import Path

from bantu import bahts, salin_mesin, tanpa_word

KEPALA = "@judul: اختبار فهرس الآيات\n@nama: طالب\n@berkas: uji\n@tanpa: hadits, maudhuat, pustaka\n@minimal_halaman: 0\n"
ISI = ("#K المقدمة\n"
       "قال الله تعالى: {Q:1:2}[^سورة الفاتحة، آية: 2.]، وقال: {Q:112:1}[^سورة الإخلاص، آية: 1.]، "
       "وقال: {Q:112:1-2}[^سورة الإخلاص، آية: 1-2.].\n"
       "#K الخاتمة\nهذا آخر البحث.\n")
QF = "KFGQPC HAFS Uthmanic Script"


def fihris_xml(akar, nama, kunci):
    f = akar / nama
    f.mkdir()
    (f / "naskah.txt").write_text(KEPALA + kunci + ISI, encoding="utf8")
    r = bahts(akar, "rakit", nama, batas=1800)
    assert r.returncode == 0, r.stdout + r.stderr
    with zipfile.ZipFile(f / "uji.docx") as z:
        xml = z.read("word/document.xml").decode("utf8")
    awal = xml.rfind("فهرس الآيات")
    assert awal > 0, "judul فهرس الآيات tidak ada"
    return xml[awal:]


def teks(p):
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji فهرس الآيات Word: " + alasan)
        return
    with tempfile.TemporaryDirectory(prefix="bahts-fihris-ayat-word-") as t:
        akar = Path(t)
        salin_mesin(akar)
        x = fihris_xml(akar, "bawaan", "")
        assert "<w:tbl>" in x, "bawaan فهرس الآيات bukan tabel lagi"
        print("lolos فهرس الآيات bawaan: tabel")
        x = fihris_xml(akar, "titik", "@fihris_ayat: titik\n")
        assert "<w:tbl>" not in x, "@fihris_ayat: titik masih mencetak tabel"
        par = [p for p in re.findall(r"<w:p[ >].*?</w:p>", x, re.S) if teks(p).strip()]
        isi = [teks(p) for p in par]
        assert any(s.strip() == "سورة الفاتحة" for s in isi) and any(s.strip() == "سورة الإخلاص" for s in isi), isi
        ayat = [p for p in par if "﴿" in teks(p)]
        assert len(ayat) == 3, isi
        # ayat rentang 112:1-2: potongannya (5 kata, kata ke-4 «أحد» pendek) melewati tanda akhir ayat ١; tanda itu
        # dibuang, nomornya dicetak sekali «١ - ٢» di ujung
        rentang = [teks(p).split("﴾")[0] for p in ayat if " - " in teks(p)]
        assert len(rentang) == 1, isi
        assert rentang[0].count("١") == 1 and rentang[0].endswith("١ - ٢"), f"nomor ayat rentang salah: {rentang[0]}"
        for p in ayat:
            s = teks(p)
            dalam = p[:p.index("﴾")]                       # run sebelum ﴾: nomor ayat, bukan nomor halaman
            nomor = [r for r in re.findall(r"<w:r>.*?</w:r>|<w:r .*?</w:r>", dalam, re.S) if re.fullmatch("[٠-٩]+", teks(r))]
            assert nomor and all(QF in r for r in nomor), f"nomor ayat tidak dalam huruf mushaf: {s}"
            n = teks(nomor[0])
            assert s.index("﴿") < s.index(n) < s.index("﴾"), f"nomor ayat tidak di dalam ﴿…﴾: {s}"
            assert "<w:tab/>" in p and "w:leader=\"dot\"" in p, f"baris ayat tanpa titik-titik ke nomor halaman: {s}"
            halaman = s.split("﴾")[-1].strip()
            assert halaman == "١", f"nomor halaman salah (semua ayat uji di halaman ١): {s}"
        print("lolos @fihris_ayat: titik: tanpa tabel, nama surat, nomor ayat mushaf di dalam ﴿…﴾, nomor halaman terisi")


if __name__ == "__main__":
    utama()
