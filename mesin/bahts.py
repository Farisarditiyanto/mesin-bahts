# SPDX-License-Identifier: AGPL-3.0-or-later
"""Satu pintu mesin bahts:  python mesin/bahts.py <perintah>

Sekali sesudah mengunduh repo:
  periksa                      apa yang sudah siap di komputer ini, dan perintah untuk tiap yang belum
  siapkan                      unduh katalog kitab + font mushaf, lalu pasang font itu (Windows)

Bahts (tiap bahts = satu folder berisi naskah.txt):
  baru <folder> "<judul>"      buat folder bahts baru + kerangka naskah.txt; <folder> boleh bahts/<orang>/<topik>
  cek <folder> [--jejak]       periksa naskah: tanda, ayat, dan semua bukti <<...>> ke kitab lokal;
                               --jejak: teks yang tidak ada di kitabnya dicari di kitab lain yang sudah diunduh
  bukti <folder> [baris|awal-akhir]   untuk pemeriksa: tiap catatan kaki berbukti <<sid|juz|hal>> (kalimat yang
                               dibuktikan, isi catatan kaki, nama kitab, bab, dan teks halaman itu di sekitar kutipan)
                               dan teks tiap ayat {Q:} persis seperti tercetak; tiap baris keluaran diawali «baris n».
                               Penunjuk saja, putusan tetap `cek`
  rakit <folder>               cek, lalu rakit .docx + .pdf (Word) ke dalam folder itu
  tanda                        daftar tanda yang dipakai di naskah.txt

Kitab (perpustakaan Shamela lokal, dipakai semua bahts):
  kitab                        daftar kitab yang sudah diunduh
  katalog "<pola>"             cari judul/pengarang di katalog Shamela (regex)
  temukan "<frasa>" [maks] [--mazhab m,…] [--kitab id,…] [--halaman n]
                               cari frasa di isi SEMUA kitab Shamela (turath.io, butuh internet) -> kitab + juz/halaman; 20 hasil
                               tiap halaman. --mazhab: hanya kitab fikih mazhab itu; --kitab: hanya kitab itu, walau belum
                               diunduh; --halaman 2: hasil ke-21 dan seterusnya
  ambil <id|folder> [...]      unduh kitab (sekali saja); nama folder bahts = semua kitab yang dirujuk naskahnya
  kartu <id>                   data cetak kitab (untuk rujukan pertama & daftar pustaka)
  cari <id|semua> "<frasa>"    cari frasa -> juz/halaman cetak; semua: paling banyak 40 baris, lalu jumlah kitab yang cocok
  teks <id> "<frasa>" [lebar] [maks]   teks asli di sekitar frasa, untuk disalin persis
  bab <id> "<frasa>"           rantai judul kitab/bab tempat frasa berada
  halaman <id> <juz> <hal>     isi satu halaman (juz "-" untuk kitab satu jilid); <hal> boleh rentang, mis. 10-14
                               (paling banyak 20 halaman sekali panggil)
  scan <id> <juz> <hal>        alamat scan cetakan halaman itu (PDF di turath.io, butuh internet), untuk bacaan yang meragukan

Takhrij (penunjuk jalan, «المنصة الحديثية», butuh internet):
  hadits "<طرف>" [maks]        tempat hadits di 12 kitab hadits + hukum ulama; tetap dibaca di kitabnya sendiri

Penelitian terdahulu (الدراسات السابقة, katalog OpenAlex dan DOAJ, butuh internet):
  dirasat "<kata kunci>" [maks] [saringan]   judul, peneliti, tahun, jurnal, tautan, dan ringkasan; dicari menurut kata
                               dan menurut makna. Saringan OpenAlex, mis. language:ar,type:dissertation
  dirasat-pdf <W…> <folder>    unduh PDF penelitian (nomor OpenAlex dari `dirasat`) ke folder bahts; butuh kunci OpenAlex
"""
import difflib, hashlib, json, math, os, re, shutil, subprocess, sys, sysconfig, tempfile, time, urllib.error, zipfile
from pathlib import Path

import dirasat, hadits, shamela  # ringan; olah (memuat teks Al-Qur'an) baru dimuat saat `cek`
from shamela import perintah
from berkas import PemulihanGagal, bahan, kosongkan_penulis, kunci, terbitkan

MESIN = Path(__file__).resolve().parent
AKAR = MESIN.parent
# Font mushaf «KFGQPC HAFS Uthmanic Script» milik مجمع الملك فهد: tidak ikut repo (lihat NOTICE), diunduh oleh `siapkan`.
FONT = "UthmanicHafs_V22.ttf"
FONT_SUMBER = ("https://static-cdn.tarteel.ai/qul/fonts/" + FONT,  # dicoba berurutan
               "https://github.com/Farisarditiyanto/mesin-bahts/releases/download/v0.0.1/" + FONT)
