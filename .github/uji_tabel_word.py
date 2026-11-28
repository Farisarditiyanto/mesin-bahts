# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regresi tabel #J lewat `rakit` dan Word asli: tabel 2 sampai 6 kolom harus terakit.

Sel angka saja (olah.sel_angka: «24», «12,5٪», «1442هـ/2021م», «10-20», «$300») rata tengah, sel teks rata kanan, kepala
rata tengah. Dokumen pertama memakai profil bahts baru `@format: baku` (mesin/naskah_baru.txt): ukuran matan/catatan
kaki/judul, awal alinea 1,5 cm, dan tepi halaman isi 2,5/2,5/3/2,5 cm dibaca dari DOCX.

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
        teks = SAMPUL_UJI + f"@judul: اختبار\n@tanpa: pustaka\n@berkas: {berkas}\n@format: baku\n#K اختبار الجداول\n"
        teks += "فقرة المتن للاختبار تحليل الباحث[^حاشية المتن للاختبار.]\n"
        for n in kolom:
            teks += f"جدول من {n} أعمدة:\n"
            for r in range(3):
                teks += "#J " + " | ".join(f"خلية{r}{c}" for c in range(n)) + "\n"
            teks += "فقرة بعد الجدول.\n"
        # tabel angka: tengah[baris][kolom] = sel itu rata tengah (kepala selalu; sel angka saja; sel teks tidak)
        angka = [["البند", "النسبة", "السنة", "المبلغ"],
                 ["الصدقة", "5%", "1442هـ/2021م", "$300"],
                 ["الزكاة الواجبة", "١٢٫٥٪", "١٠-٢٠", "50 طالبًا"],
                 ["الاحتياطي", "1,250.50", "2023م", "—"]]
        tengah = [[True] * 4, [False, True, True, True], [False, True, True, False], [False, True, True, True]]
        teks += "".join("#J " + " | ".join(b) + "\n" for b in angka) + "فقرة بعد جدول الأرقام.\n"
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
        W = f"{{{NS['w']}}}"

        # paragraf sel tanpa w:jc sendiri mengikuti gaya Normal dokumen (rakit menyetelnya rata tengah)
        with zipfile.ZipFile(folder / f"{berkas}.docx") as z:
            gaya = ET.fromstring(z.read("word/styles.xml"))
        normal = next(s for s in gaya.findall("w:style", NS) if s.get(W + "styleId") == "Normal")
        jc_normal = normal.find("w:pPr/w:jc", NS)
        jc_normal = jc_normal.get(W + "val") if jc_normal is not None else "left"

        def jc(tc):
            return {(p.find("w:pPr/w:jc", NS).get(W + "val") if p.find("w:pPr/w:jc", NS) is not None else jc_normal)
                    for p in tc.iter(W + "p")}
        sel = [tr.findall("w:tc", NS) for tr in tabel[len(kolom)].findall("w:tr", NS)]
        dapat = [["center" in jc(tc) for tc in tr] for tr in sel]
        isi_sel = [["".join(tc.itertext()) for tc in tr] for tr in sel]
        assert dapat == tengah, f"sel rata tengah tabel angka {dapat}, harus {tengah}: {isi_sel}"
        print(f"lolos tabel Word: {len(tabel)} tabel, kolom {lebar}, sel angka rata tengah", flush=True)

        # @format: baku: ukuran dalam setengah poin, awal alinea dan tepi dalam twip (1 cm = 567)
        # ukuran efektif run berteks: szCs run, kalau tidak ada dari gaya paragrafnya (dan gaya induknya, sampai Normal)
        gaya_id = {s.get(W + "styleId"): s for s in gaya.findall("w:style", NS)}

        def ukuran_gaya(sid):
            while sid in gaya_id:
                s = gaya_id[sid]
                if (sz := s.find("w:rPr/w:szCs", NS)) is not None:
                    return sz.get(W + "val")
                induk = s.find("w:basedOn", NS)
                sid = induk.get(W + "val") if induk is not None else None
            return None

        def ukuran(p):
            ps = p.find("w:pPr/w:pStyle", NS)
            dasar = ukuran_gaya(ps.get(W + "val") if ps is not None else "Normal")
            return {(r.find("w:rPr/w:szCs", NS).get(W + "val") if r.find("w:rPr/w:szCs", NS) is not None else dasar)
                    for r in p.iter(W + "r") if r.findtext("w:t", "", NS).strip() and r.find("w:rPr/w:rStyle", NS) is None}
        par = next(p for p in xml.iter(W + "p") if "فقرة المتن للاختبار" in "".join(p.itertext()))
        assert ukuran(par) == {"32"}, f"matan baku harus 16 pt (szCs 32), dapat {ukuran(par)}"
        ind = par.find("w:pPr/w:ind", NS)
        awal = ind.get(W + "firstLine") if ind is not None else None
        assert awal and abs(int(awal) - 850) <= 2, f"awal alinea baku harus 1,5 cm (850 twip), dapat {awal}"
        judul = next(p for p in xml.iter(W + "p") if "".join(p.itertext()).strip() == "اختبار الجداول")
        assert ukuran(judul) == {"36"}, f"judul #K baku harus 18 pt (szCs 36), dapat {ukuran(judul)}"
        mar = [s.find("w:pgMar", NS) for s in xml.iter(W + "sectPr")][-1]
        tepi = {k: int(mar.get(W + k)) for k in ("top", "bottom", "right", "left")}
        harus = {"top": 1417, "bottom": 1417, "right": 1701, "left": 1417}
        assert all(abs(tepi[k] - v) <= 2 for k, v in harus.items()), f"tepi halaman isi baku {tepi}, harus {harus}"
        with zipfile.ZipFile(folder / f"{berkas}.docx") as z:
            fn = ET.fromstring(z.read("word/footnotes.xml"))
        catatan = next(n for n in fn.findall("w:footnote", NS) if "حاشية المتن للاختبار" in "".join(n.itertext()))
        uk_catatan = {u for p in catatan.iter(W + "p") for u in ukuran(p)}
        assert uk_catatan == {"24"}, f"catatan kaki baku harus 12 pt (szCs 24), dapat {uk_catatan}"
        print("lolos @format: baku (matan 16, catatan kaki 12, judul 18, awal alinea 1,5 cm, tepi 2,5/2,5/3/2,5 cm)", flush=True)

        # Bahts biasa (bersampul qism + @logo: berwarna + @rujukan_ayat: matan):
        # 1) catatan kaki di dalam sel #J tidak mematikan Word (pane catatan di Draft view);
        # 2) @rujukan_ayat: matan di sel #J mencetak [الفاتحة: ٣] di sel, bukan catatan kaki;
        # 3) @logo: berwarna mengganti logo sampul dengan logo berwarna sampul_jakarta.docx;
        # 5) @qism mengganti «قسم الشريعة» (sel tabel kop) dan @isyraf: bawah memindah blok pembimbing ke bawah blok mahasiswa.
        f2 = akar / "uji2"
        f2.mkdir()
        (f2 / "naskah.txt").write_text(
            "@judul: فحص الجدول\n@nama: فلان\n@nim: 123\n@musyrif: د. علان\n@berkas: b2\n@sampul: QISM\n@logo: berwarna\n"
            "@qism: قسم العلوم الإدارية والمالية\n@isyraf: bawah\n"
            "@rujukan_ayat: matan\n@tanpa: pustaka, ayat, hadits, maudhuat\n@minimal_halaman: 0\n"
            "#K المقدمة\nنص.\n#F الفصل الأول\n"
            "#J جدول: الآية وبيانها\n"
            "#J الآية | البيان\n"
            "#J {Q:1:3}[^سورة الفاتحة، آية: 3.] | شرح[^حاشية جدول.]\n"
            "#J المصدر: إعداد الباحث.\n"
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
        # 4) «#J جدول: …» = paragraf «جدول (١): …» yang menempel tepat sebelum tabelnya, «#J المصدر: …» tepat sesudahnya
        W = f"{{{NS['w']}}}"
        badan2 = list(xml2.find("w:body", NS))
        i_tbl = next(i for i, e in enumerate(badan2) if e.tag == W + "tbl" and "البيان" in "".join(e.itertext()))
        judul_tbl, sumber_tbl = ("".join(badan2[i].itertext()).strip() for i in (i_tbl - 1, i_tbl + 1))
        assert judul_tbl == "جدول (١): الآية وبيانها", f"judul tabel sebelum tabel: «{judul_tbl}»"
        assert sumber_tbl == "المصدر: إعداد الباحث.", f"sumber tabel sesudah tabel: «{sumber_tbl}»"
        assert badan2[i_tbl - 1].find("w:pPr/w:keepNext", NS) is not None, "judul tabel tidak menempel ke tabelnya"
        # 5) sampul (bagian Word pertama): qism diganti, urutan إعداد الطالب → nama → تحت إشراف → nama pembimbing
        akhir2 = next(i for i, e in enumerate(badan2) if e.find("w:pPr/w:sectPr", NS) is not None)
        baris_sampul = [t for e in badan2[:akhir2 + 1] for p in ([e] if e.tag == W + "p" else e.iter(W + "p"))
                        if (t := "".join(p.itertext()).strip())]
        assert "قسم العلوم الإدارية والمالية" in baris_sampul and "قسم الشريعة" not in baris_sampul, f"@qism sampul qism: {baris_sampul}"
        urut = [next(i for i, t in enumerate(baris_sampul) if t == k) for k in ("إعداد الطالب:", "فلان", "تحت إشراف:", "د. علان")]
        assert urut == sorted(urut) and "المشرف" not in baris_sampul, f"@isyraf: bawah: urutan sampul {baris_sampul}"
        print("lolos tabel Word (sampul qism + @logo: berwarna + @qism + @isyraf: bawah + catatan & ayat matan di #J + judul/sumber tabel)", flush=True)
    pengantar_disusul()


def pengantar_disusul():
    """Pengantar «…:» yang disusul tabel #J, kutipan blok #Q, atau rumus #E di halaman yang sama (isi terakhir halaman,
    lalu #H) bukan «baris terakhir matan berakhir «:»». Sel #J terbaca sedikit lebih kecil daripada ukurannya di PDF."""
    kutipan = ("غلوا في إثبات قدرة العبد واختياره حتى نفوا أن يكون الله تعالى مشيئة أو اختيار أو خلق فيما يفعله "
               "العبد وزعموا أن العبد مستقل بعمله")
    isi = "وهذا نص تمهيدي للفحص يتكرر ليملأ السطر. " * 6 + "\n"
    teks = (SAMPUL_UJI + "@judul: فحص النقطتين\n@berkas: hasil\n@tanpa: pustaka, ayat, hadits, maudhuat\n"
            "#K المقدمة\n" + isi + "يوضح الجدول الآتي ذلك:\n"
            "#J جدول: بيان الأقسام\n#J القسم | البيان\n#J الأول | شرح القسم الأول\n#J الثاني | شرح القسم الثاني\n"
            "#J المصدر: إعداد الباحث.\n#H\n" + isi + "وقال الشيخ في بيان أقسام الناس في القدر:\n"
            f'#Q "{kutipan}"[^رسالة في القضاء والقدر، ابن عثيمين، ص7. <<11223|-|7>>]\n'
            "#H\n" + isi + "والمعادلة الآتية:\n#E Y_i = \\beta_0 + \\beta_1 X_{1i} + \\varepsilon_i\n"
            "#K الخاتمة\nأهم النتائج: انتهى الفحص.\n")
    for profil in ("imam_ayat16", "baku"):
        with tempfile.TemporaryDirectory(prefix="bahts-pengantar-word-") as t:
            akar = Path(t)
            salin_mesin(akar, (11223,))
            f = akar / "uji"
            f.mkdir()
            (f / "naskah.txt").write_text(teks.replace("@berkas:", f"@format: {profil}\n@berkas:"), encoding="utf8")
            r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), "rakit", "uji"], cwd=akar,
                               capture_output=True, encoding="utf8", timeout=1800)
            assert r.returncode == 0 and (f / "hasil.pdf").is_file(), r.stdout + r.stderr
            assert "berakhir «:»" not in r.stdout, f"@format: {profil}: {r.stdout}"
        print(f"lolos pengantar «:» disusul #J/#Q/#E tanpa PERINGATAN (@format: {profil})", flush=True)


if __name__ == "__main__":
    utama()
