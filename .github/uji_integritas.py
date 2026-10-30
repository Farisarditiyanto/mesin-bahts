"""Regresi berkas melalui cek/cari/halaman/rakit asli, pada salinan TEMP.
Word/COM dan kegagalan filesystem disimulasikan; rakit Word sungguhan tetap diuji lokal.
"""
import gzip, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from unittest.mock import patch

AKAR = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf8")


def jalan(akar, *args):
    return subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), *map(str, args)],
                          cwd=akar, capture_output=True, encoding="utf8")


def naskah(f, judul="المطلوب", berkas="hasil"):
    f.mkdir(parents=True, exist_ok=True)
    (f / "naskah.txt").write_text(f"@judul: {judul}\n@bentuk: kitab\n@tanpa: pustaka\n@berkas: {berkas}\n#K مقدمة\nهذا نص تجريبي.\n", encoding="utf8")


def sumber(f, baru=False):
    baris = [{"part": None, "page_num": 1, "body": "بداية الكتاب " * (20 if baru else 1), "footnotes": ""},
             {"part": None, "page_num": 3 if baru else 2,
              "body": "كلمات جديدة للبحث" if baru else "كلمات قديمة للبحث", "footnotes": ""}]
    isi = gzip.compress("\n".join(json.dumps(b, ensure_ascii=False) for b in baris).encode("utf8"), mtime=0)
    f.write_bytes(isi + b"\0" * (4096 - len(isi)))  # ukuran gzip sama meskipun isi/offset halaman berubah


# Memakai rakit yang sama dengan CLI; yang diganti hanya Word/OS host dan kegagalan eksternal.
WORD = r'''
import hashlib, json, os, subprocess, sys, types, zipfile
from pathlib import Path
akar, nama, mode, lain = map(str, sys.argv[1:])
akar = str(Path(akar).resolve())  # runner Windows GitHub: TEMP bernama pendek (RUNNER~1), mesin memakai jalur panjang
sys.stdout.reconfigure(encoding="utf8"); sys.stderr.reconfigure(encoding="utf8")
sys.path.insert(0, str(Path(akar) / "mesin"))
import bahts, teks_pdf
bahts.os = types.SimpleNamespace(**dict(vars(os), name="nt"))
bahts.font_terpasang = lambda: True
bahts.huruf_ada = lambda nama: True
run = subprocess.run
if mode == "pdf-fail":
    def gagal(*a): raise RuntimeError("injeksi pembetulan PDF gagal")
    teks_pdf.betulkan = gagal
if mode in ("publish-fail", "rollback-blocked"):
    replace = Path.replace
    ditolak = False
    def ganti(self, target):
        global ditolak
        target = Path(target)
        if mode == "rollback-blocked" and ditolak and self == Path(akar)/nama/"hasil.docx":
            raise PermissionError("injeksi DOCX baru terkunci saat ditarik")
        if not ditolak and self.name == "hasil.pdf" and self.parent != Path(akar)/nama and target.parent == Path(akar)/nama:
            ditolak = True
            raise PermissionError("injeksi penggantian PDF gagal")
        return replace(self, target)
    Path.replace = ganti
def word(args, **kwargs):
    if args[0] != "powershell": return run(args, **kwargs)
    folder = Path(args[args.index("-Folder") + 1])
    build = Path(args[args.index("-Build") + 1])
    out = Path(args[args.index("-Hasil") + 1]) if "-Hasil" in args else folder
    if mode == "snapshot":
        r = run([sys.executable, str(Path(akar)/"mesin"/"bahts.py"), "cek", lain], capture_output=True)
        assert r.returncode == 0
    if mode == "lock":
        r = run([sys.executable, __file__, akar, nama, "ok", lain], capture_output=True, encoding="utf8")
        assert r.returncode != 0 and "Rakit lain" in r.stderr, r.stdout + r.stderr
    d = json.loads(build.read_text(encoding="utf8"))
    assert d["meta"]["judul"] == "المطلوب", "Bahan rakit tertimpa cek lain"
    if mode == "save-fail": return types.SimpleNamespace(returncode=1)
    with zipfile.ZipFile(out / "hasil.docx", "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", "<document/>")
    if mode == "export-fail": return types.SimpleNamespace(returncode=1)
    from pypdf import PdfWriter
    w = PdfWriter(); w.add_blank_page(width=100, height=100)
    with open(out / "hasil.pdf", "wb") as h: w.write(h)
    with open(out / "laporan.txt", "a", encoding="utf8") as h:
        h.write("HALAMAN=99\n" if mode == "pages-fail" else "HALAMAN=1\n")
    if mode == "changed":
        with open(folder / "naskah.txt", "a", encoding="utf8") as h: h.write("نص جديد.\n")
    return types.SimpleNamespace(returncode=0)
bahts.subprocess.run = word
bahts.rakit(nama)
'''