FONT_SHA256 = "aa68bffce289b4c0ebac68e90502eb69e42356abcd1603cb2b8e99c2c723f145"
FONT_NAMA = "KFGQPC HAFS Uthmanic Script (TrueType)"
FONT_PEMAKAI = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"))
SAMPUL_SAYA = AKAR / "sampul_saya.txt"  # data sampul pemakai (@kunci: nilai); mengisi @kunci yang kosong di naskah baru
NAMA_FOLDER = r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+){0,2}"  # nama folder bahts yang diterima `baru`: «ikhlas» atau «bahts/<orang>/<topik>»
BUKAN_BAHTS = {"mesin", "kitab"}  # folder akar yang bukan tempat bahts
KELUARAN_SAYA = AKAR / "keluaran_saya.txt"  # opsional, satu baris: folder tempat `rakit` menaruh salinan PDF
FORMAT = json.loads((MESIN / "format.json").read_text(encoding="utf8"))  # profil bentuk halaman; dipilih @format di naskah
HURUF_SARAN = ("huruf ini ikut terpasang kalau Windows punya papan ketik Arab (Settings > Time & language > Language & region > Add a language > العربية).\n"
               "          Atau lewat PowerShell admin (pemakai cukup klik Yes): Start-Process powershell -Verb RunAs -Wait -ArgumentList "
               "\"Add-WindowsCapability -Online -Name Language.Fonts.Arab~~~und-ARAB~0.0.1.0\"")
# perkiraan kasar kata per halaman isi pada huruf matan 18; angka pasti hanya dari Word
KATA_PER_HALAMAN_18 = 260
PUSTAKA = ("pyarrow", "pypdf", "fontTools")  # nama modul; nama pemasangannya di requirements.txt


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
    pip = f'-m pip install -r "{AKAR / "requirements.txt"}"'
    if sys.prefix == sys.base_prefix and (Path(sysconfig.get_path("stdlib")) / "EXTERNALLY-MANAGED").exists():
        # Python bawaan distro (Ubuntu 23.04+, Debian 12, Homebrew) menolak pip (PEP 668): pustaka dipasang di venv dalam repo (diabaikan git)
        venv = AKAR / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        pip = (f'"{sys.executable}" -m venv "{AKAR / ".venv"}" && "{venv}" {pip}\n'
               f'          lalu jalankan semua perintah mesin dengan "{venv}" (Python ini menolak pip ke sistem).\n'
               '          venv gagal karena ensurepip/pip tidak ada → Debian/Ubuntu: sudo apt install python3-venv, lalu ulangi')
    else:
        pip = f'"{sys.executable}" {pip}'
    baris(all(importlib.util.find_spec(m) for m in PUSTAKA), f"pustaka Python ({', '.join(PUSTAKA)})", pip)
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
    print("WSL tidak diperlukan. Connector shamela: wajib; connector lain ikut dipasang lewat agent (AGENTS.md «Pemakai baru» langkah 4-5).")
    sys.exit(0 if siap_cek else 1)


def semua_bahts():
    """Jalur relatif tiap bahts, juga yang berada di bawah bahts/<orang>/."""
    ada = (n.parent.relative_to(AKAR) for pola in ("*/naskah.txt", "*/*/naskah.txt", "*/*/*/naskah.txt") for n in AKAR.glob(pola))
    return sorted(p.as_posix() for p in ada if p.parts[0] not in BUKAN_BAHTS)


def folder_bahts(nama):
    def folder(f):  # yang disebut berkas naskahnya, bukan foldernya
        return f.parent if f.name.lower() == "naskah.txt" else f
    f = folder((AKAR / nama).resolve())  # jalur lengkap («C:\\…\\mesin-bahts\\ikhlas») juga diterima
    # jalur relatif dibaca dulu dari folder tempat perintah dijalankan (mis. `cek .` di dalam folder bahts), lalu dari folder mesin
    sini = folder((Path.cwd() / nama).resolve())
    if (sini / "naskah.txt").exists() and sini != f:
        if sini.is_relative_to(AKAR):
            return sini
        if not (f.is_relative_to(AKAR) and (f / "naskah.txt").exists()):
            f = sini
    if not f.is_relative_to(AKAR):
        sys.exit(f"Bahts «{nama}» ({f}) di luar folder mesin ({AKAR}): tiap bahts tinggal di dalam folder itu.")
    if (f / "naskah.txt").exists():
        return f
    ada = semua_bahts()
    dekat = difflib.get_close_matches(f.name, {Path(a).name for a in ada}, n=1, cutoff=0.6)
    mirip = [a for a in ada if dekat and Path(a).name == dekat[0]]
    pesan = [f"Tidak ada bahts «{f.name}» (folder berisi naskah.txt) di {AKAR}."]
    if mirip:
        pesan.append(f"Maksudnya «{'» atau «'.join(mirip)}»?")
    pesan.append("Bahts yang ada: " + (", ".join(ada) if ada else "belum ada"))
    usul = re.sub(r"[^A-Za-z0-9_-]", "", f.name) or "<nama-latin>"
    if not (AKAR / usul).exists():  # folder yang sudah ada (mis. tanpa naskah.txt) tidak bisa dibuat `baru`
        tempat = f"bahts/<orang>/{usul}" if (AKAR / "bahts").is_dir() else usul
        pesan.append("Kalau memang bahts baru: " + perintah(f'baru {tempat} "<judul>"'))
    sys.exit("\n".join(pesan))


