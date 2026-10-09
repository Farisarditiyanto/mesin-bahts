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
  ambil <id> [<id> ...]        unduh kitab (sekali saja)
  kartu <id>                   data cetak kitab (untuk rujukan pertama & daftar pustaka)
  cari <id|semua> "<frasa>"    cari frasa -> juz/halaman cetak
  teks <id> "<frasa>" [lebar] [maks]   teks asli di sekitar frasa, untuk disalin persis
  bab <id> "<frasa>"           rantai judul kitab/bab tempat frasa berada
  halaman <id> <juz> <hal>     isi satu halaman (juz "-" untuk kitab satu jilid)

Penelitian terdahulu (الدراسات السابقة, katalog OpenAlex, butuh internet):
  dirasat "<kata kunci>" [maks]   judul, peneliti, tahun, jurnal, tautan, dan ringkasan
"""
import hashlib, http.client, json, os, re, subprocess, sys, urllib.error, urllib.request
from pathlib import Path

MESIN = Path(__file__).parent
AKAR = MESIN.parent
# Font mushaf «KFGQPC HAFS Uthmanic Script» milik مجمع الملك فهد: tidak ikut repo (lihat NOTICE), diunduh oleh `siapkan`.
FONT = "UthmanicHafs_V22.ttf"
FONT_SUMBER = ("https://static-cdn.tarteel.ai/qul/fonts/" + FONT,  # dicoba berurutan
               "https://github.com/Farisarditiyanto/mesin-bahts/releases/download/v0.0.1/" + FONT)
FONT_SHA256 = "aa68bffce289b4c0ebac68e90502eb69e42356abcd1603cb2b8e99c2c723f145"
FONT_NAMA = "KFGQPC HAFS Uthmanic Script (TrueType)"
FONT_PEMAKAI = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"))
# unduhan gagal: alamat mati, ditolak, putus di tengah, atau kehabisan waktu
GAGAL_UNDUH = (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError)
SAMPUL_SAYA = AKAR / "sampul_saya.txt"  # data sampul pemakai (@kunci: nilai); mengisi @kunci yang kosong di naskah baru


def font_terpasang():
    return any((d / FONT).exists() for d in (FONT_PEMAKAI, Path(r"C:\Windows\Fonts")))


def siapkan():
    """Lengkapi yang tidak ikut repo: katalog kitab dan font mushaf. Aman diulang."""
    shamela().siapkan()
    f = MESIN / FONT
    if not f.exists():
        for url in FONT_SUMBER:
            try:
                isi = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"}), timeout=120).read()
            except GAGAL_UNDUH as e:
                print(f"font mushaf: gagal dari {url} ({e!r})")
                continue
            if hashlib.sha256(isi).hexdigest() == FONT_SHA256:
                f.write_bytes(isi)
                break
            print(f"font mushaf: berkas dari {url} berbeda dari yang dikenal mesin, dilewati")
        else:
            sys.exit(f"Font mushaf gagal diunduh dari semua sumber.\n"
                     f"Jalan terakhir: cari sendiri {FONT} (penerbitnya: https://fonts.qurancomplex.gov.sa), taruh di mesin/, lalu ulangi `siapkan`.")
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
    print('Siap. Bahts baru: python mesin/bahts.py baru <folder> "<judul>"')


def periksa():
    """Apa yang sudah siap di komputer ini, dan perintah untuk tiap yang belum. Tidak mengubah apa pun."""
    import importlib.util
    siap_cek, siap_rakit = True, True

    def baris(ok, apa, kalau_belum, untuk_cek=True):
        nonlocal siap_cek, siap_rakit
        print(("SIAP   " if ok else "BELUM  ") + apa + ("" if ok else f"\n       -> {kalau_belum}"))
        siap_rakit &= ok
        siap_cek &= ok or not untuk_cek

    baris(sys.version_info >= (3, 12), f"Python {sys.version_info.major}.{sys.version_info.minor} (butuh 3.12 ke atas)",
          "pasang Python 3.12 (Windows: winget install Python.Python.3.12), lalu ulangi dengan Python itu")
    baris(all(importlib.util.find_spec(m) for m in ("pandas", "pyarrow")), "pustaka Python (pandas, pyarrow)",
          "pip install -r requirements.txt")
    baris((AKAR / "kitab" / shamela().KATALOG).exists(), "katalog kitab", "python mesin/bahts.py siapkan")
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
        baris(font_terpasang(), "font mushaf", "python mesin/bahts.py siapkan", untuk_cek=False)
        baris(any((Path(r"C:\Windows\Fonts") / n).exists() for n in ("trado.ttf", "tradbdo.ttf")), "huruf Traditional Arabic",
              "Settings > System > Optional features > tambah «Arabic Script Supplemental Fonts»", untuk_cek=False)
    print(f"\nMenulis dan `cek`: {'SIAP' if siap_cek else 'BELUM'}.  `rakit` (Word + PDF): {'SIAP' if siap_rakit else 'BELUM'}.")
    print("WSL tidak diperlukan. Connector shamela: pilihan, sangat disarankan (lihat README).")
    sys.exit(0 if siap_cek else 1)


def folder_bahts(nama):
    f = AKAR / nama.strip("/\\")
    if not (f / "naskah.txt").exists():
        sys.exit(f"Tidak ada {f.name}/naskah.txt. Bahts baru: python mesin/bahts.py baru {f.name} \"<judul>\"")
    return f


def baru(nama, judul):
    f = AKAR / nama.strip("/\\")
    if f.exists():
        sys.exit(f"Folder {f.name} sudah ada.")
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
              + f"\nIsi di naskah itu, atau sekali saja di {SAMPUL_SAYA.name} (dipakai tiap `baru`).")


def cek(nama):
    import olah
    f = folder_bahts(nama)
    galat, lap = olah.utama(f)
    print("\n".join(lap))
    return f, galat, lap


def rakit(nama):
    f, galat, lap = cek(nama)
    if galat:
        sys.exit(f"Belum dirakit: {galat} galat di atas harus beres dulu.")
    if os.name != "nt":
        sys.exit("`rakit` butuh Windows + Microsoft Word. Naskahnya sudah lolos `cek`.")
    if not font_terpasang():
        sys.exit("Font mushaf belum terpasang: python mesin/bahts.py siapkan, lalu ulangi.")
    ps1 = MESIN / "rakit.ps1"
    # Windows PowerShell 5.1 hanya membaca huruf Arab di skrip kalau berkasnya ber-BOM
    if not ps1.read_bytes().startswith(b"\xef\xbb\xbf"):
        ps1.write_bytes(b"\xef\xbb\xbf" + ps1.read_bytes())
    (f / "laporan.txt").write_text("\n".join(lap) + "\n", encoding="utf8")
    build = MESIN / "_tmp" / f"{f.name}.json"
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1),
                        "-Build", str(build), "-Folder", str(f)])
    if r.returncode:
        sys.exit("Perakitan Word GAGAL (lihat pesan di atas). Kalau .docx/.pdf-nya sedang terbuka, tutup dulu.")
    berkas = json.load(open(build, encoding="utf8"))["meta"]["berkas"]
    for baris in (f / "laporan.txt").read_text(encoding="utf8").splitlines():
        if baris.startswith(("HALAMAN", "CATATAN_KAKI", "KATA")):
            print(baris)
    print(f"Jadi: {f.name}/{berkas}.docx dan .pdf")


PERINTAH = {  # nama: (jumlah argumen minimal, pemanggil)
    "periksa": (0, lambda a: periksa()),
    "siapkan": (0, lambda a: siapkan()),
    "baru": (2, lambda a: baru(a[0], a[1])),
    "cek": (1, lambda a: sys.exit(1 if cek(a[0])[1] else 0)),
    "rakit": (1, lambda a: rakit(a[0])),
    "tanda": (0, lambda a: print(tanda())),
    "kitab": (0, lambda a: shamela().daftar()),
    "katalog": (1, lambda a: shamela().katalog(a[0])),
    "ambil": (1, lambda a: [shamela().ambil(x) for x in a]),
    "kartu": (1, lambda a: shamela().kartu(a[0])),
    "cari": (2, lambda a: shamela().cari(a[0], a[1])),
    "teks": (2, lambda a: shamela().teks(a[0], a[1], *map(int, a[2:4]))),
    "bab": (2, lambda a: shamela().bab(a[0], a[1])),
    "halaman": (3, lambda a: shamela().halaman(*a[:3])),
    "dirasat": (1, lambda a: dirasat().cari(a[0], *map(int, a[1:2]))),
}


def tanda():
    """Daftar tanda naskah: ditulis sekali di kepala olah.py (tempat tanda itu diurai), dicetak dari sana."""
    import olah
    return olah.__doc__[olah.__doc__.index("Tanda di naskah"):].rstrip()


def shamela():
    import shamela
    return shamela


def dirasat():
    import dirasat
    return dirasat


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd, *a = sys.argv[1:] or [""]
    if not cmd:
        print(__doc__); sys.exit(0)
    if cmd not in PERINTAH or len(a) < PERINTAH[cmd][0]:
        sys.exit(__doc__)
    try:
        PERINTAH[cmd][1](a)
    except GAGAL_UNDUH as e:
        sys.exit(f"Perintah '{cmd}' gagal mengunduh (cek internet, lalu ulangi): {e!r}")
    except (ValueError, FileNotFoundError, re.error) as e:
        sys.exit(f"Perintah '{cmd}' salah pakai: {e}\nLihat: python mesin/bahts.py")
