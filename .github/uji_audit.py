# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regresi pembersihan rakit dan pemeriksaan rujukan lewat CLI asli, tanpa bahan pribadi atau Word tiruan.

Kegagalan rakit dihentikan oleh cek, sehingga pembersihan asli tetap diuji tanpa Word.
Seluruh bahan dan tautan dibuat di TEMP; jaringan tidak dipakai.
"""
import ctypes, hashlib, json, os, random, shutil, subprocess, sys, tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent


def utama():
    sys.stdout.reconfigure(encoding="utf8")
    gagal, lolos = [], []
    with tempfile.TemporaryDirectory(prefix="bahts-audit-") as t:
        akar = Path(t)
        shutil.copytree(AKAR / "mesin", akar / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__", "*.ttf"))
        for sid in ("_meta", "11223", "2348", "1082", "7283"):
            shutil.copytree(AKAR / "kitab" / sid, akar / "kitab" / sid)
        f = akar / "uji"
        f.mkdir()
        dasar = (AKAR / "contoh" / "naskah.txt").read_text(encoding="utf8")
        (f / "riset.txt").write_text("tafsir 1:2\n", encoding="utf8")

        def jalan(cmd="cek", teks=dasar):
            (f / "naskah.txt").write_text(teks, encoding="utf8")
            r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), cmd, "uji"], cwd=akar,
                               capture_output=True, encoding="utf8", timeout=60)
            assert "Traceback" not in r.stderr and "GALAT MESIN" not in r.stdout, r.stdout + r.stderr
            return r

        def uji(nama, kerja):
            try:
                kerja()
            except AssertionError as e:
                gagal.append(nama)
                print(f"GAGAL {nama}: {str(e)[:900]}")
            else:
                lolos.append(nama)
                print(f"lolos {nama}")

        def harus(teks, pesan, ada):
            r = jalan(teks=teks)
            assert r.returncode == 0 and (pesan in r.stdout) == ada, r.stdout + r.stderr

        lengkap = dasar.replace("@jenis: مثال تجريبي", "@jenis: رسالة ماجستير").replace(
            "#K المقدمة\n", "#K المقدمة\nموضوع البحث وأهميته وأسباب اختياره وآفاقه وإجراءاته ومنهجه "
            "ومصطلحاته والدراسات السابقة وخطته.\n", 1)
        for nama in ("مقدمة في علم اللغة", "خاتمة في علم اللغة"):
            teks = lengkap.replace("#K المقدمة", f"#F {nama}\nكلام في اللغة.\n#K المقدمة", 1)
            pesan = "المقدمة belum" if nama.startswith("مقدمة") else "الخاتمة belum"
            uji(nama + " ليست قسم البحث", lambda teks=teks, pesan=pesan: harus(teks, pesan, False))
        uji("حدود البحث ليست آفاقه الأخرى", lambda: harus(lengkap.replace("وآفاقه", "وحدوده"), "آفاق البحث", True))
        for judul in ("المقدمة: تمهيد الدراسة", "الفصل الأول: المقدمة: تمهيد الدراسة"):
            teks = dasar.replace("@jenis: مثال تجريبي", "@jenis: رسالة ماجستير").replace("#K المقدمة", "#F " + judul)
            uji(judul, lambda teks=teks: harus(teks, "المقدمة belum", True))
        khatimah = dasar.split("#K الخاتمة\n", 1)[1].split("\n", 1)[0]
        uji("مخلصا ليست نتائج البحث", lambda: harus(dasar.replace(khatimah, "كتبت هذا البحث مخلصا لله تعالى."),
                                                  "الخاتمة belum menyebut النتائج", True))
        uji("خلصت إلى نتيجة فعلية", lambda: harus(dasar.replace(khatimah, "خلصت إلى أن العلم بالقضاء أصل في هذا البحث."),
                                                 "الخاتمة belum menyebut النتائج", False))

        pendek = dasar.replace("#K الخاتمة", "وانظر[^انظر: رسالة في القضاء والقدر، ابن عثيمين، ص5. "
                               "<<011223|-|5|توحيد الربوبية وهو إفراد الله تعالى بالخلق>>].\n#K الخاتمة")
        uji("nomor kitab bernol tetap rujukan kedua", lambda: harus(pendek, "rujukan pertama", False))

        def tahun_palsu():
            for tahun in ("11426هـ", "01426هـ", "14260هـ", "٠١٤٢٦هـ"):
                teks = dasar.replace("#K الخاتمة", f"وانظر[^انظر: القاموس المحيط، الفيروزآبادي، {tahun}، ص460. "
                                     "<<7283|-|460|القضاء والحكم ومبلغ الشيء>>].\n#K الخاتمة")
                harus(teks, "rujukan pertama", True)
        uji("tahun lima digit bukan tahun cetak kartu", tahun_palsu)

        # penerbit «دار ابن …» tanpa tahun tetap data cetak
        ibnu = dasar.replace("#K الخاتمة", "وانظر[^انظر: سبل السلام، الصنعاني، تحقيق: محمد حلاق، دار ابن الجوزي، "
                             "الدمام، 1/5. <<1082|1|5|إن الحمد لله نحمده>>].\n#K الخاتمة")
        uji("«دار ابن الجوزي» adalah data cetak", lambda: harus(ibnu, "rujukan pertama «سبل", False))

        # judul kitab di tempat judul (awal rujukan, sesudah «؛»/«انظر:»/titik dua lain) bukan gelar; nama sesudah «،»
        # atau «تحقيق:» tetap dinilai, juga awal baris #R bergaya muallif («**الشيخ …**»)
        judul_bergelar = (("#R", "سماحة الإسلام، عمر قريشي، 1400هـ."),
                          ("#R", "الشيخ محمد بن عبد الوهاب عقيدته السلفية، أحمد آل بوطامي، 1400هـ."),
                          ("fn", "وفي المثل: الشيخ في قومه كالنبي في أمته، ص5"),
                          ("fn", "انظر: معالي الهمم، فلان، ص5"))
        for tempat, teks in judul_bergelar:
            t = (dasar.rstrip("\n") + "\n" + teks + "\n" if tempat == "#R" else
                 dasar.replace("#K الخاتمة", f"وانظر[^{teks}. <<11223|-|5|توحيد الربوبية وهو إفراد الله تعالى بالخلق>>].\n#K الخاتمة"))
            uji(f"judul «{teks[:20]}» bukan gelar", lambda t=t: harus(t, "di depan nama", False))
        # «د.»/«الدكتور» tidak pernah awal judul: tetap dinilai di awal rujukan dan sesudah «انظر:»
        for teks in ("انظر: د. محمد بن صالح العثيمين، رسالة في القضاء والقدر، ص5", "د. محمد بن صالح العثيمين، رسالة في القضاء والقدر، ص5"):
            t = dasar.replace("#K الخاتمة", f"وانظر[^{teks}. <<11223|-|5|توحيد الربوبية وهو إفراد الله تعالى بالخلق>>].\n#K الخاتمة")
            uji(f"gelar «د.» di «{teks[:12]}» tetap ditandai", lambda t=t: harus(t, "gelar «د.» di depan nama", True))
        for teks in ("رسالة في القضاء والقدر، الشيخ محمد بن صالح العثيمين، دار الوطن، 1423هـ.",
                     "**الشيخ محمد بن صالح العثيمين**. __رسالة في القضاء والقدر__. دار الوطن، 1423هـ."):
            uji(f"gelar nama «{teks[:20]}» tetap ditandai",
                lambda teks=teks: harus(dasar.rstrip("\n") + "\n" + teks + "\n", "gelar «الشيخ» di depan nama", True))

        def kartu_berharakat():
            p = akar / "kitab" / "2348" / "book_metadata.json"
            asal = p.read_bytes()
            m = json.loads(asal)
            rng = random.Random(155)
            try:
                for _ in range(6):
                    gelar = "".join(c + rng.choice(("", "َ", "ِ", "ُ", "ّ")) for c in "الدكتور")
                    nama = "مَاهِر ياسين الفحل"
                    m["betaka_text"] = f"الكتاب: رياض الصالحين\nالمحقق: {gelar} {nama}\nالناشر: دار ابن كثير"
                    p.write_text(json.dumps(m, ensure_ascii=False), encoding="utf8")
                    r = subprocess.run([sys.executable, str(akar / "mesin" / "bahts.py"), "kartu", "2348"],
                                       cwd=akar, capture_output=True, encoding="utf8", timeout=60)
                    assert r.returncode == 0 and f"المحقق: {nama}\n" in r.stdout, r.stdout + r.stderr
                    assert "الكتاب: رياض الصالحين" in r.stdout, r.stdout
            finally:
                p.write_bytes(asal)
        uji("kartu membuang gelar berharakat tanpa merusak nama", kartu_berharakat)

        def pantau():
            tmp = akar / "mesin" / "_tmp"
            shutil.rmtree(tmp, ignore_errors=True)
            r = jalan("tahap")
            assert r.returncode == 0 and "RAKIT=BEBAS" in r.stdout, r.stdout + r.stderr
            assert not list(tmp.glob("rakit.*")), "tahap membuat berkas kunci"
            tmp.mkdir(exist_ok=True)
            kunci = tmp / "rakit.pekerjaan"
            data = b"\0metadata-pemegang-lama"
            kunci.write_bytes(data)
            r = jalan("tahap")
            assert r.returncode == 0 and "RAKIT=BEBAS" in r.stdout, r.stdout + r.stderr
            assert kunci.read_bytes() == data, "tahap mengubah metadata kunci"
        uji("tahap mengamati tanpa menulis kunci", pantau)

        def hasil_rusak():
            (f / "uji.pdf").write_bytes(b"%PDF")
            rng = random.Random(154155)
            for sidik in ("", "lama", "g" * 64, "0" * 63, "0" * 65,
                          *["".join(rng.choices("abcdef0123456789", k=rng.randrange(1, 63))) for _ in range(6)]):
                (f / "laporan.txt").write_text(f"NASKAH_SHA256={sidik}\n", encoding="utf8")
                r = jalan("tahap")
                assert "HASIL=TIDAK_DIKETAHUI" in r.stdout, r.stdout
            sidik = hashlib.sha256((f / "naskah.txt").read_bytes()).hexdigest()
            (f / "laporan.txt").write_text(f"NASKAH_SHA256={sidik}\n", encoding="utf8")
            assert "HASIL=TERKINI" in jalan("tahap").stdout
        uji("sidik laporan rusak tidak dianggap naskah berubah", hasil_rusak)

        def laporan_asing():
            jalan("tahap")
            sidik = hashlib.sha256((f / "naskah.txt").read_bytes()).hexdigest()
            (f / "laporan.txt").write_text(f"NASKAH_SHA256={sidik}\n", encoding="utf8")
            for fasl in ("catatan", "0", "2-1", "1.bak"):
                lp = f / f"laporan-fasl{fasl}.txt"
                lp.write_text("HALAMAN=1\n", encoding="utf8")
                r = jalan("tahap")
                lp.unlink()
                assert "HASIL=TERKINI" in r.stdout and "HASIL fasl" not in r.stdout, r.stdout
                assert '--fasl ' not in r.stdout, r.stdout
        uji("laporan asing tidak menjadi perintah fasl palsu", laporan_asing)

        def penanda_palsu():
            folder = f / ".rakit-penanda-palsu"
            (folder / "rakit.sementara").mkdir(parents=True)
            penting = folder / "penting.txt"
            penting.write_text("milik pemakai", encoding="utf8")
            try:
                r = jalan("tahap")
                assert "FOLDER_KERJA .rakit-penanda-palsu=ASING" in r.stdout, r.stdout + r.stderr
                if os.name == "nt":
                    r = jalan("rakit", "@fromat: salah\n" + dasar)
                    assert r.returncode != 0 and "Belum dirakit" in r.stderr, r.stdout + r.stderr
                    assert penting.is_file(), "penanda direktori memberi izin penghapusan"
            finally:
                shutil.rmtree(folder)
        uji("direktori bukan penanda sementara", penanda_palsu)

        if os.name == "nt":
            def junction():
                tujuan = akar / "milik-pemakai"
                tujuan.mkdir()
                (tujuan / "rakit.sementara").write_text("")
                penting = tujuan / "penting.txt"
                penting.write_text("milik pemakai", encoding="utf8")
                tautan = f / ".rakit-tautan"
                r = subprocess.run(["cmd", "/c", "mklink", "/J", str(tautan), str(tujuan)], capture_output=True)
                assert r.returncode == 0, r.stderr
                try:
                    r = jalan("rakit", "@fromat: salah\n" + dasar)
                    assert r.returncode != 0 and "Belum dirakit" in r.stderr, r.stdout + r.stderr
                    assert penting.is_file() and penting.read_text(encoding="utf8") == "milik pemakai", "isi tujuan tautan terhapus"
                    assert (tujuan / "rakit.sementara").is_file(), "penanda tujuan tautan terhapus"
                finally:
                    if tautan.exists():
                        tautan.rmdir()  # hanya junction TEMP ini, bukan isi tujuannya
            uji("rakit tidak menghapus isi junction .rakit", junction)

            def junction_di_dalam():
                tujuan = akar / "milik-pemakai-2"
                tujuan.mkdir()
                penting = tujuan / "penting.txt"
                penting.write_text("milik pemakai", encoding="utf8")
                folder = f / ".rakit-berjunction"
                folder.mkdir()
                (folder / "rakit.sementara").write_text("")
                r = subprocess.run(["cmd", "/c", "mklink", "/J", str(folder / "j"), str(tujuan)], capture_output=True)
                assert r.returncode == 0, r.stderr
                r = jalan("rakit", "@fromat: salah\n" + dasar)
                assert r.returncode != 0 and "Belum dirakit" in r.stderr, r.stdout + r.stderr
                assert penting.read_text(encoding="utf8") == "milik pemakai", "isi tujuan junction terhapus"
                assert not folder.exists(), "folder sementara berisi junction tidak pernah dibuang: " + r.stderr[-300:]
            uji("junction di dalam folder sementara: tautannya saja yang dibuang", junction_di_dalam)

            def folder_terkunci():
                folder = f / ".rakit-terkunci"
                folder.mkdir()
                penanda = folder / "rakit.sementara"
                penanda.write_text("")
                api = ctypes.WinDLL("kernel32", use_last_error=True)
                api.CreateFileW.restype = ctypes.c_void_p
                api.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p,
                                            ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p]
                api.CloseHandle.argtypes = [ctypes.c_void_p]
                h = api.CreateFileW(str(folder), 0x80000000, 3, None, 3, 0x02000000, None)
                assert h != ctypes.c_void_p(-1).value, ctypes.get_last_error()
                try:
                    r = jalan("rakit", "@fromat: salah\n" + dasar)
                    assert r.returncode != 0 and "Belum dirakit" in r.stderr, r.stdout + r.stderr
                    assert penanda.is_file(), "folder terkunci kehilangan penanda"
                finally:
                    api.CloseHandle(h)
                r = jalan("rakit", "@fromat: salah\n" + dasar)
                assert not folder.exists(), r.stdout + r.stderr
            uji("folder terkunci tetap sementara lalu dibuang putaran berikutnya", folder_terkunci)
        else:
            print("lewati junction dan handle direktori: khusus Windows")
    print(f"uji audit: {len(lolos)} lolos, {len(gagal)} gagal")
    return bool(gagal)


if __name__ == "__main__":
    sys.exit(utama())
