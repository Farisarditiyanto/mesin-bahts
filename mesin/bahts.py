# SPDX-License-Identifier: AGPL-3.0-or-later
"""Satu pintu mesin bahts:  python mesin/bahts.py <perintah>

Sekali sesudah mengunduh repo:
  periksa                      apa yang sudah siap di komputer ini, dan perintah untuk tiap yang belum
  siapkan                      unduh katalog kitab, tabel layanan (tafsir, takhrij, rawi, akar) + font mushaf, lalu pasang
                               font itu (Windows)

Bahts (tiap bahts = satu folder berisi naskah.txt):
  baru <folder> "<judul>"      buat folder bahts baru + kerangka naskah.txt; <folder> boleh bahts/<orang>/<topik>
  cek <folder> [--jejak]       periksa naskah: tanda, ayat, dan semua bukti <<...>> ke kitab lokal;
                               --jejak: teks yang tidak ada di kitabnya dicari di kitab lain yang sudah diunduh
  bukti <folder> [baris|awal-akhir]   untuk pemeriksa: tiap catatan kaki berbukti <<sid|juz|hal>> (kalimat yang
                               dibuktikan, isi catatan kaki, nama kitab, bab, dan teks halaman itu di sekitar kutipan)
                               dan teks tiap ayat {Q:} persis seperti tercetak, juga tiap paragraf isi tanpa catatan
                               kaki (untuk dinilai: penisbatan tanpa sumber); tiap baris keluaran diawali «baris n».
                               Penunjuk saja, putusan tetap `cek`
  rakit <folder> [--fasl n]    cek, lalu rakit .docx + .pdf (Word) ke dalam folder itu; --fasl 2 (atau 1-2): hanya #F
                               ke-2, untuk bahts yang dikumpulkan bertahap per فصل (lihat `tanda`); `cek` tetap
                               memeriksa seluruh naskah
  tahap <folder>               tahap bahts sekarang dan satu langkah berikutnya: naskah (GAGAL/PERHATIAN/LOLOS), hasil
                               rakit (BELUM/TERKINI/USANG, juga tiap --fasl), rakit yang sedang jalan, folder .rakit-*
                               dan _arsip/rakit-*. Folder bahts tidak disentuh; untuk sesi baru yang tidak tahu bahts
                               ini sampai mana
  tanda                        daftar tanda yang dipakai di naskah.txt
  diagram <folder>             tiap diagram Mermaid <nama>.mmd di folder itu jadi <nama>.png (butuh Node.js + Chrome/Edge),
                               lalu dicetak dengan «#G <nama>.png | keterangan»; `cek` dan `rakit` hanya memakai PNG-nya

Kitab (perpustakaan Shamela lokal, dipakai semua bahts):
  kitab                        daftar kitab yang sudah diunduh
  katalog "<pola>"             cari judul/pengarang di katalog Shamela (regex)
  temukan "<frasa>" [maks] [--mazhab m,…] [--kitab id,…] [--halaman n]
                               cari frasa di isi SEMUA kitab Shamela (turath.io, butuh internet) -> kitab + juz/halaman; 20 hasil
                               tiap halaman. --mazhab: hanya kitab fikih mazhab itu; --kitab: hanya kitab itu, walau belum
                               diunduh; --halaman 2: hasil ke-21 dan seterusnya
  ambil <id|folder> [...]      unduh kitab (sekali saja); nama folder bahts = semua kitab yang dirujuk naskahnya
  kartu <id>                   data cetak kitab (untuk rujukan pertama & daftar pustaka) + bentuk bukti <<…>> kitab itu
  cari <id|semua> "<frasa>" [--potongan]
                               cari frasa -> juz/halaman cetak; semua: paling banyak 40 baris, lalu jumlah kitab yang cocok.
                               Frasa dicocokkan sebagai kata utuh (huruf sambung و ف ب ل ك dan «ال» di depan kata pertama
                               boleh): «العربان» tidak cocok dengan «العرب ان». Yang hanya cocok sebagai potongan kata
                               disebut jumlahnya; --potongan: ikut ditampilkan (mis. mencari awal kata)
  teks <id> "<frasa>" [lebar] [maks] [--potongan]   teks asli di sekitar frasa, untuk disalin persis
  bab <id> "<frasa>" [--potongan]   rantai judul kitab/bab tempat frasa berada
  halaman <id> <juz> <hal>     isi satu halaman (juz "-" untuk kitab satu jilid); <hal> boleh rentang, mis. 10-14
                               (paling banyak 20 halaman sekali panggil)
  scan <id> <juz> <hal>        alamat scan cetakan halaman itu (PDF di turath.io, butuh internet), untuk bacaan yang meragukan
  ekspor <id|w…> [...] [--ke <folder>]   seluruh kitab jadi satu .docx untuk dibaca di Word (kanan-ke-kiri, judul bab,
                               penanda juz/halaman, حاشية sesudah halamannya); yang belum diunduh diunduh dulu.
                               Bawaan ke folder Downloads; nama berkas = judul kitab. Bukan bahan bahts

Kitab Waqfeya (scan cetakan + OCR, untuk kitab yang tidak ada di Shamela; disimpan di kitab/waqfeya, dipakai semua bahts):
  waqfeya "<judul/pengarang>" [maks]   cari di katalog Waqfeya (±10.000 kitab) -> nomor w… (diunduh sekali, ±17 MB)
  ambil w<nomor> [...]         unduh OCR + PDF scan kitab itu (sekali saja)
  kartu w<nomor>               data katalog + OCR halaman judul (data cetak disalin dari scan-nya) + bentuk bukti
  cari w<nomor> "<frasa>"      halaman PDF yang OCR-nya memuat frasa; tidak ada yang persis -> yang paling mirip
  halaman w<nomor> <berkas> <hal>   teks OCR halaman PDF ke-hal di berkas itu + nomor cetak yang terbaca + PDF/PNG scan-nya.
                               OCR bisa salah huruf: lafaz dan juz/halaman cetak disalin dari scan, bukti <<w…|berkas|hal>>

Layanan Shamela (penunjuk jalan tanpa internet, dari dataset yang sama dengan `ambil`):
  tafsir <surat:ayat[-ayat]>   kitab tafsir yang menafsirkan ayat itu (14 kitab, mis. الطبري، ابن كثير، زاد المسير) +
                               juz/halaman cetak awal pembahasannya, urut dari pengarang yang lebih dulu wafat
  takhrij <id> <juz> <hal>     hadits di halaman itu ada juga di mana: 8 kitab (البخاري، مسلم، أبو داود، الترمذي، النسائي،
                               الموطأ، الطيالسي، ابن الجارود) + juz/halaman dan nomor haditsnya; edisi lain kitab itu
                               (mis. مسلم 1727) lewat nomor hadits, dengan edisi yang dipakai Shamela (mis. 711) sebagai jembatan
  rawi <id> <juz> <hal>        sanad tiap hadits di halaman itu, berurutan dari pengarang (layanan sanad Shamela di 8 kitab
                               hadits; edisi lain lewat jembatan nomor hadits) + rutbah ringkas: ابن حجر، الذهبي، wafat
  rawi <nomor> | rawi "<nama>" ucapan جرح وتعديل rawi itu + tempat lafaznya di edisi lokal kitab rijal sumbernya (dicari ulang,
                               bukan juz/halaman tabel); dengan nama: cari nomor rawinya
  akar <id> "<akar>"           bentuk kata berakar itu di kitab (kamus akar Shamela) + jumlahnya, dikelompokkan seperti
                               `cari` mencocokkan kata: istilah yang tidak tertangkap frasa («الشفيع» untuk شفع)

Takhrij (penunjuk jalan, «المنصة الحديثية», butuh internet):
  hadits "<طرف>" [maks]        tempat hadits di 12 kitab hadits + hukum ulama; tetap dibaca di kitabnya sendiri. Kitab yang
                               sudah diunduh: juz/halaman edisi lokal ikut dicetak (juz/halaman layanan bisa edisi lain)

Penelitian terdahulu (الدراسات السابقة, katalog OpenAlex dan DOAJ, butuh internet):
  dirasat "<kata kunci>" [maks] [saringan]   judul, peneliti, tahun, jurnal, tautan, dan ringkasan; dicari menurut kata
                               dan menurut makna. Saringan OpenAlex, mis. language:ar,type:dissertation
  dirasat-pdf <W…> <folder>    unduh PDF penelitian (nomor OpenAlex dari `dirasat`) ke folder bahts; butuh kunci OpenAlex
"""
import difflib, hashlib, json, os, re, shutil, sys, sysconfig, urllib.error
from pathlib import Path

