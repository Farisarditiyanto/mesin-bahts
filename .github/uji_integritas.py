"""Regresi berkas melalui cek/cari/halaman/rakit asli, pada salinan TEMP.
Word/COM dan kegagalan filesystem disimulasikan; rakit Word sungguhan tetap diuji lokal.
"""
import gzip, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

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
if mode == "publish-fail":
    replace = Path.replace
    ditolak = False
    def ganti(self, target):
        global ditolak
        target = Path(target)
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

        uji("bahan dua folder bernama sama terpisah", terpisah)
        uji("cache mengikuti perubahan isi meski ukuran dan mtime sama", cache_usang)
        uji("indeks mengikuti isi/offset baru meski ukuran dan mtime sama", indeks_usang)
        uji("cache JSON null/bentuk salah dihitung ulang", cache_rusak)

        def rakit(mode):
            folder = akar / "a" / "sama"
            naskah(folder)
            sebelum = {"hasil.docx": b"DOCX-LAMA", "hasil.pdf": b"PDF-LAMA", "laporan.txt": b"LAPORAN-LAMA"}
            for n, isi in sebelum.items(): (folder / n).write_bytes(isi)
            r = subprocess.run([sys.executable, str(runner), str(akar), "a/sama", mode, "b/sama"],
                               cwd=akar, capture_output=True, encoding="utf8")
            if mode in ("snapshot", "lock", "ok"):
                assert r.returncode == 0, r.stdout + r.stderr
                assert (folder / "hasil.pdf").read_bytes().startswith(b"%PDF")
                sidik = hashlib.sha256((folder / "naskah.txt").read_bytes()).hexdigest()
                assert "NASKAH_SHA256=" + sidik in (folder / "laporan.txt").read_text(encoding="utf8")
                cadangan = list((folder / "_arsip").glob("*/hasil.pdf"))
                assert any(p.read_bytes() == sebelum["hasil.pdf"] for p in cadangan)
            else:
                assert r.returncode != 0, r.stdout + r.stderr
                pesan = {"save-fail": "Perakitan Word gagal", "export-fail": "Perakitan Word gagal",
                         "pdf-fail": "pembetulan PDF gagal", "pages-fail": "PDF dan laporan halaman tidak cocok",
                         "publish-fail": "penggantian PDF gagal", "changed": "Naskah berubah"}
                assert pesan[mode] in r.stderr, r.stdout + r.stderr
                assert all((folder / n).read_bytes() == isi for n, isi in sebelum.items()), "Hasil lama berubah atau berbeda generasi"

        for mode in ("save-fail", "export-fail", "pdf-fail", "pages-fail", "publish-fail", "changed", "snapshot", "lock"):
            uji("rakit " + mode, lambda mode=mode: rakit(mode))
        if gagal:
            sys.exit(f"{len(gagal)} uji integritas gagal: " + ", ".join(gagal))
        print("uji integritas: 12 skenario sesuai; Word disimulasikan")


if __name__ == "__main__":
    utama()
