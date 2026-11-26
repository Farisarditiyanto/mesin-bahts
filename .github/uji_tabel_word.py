# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regresi tabel #J lewat `rakit` dan Word asli: tabel 2 sampai 6 kolom harus terakit.

Lebar kolom tabel ≥3 kolom = 82 / (kolom - 1) persen; untuk 4 kolom itu pecahan (27.33), yang ditolak Word
kalau dikirim bukan sebagai bilangan tunggal («Specified cast is not valid», rakit.ps1). Runner tanpa Word melaporkan lewati. Semua bahan tinggal di TEMP.
"""
import subprocess, sys, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from bantu import SAMPUL_UJI, salin_mesin, tanpa_word

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    if alasan := tanpa_word():
        print("lewati uji tabel Word: " + alasan)
        return
    kolom = range(2, 7)
    with tempfile.TemporaryDirectory(prefix="bahts-tabel-word-") as t:
        akar = Path(t)
        salin_mesin(akar)
        folder = akar / "uji"
        folder.mkdir()
        berkas = "kerja"
        teks = SAMPUL_UJI + f"@judul: اختبار\n@tanpa: pustaka\n@berkas: {berkas}\n#K اختبار الجداول\n"
        for n in kolom:
            teks += f"جدول من {n} أعمدة:\n"
            for r in range(3):
                teks += "#J " + " | ".join(f"خلية{r}{c}" for c in range(n)) + "\n"
            teks += "فقرة بعد الجدول.\n"
        (folder / "naskah.txt").write_text(teks, encoding="utf8")
        r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), "rakit", "uji"], cwd=akar,
                           capture_output=True, encoding="utf8", timeout=1800)
        assert r.returncode == 0 and (folder / f"{berkas}.pdf").is_file(), r.stdout + r.stderr
        with zipfile.ZipFile(folder / f"{berkas}.docx") as z:
            xml = ET.fromstring(z.read("word/document.xml"))
        # tabel sesudah bagian sampul (bagian Word pertama, berakhir di paragraf ber-sectPr; sampul qism bertabel)
        badan = list(xml.find("w:body", NS))
        akhir_sampul = next(i for i, e in enumerate(badan) if e.find("w:pPr/w:sectPr", NS) is not None)
        tabel = [tb for e in badan[akhir_sampul + 1:] for tb in ([e] if e.tag == f"{{{NS['w']}}}tbl" else e.findall(".//w:tbl", NS))]
        lebar = [len(tb.find("w:tr", NS).findall("w:tc", NS)) for tb in tabel]
        # tabel #J naskah lebih dulu; sesudahnya bisa ada tabel فهرس buatan rakit sendiri
        assert lebar[:len(kolom)] == list(kolom), f"jumlah kolom tabel di DOCX {lebar}, harus diawali {list(kolom)}"
        # Isi sel (baris kedua dst.) harus rata kanan di halaman. Dokumen RTL: jc="right" = ujung akhir = rata kiri.
        for tb in tabel[:len(kolom)]:
            for tr in tb.findall("w:tr", NS)[1:]:
                for jc in tr.iter(f"{{{NS['w']}}}jc"):
                    assert jc.get(f"{{{NS['w']}}}val") != "right", "isi sel tabel #J tercetak rata kiri (jc=right di paragraf RTL)"
        print(f"lolos tabel Word: {len(tabel)} tabel, kolom {lebar}", flush=True)

        # Bahts biasa (bersampul qism + @logo: berwarna + @rujukan_ayat: matan):
        # 1) catatan kaki di dalam sel #J tidak mematikan Word (pane catatan di Draft view);
        # 2) @rujukan_ayat: matan di sel #J mencetak [الفاتحة: ٣] di sel, bukan catatan kaki;
        # 3) @logo: berwarna mengganti logo sampul dengan logo berwarna sampul_jakarta.docx.
        f2 = akar / "uji2"
        f2.mkdir()
        (f2 / "naskah.txt").write_text(
            "@judul: فحص الجدول\n@nama: فلان\n@berkas: b2\n@sampul: QISM\n@logo: berwarna\n"
            "@rujukan_ayat: matan\n@tanpa: pustaka, ayat, hadits, maudhuat\n@minimal_halaman: 0\n"
            "#K المقدمة\nنص.\n#F الفصل الأول\n"
            "#J الآية | البيان\n"
            "#J {Q:1:3}[^سورة الفاتحة، آية: 3.] | شرح[^حاشية جدول.]\n"
            "#K الخاتمة\nأهم النتائج: تم.\n",
            encoding="utf8",
        )
        r2 = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), "rakit", "uji2"], cwd=akar,
                            capture_output=True, encoding="utf8", timeout=1800)
        assert r2.returncode == 0 and (f2 / "b2.pdf").is_file(), r2.stdout + r2.stderr
        with zipfile.ZipFile(f2 / "b2.docx") as z, zipfile.ZipFile(akar / "mesin" / "sampul_jakarta.docx") as zj:
            xml2 = ET.fromstring(z.read("word/document.xml"))
            fn2 = ET.fromstring(z.read("word/footnotes.xml"))
            logo_hasil = z.read("word/media/image2.png")
            logo_warna = zj.read("word/media/image2.png")
        assert logo_hasil == logo_warna, "@logo: berwarna tidak memasang logo berwarna sampul_jakarta.docx"
        isi_fn = ["".join(n.itertext()) for n in fn2.findall("w:footnote", NS)
                  if int(n.attrib.get(f"{{{NS['w']}}}id", "0")) > 0]
        assert len(isi_fn) == 1 and "حاشية جدول" in isi_fn[0], f"catatan kaki di tabel: {isi_fn}"
        teks_tabel = "\n".join("".join(tb.itertext()) for tb in xml2.findall(".//w:tbl", NS))
        assert "[الفاتحة: ٣]" in teks_tabel, f"rujukan ayat matan hilang di sel #J: {teks_tabel}"
        print("lolos tabel Word (sampul qism + @logo: berwarna + catatan & ayat matan di #J)", flush=True)


if __name__ == "__main__":
    utama()