import diagram, dirasat, hadits, huruf, jaringan, layanan, shamela, turath, waqfeya  # ringan; olah (memuat teks Al-Qur'an) baru dimuat saat `cek`
from dasar import HALAMAN_MAKS, perintah
from huruf import FONT, FONT_PEMAKAI

MESIN = Path(__file__).resolve().parent
AKAR = MESIN.parent
FONT_SUMBER = ("https://static-cdn.tarteel.ai/qul/fonts/" + FONT,  # dicoba berurutan
               "https://github.com/Farisarditiyanto/mesin-bahts/releases/download/v0.0.1/" + FONT)
FONT_SHA256 = "aa68bffce289b4c0ebac68e90502eb69e42356abcd1603cb2b8e99c2c723f145"
FONT_NAMA = "KFGQPC HAFS Uthmanic Script (TrueType)"
SAMPUL_SAYA = AKAR / "sampul_saya.txt"  # data sampul pemakai (@kunci: nilai); mengisi @kunci yang kosong di naskah baru
DATA_DIRI = ("nama", "nim", "jenis", "fasl", "thalibah", "sampul")  # milik satu orang (sampul = kampusnya): tidak disalin dari SAMPUL_SAYA ke bahts/<orang>/…
NAMA_FOLDER = r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+){0,2}"  # nama folder bahts yang diterima `baru`: «ikhlas» atau «bahts/<orang>/<topik>»
BUKAN_BAHTS = {"mesin", "kitab"}  # folder akar yang bukan tempat bahts
FORMAT = json.loads((MESIN / "format.json").read_text(encoding="utf8"))  # profil bentuk halaman; dipilih @format di naskah
PUSTAKA = ("pyarrow", "pypdf", "fontTools", "rapidfuzz")  # nama modul; nama pemasangannya di requirements.txt


