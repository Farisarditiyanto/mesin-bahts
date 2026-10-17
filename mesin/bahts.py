"""Satu pintu mesin bahts:  python mesin/bahts.py <perintah>

Sekali sesudah mengunduh repo:
  periksa                      apa yang sudah siap di komputer ini, dan perintah untuk tiap yang belum
  siapkan                      unduh katalog kitab + font mushaf, lalu pasang font itu (Windows)

Bahts (tiap bahts = satu folder berisi naskah.txt):
  baru <folder> "<judul>"      buat folder bahts baru + kerangka naskah.txt
  cek <folder>                 periksa naskah: tanda, ayat, dan semua bukti <<...>> ke kitab lokal
  rakit <folder>               cek, lalu rakit .docx + .pdf (Word) ke dalam folder itu
  tanda                        daftar tanda yang dipakai di naskah.txt

Kitab (perpustakaan Shamela lokal, dipakai semua bahts):
  kitab                        daftar kitab yang sudah diunduh
  katalog "<pola>"             cari judul/pengarang di katalog Shamela (regex)
  temukan "<frasa>" [maks]     cari frasa di isi SEMUA kitab Shamela (turath.io, butuh internet) -> kitab + juz/halaman; paling banyak 20
  ambil <id> [<id> ...]        unduh kitab (sekali saja)
  kartu <id>                   data cetak kitab (untuk rujukan pertama & daftar pustaka)
  cari <id|semua> "<frasa>"    cari frasa -> juz/halaman cetak
  teks <id> "<frasa>" [lebar] [maks]   teks asli di sekitar frasa, untuk disalin persis
  bab <id> "<frasa>"           rantai judul kitab/bab tempat frasa berada
  halaman <id> <juz> <hal>     isi satu halaman (juz "-" untuk kitab satu jilid)
  scan <id> <juz> <hal>        alamat scan cetakan halaman itu (PDF di turath.io, butuh internet), untuk bacaan yang meragukan

Takhrij (penunjuk jalan, «المنصة الحديثية», butuh internet):
  hadits "<طرف>" [maks]        tempat hadits di 12 kitab hadits + hukum ulama; tetap dibaca di kitabnya sendiri

Penelitian terdahulu (الدراسات السابقة, katalog OpenAlex dan DOAJ, butuh internet):
  dirasat "<kata kunci>" [maks] [saringan]   judul, peneliti, tahun, jurnal, tautan, dan ringkasan; dicari menurut kata
                               dan menurut makna. Saringan OpenAlex, mis. language:ar,type:dissertation
  dirasat-pdf <W…> <folder>    unduh PDF penelitian (nomor OpenAlex dari `dirasat`) ke folder bahts; butuh kunci OpenAlex
"""
import difflib, hashlib, json, math, os, re, shutil, subprocess, sys, urllib.error
from pathlib import Path

import dirasat, hadits, shamela  # ringan; olah (memuat teks Al-Qur'an) baru dimuat saat `cek`
from shamela import perintah

MESIN = Path(__file__).parent
AKAR = MESIN.parent
# Font mushaf «KFGQPC HAFS Uthmanic Script» milik مجمع الملك فهد: tidak ikut repo (lihat NOTICE), diunduh oleh `siapkan`.
FONT = "UthmanicHafs_V22.ttf"
FONT_SUMBER = ("https://static-cdn.tarteel.ai/qul/fonts/" + FONT,  # dicoba berurutan
               "https://github.com/Farisarditiyanto/mesin-bahts/releases/download/v0.0.1/" + FONT)