def baru(nama, judul):
    nama = nama.removeprefix("./").removeprefix(".\\").replace("\\", "/")
    if Path(nama).is_absolute() or ".." in nama.split("/"):  # jalur lengkap atau naik folder: yang di dalam repo dipakai
        jalur = (AKAR / nama).resolve()
        if not jalur.is_relative_to(AKAR.resolve()):
            sys.exit(f"Folder «{nama}» di luar folder mesin ({AKAR}): tiap bahts harus di dalam folder repo ini "
                     f"(mis. ikhlas, atau bahts/ahmad/ikhlas untuk bahts banyak orang).")
        nama = jalur.relative_to(AKAR.resolve()).as_posix()
    nama = nama.strip("/")
    if not re.fullmatch(NAMA_FOLDER, nama) or nama.split("/")[0] in BUKAN_BAHTS:
        sys.exit(f"Nama folder «{nama}»: pakai huruf Latin, angka, - atau _ saja, tanpa spasi (mis. ikhlas, atau bahts/ahmad/ikhlas untuk bahts banyak orang).")
    if not judul.strip():
        sys.exit('Judul bahts masih kosong: ' + perintah(f'baru {nama.strip(".")} "<judul>"'))
    f = AKAR / nama
    kembar = [d.name for d in f.parent.iterdir() if d.name.lower() == f.name.lower()] if f.parent.is_dir() else []
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
    riset = (MESIN / "riset_baru.txt").read_text(encoding="utf8")  # jejak langkah connector (olah.periksa_riset)
    f.mkdir(parents=True)
    (f / "riset.txt").write_text(riset, encoding="utf8")
    (f / "naskah.txt").write_text(isi, encoding="utf8")
    print(f"Siap: {f / 'naskah.txt'} (dan riset.txt untuk jejak langkah riset)")
    sub = re.match(r"^(.+?)\s+[-–—]\s*(.+)$", judul.strip())  # pemisah yang sama dengan rakit.ps1 ($JUDUL2)
    if sub:
        print(f"Sub-judul sampul «{sub.group(2)}» akan tercetak di sampul. Tulis hanya kalau dosen, خطة, "
              f"atau pemakai memang menulisnya; kalau tidak, hapus « - …» dari @judul (tanpa sub-judul sampul tetap rapi). "
              f"Jenjang atau jenis tugas masuk @jenis, bukan sub-judul.")
    kosong = re.findall(r"^@(\w+):[ \t]*$", isi, re.M)
    if kosong:
        print("Data sampul yang masih kosong: " + ", ".join("@" + k for k in kosong)
              + f"\nIsi di naskah itu. Yang sama untuk tiap bahts (nama, nim, jenis, fasl) boleh ditulis sekali di {SAMPUL_SAYA.name}."
              + ("\nContoh @jenis (huruf Arab, tercetak di sampul): بحث صفي للمستوى الرابع" if "jenis" in kosong else ""))