def siapkan():
    """Lengkapi yang tidak ikut repo: katalog kitab dan font mushaf. Aman diulang."""
    shamela.siapkan()
    layanan.siapkan()
    f = MESIN / FONT
    if not f.exists():
        for url in FONT_SUMBER:
            try:
                with jaringan.buka(url, waktu=120) as r:
                    isi = r.read()
            except jaringan.GAGAL_JARINGAN as e:
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
    elif huruf.font_terpasang():
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
    baris(bool(importlib.util.find_spec("pymupdf")), "pustaka Python pymupdf (hanya untuk gambar PNG scan Waqfeya di "
          "`halaman w…`; tanpa itu scan dibuka sebagai PDF)", pip, untuk_cek=False, untuk_rakit=False)
    baris((shamela.ROOT / shamela.KATALOG).exists(), "katalog kitab", perintah("siapkan"))
    baris(layanan.siap(), "tabel layanan Shamela (hanya untuk `tafsir`, `takhrij`, `rawi`, `akar`)", perintah("siapkan"),
          untuk_cek=False, untuk_rakit=False)
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
        baris(huruf.font_terpasang(), "font mushaf", perintah("siapkan"), untuk_cek=False)
        # huruf tiap profil format.json; yang wajib hanya huruf profil bahts baru (@format di kerangka naskah)
        m = re.search(r"^@format:[ \t]*(\S+)", (MESIN / "naskah_baru.txt").read_text(encoding="utf8"), re.M)
        wajib = FORMAT[m.group(1) if m else "imam"]["huruf"]
        for h in dict.fromkeys(p["huruf"] for p in FORMAT.values()):
            profil = [k for k, p in FORMAT.items() if p["huruf"] == h]
            baris(huruf.huruf_ada(h), f"huruf {h}" + ("" if h == wajib else f" (hanya untuk @format {', '.join(profil)})"),
                  huruf.HURUF_SARAN, untuk_cek=False, untuk_rakit=h == wajib)
    baris(bool(shutil.which("npx") and diagram.browser()), "Node.js + Chrome/Edge (hanya untuk `diagram`: Mermaid jadi PNG)",
          "pasang Node.js LTS (Windows: winget install OpenJS.NodeJS.LTS) dan Google Chrome atau Microsoft Edge; "
          "tanpa keduanya diagram tetap bisa dicetak dari PNG yang dibuat di tempat lain", untuk_cek=False, untuk_rakit=False)
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
    data, asal = [], None
    if SAMPUL_SAYA.exists():
        try:
            data = re.findall(r"^@(\w+):[ \t]*(\S.*)$", SAMPUL_SAYA.read_text(encoding="utf-8-sig"), re.M)
        except UnicodeDecodeError:
            sys.exit(f"{SAMPUL_SAYA.name} harus disimpan sebagai UTF-8. Simpan ulang, lalu ulangi.")
    bagian = nama.split("/")
    orang_lain = len(bagian) == 3 and bagian[0].lower() == "bahts"  # bahts/<orang>/<topik>: data diri pemilik repo bukan miliknya
    if orang_lain:
        data = [(k, v) for k, v in data if k not in DATA_DIRI]
        lama = sorted(f.parent.glob("*/naskah.txt"), key=lambda x: x.stat().st_mtime)  # bahts terakhir orang yang sama
        if lama:
            asal = lama[-1]
            data += [(k, v) for k, v in re.findall(r"^@(\w+):[ \t]*(\S.*)$", asal.read_text(encoding="utf-8-sig"), re.M)
                     if k in DATA_DIRI]
    if data:
        for k, v in data:
            if re.search(rf"^@{k}:", isi, re.M):
                isi = re.sub(rf"^@{k}:[ \t]*$", lambda m: f"@{k}: {v.strip()}", isi, flags=re.M)
            else:  # kunci yang tidak ada di kerangka (mis. @thalibah) ikut ditulis
                isi = isi.replace("@berkas:", f"@{k}: {v.strip()}\n@berkas:", 1)
    riset = (MESIN / "riset_baru.txt").read_text(encoding="utf8")  # jejak langkah connector (cek_seluruh.periksa_riset)
    f.mkdir(parents=True)
    (f / "riset.txt").write_text(riset, encoding="utf8")
    (f / "naskah.txt").write_text(isi, encoding="utf8")
    print(f"Siap: {f / 'naskah.txt'} (dan riset.txt untuk jejak langkah riset)")
    if orang_lain:
        print(f"Data diri ({', '.join('@' + k for k in DATA_DIRI)}) " + (
            f"disalin dari bahts «{bagian[1]}» sebelumnya: {asal.relative_to(AKAR).as_posix()}; pastikan masih benar."
            if asal else f"tidak diambil dari {SAMPUL_SAYA.name} (itu data pemilik repo): isi data «{bagian[1]}» di naskahnya."))
    sub = re.match(r"^(.+?)\s+[-–—]\s*(.+)$", judul.strip())  # pemisah yang sama dengan rakit.ps1 ($JUDUL2)
    if sub:
        print(f"Sub-judul sampul «{sub.group(2)}» akan tercetak di sampul. Tulis hanya kalau dosen, خطة, "
              f"atau pemakai memang menulisnya; kalau tidak, hapus « - …» dari @judul (tanpa sub-judul sampul tetap rapi). "
              f"Jenjang atau jenis tugas masuk @jenis, bukan sub-judul.")
    kosong = re.findall(r"^@(\w+):[ \t]*$", isi, re.M)
    if kosong:
        print("Data sampul yang masih kosong: " + ", ".join("@" + k for k in kosong)
              + (f"\nTanyakan ke «{bagian[1]}» (nama, nomor mahasiswa, jenis tugas, mahasiswa/mahasiswi, kampus, pembimbing), "
                 f"lalu isi di naskah itu, bukan di {SAMPUL_SAYA.name}." if orang_lain else
                 f"\nIsi di naskah itu. Yang sama untuk tiap bahts (nama, nim, jenis, fasl) boleh ditulis sekali di {SAMPUL_SAYA.name}.")
              + ("\nContoh @jenis (huruf Arab, tercetak di sampul): بحث صفي للمستوى الرابع" if "jenis" in kosong else ""))