FONT_SHA256 = "aa68bffce289b4c0ebac68e90502eb69e42356abcd1603cb2b8e99c2c723f145"
FONT_NAMA = "KFGQPC HAFS Uthmanic Script (TrueType)"
FONT_PEMAKAI = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"))
SAMPUL_SAYA = AKAR / "sampul_saya.txt"  # data sampul pemakai (@kunci: nilai); mengisi @kunci yang kosong di naskah baru
NAMA_FOLDER = r"[A-Za-z0-9_-]+"  # nama folder bahts yang diterima `baru`
FORMAT = json.load(open(MESIN / "format.json", encoding="utf8"))  # profil bentuk halaman; dipilih @format di naskah
HURUF_SARAN = ("huruf ini ikut terpasang kalau Windows punya papan ketik Arab (Settings > Time & language > Language & region > Add a language > العربية).\n"
               "          Atau lewat PowerShell admin (pemakai cukup klik Yes): Start-Process powershell -Verb RunAs -Wait -ArgumentList "
               "\"Add-WindowsCapability -Online -Name Language.Fonts.Arab~~~und-ARAB~0.0.1.0\"")
# perkiraan halaman isi tanpa Word: kata per halaman pada huruf matan 18 (ditera dari satu bahts nyata: ±5500 kata setara matan = 24 halaman isi)
KATA_PER_HALAMAN_18 = 260
PUSTAKA = ("pandas", "pyarrow", "pypdf", "fontTools")  # nama modul; nama pemasangannya di requirements.txt