def perkiraan_halaman(d):
    """Perkiraan kasar (isi, seluruh PDF, rincian) dari jumlah kata, untuk yang belum bisa `rakit`; None tanpa profil.
    isi = المقدمة s.d. الخاتمة: tiap #K/#F (dan judul di @halaman_baru) mulai halaman baru; kata catatan kaki dihitung
    menurut perbandingan luas hurufnya. Seluruh PDF = sampul + halaman sebelum المقدمة (@nomor) + isi + المصادر + فهرس,
    yang dicetak sama dengan yang dicetak rakit.ps1 (@tanpa, @bentuk: kitab, فهرس kosong tidak dicetak)."""
    fmt = d.get("format")
    if not fmt:
        return None
    # huruf lebih kecil = lebih banyak kata, tetapi tidak sebanyak luasnya (pangkat 1,1, bukan 2: 3 PDF @format tatbiqi)
    per_hal = KATA_PER_HALAMAN_18 * (18 / fmt["matan"]) ** 1.1 / fmt.get("spasi", 1)  # 1,5 spasi = baris lebih sedikit
    import olah
    kata, meta = olah.kata, d["meta"]

    def halaman(blok):
        bagian = []
        for b in blok:
            if b["k"] in ("K", "F", "H", *meta.get("halaman_baru", [])) or not bagian:
                bagian.append(0.0)
            fn = sum(kata(d["catatan"][r["fn"]]["runs"]) for r in b["runs"] if r.get("fn") is not None)
            bagian[-1] += kata(b["runs"]) + fn * (fmt["catatan"] / fmt["matan"]) ** 2
        return sum(max(1, math.ceil(x / per_hal)) for x in bagian)

    blok = d["blok"]
    blok = blok[:next((i for i, b in enumerate(blok) if b["k"] == "R"), len(blok))]
    mula = next((i for i, b in enumerate(blok) if b.get("judul") == "المقدمة"), 0) if meta.get("nomor") else 0
    isi = halaman(blok[mula:])  # @nomor: abjad: الإهداء dst. sebelum المقدمة bukan halaman isi
    tanpa = set(re.split(r"[,، ]+", meta.get("tanpa", "")))
    kitab = meta.get("bentuk") == "kitab"
    rinci = {"sampul": 0 if kitab else 1, "sebelum المقدمة": halaman(blok[:mula]) if mula else 0}
    judul = sum(b["k"] in ("K", "F", "B", "M") for b in blok)  # baris فهرس الموضوعات
    for nama, n, per in (("المصادر", len(d["pustaka"]) if "pustaka" not in tanpa and (not kitab or d["pustaka"]) else 0, 12),
                         ("فهرس الآيات", 0 if "ayat" in tanpa else len(d["ayat"]), 26),
                         ("فهرس الأحاديث", 0 if "hadits" in tanpa else len(d["hadits"]), 20),
                         ("فهرس الموضوعات", 0 if "maudhuat" in tanpa else max(judul, 1), 25)):
        rinci[nama] = math.ceil(n / per)  # baris per halaman dari 30 PDF bahts nyata (selisih paling banyak 1 halaman)
    return isi, isi + sum(rinci.values()), {k: v for k, v in rinci.items() if v}


def cek(nama, keluar=None, jejak=False):
    import olah
    f = folder_bahts(nama)
    galat, lap = olah.utama(f, keluar)
    print("\n".join(lap))
    if olah.TERTOLAK:
        if jejak:
            print("petunjuk dari kitab lain (hanya petunjuk, bukan bukti; putusan tetap milik `cek`):")
            print("\n".join(olah.jejak(olah.TERTOLAK)))
        else:
            n = len({shamela.padat(t) for _, t in olah.TERTOLAK})
            jalur = nama.rstrip("/\\") or nama  # «"folder\"»: garis miring menelan tanda petik penutupnya
            print(f"{n} teks tidak ditemukan di kitab yang dirujuk; cari di kitab lain yang sudah diunduh: "
                  + perintah(f'cek "{jalur}" --jejak'))
    elif jejak:
        print("jejak: tidak ada bukti yang gagal «teks TIDAK KETEMU di kitab».")
    try:
        n = perkiraan_halaman(json.loads((keluar or bahan(f)).read_text(encoding="utf8")))
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        n = None
    if n:
        isi, total, rinci = n
        print(f"perkiraan halaman isi (المقدمة s.d. الخاتمة): ±{isi}; seluruh PDF: ±{total} ("
              + ", ".join(f"{k} {v}" for k, v in rinci.items()) + f", isi {isi}) "
              "(kasar, dari jumlah kata; angka pasti = HALAMAN_ISI dan HALAMAN sesudah `rakit`)")
    return f, galat, lap


RAKIT_ANTRE = 30 * 60  # detik; rakit terlama yang tercatat ±10 menit: dua rakit di depan masih tertampung
RAKIT_PS_KUNCI = MESIN / "_tmp" / "rakit.kunci"  # dibuka rakit.ps1 tanpa berbagi selama ia hidup (dilepas OS saat mati)
RAKIT_GALAT = "rakit.galat"  # di folder kerja: pesan galat rakit.ps1 (UTF-8), ditulis sebelum PowerShell berhenti
RAKIT_SEMENTARA = "rakit.sementara"  # penanda folder .rakit-* bahan sementara rakit versi ini: boleh dibuang rakit berikutnya
RAKIT_SIMPAN = "JANGAN_DIHAPUS.txt"  # pengganti penanda di atas bila folder itu berisi hasil baru yang belum terpasang (PemulihanGagal)


def rakit(nama):
    if os.name == "nt":
        try:
            apa = folder_bahts(nama).relative_to(AKAR).as_posix()
            with kunci(MESIN / "_tmp" / "rakit.pekerjaan", tunggu=RAKIT_ANTRE, apa=apa):
                _tunggu_ps_yatim()
                _rakit(nama)
        except PermissionError as e:  # hasil lama (atau yang baru) sedang dibuka aplikasi lain; hasil lama tetap utuh
            sys.exit(f"Perakitan GAGAL: {Path(e.filename or '').name or 'hasil'} sedang terbuka di aplikasi lain (Word "
                     f"atau pembaca PDF). Tutup dulu, lalu ulangi `rakit`. Hasil lama tidak berubah.")
        except Exception as e:
            sys.exit(f"Perakitan GAGAL: {type(e).__name__}: {e}")
    else:
        _, galat, _ = cek(nama)
        sys.exit(f"Belum dirakit: {galat} galat harus beres dulu." if galat else
                 "`rakit` butuh Windows + Microsoft Word. Naskahnya sudah lolos `cek`.")