def jalur_ketik(nama):
    """Bahts seperti diketik pemakai, untuk perintah yang disarankan."""
    return nama.rstrip("/\\") or nama  # «"folder\"»: garis miring menelan tanda petik penutupnya


def cek(nama, jejak=False):
    """Periksa naskah, tulis bahannya, cetak laporannya. Kembalikan jumlah galat."""
    import olah
    f = folder_bahts(nama)
    hasil = olah.periksa(f)
    olah.tulis_bahan(hasil.bahan, olah.alamat_bahan(f))
    olah.cetak(hasil, jalur_ketik(nama), jejak)
    return len(hasil.ctx.galat)


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
    sid, bukan_folder, ww = [], [], []
    for x in nomor:
        if wq(x):
            ww.append(x); continue
        if not x.isdigit():
            try:
                f = folder_bahts(x)
            except SystemExit as e:
                if re.search(r"[/\\]", x):  # jalur folder yang salah: pesan folder, bukan «bukan nomor kitab»
                    print(f"{x}: {e.code}"); bukan_folder.append(x); continue
                sid.append(x); continue  # shamela.ambil yang menjelaskan kenapa bukan nomor kitab
            dirujuk, dirujuk_w = olah.kitab_dirujuk(f)
            print(f"{f.name}: {len(dirujuk) + len(dirujuk_w)} kitab dirujuk naskahnya")
            sid += dirujuk; ww += dirujuk_w; continue
        sid.append(x)
    gagal = bukan_folder + (shamela.ambil(*dict.fromkeys(sid)) if sid else []) + waqfeya.ambil(*dict.fromkeys(ww))
    if gagal:
        sys.exit(f"Belum terunduh: {', '.join(gagal)} (lihat pesan di atas).")


