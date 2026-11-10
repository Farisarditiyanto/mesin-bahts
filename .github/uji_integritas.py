# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regresi berkas melalui cek/cari/halaman/rakit asli, pada salinan TEMP.
Word/COM dan kegagalan filesystem disimulasikan; rakit Word sungguhan tetap diuji lokal.
"""
import gzip, hashlib, json, os, random, shutil, subprocess, sys, tempfile, zipfile
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
if mode == "simpan-unlink-gagal":  # penanda bahan sementara tidak bisa dicabut (mis. terkunci antivirus)
    unlink = Path.unlink
    def cabut(self, *a, **k):
        if self.name == bahts.RAKIT_SEMENTARA and ditolak:  # hanya sesudah penggantian hasil gagal
            raise PermissionError("injeksi penanda tidak bisa dicabut")
        return unlink(self, *a, **k)
    Path.unlink = cabut
if mode in ("publish-fail", "rollback-blocked", "simpan-unlink-gagal"):
    replace = Path.replace
    ditolak = False
    def ganti(self, target):
        global ditolak
        target = Path(target)
        if mode in ("rollback-blocked", "simpan-unlink-gagal") and ditolak and self == Path(akar)/nama/"hasil.docx":
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
        # rakit kedua antre dulu (kabar «menunggu giliran»), lalu berhenti sesudah RAKIT_ANTRE habis
        assert r.returncode != 0 and "Rakit lain" in r.stderr and "menunggu giliran" in r.stdout, r.stdout + r.stderr
        # yang antre menyebut pemegang kunci (folder, proses, jam mulai), supaya rakit yang bekerja tidak dimatikan
        assert f"{nama}, proses {os.getpid()}, mulai " in r.stdout and f"({nama}, proses {os.getpid()}" in r.stderr, r.stdout + r.stderr
    d = json.loads(build.read_text(encoding="utf8"))
    assert d["meta"]["judul"] == "المطلوب", "Bahan rakit tertimpa cek lain"
    if mode == "save-fail": return types.SimpleNamespace(returncode=1)
    if mode == "ps-mati": return types.SimpleNamespace(returncode=4294967295)  # Stop-Process -Force: tanpa pesan apa pun
    if mode == "ps-asli":  # rakit.ps1 asli gagal sebelum Word dibuat: kuncinya sedang dibuka proses lain
        with open(args[args.index("-Kunci") + 1], "ab"):
            return run(args, **kwargs)
    hasil = d["meta"]["berkas"]
    if mode.startswith("fasl"):  # bahan yang diterima perakit, untuk diperiksa uji
        (Path(akar) / "bahan-fasl.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf8")
    with zipfile.ZipFile(out / f"{hasil}.docx", "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", "<document/>")
        z.writestr("docProps/core.xml", "<cp:coreProperties><dc:creator>Nama Orang</dc:creator>"
                   "<dc:title>Judul</dc:title><cp:lastModifiedBy>Nama Orang</cp:lastModifiedBy></cp:coreProperties>")
    if mode == "export-fail": return types.SimpleNamespace(returncode=1)
    from pypdf import PdfWriter
    w = PdfWriter(); w.add_blank_page(width=100, height=100)
    with open(out / f"{hasil}.pdf", "wb") as h: w.write(h)
    with open(out / "laporan.txt", "a", encoding="utf8") as h:
        h.write("HALAMAN=99\n" if mode == "pages-fail" else "HALAMAN=1\n")
    if mode == "changed":
        with open(folder / "naskah.txt", "a", encoding="utf8") as h: h.write("نص جديد.\n")
    return types.SimpleNamespace(returncode=0)
bahts.subprocess.run = word
bahts.RAKIT_ANTRE = 3  # antrean asli 30 menit; rakit di dalam rakit (mode lock) tidak boleh menunggu selama itu
fasl = mode[5:] if mode.startswith("fasl:") else None
if mode == "ps-yatim":  # rakit.ps1 yang Python-nya dimatikan masih hidup dan memegang kuncinya, seperti di rakit.ps1
    bahts.RAKIT_PS_KUNCI.parent.mkdir(parents=True, exist_ok=True)
    yatim = subprocess.Popen(["powershell", "-NoProfile", "-Command", f"$k = [IO.File]::Open('{bahts.RAKIT_PS_KUNCI}', "
                              "'OpenOrCreate', 'ReadWrite', 'None'); 'pegang'; Start-Sleep 60"],
                             stdout=subprocess.PIPE, text=True)
    assert yatim.stdout.readline().strip() == "pegang"
    try:
        bahts.rakit(nama, fasl)
    finally:
        yatim.kill()
else:
    bahts.rakit(nama, fasl)
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
        gagal, diuji = [], []

        def uji(nama, fn):
            diuji.append(nama)
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
            f = kitab / f"padat-{norma.VERSI}.bin"
            assert jalan(akar, "cari", "11223", "كلمات جديدة للبحث").returncode == 0
            utuh = f.read_bytes()
            kepala, _, isi = utuh.partition(b"\n")
            # kepala bukan JSON / bentuk salah / sidik lain / tanpa kunci crc32, isi terpotong / berlebih / satu byte berubah (crc32)
            for payload in (b"", b"null\n", b"[null]\n", b"{}\n" + isi, kepala.replace(b'"sumber": "', b'"sumber": "x') + b"\n" + isi,
                            kepala.replace(b'"crc32"', b'"brc32"') + b"\n" + isi,
                            utuh[:len(utuh) // 2], utuh + b"\0", utuh[:-3] + bytes([utuh[-3] ^ 1]) + utuh[-2:]):
                f.write_bytes(payload)
                r = jalan(akar, "cari", "11223", "كلمات جديدة للبحث")
                assert r.returncode == 0, repr(payload[:80]) + r.stdout + r.stderr
                assert f.read_bytes() == utuh, "berkas padat rusak tidak dibuat ulang"

        def angka_ayat_sehalaman():
            f = akar / "uji-angka-ayat"
            sebelum = pages.read_bytes()
            meleset = []

            def cek(body, kutipan, halaman, salah=False, footnotes="", hasyiah=False, samar=False):
                with gzip.open(pages, "wt", encoding="utf8") as h:
                    h.write(json.dumps({"part": None, "page_num": 5, "body": body,
                                        "footnotes": footnotes}, ensure_ascii=False) + "\n")
                naskah(f)
                with open(f / "naskah.txt", "a", encoding="utf8") as h:
                    h.write(f'قال: «{kutipan}»[^رسالة في القضاء والقدر، ص{halaman}. <<11223|-|{halaman}>>].\n')
                r = jalan(akar, "cek", f)
                out = r.stdout + r.stderr
                assert "GALAT MESIN" not in out and "Traceback" not in out, out
                if (r.returncode != 0) != salah or hasyiah and "bukti ada di حاشية المحقق" not in out:
                    meleset.append(f"hal {halaman}, «{kutipan}»: keluar={r.returncode}, harus gagal={salah}, hasyiah={hasyiah}")
                if samar and "halaman tiap catatan di rekaman ini tidak tercatat" not in out:
                    meleset.append("Ketidakpastian halaman حاشية tidak disebut")

            try:
                angka = "عدد أبواب هذا الكتاب {} أبواب"
                body = angka.format(10) + ". ⦗٦⦘ " + angka.format(20) + "."
                for halaman, benar, keliru in ((5, 10, 20), (6, 20, 10)):
                    cek(body, angka.format(benar), halaman)
                    cek(body, angka.format(keliru), halaman, salah=True)
                ayat = "قال الله تعالى: {} ثم انتهى الكلام"
                body = ayat.format("﴿الحمد لله رب العالمين﴾ [الفاتحة:٢]") + ". ⦗٦⦘ " + ayat.format(
                    "﴿قل هو الله أحد﴾ [الإخلاص:١]") + "."
                for halaman, benar, keliru in ((5, "1:2", "112:1"), (6, "112:1", "1:2")):
                    cek(body, ayat.format("{Q:" + benar + "}"), halaman)
                    cek(body, ayat.format("{Q:" + keliru + "}"), halaman, salah=True)
                # Angka yang benar hanya di kemunculan yang berakhir di tengah kata tidak boleh dipakai.
                cek(angka.format(10) + ". " + angka.format(20) + "نا.", angka.format(20), 5, salah=True)
                cek("قال العلماء هذا الكلام ثم " + angka.format(20) + "نا ثم " + angka.format(20),
                    "قال العلماء هذا الكلام ... " + angka.format(20), 5)
                # Kemunculan sah setelah 50 calon tetap harus diperiksa.
                cek((angka.format(20) + ". ") * 60 + angka.format(10), angka.format(10), 5)
                # Angka yang hanya cocok di حاشية tetap harus menyebut sumbernya, walau hurufnya cocok di matan.
                cek(angka.format(10), angka.format(20), 5, footnotes=angka.format(20), hasyiah=True)
                cek(angka.format(10) + " ⦗٦⦘ " + angka.format(10), angka.format(20), 6,
                    footnotes=angka.format(20), hasyiah=True, samar=True)
                # Kepala/ekor angka ikut terikat halaman, bukan hanya posisi huruf Arabnya.
                for body, kutipan, halaman in (("عدد أبواب هذا الكتاب ⦗٦⦘ 20 خاتمة", "عدد أبواب هذا الكتاب 20", 5),
                                               ("20 ⦗٦⦘ عدد أبواب هذا الكتاب", "20 عدد أبواب هذا الكتاب", 6)):
                    cek(body, kutipan, halaman, salah=True)
                    cek(body, kutipan, "5-6")
                cek("عدد أبواب هذا الكتاب 10 ⦗٦⦘ خاتمة", "عدد أبواب هذا الكتاب 20", 5, salah=True,
                    footnotes="عدد أبواب هذا الكتاب ⦗٦⦘ 20 خاتمة")
                # Konteks ayat di luar halaman bukti tetap dibaca; membatasi calon tidak boleh membuang konteksnya.
                for spec, salah in (("1:2", False), ("112:1", True)):
                    cek("قال الله تعالى ⦗٦⦘ ﴿الحمد لله رب العالمين﴾ [الفاتحة:٢]",
                        "قال الله تعالى {Q:" + spec + "}", 5, salah=salah)
                    cek("﴿الحمد لله رب العالمين﴾ [الفاتحة:٢] ⦗٦⦘ وفي الآية بيان واضح",
                        "{Q:" + spec + "} وفي الآية بيان واضح", 6, salah=salah)
                # Derajat di halaman tetangga satu rekaman tidak membuktikan derajat di halaman yang dirujuk.
                with gzip.open(pages, "wt", encoding="utf8") as h:
                    h.write(json.dumps({"part": None, "page_num": 5,
                                        "body": "هذا نص الحديث للاختبار. وهو حديث ضعيف. ⦗٦⦘ هذا حديث صحيح.",
                                        "footnotes": ""}, ensure_ascii=False) + "\n")
                for derajat, salah in (("صحيح", True), ("ضعيف", False)):
                    naskah(f)
                    with (f / "naskah.txt").open("a", encoding="utf8") as h:
                        h.write("معنى من المصدر[^أخرجه أبو داود، انظر: رسالة في القضاء والقدر، ص5، "
                                f"وهو حديث {derajat}. <<11223|-|5|هذا نص الحديث للاختبار>>].\n")
                    r = jalan(akar, "cek", f)
                    assert (r.returncode != 0) == salah, r.stdout + r.stderr
                # حاشية tanpa penanda halaman milik seluruh rekaman (Abu Dawud 1726 1/2): derajatnya tetap terbaca
                # untuk bukti di halaman kedua rekaman, jadi «صحيح» hadits lain di halaman itu tidak membuat GAGAL palsu.
                with gzip.open(pages, "wt", encoding="utf8") as h:
                    h.write(json.dumps({"part": None, "page_num": 5,
                                        "body": "تمهيد الباب. ⦗٦⦘ هذا نص الحديث للاختبار. وفي الباب حديث صحيح.",
                                        "footnotes": "الحكم ضعيف."}, ensure_ascii=False) + "\n")
                naskah(f)
                with (f / "naskah.txt").open("a", encoding="utf8") as h:
                    h.write("معنى من المصدر[^أخرجه أبو داود، انظر: رسالة في القضاء والقدر، ص6، "
                            "وهو حديث ضعيف. <<11223|-|6|هذا نص الحديث للاختبار>>].\n")
                r = jalan(akar, "cek", f)
                assert r.returncode == 0 and "berlawanan" not in r.stdout, r.stdout + r.stderr
                # Dengan nomor takhrij, حاشية hadits berikutnya juga tidak boleh dipakai.
                with gzip.open(pages, "wt", encoding="utf8") as h:
                    h.write(json.dumps({"part": None, "page_num": 5,
                                        "body": "1 - هذا نص الحديث للاختبار. وهو حديث ضعيف.\n⦗٦⦘\n2 - هذا نص آخر للاختبار.",
                                        "footnotes": "الحكم ضعيف. ⦗٦⦘ الحكم صحيح."}, ensure_ascii=False) + "\n")
                for derajat, salah in (("صحيح", True), ("ضعيف", False)):
                    naskah(f)
                    with (f / "naskah.txt").open("a", encoding="utf8") as h:
                        h.write("معنى من المصدر[^أخرجه أبو داود، انظر: رسالة في القضاء والقدر، رقم الحديث (1)، ص5، "
                                f"وهو حديث {derajat}. <<11223|-|5|هذا نص الحديث للاختبار>>].\n")
                    r = jalan(akar, "cek", f)
                    assert (r.returncode != 0) == salah, r.stdout + r.stderr
                # Properti: angka dari halaman tetangga tidak boleh membuktikan 100 kutipan acak (benih tetap).
                rng = random.Random(17)
                potong, sampel = [], []
                for i in range(100):
                    kata = " ".join(rng.choices("باب فصل علم عمل كتاب دليل حكم قول شرط أصل بيان سبب".split(), k=6))
                    a, b = rng.sample(range(100, 10000), 2)
                    frasa = lambda n: f"في {kata} العدد {n} مسائل"
                    for hal, teks in ((5 + 2 * i, frasa(a)), (6 + 2 * i, frasa(b))):
                        potong.append((f" ⦗{str(hal).translate(str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩'))}⦘ " if potong else "") + teks)
                    sampel.append((5 + 2 * i, frasa(a), frasa(b)))
                with gzip.open(pages, "wt", encoding="utf8") as h:
                    h.write(json.dumps({"part": None, "page_num": 5, "body": ". ".join(potong),
                                        "footnotes": ""}, ensure_ascii=False) + "\n")
                for salah in (False, True):
                    naskah(f)
                    with open(f / "naskah.txt", "a", encoding="utf8") as h:
                        for hal, benar, keliru in sampel:
                            h.write(f'قال: «{keliru if salah else benar}»[^رسالة في القضاء والقدر، ص{hal}. <<11223|-|{hal}>>].\n')
                    r = jalan(akar, "cek", f)
                    out = r.stdout + r.stderr
                    assert "GALAT MESIN" not in out and "Traceback" not in out, out
                    if f"| GAGAL: {len(sampel) if salah else 0}\n" not in out:
                        meleset.append(f"100 kutipan acak, harus gagal={salah}: " + out.splitlines()[1])
                assert not meleset, "\n".join(meleset)
            finally:
                pages.write_bytes(sebelum)

        def takhrij_per_kitab():
            f = akar / "uji-takhrij"
            kedua = akar / "kitab" / "99999"
            kedua.mkdir()
            meta = json.loads((kitab / "book_metadata.json").read_text(encoding="utf8"))
            meta["title_ar"] = "كتاب الفحص الثاني"
            (kedua / "book_metadata.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf8")
            sebelum = pages.read_bytes()
            try:
                for tujuan, nomor, lafaz in ((pages, 1, "الأول"), (kedua / "pages.jsonl.gz", 2, "الثاني")):
                    with gzip.open(tujuan, "wt", encoding="utf8") as h:
                        h.write(json.dumps({"part": None, "page_num": 5,
                                            "body": f"{nomor} - هذا نص الحديث {lafaz} للاختبار.", "footnotes": ""},
                                           ensure_ascii=False) + "\n")
                naskah(f)
                with (f / "naskah.txt").open("a", encoding="utf8") as h:
                    h.write("معنى من المصدر[^أخرجه أبو داود، انظر: رسالة في القضاء والقدر، رقم الحديث (1)، ص5؛ "
                            "وكتاب الفحص الثاني، رقم الحديث (2)، ص5، ولم أقف على حكم لأهل العلم. "
                            "<<11223|-|5|هذا نص الحديث الأول للاختبار>> <<99999|-|5|هذا نص الحديث الثاني للاختبار>>].\n")
                r = jalan(akar, "cek", f)
                assert r.returncode == 0 and "perhatian (lolos, tetapi lihat sendiri): 0" in r.stdout, r.stdout + r.stderr
            finally:
                pages.write_bytes(sebelum)

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

        def temukan_saring():
            import contextlib, io, shamela, urllib.parse
            rows = [{"shamela_id": 99001, "has_multi_part": False}, {"shamela_id": 8370, "has_multi_part": True}]
            jawaban = {"count": 45, "data": [{"book_id": 99001, "snip": "نص", "meta": json.dumps(
                {"vol": 1, "page": 9, "book_name": "كتاب", "author_name": "مؤلف"})}] * 20}
            alamat = []
            def buka(url, *a):
                alamat.append(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query))
                return io.StringIO(json.dumps(jawaban))
            out = io.StringIO()
            with patch.object(shamela, "_meta", return_value=rows), patch.object(shamela, "buka", side_effect=buka), contextlib.redirect_stdout(out):
                assert shamela.temukan("نص البحث", 20, ["hanafi", "hanbali"], [], 2) == 45
                assert shamela.temukan("نص البحث", 5, [], ["8370"]) == 45
                shamela.temukan("نص البحث")
            assert alamat[0]["cat"] == ["14,17"] and alamat[0]["page"] == ["2"], alamat
            assert alamat[1]["book"] == ["8370"] and "cat" not in alamat[1], alamat
            assert "cat" not in alamat[2] and "book" not in alamat[2], alamat
            keluar = out.getvalue()
            assert "45 tempat cocok di fikih hanafi, hanbali" in keluar and "21-40 dari 45" in keluar and "--halaman 3" in keluar, keluar
            assert "1-5 dari 45" in keluar and "45 tempat cocok di kitab 8370" in keluar and "45 tempat cocok di seluruh Shamela" in keluar, keluar
            assert "hasil berikutnya: naikkan maks" in keluar, "maks kecil + --halaman melompati hasil"
            jawaban["data"] = []
            out = io.StringIO()
            with patch.object(shamela, "_meta", return_value=rows), patch.object(shamela, "buka", side_effect=buka), contextlib.redirect_stdout(out):
                assert shamela.temukan("نص البحث", 20, [], [], 9) == 0
            assert "Halaman 9 melewati akhir hasil: 45" in out.getvalue(), out.getvalue()
            with patch.object(shamela, "_meta", return_value=rows), patch.object(
                    shamela, "buka", side_effect=AssertionError("saringan salah tidak boleh sampai ke turath")):
                for salah, kata in ((dict(mazhab=["zahiri"]), "zahiri"), (dict(mazhab=["hanafi"], kitab=["8370"]), "salah satu"),
                                    (dict(kitab=["5"]), "katalog")):
                    try:
                        shamela.temukan("نص البحث", **salah)
                    except ValueError as e:
                        assert kata in str(e), e
                    else:
                        raise AssertionError(f"harus ditolak: {salah}")

        uji("bahan dua folder bernama sama terpisah", terpisah)
        uji("cache mengikuti perubahan isi meski ukuran dan mtime sama", cache_usang)
        uji("indeks mengikuti isi/offset baru meski ukuran dan mtime sama", indeks_usang)
        uji("berkas padat rusak/terpotong/bentuk salah dihitung ulang", cache_rusak)
        uji("angka dan ayat terikat halaman, batas kata, dan bagian kitab", angka_ayat_sehalaman)
        uji("nomor takhrij dipasangkan ke kitabnya walau halaman sama", takhrij_per_kitab)
        uji("templat/PDF sumber tidak ditimpa hasil rakit", bahan_terlindungi)
        uji("PDF rusak dan penulisan putus tidak meninggalkan hasil", pdf_utuh)
        uji("katalog tanpa pandas dan regex salah tidak crash", katalog_ringan)
        uji("temukan: saringan mazhab, kitab, dan halaman sampai ke turath", temukan_saring)
        uji("ambil/temukan memakai metadata judul dan jilid yang benar", konsumen_katalog)

        def rakit_ringkas():
            folder = akar / "a" / "ringkas"
            naskah(folder)
            luar = 'قال الباحث: "القدر من أعظم أبواب الاعتقاد"[^بحث وهمي، ص5. <<luar>>].\n'  # lolos + satu perhatian
            tanpa = "وهذا معنى التوحيد[^انظر: كتاب التوحيد، ص٣.].\n"  # lolos + catatan kaki tanpa bukti
            with open(folder / "naskah.txt", "a", encoding="utf8") as h: h.write(luar + tanpa)
            r = subprocess.run([sys.executable, str(runner), str(akar), "a/ringkas", "ok", "-"],
                               cwd=akar, capture_output=True, encoding="utf8")
            assert r.returncode == 0, r.stdout + r.stderr
            lap = (folder / "laporan.txt").read_text(encoding="utf8")
            rinci = [b for b in lap.splitlines() if b.startswith("  ! ")]
            # cek lolos: laporan.txt tetap lengkap, layar rakit hanya satu baris cek lalu hasil rakit
            assert rinci and "GAGAL: 0" in lap, lap
            assert f"cek: GAGAL 0, perhatian {len(rinci)}" in r.stdout and not any(b in r.stdout for b in rinci), r.stdout
            fn = [b for b in lap.splitlines() if b.startswith("catatan kaki tanpa bukti")]  # jumlahnya tetap di layar
            assert fn and not fn[0].endswith(": 0") and fn[0] in r.stdout, (fn, r.stdout)
            assert "HALAMAN=1" in r.stdout and "Jadi:" in r.stdout, r.stdout
            # cek GAGAL: rinciannya tetap tercetak lengkap (agent perlu baris ✗-nya)
            with open(folder / "naskah.txt", "a", encoding="utf8") as h:
                h.write('قال الشيخ: "نص لا يوجد في الكتاب أصلا ألبتة"[^رسالة، ص5. <<11223|-|5>>].\n')
            r = subprocess.run([sys.executable, str(runner), str(akar), "a/ringkas", "ok", "-"],
                               cwd=akar, capture_output=True, encoding="utf8")
            assert r.returncode != 0 and "  ✗ " in r.stdout and "  ! " in r.stdout and "cek: GAGAL" not in r.stdout, r.stdout + r.stderr
        uji("rakit: cek lolos dicetak satu baris, cek GAGAL dicetak lengkap", rakit_ringkas)

        def rakit(mode):
            folder = akar / "a" / "sama"
            naskah(folder)
            sebelum = {"hasil.docx": b"DOCX-LAMA", "hasil.pdf": b"PDF-LAMA", "laporan.txt": b"LAPORAN-LAMA"}
            for n, isi in sebelum.items(): (folder / n).write_bytes(isi)
            arsip_awal = set((folder / "_arsip").iterdir()) if (folder / "_arsip").exists() else set()
            yatim = folder / ".rakit-yatim"  # tertinggal rakit versi ini yang Python-nya dimatikan
            lama = folder / ".rakit-lama"  # disimpan versi lama («Bahan percobaan disimpan») tanpa penanda apa pun
            if mode in ("sisa", "ps-yatim"):
                yatim.mkdir(exist_ok=True); (yatim / "bahan.json").write_text("{}")
                (yatim / bahts.RAKIT_SEMENTARA).write_text("")
                lama.mkdir(exist_ok=True); (lama / "hasil.pdf").write_bytes(b"%PDF-HASIL-BARU")
            kerja_awal = set(folder.glob(".rakit-*"))
            r = subprocess.run([sys.executable, str(runner), str(akar), "a/sama", mode, "b/sama"],
                               cwd=akar, capture_output=True, encoding="utf8")
            # bahan sementara tidak tertinggal, kecuali hasil baru yang belum bisa dipulihkan (rollback-blocked)
            if mode == "sisa":  # sisa rakit mati dibuang; hasil baru rollback-blocked (bertanda) dibiarkan
                assert set(folder.glob(".rakit-*")) == kerja_awal - {yatim}, "Sisa .rakit-* salah dibersihkan"
                assert "Sisa rakit yang terhenti dibuang: .rakit-yatim" in r.stdout, r.stdout + r.stderr
                assert (lama / "hasil.pdf").read_bytes() == b"%PDF-HASIL-BARU", "Folder versi lama tanpa penanda dibuang"
                assert "Folder .rakit-lama dibiarkan" in r.stdout, r.stdout + r.stderr
                assert any((k / bahts.RAKIT_SIMPAN).is_file() for k in kerja_awal), "Hasil baru rollback-blocked tidak bertanda"
            elif mode not in ("rollback-blocked", "simpan-unlink-gagal"):
                assert set(folder.glob(".rakit-*")) == kerja_awal, "Rakit meninggalkan atau membuang folder .rakit-* di folder bahts"
            if mode in ("snapshot", "lock", "ok", "pdf-fail", "sisa"):
                assert r.returncode == 0, r.stdout + r.stderr
                if mode == "pdf-fail":  # PDF tetap jadi; hanya teks salin/cari yang belum dibetulkan
                    assert "PERINGATAN: PDF jadi" in r.stdout, r.stdout + r.stderr
                assert (folder / "hasil.pdf").read_bytes().startswith(b"%PDF")
                with zipfile.ZipFile(folder / "hasil.docx") as z:
                    inti = z.read("docProps/core.xml").decode("utf8")
                assert "Nama Orang" not in inti and "<dc:title>Judul</dc:title>" in inti, "Nama pengguna Word tertinggal di .docx"
                sidik = hashlib.sha256((folder / "naskah.txt").read_bytes()).hexdigest()
                assert "NASKAH_SHA256=" + sidik in (folder / "laporan.txt").read_text(encoding="utf8")
                arsip_akhir = set((folder / "_arsip").iterdir()) if (folder / "_arsip").exists() else set()
                assert arsip_akhir == arsip_awal, "Rakit yang berhasil meninggalkan cadangan di folder bahts"
            else:
                assert r.returncode != 0, r.stdout + r.stderr
                if mode in ("rollback-blocked", "simpan-unlink-gagal"):
                    assert "Pemulihan hasil belum lengkap" in r.stderr, r.stdout + r.stderr
                    simpanan = set(folder.glob(".rakit-*")) - kerja_awal  # hasil baru yang belum terpasang
                    assert simpanan and all((k / bahts.RAKIT_SIMPAN).is_file() for k in simpanan), "Hasil baru tidak disimpan bertanda"
                    assert (folder / "hasil.docx").read_bytes().startswith(b"PK")
                    assert not (folder / "hasil.pdf").exists(), "DOCX baru dipasangkan dengan PDF lama"
                    assert not (folder / "laporan.txt").exists(), "DOCX baru dipasangkan dengan laporan lama"
                    assert any(all((p / n).is_file() and (p / n).read_bytes() == isi for n, isi in sebelum.items())
                               for p in (folder / "_arsip").iterdir())
                    return
                tanpa_pesan = "Perakitan Word gagal: rakit.ps1 berhenti tanpa pesan (kode keluar {})"
                pesan = {"save-fail": tanpa_pesan.format(1), "export-fail": tanpa_pesan.format(1),
                         "ps-mati": tanpa_pesan.format(4294967295),
                         "ps-asli": "Perakitan Word gagal (rakit.ps1, kode keluar 1): Rakit lain sedang jalan (memakai Word yang sama)",
                         "ps-yatim": "rakit.ps1 dari rakit yang dimatikan masih jalan",
                         "pages-fail": "PDF dan laporan halaman tidak cocok",
                         "publish-fail": "sedang terbuka di aplikasi lain", "changed": "Naskah berubah"}
                # dicari di baris GAGAL itu sendiri: pemanggil sering hanya melihat ekornya (tail/grep)
                akhir = [b for b in r.stderr.splitlines() if b.startswith("Perakitan GAGAL")]
                assert akhir and pesan[mode] in akhir[-1], r.stdout + r.stderr
                assert all((folder / n).read_bytes() == isi for n, isi in sebelum.items()), "Hasil lama berubah atau berbeda generasi"

        def per_fasl():
            folder = akar / "a" / "fasl"
            folder.mkdir(parents=True)
            isi = "نص الفصل للتجربة."
            teks = ("@judul: المطلوب\n@nama: اسم\n@berkas: hasil\n#K المقدمة\n" + isi + "\n"
                    "#F الفصل الأول: أ\nقال تعالى: {Q:1:2}[^سورة الفاتحة، آية: ٢.].\n"
                    "{N:عمر بن الخطاب}{H:إنما الأعمال بالنيات|عمر|niyya}قال: إنما الأعمال بالنيات[^أخرجه البخاري.].\n"
                    "#F الفصل الثاني: ب\nقال تعالى: {Q:1:5}[^سورة الفاتحة، آية: ٥.].\n{H2:niyya}قال: إنما الأعمال بالنيات[^PG].\n"
                    "#F الفصل الثالث: ج\nقال تعالى: {Q:1:4}[^سورة الفاتحة، آية: ٤.].\n"
                    "{N:عمر بن الخطاب}{N:تميم الداري}{H:الدين النصيحة|تميم|nasiha}قال: الدين النصيحة[^أخرجه مسلم.].\n{H2:nasiha}قال: الدين النصيحة[^سبق تخريجه، ص{P:nasiha}.].\n"
                    "#K الخاتمة\n" + isi + "\n#R المصادر والمراجع\nالقرآن الكريم.\n")
            (folder / "laporan.txt").write_text("LAPORAN-UTUH", encoding="utf8")

            def rakit_fasl(n, pg="أخرجه البخاري."):
                (folder / "naskah.txt").write_text(teks.replace("PG", pg), encoding="utf8")
                (akar / "bahan-fasl.json").unlink(missing_ok=True)
                r = subprocess.run([sys.executable, str(runner), str(akar), "a/fasl", "fasl:" + n, "-"],
                                   cwd=akar, capture_output=True, encoding="utf8")
                b = json.loads((akar / "bahan-fasl.json").read_text(encoding="utf8")) if r.returncode == 0 else None
                return r, b

            def judul(b):
                return [x["judul"] for x in b["blok"] if x["k"] in ("K", "F", "B", "M")]
            r, b = rakit_fasl("1")
            assert r.returncode == 0, r.stdout + r.stderr
            assert judul(b) == ["المقدمة", "الفصل الأول: أ"], judul(b)
            assert not b["meta"].get("tanpa_sampul") and b["meta"]["tanpa"] == "ayat, hadits, alam, maudhuat, pustaka", b["meta"]
            assert b["meta"]["berkas"] == "hasil - المقدمة والفصل الأول" and (folder / "hasil - المقدمة والفصل الأول.pdf").is_file()
            assert [a["a"] for a in b["ayat"]] == ["2"] and [h["k"] for h in b["hadits"]] == ["h_niyya"], (b["ayat"], b["hadits"])
            assert (folder / "laporan-fasl1.txt").read_text(encoding="utf8").startswith("POTONGAN=--fasl 1: المقدمة والفصل الأول")
            assert (folder / "laporan.txt").read_text(encoding="utf8") == "LAPORAN-UTUH", "laporan seluruh naskah tertimpa"
            r, b = rakit_fasl("2")  # {H2:} di sini, {H:}-nya di potongan 1: halaman فهرسnya hanya yang di sini
            assert r.returncode == 0, r.stdout + r.stderr
            assert judul(b) == ["الفصل الثاني: ب"] and b["meta"]["tanpa_sampul"], (judul(b), b["meta"])
            assert [h["k"] for h in b["hadits"]] == ["h_niyya_1"] and b["meta"]["tanpa"] == "ayat, hadits, alam, maudhuat, pustaka"
            r, b = rakit_fasl("3")
            assert r.returncode == 0, r.stdout + r.stderr
            assert judul(b) == ["الفصل الثالث: ج", "الخاتمة"] and b["meta"]["tanpa_sampul"] and not b["meta"].get("tanpa"), b["meta"]
            assert b["meta"]["berkas"] == "hasil - الفصل الثالث والخاتمة" and b["pustaka"] == ["القرآن الكريم."]
            assert [a["a"] for a in b["ayat"]] == ["4"] and [h["k"] for h in b["hadits"]] == ["h_nasiha"], (b["ayat"], b["hadits"])
            # {N:} yang sama di potongan lain: halaman فهرس الأعلام hanya yang di sini; urut tanpa «ال/ابن/أبو»
            assert [(a["t"], len(a["k"])) for a in b["alam"]] == [("تميم الداري", 1), ("عمر بن الخطاب", 1)], b["alam"]
            r, b = rakit_fasl("1-3")
            assert r.returncode == 0 and len(judul(b)) == 5 and not b["meta"].get("tanpa_sampul") and not b["meta"].get("tanpa")
            # {P:} ke hadits di potongan lain: nomor halamannya tidak ada di PDF potongan itu; berhenti sebelum Word
            r, _ = rakit_fasl("2", "سبق تخريجه، ص{P:niyya}.")
            assert r.returncode != 0 and "{P:niyya}" in r.stderr and "takhrij lengkap" in r.stderr, r.stdout + r.stderr
            assert not (akar / "bahan-fasl.json").exists(), "Word dipanggil untuk potongan yang rusak"
            for salah, pesan in (("4", "hanya punya 3 #F"), ("3-1", "dari kecil ke besar"), ("x", "tulis nomor #F")):
                r, _ = rakit_fasl(salah)
                assert r.returncode != 0 and pesan in r.stderr, (salah, r.stdout + r.stderr)
            # Judul sah yang mengandung tanda nama berkas Windows hanya dibersihkan di nama hasilnya.
            asli = teks
            teks = teks.replace("الفصل الثاني: ب", "الفصل الثاني / التحقيق")
            r, b = rakit_fasl("2")
            assert r.returncode == 0, r.stdout + r.stderr
            assert judul(b) == ["الفصل الثاني / التحقيق"] and "/" not in b["meta"]["berkas"], b["meta"]
            teks = asli
            # Nama hasil berubah sesudah cek seluruh naskah: PDF sumber potongan tetap harus dilindungi.
            pdf = folder / "hasil - الفصل الثاني.pdf"
            from pypdf import PdfWriter
            w = PdfWriter(); w.add_blank_page(width=100, height=100)
            with pdf.open("wb") as h: w.write(h)
            sebelum = pdf.read_bytes()
            teks = teks.replace("#F الفصل الثاني: ب\n", "#F الفصل الثاني: ب\nمعنى من المصدر[^انظر: دراسة، ص1. "
                                "<<luar|hasil - الفصل الثاني.pdf|1>>].\n")
            r, _ = rakit_fasl("2")
            assert r.returncode != 0 and "menimpa bahan sumber" in r.stdout + r.stderr, r.stdout + r.stderr
            assert pdf.read_bytes() == sebelum, "rakit --fasl mengganti PDF sumber"
            assert not (akar / "bahan-fasl.json").exists(), "Word dipanggil sebelum melindungi PDF sumber potongan"
        uji("rakit --fasl: satu naskah, potongan per فصل", per_fasl)
        for mode in ("save-fail", "export-fail", "ps-mati", "pdf-fail", "pages-fail", "publish-fail", "rollback-blocked", "simpan-unlink-gagal",
                     "changed", "snapshot", "lock", "sisa", *(("ps-asli", "ps-yatim") if os.name == "nt" else ())):
            uji("rakit " + mode, lambda mode=mode: rakit(mode))
        if gagal:
            sys.exit(f"{len(gagal)} uji integritas gagal: " + ", ".join(gagal))
        print(f"uji integritas: {len(diuji)} skenario sesuai; Word disimulasikan")


def word_asli():
    """Opsional lokal: python .github/uji_integritas.py --word (Windows + Word, tidak disimulasikan).
    Isi catatan tetap sama saat nomor diulang per halaman, juga di potongan dan sesudah bukti tanpa catatan tercetak."""
    from xml.etree import ElementTree as ET
    from pypdf import PdfReader
    with tempfile.TemporaryDirectory(prefix="bahts-word-") as t:
        akar = Path(t)
        shutil.copytree(AKAR / "mesin", akar / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__"))
        for sid in ("_meta", "11223"):
            shutil.copytree(AKAR / "kitab" / sid, akar / "kitab" / sid)
        f = akar / "uji"
        f.mkdir()
        teks = ("@judul: فحص الحواشي\n@bentuk: kitab\n@berkas: hasil\n"
                "@tanpa: pustaka, ayat, hadits, maudhuat\n@halaman_baru: B\n@rumuz: 11223=-\n"
                "#K المقدمة\nهذا تمهيد للفحص.\n#F الفصل الأول\nهذا فصل سابق[^OLD-FIRST-NOTE].\n"
                "#F الفصل الثاني\nهذا تمهيد للفصل الثاني.\n#B المبحث الأول\n"
                "توحيد الربوبية وهو إفراد الله تعالى بالخلق والملك والتدبير[^<<11223|-|5>>]\n"
                "هذا نص المبحث الأول[^EXPECTED-SECOND-NOTE].\n"
                "#B المبحث الثاني\nهذا نص المبحث الثاني[^EXPECTED-THIRD-NOTE].\n#K الخاتمة\nانتهى الفحص.\n")
        (f / "naskah.txt").write_text(teks, encoding="utf8")
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        for args, nama, harus in (((), "hasil", ["OLD-FIRST-NOTE", "EXPECTED-SECOND-NOTE", "EXPECTED-THIRD-NOTE"]),
                                  (("--fasl", "2"), "hasil - الفصل الثاني والخاتمة", ["EXPECTED-SECOND-NOTE", "EXPECTED-THIRD-NOTE"])):
            r = jalan(akar, "rakit", "uji", *args)
            assert r.returncode == 0, r.stdout + r.stderr
            with zipfile.ZipFile(f / f"{nama}.docx") as z:
                tree = ET.fromstring(z.read("word/footnotes.xml"))
            catatan = ["".join(n.itertext()) for n in tree.findall("w:footnote", ns)
                       if int(n.attrib.get("{" + ns["w"] + "}id", "0")) > 0]
            assert len(catatan) == len(harus) and all(h in c for h, c in zip(harus, catatan)), catatan
            pdf = "\n".join(p.extract_text() or "" for p in PdfReader(f / f"{nama}.pdf").pages)
            assert all(h in pdf for h in harus), pdf
            print(f"Word asli {args or 'utuh'}: {len(catatan)} isi catatan DOCX dan PDF tetap benar")


if __name__ == "__main__":
    word_asli() if sys.argv[1:] == ["--word"] else utama()