def _tunggu_ps_yatim():
    """rakit.ps1 milik rakit yang dimatikan (Python-nya mati, PowerShell-nya belum) masih memakai Word dan folder
    kerjanya: tunggu sampai ia berhenti sendiri, supaya Word tidak dipakai berdua dan foldernya tidak dibuang saat masih
    ditulisi. Word-nya dibereskan rakit.ps1 itu sendiri (atau rakit.ps1 berikutnya, lewat catatan Word yatim)."""
    batas, kabar = time.monotonic() + RAKIT_ANTRE, False
    while True:
        try:
            with open(RAKIT_PS_KUNCI, "ab"):
                return
        except PermissionError:
            if time.monotonic() >= batas:
                raise RuntimeError("rakit.ps1 dari rakit yang dimatikan masih jalan: tunggu sampai berhenti, lalu ulangi.") from None
            if not kabar:
                print("rakit.ps1 dari rakit sebelumnya yang dimatikan masih memakai Word: menunggu sampai berhenti sendiri "
                      "(jangan matikan Word atau PowerShell-nya)...", flush=True)
                kabar = True
            time.sleep(2)


def _buang_sisa(f, kerja):
    """Buang folder kerja rakit ini dan folder .rakit-* yang tertinggal rakit yang dimatikan (Python-nya mati sebelum
    membersihkannya). Aman: kunci rakit dipegang rakit ini dan rakit.ps1 sisa rakit lain sudah berhenti (_tunggu_ps_yatim),
    jadi tidak ada rakit lain yang masih memakainya. Dipanggil sesudah rakit.ps1, yang menghentikan Word yatim rakit lama
    (Word itu masih membuka berkas di foldernya). Yang dibuang hanya folder bertanda RAKIT_SEMENTARA (bahan sementara versi
    ini). Tanpa penanda itu (hasil baru yang belum terpasang, atau folder dari versi lama yang mungkin sengaja disimpan)
    hanya disebut, tidak pernah dibuang."""
    for sisa in sorted(f.glob(".rakit-*")):
        if not sisa.is_dir():
            continue
        if (sisa / RAKIT_SIMPAN).exists() or not (sisa / RAKIT_SEMENTARA).exists():
            print(f"Folder {sisa.name} dibiarkan: mungkin berisi hasil yang sengaja disimpan; periksa isinya, lalu hapus sendiri.")
            continue
        shutil.rmtree(sisa, ignore_errors=True)
        if sisa.exists():
            print(f"Bahan sementara rakit belum bisa dibuang (ada berkas yang masih terbuka; `rakit` berikutnya mencoba lagi): {sisa}")
        elif sisa != kerja:
            print(f"Sisa rakit yang terhenti dibuang: {sisa.name}")


def _word_gagal(kode, galat):
    """Pesan rakit.ps1 yang gagal. Pesannya diambil dari berkas `galat` (ditulis trap rakit.ps1), bukan dari layar: layar
    bisa dipotong `tail`/`grep` pemanggil. Tanpa berkas itu PowerShell mati sebelum sempat menulis apa pun."""
    try:
        isi = galat.read_text(encoding="utf8").strip()
    except OSError:
        isi = ""
    if isi:
        return f"Perakitan Word gagal (rakit.ps1, kode keluar {kode}): {isi}. Hasil lama belum diganti."
    return (f"Perakitan Word gagal: rakit.ps1 berhenti tanpa pesan (kode keluar {kode}). Artinya PowerShell atau Word-nya "
            "dimatikan dari luar (Stop-Process, Task Manager, batas waktu alat, terminal ditutup) atau mati mendadak. "
            "Hasil lama belum diganti; ulangi `rakit`. Rakit yang sedang jalan jangan dimatikan: rakit berikutnya antre sendiri.")


def _rakit(nama):
    f = folder_bahts(nama)
    kerja = Path(tempfile.mkdtemp(prefix=".rakit-", dir=f))
    (kerja / RAKIT_SEMENTARA).write_text("Bahan sementara `rakit`; dibuang sendiri oleh rakit berikutnya.\n", encoding="utf8")
    try:
        _rakit_di(nama, f, kerja)
    except PemulihanGagal:  # hasil baru masih di folder kerja: jangan dibuang, juga oleh rakit berikutnya
        (kerja / RAKIT_SIMPAN).write_text("Hasil baru yang belum terpasang (pemulihan rakit gagal; lihat pesan rakit).\n"
                                          "`rakit` tidak membuang folder ini: selamatkan isinya, lalu hapus sendiri.\n",
                                          encoding="utf8")
        try:  # RAKIT_SIMPAN sudah melindunginya; penanda sementara dicabut supaya versi lain pun tidak membuangnya
            (kerja / RAKIT_SEMENTARA).unlink()
        except OSError:
            pass
        print(f"Bahan percobaan disimpan: {kerja}")
        raise
    finally:  # berhasil, atau galat cek, Word gagal, berkas terkunci: hasil lama utuh, bahan sementara tidak dibutuhkan
        _buang_sisa(f, kerja)