def bendera_temukan(frasa, a):
    """Argumen `turath.temukan` dari `temukan "<frasa>" [maks] [--mazhab m,…] [--kitab id,…] [--halaman n]`."""
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


def wq(x):
    """Argumen nomor kitab Waqfeya («w» + huruf), bukan nomor Shamela."""
    return str(x).startswith("w") and len(str(x)) > 1


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
    sys.exit(1 if cek(folder, jejak="--jejak" in a) else 0)


def perintah_bukti(a):
    """`bukti <folder> [baris|awal-akhir]`: penunjuk untuk pemeriksa (lihat penunjuk.bukti); 0 yang dicetak = kode keluar 1."""
    import penunjuk
    dari = sampai = None
    if len(a) == 2:
        m = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", a[1].strip())
        if not m or int(m[2] or m[1]) < int(m[1]):
            raise ValueError(f"baris ditulis angka (mis. 15) atau rentang awal-akhir (mis. 10-40), bukan «{a[1]}»")
        dari, sampai = int(m[1]), int(m[2] or m[1])
    ketemu(penunjuk.bukti(folder_bahts(a[0]), dari, sampai))


def perintah_tahap(a):
    """`tahap <folder>`: keadaan bahts dibaca ulang dari barang aslinya; mesin keadaannya di tahap.py. Folder bahts dan
    bahan `cek` di mesin/_tmp tidak disentuh."""
    import tahap
    print("\n".join(tahap.baris(tahap.baca(folder_bahts(a[0]), jalur_ketik(a[0])))))


def perintah_rakit(a):
    """`rakit <folder> [--fasl n]`: bendera boleh sebelum/sesudah folder. Alurnya di rakit.py."""
    a = list(a)
    fasl = None
    if "--fasl" in a:
        i = a.index("--fasl")
        if i + 1 >= len(a):
            raise ValueError("--fasl perlu nomor #F, mis. --fasl 2")
        fasl = a.pop(i + 1)
        a.pop(i)
    if len(a) != 1 or a[0].startswith("--"):
        raise ValueError(f"argumen tidak dikenal atau berlebih: {a}")
    if os.name != "nt":
        galat = cek(a[0])
        sys.exit(f"Belum dirakit: {galat} galat harus beres dulu." if galat else
                 "`rakit` butuh Windows + Microsoft Word. Naskahnya sudah lolos `cek`.")
    import rakit
    rakit.rakit(folder_bahts(a[0]), jalur_ketik(a[0]), fasl)


def perintah_ekspor(a):
    """`ekspor <id|w…> [...] [--ke <folder>]`: --ke boleh di mana saja."""
    import ekspor
    a, ke = list(a), Path.home() / "Downloads"
    if "--ke" in a:
        i = a.index("--ke")
        if i + 1 >= len(a) or a[i + 1].startswith("--"):
            raise ValueError("--ke perlu nama folder")
        ke = Path(a.pop(i + 1)); a.pop(i)
    if not a or any(x.startswith("--") for x in a):
        raise ValueError(f"argumen tidak dikenal atau kurang: {a}")
    ekspor.ekspor(a, ke)