def huruf_ada(nama):
    """Huruf `nama` terpasang di Windows, untuk semua akun atau untuk akun ini saja (daftar huruf di registry)."""
    import winreg
    for akar in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(akar, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts") as k:
                for i in range(winreg.QueryInfoKey(k)[1]):
                    # nama terdaftar mis. «Traditional Arabic (TrueType)» atau «Cambria & Cambria Math (TrueType)»
                    if nama.lower() in (x.strip().lower() for x in re.sub(r"\s*\(.*\)$", "", winreg.EnumValue(k, i)[0]).split("&")):
                        return True
        except OSError:
            pass
    return False


def font_terpasang():
    return any((d / FONT).exists() for d in (FONT_PEMAKAI, Path(r"C:\Windows\Fonts")))


def siapkan():
    """Lengkapi yang tidak ikut repo: katalog kitab dan font mushaf. Aman diulang."""
    shamela.siapkan()
    f = MESIN / FONT
    if not f.exists():
        for url in FONT_SUMBER:
            try:
                with shamela.buka(url, waktu=120) as r:
                    isi = r.read()
            except shamela.GAGAL_JARINGAN as e:
                print(f"font mushaf: gagal dari {url} ({e!r})")
                continue
            if hashlib.sha256(isi).hexdigest() == FONT_SHA256:
                f.write_bytes(isi)
                break
            print(f"font mushaf: berkas dari {url} berbeda dari yang dikenal mesin, dilewati")
        else:
            sys.exit(f"Font mushaf gagal diunduh dari semua sumber.\n"
                     f"Jalan terakhir: cari sendiri {FONT} (penerbitnya: https://fonts.qurancomplex.gov.sa), taruh di {MESIN}, lalu ulangi `siapkan`.")
    if hashlib.sha256(f.read_bytes()).hexdigest() != FONT_SHA256:
        sys.exit(f"mesin/{FONT} berbeda dari font yang dikenal mesin (sha256 {FONT_SHA256}): pindahkan berkas itu, lalu ulangi `siapkan`.")
    print("font mushaf: ada di mesin/")
    if os.name != "nt":
        print("font mushaf: TIDAK dipasang (bukan Windows). `cek` tetap jalan; `rakit` butuh Windows + Microsoft Word.")
    elif font_terpasang():
        print("font mushaf: sudah terpasang")
    else:
        # sama dengan klik kanan > Install: salin ke folder font pemakai + daftarkan, tanpa hak admin
        import ctypes, winreg
        FONT_PEMAKAI.mkdir(parents=True, exist_ok=True)
        (FONT_PEMAKAI / FONT).write_bytes(f.read_bytes())
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts") as k:
            winreg.SetValueEx(k, FONT_NAMA, 0, winreg.REG_SZ, str(FONT_PEMAKAI / FONT))
        ctypes.windll.gdi32.AddFontResourceW(str(FONT_PEMAKAI / FONT))
        print("font mushaf: dipasang")
    print("Siap. Bahts baru: " + perintah('baru <folder> "<judul>"'))


def periksa():
    """Apa yang sudah siap di komputer ini, dan perintah untuk tiap yang belum. Tidak mengubah apa pun."""
    import importlib.util
    siap_cek, siap_rakit = True, True

    def baris(ok, apa, kalau_belum, untuk_cek=True, untuk_rakit=True):
        nonlocal siap_cek, siap_rakit
        print(("SIAP   " if ok else "BELUM  ") + apa + ("" if ok else f"\n       -> {kalau_belum}"))
        siap_rakit &= ok or not untuk_rakit
        siap_cek &= ok or not untuk_cek

    baris(sys.version_info >= (3, 12), f"Python {sys.version_info.major}.{sys.version_info.minor} (butuh 3.12 ke atas)",
          "pasang Python 3.12 (Windows: winget install Python.Python.3.12), lalu ulangi dengan Python itu")
    baris(all(importlib.util.find_spec(m) for m in PUSTAKA), f"pustaka Python ({', '.join(PUSTAKA)})",
          f'"{sys.executable}" -m pip install -r "{AKAR / "requirements.txt"}"')
    baris((AKAR / "kitab" / shamela.KATALOG).exists(), "katalog kitab", perintah("siapkan"))
    baris(os.name == "nt", "Windows", "`rakit` hanya jalan di Windows; di sini mesin berhenti di `cek`", untuk_cek=False)
    if os.name == "nt":
        import winreg
        try:
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"))
            word = True
        except OSError:
            word = False
        baris(word, "Microsoft Word versi desktop", "pasang Microsoft Word (pemakai sendiri; butuh lisensinya). "
              "Tanpa Word naskah tetap bisa ditulis dan dicek, tetapi .docx dan .pdf tidak terbentuk", untuk_cek=False)
        baris(font_terpasang(), "font mushaf", perintah("siapkan"), untuk_cek=False)
        # huruf tiap profil format.json; yang wajib hanya huruf profil bahts baru (@format di kerangka naskah)
        m = re.search(r"^@format:[ \t]*(\S+)", (MESIN / "naskah_baru.txt").read_text(encoding="utf8"), re.M)
        wajib = FORMAT[m.group(1) if m else "imam"]["huruf"]
        for h in dict.fromkeys(p["huruf"] for p in FORMAT.values()):
            profil = [k for k, p in FORMAT.items() if p["huruf"] == h]
            baris(huruf_ada(h), f"huruf {h}" + ("" if h == wajib else f" (hanya untuk @format {', '.join(profil)})"),
                  HURUF_SARAN, untuk_cek=False, untuk_rakit=h == wajib)
    print(f"\nMenulis dan `cek`: {'SIAP' if siap_cek else 'BELUM'}.  `rakit` (Word + PDF): {'SIAP' if siap_rakit else 'BELUM'}.")
    print("WSL tidak diperlukan. Connector shamela: pilihan, sangat disarankan (lihat README).")
    sys.exit(0 if siap_cek else 1)


def folder_bahts(nama):
    f = (AKAR / nama).resolve()  # jalur lengkap («C:\\…\\mesin-bahts\\ikhlas») juga diterima
    if f.name.lower() == "naskah.txt":  # yang disebut berkas naskahnya, bukan foldernya
        f = f.parent
    if not f.is_relative_to(AKAR.resolve()):
        sys.exit(f"Bahts «{nama}» di luar folder mesin ({AKAR}): tiap bahts tinggal di dalam folder itu.")
    if (f / "naskah.txt").exists():
        return f
    ada = sorted(d.name for d in AKAR.iterdir() if (d / "naskah.txt").exists())
    mirip = difflib.get_close_matches(f.name, ada, n=1, cutoff=0.6)
    pesan = [f"Tidak ada bahts «{f.name}» (folder berisi naskah.txt) di {AKAR}."]
    if mirip:
        pesan.append(f"Maksudnya «{mirip[0]}»?")
    pesan.append("Bahts yang ada: " + (", ".join(ada) if ada else "belum ada"))
    usul = re.sub(r"[^A-Za-z0-9_-]", "", f.name) or "<nama-latin>"
    if not (AKAR / usul).exists():  # folder yang sudah ada (mis. tanpa naskah.txt) tidak bisa dibuat `baru`
        pesan.append("Kalau memang bahts baru: " + perintah(f'baru {usul} "<judul>"'))
    sys.exit("\n".join(pesan))


def baru(nama, judul):
    nama = nama.removeprefix("./").removeprefix(".\\")
    if not re.fullmatch(NAMA_FOLDER, nama.strip("/\\")):
        sys.exit(f"Nama folder «{nama}»: pakai huruf Latin, angka, - atau _ saja, tanpa spasi (mis. ikhlas).")
    if not judul.strip():
        sys.exit('Judul bahts masih kosong: ' + perintah(f'baru {nama.strip("/.")} "<judul>"'))
    f = AKAR / nama.strip("/\\")
    kembar = [d.name for d in AKAR.iterdir() if d.name.lower() == f.name.lower()]
    if kembar:  # di Windows «Ikhlas» dan «ikhlas» satu folder
        sys.exit(f"Folder {kembar[0]} sudah ada.")
    isi = (MESIN / "naskah_baru.txt").read_text(encoding="utf8").replace("{judul}", judul).replace("{folder}", f.name)
    if SAMPUL_SAYA.exists():
        try:
            saya = SAMPUL_SAYA.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            sys.exit(f"{SAMPUL_SAYA.name} harus disimpan sebagai UTF-8. Simpan ulang, lalu ulangi.")
        for k, v in re.findall(r"^@(\w+):[ \t]*(\S.*)$", saya, re.M):
            if re.search(rf"^@{k}:", isi, re.M):
                isi = re.sub(rf"^@{k}:[ \t]*$", lambda m: f"@{k}: {v.strip()}", isi, flags=re.M)
            else:  # kunci yang tidak ada di kerangka (mis. @thalibah) ikut ditulis
                isi = isi.replace("@berkas:", f"@{k}: {v.strip()}\n@berkas:", 1)
    f.mkdir()
    (f / "naskah.txt").write_text(isi, encoding="utf8")
    print(f"Siap: {f.name}/naskah.txt")
    kosong = re.findall(r"^@(\w+):[ \t]*$", isi, re.M)
    if kosong:
        print("Data sampul yang masih kosong: " + ", ".join("@" + k for k in kosong)
              + f"\nIsi di naskah itu. Yang sama untuk tiap bahts (nama, nim, jenis, fasl) boleh ditulis sekali di {SAMPUL_SAYA.name}."
              + ("\nContoh @jenis (huruf Arab, tercetak di sampul): بحث صفي للمستوى الرابع" if "jenis" in kosong else ""))


def bahan(f):
    """Bahan rakit yang ditulis olah.utama saat `cek` (meta, format, blok, catatan, ...)."""
    return MESIN / "_tmp" / f"{f.name}.json"


def perkiraan_halaman(d):
    """Perkiraan kasar halaman isi (المقدمة s.d. الخاتمة) dari jumlah kata, untuk yang belum bisa `rakit`.
    Tiap #K/#F mulai halaman baru; kata catatan kaki dihitung menurut perbandingan luas hurufnya."""
    fmt = d.get("format")
    if not fmt:
        return None
    per_hal = KATA_PER_HALAMAN_18 * (18 / fmt["matan"]) ** 2
    def kata(runs): return sum(len(re.findall(r"[؀-ۿ]+", r.get("t") or "")) for r in runs)
    bagian = []
    for b in d["blok"]:
        if b["k"] == "R":
            break
        if b["k"] in ("K", "F") or not bagian:
            bagian.append(0.0)
        fn = sum(kata(d["catatan"][r["fn"]]["runs"]) for r in b["runs"] if r.get("fn") is not None)
        bagian[-1] += kata(b["runs"]) + fn * (fmt["catatan"] / fmt["matan"]) ** 2
    return sum(max(1, math.ceil(x / per_hal)) for x in bagian)


def cek(nama):
    import olah
    f = folder_bahts(nama)
    galat, lap = olah.utama(f)
    print("\n".join(lap))
    try:
        n = perkiraan_halaman(json.load(open(bahan(f), encoding="utf8")))
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        n = None
    if n:
        print(f"perkiraan halaman isi (المقدمة s.d. الخاتمة): ±{n} (kasar, dari jumlah kata; angka pasti = HALAMAN_ISI sesudah `rakit`)")
    return f, galat, lap


def rakit(nama):
    f, galat, lap = cek(nama)
    if galat:
        sys.exit(f"Belum dirakit: {galat} galat di atas harus beres dulu.")
    if os.name != "nt":
        sys.exit("`rakit` butuh Windows + Microsoft Word. Naskahnya sudah lolos `cek`.")
    if not font_terpasang():
        sys.exit(f"Font mushaf belum terpasang: {perintah('siapkan')}, lalu ulangi.")
    build = bahan(f)
    huruf = json.load(open(build, encoding="utf8"))["format"]["huruf"]
    if not huruf_ada(huruf):  # tanpa huruf profil, Word diam-diam memakai huruf lain
        sys.exit(f"Huruf {huruf} (dipakai @format naskah ini) belum terpasang di Windows.\n       -> {HURUF_SARAN}\n"
                 f"Sesudah itu: {perintah('periksa')}, lalu ulangi `rakit`.")
    ps1 = MESIN / "rakit.ps1"
    # Windows PowerShell 5.1 hanya membaca huruf Arab di skrip kalau berkasnya ber-BOM
    if not ps1.read_bytes().startswith(b"\xef\xbb\xbf"):
        ps1.write_bytes(b"\xef\xbb\xbf" + ps1.read_bytes())
    (f / "laporan.txt").write_text("\n".join(lap) + "\n", encoding="utf8")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1),
                        "-Build", str(build), "-Folder", str(f)])
    if r.returncode:
        sys.exit("Perakitan Word GAGAL (lihat pesan di atas). Kalau .docx/.pdf-nya sedang terbuka, tutup dulu.")
    berkas = json.load(open(build, encoding="utf8"))["meta"]["berkas"]
    import teks_pdf
    try:  # supaya teks Arab PDF tersalin dan tercari dengan benar; tampilannya tidak berubah
        teks_pdf.betulkan(f / f"{berkas}.pdf")
    except Exception as e:
        print(f"PERINGATAN: PDF jadi, tetapi teks Arabnya belum dibetulkan (salin/cari bisa terbalik): {type(e).__name__}: {e}")
    for baris in (f / "laporan.txt").read_text(encoding="utf8").splitlines():
        if baris.startswith(("HALAMAN", "CATATAN_KAKI", "KATA")):
            print(baris)
    print(f"Jadi: {f / berkas}.docx dan .pdf")