def _rakit_di(nama, f, kerja):
    build = kerja / "bahan.json"
    f, galat, lap = cek(nama, build)
    if galat:
        sys.exit(f"Belum dirakit: {galat} galat di atas harus beres dulu.")
    if os.name != "nt":
        sys.exit("`rakit` butuh Windows + Microsoft Word. Naskahnya sudah lolos `cek`.")
    if not font_terpasang():
        sys.exit(f"Font mushaf belum terpasang: {perintah('siapkan')}, lalu ulangi.")
    d = json.loads(build.read_text(encoding="utf8"))
    huruf = d["format"]["huruf"]
    if not huruf_ada(huruf):  # tanpa huruf profil, Word diam-diam memakai huruf lain
        sys.exit(f"Huruf {huruf} (dipakai @format naskah ini) belum terpasang di Windows.\n       -> {HURUF_SARAN}\n"
                 f"Sesudah itu: {perintah('periksa')}, lalu ulangi `rakit`.")
    ps1 = MESIN / "rakit.ps1"
    # Windows PowerShell 5.1 hanya membaca huruf Arab di skrip kalau berkasnya ber-BOM
    if not ps1.read_bytes().startswith(b"\xef\xbb\xbf"):
        ps1.write_bytes(b"\xef\xbb\xbf" + ps1.read_bytes())
    (kerja / "laporan.txt").write_text("\n".join(lap) + "\n", encoding="utf8")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1),
                        "-Build", str(build), "-Folder", str(f), "-Hasil", str(kerja),
                        "-Kunci", str(RAKIT_PS_KUNCI), "-Galat", str(kerja / RAKIT_GALAT)])
    if r.returncode:
        raise RuntimeError(_word_gagal(r.returncode, kerja / RAKIT_GALAT))
    berkas = d["meta"]["berkas"]
    import teks_pdf
    try:  # supaya teks Arab PDF tersalin dan tercari dengan benar; tampilannya tidak berubah
        teks_pdf.betulkan(kerja / f"{berkas}.pdf")
    except Exception as e:
        print(f"PERINGATAN: PDF jadi, tetapi teks Arabnya belum dibetulkan (salin/cari bisa terbalik): {type(e).__name__}: {e}")
    with zipfile.ZipFile(kerja / f"{berkas}.docx") as z:
        if z.testzip() or not {"[Content_Types].xml", "word/document.xml"} <= set(z.namelist()):
            raise RuntimeError("Word menghasilkan DOCX yang tidak utuh; hasil lama belum diganti.")
    kosongkan_penulis(kerja / f"{berkas}.docx")
    from pypdf import PdfReader
    halaman = len(PdfReader(kerja / f"{berkas}.pdf").pages)
    laporan = (kerja / "laporan.txt").read_text(encoding="utf8")
    if f"HALAMAN={halaman}" not in laporan.splitlines() or not halaman:
        raise RuntimeError("PDF dan laporan halaman tidak cocok; hasil lama belum diganti.")
    if hashlib.sha256((f / "naskah.txt").read_bytes()).hexdigest() != d["naskah_sha256"]:
        raise RuntimeError("Naskah berubah selama rakit; hasil lama belum diganti. Ulangi rakit.")
    terbitkan(kerja, f, [f"{berkas}.docx", f"{berkas}.pdf", "laporan.txt"])
    for baris in (f / "laporan.txt").read_text(encoding="utf8").splitlines():
        if baris.startswith(("HALAMAN", "CATATAN_KAKI", "KATA")):
            print(baris)
    print(f"Jadi: {f / berkas}.docx dan .pdf")
    salin_keluaran(f, berkas)


def salin_keluaran(f, berkas):
    """Salinan PDF di folder pilihan pemakai, per orang: bahts/ahmad/ikhlas -> <keluaran>/ahmad/<berkas>.pdf.
    Induknya tetap folder bahts, jadi salinan yang gagal hanya diperingatkan."""
    if not KELUARAN_SAYA.exists():
        return
    induk = KELUARAN_SAYA.read_text(encoding="utf-8-sig").strip()
    bagian = f.relative_to(AKAR).parts[:-1]
    tujuan = Path(induk, *bagian[bagian[:1] == ("bahts",):]) / f"{berkas}.pdf"
    try:
        tujuan.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f / f"{berkas}.pdf", tujuan)
        print(f"Salinan: {tujuan}")
    except OSError as e:
        print(f"PERINGATAN: PDF jadi di folder bahts, tetapi salinan ke {tujuan} gagal: {e}")


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
    except (re.error, OverflowError):  # OverflowError: pengulangan raksasa, mis. a{99999999999}
        return re.escape(teks)