PERINTAH = {  # nama: (jumlah argumen minimal, maksimal (None = diperiksa pemanggilnya), pemanggil)
    "periksa": (0, 0, lambda a: periksa()),
    "siapkan": (0, 0, lambda a: siapkan()),
    "baru": (2, 2, lambda a: baru(a[0], a[1])),
    "cek": (0, None, perintah_cek),
    "rakit": (1, None, perintah_rakit),
    "bukti": (1, 2, perintah_bukti),
    "tahap": (1, 1, perintah_tahap),
    "tanda": (0, 0, lambda a: print(tanda())),
    "diagram": (1, 1, lambda a: sys.exit(1 if diagram.render(folder_bahts(a[0])) else 0)),
    "kitab": (0, 0, lambda a: shamela.daftar()),
    "katalog": (1, 1, lambda a: ketemu(shamela.katalog(pola(a[0])))),
    "temukan": (1, None, lambda a: ketemu(turath.temukan(*bendera_temukan(a[0], a[1:])))),
    "ambil": (1, None, lambda a: ambil(a)),
    "kartu": (1, 1, lambda a: waqfeya.kartu(a[0]) if wq(a[0]) else shamela.kartu(a[0])),
    "cari": (2, 2, lambda a, **k: ketemu(waqfeya.cari(a[0], a[1]) if wq(a[0]) else shamela.cari(a[0], a[1], **k))),
    "waqfeya": (1, 2, lambda a: ketemu(waqfeya.cari_katalog(a[0], *(angka(x, "maks") for x in a[1:])))),
    "teks": (2, 4, lambda a, **k: ketemu(shamela.teks(a[0], a[1], *(angka(x, apa) for x, apa in zip(a[2:], ("lebar", "maks"))), **k))),
    "bab": (2, 2, lambda a, **k: ketemu(shamela.bab(a[0], a[1], **k))),
    "halaman": (3, 3, lambda a: ketemu(waqfeya.halaman(*a) if wq(a[0]) else halaman(*a))),
    "scan": (3, 3, lambda a: ketemu(turath.scan(*a))),
    "ekspor": (1, None, perintah_ekspor),
    "tafsir": (1, 1, lambda a: ketemu(layanan.tafsir(a[0]))),
    "takhrij": (3, 3, lambda a: ketemu(layanan.takhrij(*a))),
    "rawi": (1, 3, lambda a: ketemu(layanan.rawi(*a)) if len(a) != 2 else sys.exit(
        "Perintah «rawi»: tulis <id> <juz> <hal>, satu nomor rawi, atau satu nama dalam tanda petik.")),
    "akar": (2, 2, lambda a: ketemu(layanan.akar(*a))),
    "hadits": (1, 2, lambda a: ketemu(hadits.cari(a[0], *(angka(x, "maks") for x in a[1:])))),
    "dirasat": (1, 3, lambda a: dirasat.cari(a[0], *(angka(x, "maks") for x in a[1:2]), *a[2:])),
    "dirasat-pdf": (2, 2, lambda a: dirasat.pdf(a[0], folder_bahts(a[1]))),
}

POTONGAN = ("cari", "teks", "bab")  # perintah yang menerima --potongan (frasa boleh cocok di tengah kata)


def tanda():
    """Daftar tanda naskah: ditulis sekali di olah.py (pintu `cek`; penguraiannya di naskah.py), dicetak dari sana."""
    import olah
    return olah.TANDA


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
    k = {}
    if cmd in POTONGAN and "--potongan" in a:  # bendera boleh di mana saja; tidak dihitung sebagai argumen
        a, k = [x for x in a if x != "--potongan"], {"potongan": True}
    if len(a) < paling_sedikit:
        sys.exit(f"Perintah «{cmd}» kurang argumen. Bentuknya:\n{bentuk}")
    if paling_banyak is not None and len(a) > paling_banyak:
        # argumen berlebih ditolak, bukan ditelan: `halaman 1679 - 8 9` jangan diam-diam mengabaikan 9
        bendera = [x for x in a if x.startswith("--")]
        sys.exit(f"Argumen perintah «{cmd}» tidak dikenal atau berlebih: {a[paling_banyak:]}"
                 + (f" (perintah «{cmd}» tidak punya bendera {', '.join(bendera)})" if bendera else "")
                 + f"\nBentuknya:\n{bentuk}")
    try:
        jalankan(a, **k)
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
    except jaringan.GAGAL_JARINGAN as e:
        sys.exit(f"Perintah '{cmd}' gagal mengunduh (cek internet, lalu ulangi): {e!r}")
    except (ValueError, FileNotFoundError, re.error) as e:
        sys.exit(f"Perintah '{cmd}' salah pakai: {e}\nBentuknya:\n{bentuk}")