def utama():
    with tempfile.TemporaryDirectory(prefix="bahts-integritas-") as t:
        akar = Path(t)
        shutil.copytree(AKAR / "mesin", akar / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__", "*.ttf"))
        shutil.copytree(AKAR / "kitab" / "11223", akar / "kitab" / "11223")
        shutil.copytree(AKAR / "kitab" / "_meta", akar / "kitab" / "_meta")
        sys.path.insert(0, str(akar / "mesin"))
        import bahts, norma
        kitab = akar / "kitab" / "11223"
        pages = kitab / "pages.jsonl.gz"
        runner = akar / "word_fixture.py"
        runner.write_text(WORD, encoding="utf8")
        gagal = []

        def uji(nama, fn):
            try:
                fn()
                print("lolos:", nama)
            except Exception as e:
                gagal.append(nama)
                print("GAGAL:", nama, type(e).__name__, str(e)[-1000:])

        def terpisah():
            a, b = akar / "a" / "sama", akar / "b" / "sama"
            naskah(a); naskah(b, "عنوان آخر", "lain")
            for f in (a, b):
                r = jalan(akar, "cek", f)
                assert r.returncode == 0, r.stdout + r.stderr
            assert bahts.bahan(a) != bahts.bahan(b), "Dua jalur memakai satu bahan"
            assert json.loads(bahts.bahan(a).read_text(encoding="utf8"))["meta"]["judul"] == "المطلوب"

        def cache_usang():
            sumber(pages)
            assert jalan(akar, "cari", "11223", "كلمات قديمة للبحث").returncode == 0
            stamp = pages.stat()
            sumber(pages, True)
            os.utime(pages, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            r = jalan(akar, "cari", "11223", "كلمات جديدة للبحث")
            assert r.returncode == 0, r.stdout + r.stderr

        def indeks_usang():
            f = akar / "uji-indeks"
            def cek_bukti(hal, frasa):
                naskah(f)
                with open(f / "naskah.txt", "a", encoding="utf8") as h:
                    h.write(f"هذا معنى العبارة[^انظر: رسالة في القضاء والقدر، ص{hal}. <<11223|-|{hal}|{frasa}>>].\n")
                return jalan(akar, "cek", f)
            sumber(pages)
            r = cek_bukti(2, "كلمات قديمة للبحث")
            assert r.returncode == 0, r.stdout + r.stderr
            assert (kitab / "indeks.json").exists(), "Pintu uji tidak menyentuh indeks"
            stamp = pages.stat()
            sumber(pages, True)
            os.utime(pages, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            r = cek_bukti(3, "كلمات جديدة للبحث")
            assert r.returncode == 0, r.stdout + r.stderr

        def cache_rusak():
            sumber(pages, True)
            for payload in (None, {}, [None], {"sumber": "salah", "rekaman": []}):
                with gzip.open(kitab / f"padat-{norma.VERSI}.json.gz", "wt", encoding="utf8") as h:
                    json.dump(payload, h)
                r = jalan(akar, "cari", "11223", "كلمات جديدة للبحث")
                assert r.returncode == 0, repr(payload) + r.stdout + r.stderr

        def cache_deflate_rusak():
            sumber(pages, True)
            # Header gzip sah, tetapi blok DEFLATE tidak sah: zlib.error, bukan BadGzipFile.
            (kitab / f"padat-{norma.VERSI}.json.gz").write_bytes(bytes.fromhex("1f8b08000000000000030600") + b"\0" * 8)
            r = jalan(akar, "cari", "11223", "كلمات جديدة للبحث")
            assert r.returncode == 0, r.stdout + r.stderr

        def bahan_terlindungi():
            f = akar / "uji-bahan"
            f.mkdir()
            tpl, pdf = f / "hasil.docx", f / "hasil.pdf"
            tpl.write_bytes(b"TEMPLAT-PEMAKAI")
            from pypdf import PdfWriter
            w = PdfWriter(); w.add_blank_page(width=100, height=100)
            with pdf.open("wb") as h: w.write(h)
            awal = {p: p.read_bytes() for p in (tpl, pdf)}
            for tambahan in ("@bentuk: bahts\n@templat: hasil.docx\n",
                             "@bentuk: bahts\n@templat: HASIL.docx\n",
                             "معنى من المصدر[^انظر: دراسة، ص1. <<luar|hasil.pdf|1>>].\n"):
                naskah(f)
                with (f / "naskah.txt").open("a", encoding="utf8") as h: h.write(tambahan)
                r = jalan(akar, "cek", f)
                assert r.returncode != 0 and "menimpa bahan sumber" in r.stdout + r.stderr, r.stdout + r.stderr
                assert all(p.read_bytes() == isi for p, isi in awal.items()), "Bahan pemakai berubah"

        def pdf_utuh():
            import dirasat, io
            from pypdf import PdfWriter
            w = PdfWriter(); w.add_blank_page(width=100, height=100)
            buf = io.BytesIO(); w.write(buf)
            isi = buf.getvalue()
            f = akar / "uji-unduh"
            f.mkdir()
            tujuan = f / "W123.pdf"
            tulis = Path.write_bytes
            def putus(p, data):
                tulis(p, data[:8])
                raise OSError("injeksi disk penuh")
            for data, gagal in ((b"%PDF-1.7\nterpotong", True), (isi, True), (isi, False)):
                with patch.object(dirasat, "_buka", side_effect=lambda *a: io.BytesIO(data)):
                    try:
                        if data == isi and gagal:
                            with patch.object(Path, "write_bytes", putus): dirasat.pdf("W123", f)
                        else:
                            dirasat.pdf("W123", f)
                    except (OSError, SystemExit):
                        assert gagal, "PDF sah ditolak"
                    else:
                        assert not gagal, "PDF rusak/penulisan terputus dianggap berhasil"
                assert tujuan.exists() != gagal
                assert not list(f.glob("*.part")), "Sisa unduhan tidak dibersihkan"
            assert tujuan.read_bytes() == isi
            with patch.object(dirasat, "_buka", side_effect=AssertionError("PDF sah diunduh lagi")):
                dirasat.pdf("W123", f)
            tujuan.write_bytes(b"%PDF-lama-terpotong")
            with patch.object(dirasat, "_buka", side_effect=lambda *a: io.BytesIO(b"%PDF-baru-terpotong")):
                try:
                    dirasat.pdf("W123", f)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("PDF rusak dianggap selesai")
            assert tujuan.read_bytes() == b"%PDF-lama-terpotong", "Kegagalan unduh mengganti berkas lama"
            with patch.object(dirasat, "_buka", side_effect=lambda *a: io.BytesIO(isi)):
                dirasat.pdf("W123", f)
            assert tujuan.read_bytes() == isi, "PDF lama yang rusak tidak dipulihkan"
            # Revisi kedua terpotong: pypdf masih bisa membaca revisi pertama, tetapi unduhannya belum selesai.
            tujuan.write_bytes(isi + b"\n9 0 obj\n<<" + b"0" * 2048)
            with patch.object(dirasat, "_buka", side_effect=lambda *a: io.BytesIO(isi)):
                dirasat.pdf("W123", f)
            assert tujuan.read_bytes() == isi, "PDF terpotong sesudah revisi lama dianggap utuh"

        def katalog_ringan():
            # Proses baru: pembacaan katalog tidak boleh diam-diam mengimpor pandas.
            r = subprocess.run([sys.executable, "-c",
                "import sys; sys.path.insert(0, 'mesin'); import shamela; "
                "assert shamela._meta(); assert 'pandas' not in sys.modules; "
                "assert shamela.nomor_judul('رسالة في القضاء والقدر')[0]; "
                "assert shamela.katalog('(رياض') > 0; shamela.katalog('a{99999999999}')"],
                cwd=akar, capture_output=True, encoding="utf8", env=dict(os.environ, PYTHONIOENCODING="utf8"))
            assert r.returncode == 0, r.stdout + r.stderr

        def konsumen_katalog():
            import contextlib, io, shamela
            rows = [{"shamela_id": 99001, "book_id": 777, "category_id": 7, "title_ar": "كتاب تجريبي",
                     "main_author_name_ar": "مؤلف", "category_name_ar": "قسم", "has_multi_part": False},
                    {"shamela_id": 99002, "has_multi_part": True}]
            unduh = []
            def ls(p=""):
                return [{"path": "07__قسم/777__كتاب" if p else "07__قسم"}]
            def ambil(url, tujuan, buka):
                unduh.append(url)
                tujuan.write_bytes(b"uji unduh")
            jawaban = {"count": 2, "data": [{"book_id": sid, "snip": "نص البحث",
                "meta": json.dumps({"vol": 1, "page": 9, "book_name": "كتاب", "author_name": "مؤلف"})}
                for sid in (99001, 99002)]}
            out = io.StringIO()
            with patch.object(shamela, "_meta", return_value=rows), contextlib.redirect_stdout(out):
                with patch.object(shamela, "_ls", side_effect=ls), patch.object(shamela, "_unduh", side_effect=ambil), patch.object(shamela, "_cache"):
                    shamela._ambil(99001)
                with patch.object(shamela, "buka", side_effect=lambda *a: io.StringIO(json.dumps(jawaban))):
                    assert shamela.temukan("نص البحث") == 2
            assert len(unduh) == 3 and all("/07__" in u and "/777__" in u for u in unduh), unduh
            assert "ج- ص9" in out.getvalue() and "ج1 ص9" in out.getvalue(), out.getvalue()

        uji("bahan dua folder bernama sama terpisah", terpisah)
        uji("cache mengikuti perubahan isi meski ukuran dan mtime sama", cache_usang)
        uji("indeks mengikuti isi/offset baru meski ukuran dan mtime sama", indeks_usang)
        uji("cache JSON null/bentuk salah dihitung ulang", cache_rusak)
        uji("cache DEFLATE rusak dihitung ulang", cache_deflate_rusak)
        uji("templat/PDF sumber tidak ditimpa hasil rakit", bahan_terlindungi)
        uji("PDF rusak dan penulisan putus tidak meninggalkan hasil", pdf_utuh)
        uji("katalog tanpa pandas dan regex salah tidak crash", katalog_ringan)
        uji("ambil/temukan memakai metadata judul dan jilid yang benar", konsumen_katalog)

        def rakit(mode):
            folder = akar / "a" / "sama"
            naskah(folder)
            sebelum = {"hasil.docx": b"DOCX-LAMA", "hasil.pdf": b"PDF-LAMA", "laporan.txt": b"LAPORAN-LAMA"}
            for n, isi in sebelum.items(): (folder / n).write_bytes(isi)
            arsip_awal = set((folder / "_arsip").iterdir()) if (folder / "_arsip").exists() else set()
            kerja_awal = set(folder.glob(".rakit-*"))
            r = subprocess.run([sys.executable, str(runner), str(akar), "a/sama", mode, "b/sama"],
                               cwd=akar, capture_output=True, encoding="utf8")
            # bahan sementara tidak tertinggal, kecuali hasil baru yang belum bisa dipulihkan (rollback-blocked)
            if mode != "rollback-blocked":
                assert set(folder.glob(".rakit-*")) == kerja_awal, "Rakit meninggalkan folder .rakit-* di folder bahts"
            if mode in ("snapshot", "lock", "ok", "pdf-fail"):
                assert r.returncode == 0, r.stdout + r.stderr
                if mode == "pdf-fail":  # PDF tetap jadi; hanya teks salin/cari yang belum dibetulkan
                    assert "PERINGATAN: PDF jadi" in r.stdout, r.stdout + r.stderr
                assert (folder / "hasil.pdf").read_bytes().startswith(b"%PDF")
                sidik = hashlib.sha256((folder / "naskah.txt").read_bytes()).hexdigest()
                assert "NASKAH_SHA256=" + sidik in (folder / "laporan.txt").read_text(encoding="utf8")
                arsip_akhir = set((folder / "_arsip").iterdir()) if (folder / "_arsip").exists() else set()
                assert arsip_akhir == arsip_awal, "Rakit yang berhasil meninggalkan cadangan di folder bahts"
            else:
                assert r.returncode != 0, r.stdout + r.stderr
                if mode == "rollback-blocked":
                    assert "Pemulihan hasil belum lengkap" in r.stderr, r.stdout + r.stderr
                    assert (folder / "hasil.docx").read_bytes().startswith(b"PK")
                    assert not (folder / "hasil.pdf").exists(), "DOCX baru dipasangkan dengan PDF lama"
                    assert not (folder / "laporan.txt").exists(), "DOCX baru dipasangkan dengan laporan lama"
                    assert any(all((p / n).is_file() and (p / n).read_bytes() == isi for n, isi in sebelum.items())
                               for p in (folder / "_arsip").iterdir())
                    return
                pesan = {"save-fail": "Perakitan Word gagal", "export-fail": "Perakitan Word gagal",
                         "pages-fail": "PDF dan laporan halaman tidak cocok",
                         "publish-fail": "sedang terbuka di aplikasi lain", "changed": "Naskah berubah"}
                assert pesan[mode] in r.stderr, r.stdout + r.stderr
                assert all((folder / n).read_bytes() == isi for n, isi in sebelum.items()), "Hasil lama berubah atau berbeda generasi"

        for mode in ("save-fail", "export-fail", "pdf-fail", "pages-fail", "publish-fail", "rollback-blocked", "changed", "snapshot", "lock"):
            uji("rakit " + mode, lambda mode=mode: rakit(mode))
        if gagal:
            sys.exit(f"{len(gagal)} uji integritas gagal: " + ", ".join(gagal))
        print("uji integritas: 18 skenario sesuai; Word disimulasikan")


if __name__ == "__main__":
    utama()