def angka(teks, apa):
    """Argumen angka (maks, lebar): ditolak dengan pesan yang bisa dipahami kalau bukan bilangan bulat 1 ke atas."""
    try:
        n = int(teks)
    except ValueError:
        raise ValueError(f"{apa} harus angka, mis. 10 (yang tertulis: «{teks}»)") from None
    if n < 1:
        raise ValueError(f"{apa} paling kecil 1 (yang tertulis: {n})")
    return n


def pola(teks):
    """Pola `katalog` (regex). Yang bukan regex sah, mis. judul berkurung «(», dicari sebagai teks biasa."""
    try:
        re.compile(teks)
        return teks
    except re.error:
        return re.escape(teks)


def ambil(nomor):
    """Unduh tiap kitab; satu yang gagal tidak membatalkan yang lain. Keluar dengan kode 1 kalau ada yang belum terunduh."""
    gagal = shamela.ambil(*nomor)
    if gagal:
        sys.exit(f"Belum terunduh: {', '.join(gagal)} (lihat pesan di atas).")


def ketemu(n):
    """Pencarian yang kosong keluar dengan kode 1, supaya skrip/agent tahu tanpa membaca pesannya."""
    if not n:
        sys.exit(1)


PERINTAH = {  # nama: (jumlah argumen minimal, pemanggil)
    "periksa": (0, lambda a: periksa()),
    "siapkan": (0, lambda a: siapkan()),
    "baru": (2, lambda a: baru(a[0], a[1])),
    "cek": (1, lambda a: sys.exit(1 if cek(a[0])[1] else 0)),
    "rakit": (1, lambda a: rakit(a[0])),
    "tanda": (0, lambda a: print(tanda())),
    "kitab": (0, lambda a: shamela.daftar()),
    "katalog": (1, lambda a: ketemu(shamela.katalog(pola(a[0])))),
    "temukan": (1, lambda a: shamela.temukan(a[0], *(angka(x, "maks") for x in a[1:2]))),
    "ambil": (1, lambda a: ambil(a)),
    "kartu": (1, lambda a: shamela.kartu(a[0])),
    "cari": (2, lambda a: ketemu(shamela.cari(a[0], a[1]))),
    "teks": (2, lambda a: ketemu(shamela.teks(a[0], a[1], *(angka(x, apa) for x, apa in zip(a[2:4], ("lebar", "maks")))))),
    "bab": (2, lambda a: ketemu(shamela.bab(a[0], a[1]))),
    "halaman": (3, lambda a: ketemu(shamela.halaman(*a[:3]))),
    "scan": (3, lambda a: ketemu(shamela.scan(*a[:3]))),
    "hadits": (1, lambda a: hadits.cari(a[0], *(angka(x, "maks") for x in a[1:2]))),
    "dirasat": (1, lambda a: dirasat.cari(a[0], *(angka(x, "maks") for x in a[1:2]), *a[2:3])),
    "dirasat-pdf": (2, lambda a: dirasat.pdf(a[0], folder_bahts(a[1]))),
}