def ambil(nomor):
    """Unduh tiap kitab; satu yang gagal tidak membatalkan yang lain. Keluar dengan kode 1 kalau ada yang belum terunduh.
    Nama folder bahts = semua kitab yang dirujuk bukti naskahnya (yang sudah ada dilewati)."""
    import olah
    sid, bukan_folder = [], []
    for x in nomor:
        if not x.isdigit():
            try:
                f = folder_bahts(x)
            except SystemExit as e:
                if re.search(r"[/\\]", x):  # jalur folder yang salah: pesan folder, bukan «bukan nomor kitab»
                    print(f"{x}: {e.code}"); bukan_folder.append(x); continue
                sid.append(x); continue  # shamela.ambil yang menjelaskan kenapa bukan nomor kitab
            dirujuk = olah.kitab_dirujuk(f)
            print(f"{f.name}: {len(dirujuk)} kitab dirujuk naskahnya")
            sid += dirujuk; continue
        sid.append(x)
    gagal = bukan_folder + shamela.ambil(*dict.fromkeys(sid))
    if gagal:
        sys.exit(f"Belum terunduh: {', '.join(gagal)} (lihat pesan di atas).")


def bendera_temukan(frasa, a):
    """Argumen `shamela.temukan` dari `temukan "<frasa>" [maks] [--mazhab m,…] [--kitab id,…] [--halaman n]`."""
    maks, saring, tersebut = 20, {"--mazhab": "", "--kitab": "", "--halaman": "1"}, set()
    contoh = {"--mazhab": "hanbali", "--kitab": "8370", "--halaman": "2"}
    while a:
        if a[0] in saring:
            if len(a) < 2 or not a[1].strip(" ,،"):
                raise ValueError(f"{a[0]} butuh nilai, mis. {a[0]} {contoh[a[0]]}")
            if a[0] in tersebut:
                raise ValueError(f"{a[0]} disebut dua kali; nilai ganda ditulis dengan koma, mis. {a[0]} {contoh[a[0]]},…")
            tersebut.add(a[0])
            saring[a[0]], a = a[1], a[2:]
        elif a[0].startswith("--"):
            raise ValueError(f"bendera «{a[0]}» tidak dikenal")
        else:
            maks, a = angka(a[0], "maks"), a[1:]
    daftar = lambda s: [x.strip() for x in s.replace("،", ",").split(",") if x.strip()]
    return frasa, maks, daftar(saring["--mazhab"]), daftar(saring["--kitab"]), angka(saring["--halaman"], "halaman")


HALAMAN_MAKS = 20


def halaman(sid, juz, hal):
    """`halaman` satu halaman atau rentang «10-14» (angka Arab boleh): agent tidak perlu memanggilnya berkali-kali."""
    m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", str(hal))
    if not m:
        return shamela.halaman(sid, juz, hal)
    a, z = int(m[1]), int(m[2])
    if not a <= z < a + HALAMAN_MAKS:
        sys.exit(f"Rentang halaman {hal}: tulis awal-akhir dengan awal ≤ akhir, paling banyak {HALAMAN_MAKS} halaman.")
    ada = False
    for h in range(a, z + 1):
        print(f"===== [{sid}] {juz}/{h} =====")
        ada |= shamela.halaman(sid, juz, h)  # jangan berhenti di halaman bolong: kitab bisa melompati nomor di tengah
    return ada


def ketemu(n):
    """Pencarian yang kosong keluar dengan kode 1, supaya skrip/agent tahu tanpa membaca pesannya."""
    if not n:
        sys.exit(1)


def perintah_cek(a):
    """`cek <folder> [--jejak]`: bendera boleh sebelum/sesudah folder; bendera saja = kurang argumen."""
    folder = next((x for x in a if x != "--jejak"), None)
    if folder is None:
        sys.exit(f"Perintah «cek» kurang argumen. Bentuknya:\n  {re.search(r'^  cek .*', __doc__, re.M).group(0)}")
    if len([x for x in a if x != "--jejak"]) != 1 or folder.startswith("--"):
        sys.exit(f"Argumen perintah «cek» tidak dikenal atau berlebih: {a}\nBentuknya:\n"
                 f"{re.search(r'^  cek .*', __doc__, re.M).group(0)}")
    sys.exit(1 if cek(folder, jejak="--jejak" in a)[1] else 0)