def tanda():
    """Daftar tanda naskah: ditulis sekali di kepala olah.py (tempat tanda itu diurai), dicetak dari sana."""
    import olah
    return olah.__doc__[olah.__doc__.index("Tanda di naskah"):].rstrip()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd, *a = sys.argv[1:] or [""]
    if cmd in ("", "-h", "--help", "bantuan"):
        print(__doc__); sys.exit(0)
    if cmd not in PERINTAH:
        mirip = difflib.get_close_matches(cmd, PERINTAH, n=1)
        sys.exit(f"Perintah «{cmd}» tidak dikenal." + (f" Maksudnya «{mirip[0]}»?" if mirip else "")
                 + "\nDaftar perintah: " + perintah(""))
    # cukup baris bantuan perintah itu, berikut baris lanjutannya yang menjorok
    bantu = re.search(rf"^  {re.escape(cmd)}\s.*(?:\n {{20,}}\S.*)*", __doc__, re.M)
    bentuk = bantu.group(0) if bantu else cmd
    if len(a) < PERINTAH[cmd][0]:
        sys.exit(f"Perintah «{cmd}» kurang argumen. Bentuknya:\n{bentuk}")
    try:
        PERINTAH[cmd][1](a)
    except urllib.error.HTTPError as e:
        if not 400 <= e.code < 500 or e.code == 429:
            sys.exit(f"Perintah '{cmd}': layanannya sedang menolak atau sibuk (HTTP {e.code}). Ulangi sebentar lagi.")
        sys.exit(f"Perintah '{cmd}': layanannya menolak permintaan ini (HTTP {e.code}). Periksa kata/angka yang diketik: {a}")
    except BrokenPipeError:  # keluarannya dipotong pembaca (mis. `| head`): bukan masalah internet
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    except shamela.GAGAL_JARINGAN as e:
        sys.exit(f"Perintah '{cmd}' gagal mengunduh (cek internet, lalu ulangi): {e!r}")
    except (ValueError, FileNotFoundError, re.error) as e:
        sys.exit(f"Perintah '{cmd}' salah pakai: {e}\nBentuknya:\n{bentuk}")