def perintah_bukti(a):
    """`bukti <folder> [baris|awal-akhir]`: penunjuk untuk pemeriksa (lihat olah.bukti); 0 yang dicetak = kode keluar 1."""
    import olah
    dari = sampai = None
    if len(a) == 2:
        m = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", a[1].strip())
        if not m or int(m[2] or m[1]) < int(m[1]):
            raise ValueError(f"baris ditulis angka (mis. 15) atau rentang awal-akhir (mis. 10-40), bukan «{a[1]}»")
        dari, sampai = int(m[1]), int(m[2] or m[1])
    ketemu(olah.bukti(folder_bahts(a[0]), dari, sampai))


PERINTAH = {  # nama: (jumlah argumen minimal, maksimal (None = diperiksa pemanggilnya), pemanggil)
    "periksa": (0, 0, lambda a: periksa()),
    "siapkan": (0, 0, lambda a: siapkan()),
    "baru": (2, 2, lambda a: baru(a[0], a[1])),
    "cek": (0, None, perintah_cek),
    "rakit": (1, 1, lambda a: rakit(a[0])),
    "bukti": (1, 2, perintah_bukti),
    "tanda": (0, 0, lambda a: print(tanda())),
    "kitab": (0, 0, lambda a: shamela.daftar()),
    "katalog": (1, 1, lambda a: ketemu(shamela.katalog(pola(a[0])))),
    "temukan": (1, None, lambda a: ketemu(shamela.temukan(*bendera_temukan(a[0], a[1:])))),
    "ambil": (1, None, lambda a: ambil(a)),
    "kartu": (1, 1, lambda a: shamela.kartu(a[0])),
    "cari": (2, 2, lambda a: ketemu(shamela.cari(a[0], a[1]))),
    "teks": (2, 4, lambda a: ketemu(shamela.teks(a[0], a[1], *(angka(x, apa) for x, apa in zip(a[2:], ("lebar", "maks")))))),
    "bab": (2, 2, lambda a: ketemu(shamela.bab(a[0], a[1]))),
    "halaman": (3, 3, lambda a: ketemu(halaman(*a))),
    "scan": (3, 3, lambda a: ketemu(shamela.scan(*a))),
    "hadits": (1, 2, lambda a: ketemu(hadits.cari(a[0], *(angka(x, "maks") for x in a[1:])))),
    "dirasat": (1, 3, lambda a: dirasat.cari(a[0], *(angka(x, "maks") for x in a[1:2]), *a[2:])),
    "dirasat-pdf": (2, 2, lambda a: dirasat.pdf(a[0], folder_bahts(a[1]))),
}


def tanda():
    """Daftar tanda naskah: ditulis sekali di kepala olah.py (tempat tanda itu diurai), dicetak dari sana."""
    import olah
    return olah.__doc__[olah.__doc__.index("Tanda di naskah"):].rstrip()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")  # pesan galat memuat «» dan huruf Arab; konsol Windows tidak bisa mencetaknya
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
    paling_sedikit, paling_banyak, jalankan = PERINTAH[cmd]
    if len(a) < paling_sedikit:
        sys.exit(f"Perintah «{cmd}» kurang argumen. Bentuknya:\n{bentuk}")
    if paling_banyak is not None and len(a) > paling_banyak:
        # dulu ditelan diam-diam: `katalog "زاد" --mazhab hanbali` tidak tersaring, `halaman 1679 - 8 9` mengabaikan 9
        bendera = [x for x in a if x.startswith("--")]
        sys.exit(f"Argumen perintah «{cmd}» tidak dikenal atau berlebih: {a[paling_banyak:]}"
                 + (f" (perintah «{cmd}» tidak punya bendera {', '.join(bendera)})" if bendera else "")
                 + f"\nBentuknya:\n{bentuk}")
    try:
        jalankan(a)
    except urllib.error.HTTPError as e:
        if not 400 <= e.code < 500 or e.code == 429:
            sys.exit(f"Perintah '{cmd}': layanannya sedang menolak atau sibuk (HTTP {e.code}). Ulangi sebentar lagi.")
        sys.exit(f"Perintah '{cmd}': layanannya menolak permintaan ini (HTTP {e.code}). Periksa kata/angka yang diketik: {a}")
    except MemoryError:
        sys.exit(f"Perintah '{cmd}': memori komputer habis. Tutup aplikasi lain, lalu ulangi.")
    except BrokenPipeError:  # keluarannya dipotong pembaca (mis. `| head`): bukan masalah internet
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    except TimeoutError:
        sys.exit(f"Perintah '{cmd}': layanannya terlalu lama menjawab. Ulangi sebentar lagi.")
    except shamela.GAGAL_JARINGAN as e:
        sys.exit(f"Perintah '{cmd}' gagal mengunduh (cek internet, lalu ulangi): {e!r}")
    except (ValueError, FileNotFoundError, re.error) as e:
        sys.exit(f"Perintah '{cmd}' salah pakai: {e}\nBentuknya:\n{bentuk}")
