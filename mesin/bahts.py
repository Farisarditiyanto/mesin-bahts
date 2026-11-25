# SPDX-License-Identifier: AGPL-3.0-or-later
"""Satu pintu mesin bahts: python mesin/bahts.py <perintah>. Tabel perintahnya (DAFTAR) = teks bantuan dan yang dijalankan."""
import os, re, sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dasar import HALAMAN_MAKS, SUBJUDUL, perintah, profil_format
from huruf import FONT


def _mod(nama):
    return __import__(nama)


def _http_error():
    import urllib.error
    return urllib.error.HTTPError


def _gagal_jaringan():
    import jaringan
    return jaringan.GAGAL_JARINGAN

MESIN = Path(__file__).resolve().parent
AKAR = MESIN.parent
FONT_SUMBER = ("https://static-cdn.tarteel.ai/qul/fonts/" + FONT,  # dicoba berurutan
               "https://github.com/Farisarditiyanto/mesin-bahts/releases/download/v0.0.1/" + FONT)
FONT_SHA256 = "aa68bffce289b4c0ebac68e90502eb69e42356abcd1603cb2b8e99c2c723f145"
BUTUH_WORD = "`rakit` butuh Windows + Microsoft Word."
SAMPUL_SAYA = AKAR / "sampul_saya.txt"  # data sampul pemakai (@kunci: nilai); mengisi @kunci yang kosong di naskah baru
DATA_DIRI = ("nama", "nim", "jenis", "fasl", "thalibah", "sampul")  # milik satu orang (sampul = kampusnya): tidak disalin dari SAMPUL_SAYA ke bahts/<orang>/…
NAMA_FOLDER = r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+){0,2}"  # nama folder bahts yang diterima `baru`: «ikhlas» atau «bahts/<orang>/<topik>»
BUKAN_BAHTS = {"mesin", "kitab"}
PUSTAKA = ("pyarrow", "pypdf", "fontTools", "rapidfuzz")  # nama modul; nama pemasangannya di requirements.txt


def siapkan():
    """Lengkapi yang tidak ikut repo: katalog kitab dan font mushaf. Aman diulang."""
    import hashlib
    import huruf, jaringan, layanan, shamela
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
        print(f"font mushaf: TIDAK dipasang (bukan Windows). `cek` tetap jalan; {BUTUH_WORD}")
    elif huruf.font_terpasang():
        print("font mushaf: sudah terpasang")
    else:
        huruf.pasang_font(f)
        print("font mushaf: dipasang")
    print("Siap. Bahts baru: " + perintah('baru <folder> "<judul>"'))


def periksa():
    """Apa yang sudah siap di komputer ini, dan perintah untuk tiap yang belum. Tidak mengubah apa pun."""
    import importlib.util, sysconfig
    import diagram, huruf, layanan, shamela
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
    baris(bool(importlib.util.find_spec("pymupdf")), "pustaka Python pymupdf (untuk gambar PNG scan Waqfeya di "
          "`halaman w…` dan grid visual `pratinjau`; tanpa itu scan dibuka sebagai PDF)", pip, untuk_cek=False, untuk_rakit=False)
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
        # huruf tiap profil format.json (matan dan judul); yang wajib hanya huruf profil bahts baru (@format di kerangka naskah)
        format_ = profil_format()
        m = re.search(r"^@format:[ \t]*(\S+)", (MESIN / "naskah_baru.txt").read_text(encoding="utf8"), re.M)
        wajib = format_[m.group(1) if m else "imam"]["huruf"]
        semua_huruf = dict.fromkeys(h for p in format_.values() for h in (p["huruf"], p.get("huruf_judul")) if h)
        for h in semua_huruf:
            profil = [k for k, p in format_.items() if h in (p["huruf"], p.get("huruf_judul"))]
            baris(huruf.huruf_ada(h), f"huruf {h}" + ("" if h == wajib else f" (hanya untuk @format {', '.join(profil)})"),
                  huruf.HURUF_SARAN, untuk_cek=False, untuk_rakit=h == wajib)
    baris(bool(diagram.npx() and diagram.browser()), "Node.js + Chrome/Edge (hanya untuk `diagram`: Mermaid jadi PNG)",
          f"pasang {diagram.PASANG_NODE} dan {diagram.PASANG_BROWSER}; "
          "tanpa keduanya diagram tetap bisa dicetak dari PNG yang dibuat di tempat lain", untuk_cek=False, untuk_rakit=False)
    print(f"\nMenulis dan `cek`: {'SIAP' if siap_cek else 'BELUM'}.  `rakit` (Word + PDF): {'SIAP' if siap_rakit else 'BELUM'}.")
    print("WSL tidak diperlukan. Connector shamela: wajib; connector lain ikut dipasang lewat agent (dok/pemakai-baru.md langkah 4-5).")
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
    import difflib
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
        lama = sorted(f.parent.glob("*/naskah.txt"), key=lambda x: x.stat().st_mtime)
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
    sub = SUBJUDUL.match(judul.strip())  # pemisah yang sama dengan olah.rencana_cetak
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
            import olah
            dirujuk, dirujuk_w = olah.kitab_dirujuk(f)
            print(f"{f.name}: {len(dirujuk) + len(dirujuk_w)} kitab dirujuk naskahnya")
            sid += dirujuk; ww += dirujuk_w; continue
        sid.append(x)
    gagal = (bukan_folder
             + (_mod("shamela").ambil(*dict.fromkeys(sid)) if sid else [])
             + (_mod("waqfeya").ambil(*dict.fromkeys(ww)) if ww else []))
    if gagal:
        sys.exit(f"Belum terunduh: {', '.join(gagal)} (lihat pesan di atas).")


@dataclass(frozen=True)
class Bendera:
    """Satu bendera perintah. Yang bernilai (`kurang` terisi) memakai argumen sesudahnya sebagai nilainya."""
    nama: str
    kurang: str = ""  # pesan kalau nilainya tidak ada; kosong = bendera tanpa nilai
    bukan_nilai: Callable[[str], bool] = lambda x: False  # argumen sesudahnya yang tidak diterima sebagai nilai
    ganda: str = ""  # pesan kalau disebut dua kali; kosong = sebutan kedua dibaca sebagai argumen biasa


POTONGAN = Bendera("--potongan", ganda="--potongan disebut lebih dari sekali")  # frasa boleh cocok di tengah kata
JEJAK = Bendera("--jejak", ganda="--jejak disebut lebih dari sekali")
FASL = Bendera("--fasl", "--fasl perlu nomor #F, mis. --fasl 2")
KE = Bendera("--ke", "--ke perlu nama folder", lambda x: x.startswith("--"))
SARING = tuple(Bendera(n, f"{n} butuh nilai, mis. {n} {contoh}", lambda x: not x.strip(" ,،"),
                       f"{n} disebut dua kali; nilai ganda ditulis dengan koma, mis. {n} {contoh},…")
               for n, contoh in (("--mazhab", "hanbali"), ("--kitab", "8370"), ("--halaman", "2")))
DIRASAT_BENDERA = tuple(
    Bendera(n, f"{n} butuh nilai, mis. {n} {contoh}", lambda x: x.startswith("--") or not x.strip(),
            f"{n} disebut lebih dari sekali")
    for n, contoh in (("--dari", "2020"), ("--sampai", "2025"), ("--bahasa", "ar"), ("--urut", "terbaru"))
)


def urai(a, sah):
    """Pengurai bendera semua perintah: tiap argumen jadi (nama bendera tanpa «--», nilai) atau (None, argumen), menurut
    urutan ketikannya. Bendera boleh di mana saja; yang salah pakai = ValueError saat sampai di situ."""
    sah, a, tersebut = {b.nama: b for b in sah}, list(a), set()
    while a:
        x = a.pop(0)
        b = sah.get(x)
        if b is None or (x in tersebut and not b.ganda):
            yield None, x
        elif not b.kurang:
            if x in tersebut:
                raise ValueError(b.ganda)
            tersebut.add(x)
            yield x[2:], True
        else:
            if not a or b.bukan_nilai(a[0]):
                raise ValueError(b.kurang)
            if x in tersebut:
                raise ValueError(b.ganda)
            tersebut.add(x)
            yield x[2:], a.pop(0)


def pisah(a, sah):
    """`urai` sampai habis: (argumen biasa, {bendera: nilai})."""
    urut = list(urai(a, sah))
    return [x for n, x in urut if n is None], {n: x for n, x in urut if n}


def bendera_temukan(frasa, a):
    """Argumen `turath.temukan` dari `temukan "<frasa>" [maks] [--mazhab m,…] [--kitab id,…] [--halaman n]`."""
    maks, saring = 20, {"mazhab": "", "kitab": "", "halaman": "1"}
    for nama, nilai in urai(a, PERINTAH["temukan"].bendera):
        if nama:
            saring[nama] = nilai
        elif nilai.startswith("--"):
            raise ValueError(f"bendera «{nilai}» tidak dikenal")
        else:
            maks = angka(nilai, "maks")
    daftar = lambda s: [x.strip() for x in s.replace("،", ",").split(",") if x.strip()]
    return frasa, maks, daftar(saring["mazhab"]), daftar(saring["kitab"]), angka(saring["halaman"], "halaman")


def halaman(sid, juz, hal):
    """`halaman` satu halaman atau rentang «10-14» (angka Arab boleh): agent tidak perlu memanggilnya berkali-kali."""
    import shamela
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


def _cari_waqfeya(a, k):
    if k:
        raise ValueError("perintah «cari w…» tidak memakai bendera --potongan")
    import waqfeya
    return waqfeya.cari(a[0], a[1])


def wq(x):
    """Argumen nomor kitab Waqfeya («w» + huruf), bukan nomor Shamela."""
    return str(x).startswith("w") and len(str(x)) > 1


def ketemu(n):
    """Pencarian yang kosong keluar dengan kode 1, supaya skrip/agent tahu tanpa membaca pesannya."""
    if not n:
        sys.exit(1)


def perintah_cek(a):
    """`cek <folder> [--jejak]`: bendera boleh sebelum/sesudah folder; bendera saja = kurang argumen."""
    folder, k = pisah(a, PERINTAH["cek"].bendera)
    bentuk = PERINTAH["cek"].bantuan().split("\n")[0]
    if not folder:
        sys.exit(f"Perintah «cek» kurang argumen. Bentuknya:\n  {bentuk}")
    if len(folder) != 1 or folder[0].startswith("--"):
        sys.exit(f"Argumen perintah «cek» tidak dikenal atau berlebih: {a}\nBentuknya:\n{bentuk}")
    sys.exit(1 if cek(folder[0], jejak="jejak" in k) else 0)


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


def perintah_peta(a):
    """`peta <folder>`: peta struktur, sijil sumber/mazhab, busur argumen, hadits, dan `terima` (lihat peta.cetak)."""
    import peta
    peta.cetak(folder_bahts(a[0]))


def perintah_edisi(a):
    """`edisi <kueri|sid|w…> [pengarang]`: rekonsiliasi edisi lintas katalog Shamela & Waqfeya (lihat edisi.cetak)."""
    import edisi, waqfeya
    ketemu(edisi.cetak(a[0], a[1] if len(a) > 1 else "", wq=waqfeya))


def perintah_pustaka(a):
    """`pustaka <folder>`: susun draf `#R` dari kitab berbukti di catatan kaki (lihat pustaka.cetak)."""
    import pustaka
    pustaka.cetak(folder_bahts(a[0]))


def perintah_tahap(a):
    """`tahap <folder>`: keadaan bahts dibaca ulang dari barang aslinya; mesin keadaannya di tahap.py. Folder bahts dan
    bahan `cek` di mesin/_tmp tidak disentuh."""
    import tahap
    print("\n".join(tahap.baris(tahap.baca(folder_bahts(a[0]), jalur_ketik(a[0])))))


def perintah_rakit(a):
    """`rakit <folder> [--fasl n]`: bendera boleh sebelum/sesudah folder. Alurnya di rakit.py."""
    a, k = pisah(a, PERINTAH["rakit"].bendera)
    if len(a) != 1 or a[0].startswith("--"):
        raise ValueError(f"argumen tidak dikenal atau berlebih: {a}")
    if os.name != "nt":
        galat = cek(a[0])
        sys.exit(f"Belum dirakit: {galat} galat harus beres dulu." if galat else
                 f"{BUTUH_WORD} Naskahnya sudah lolos `cek`.")
    import rakit
    rakit.rakit(folder_bahts(a[0]), jalur_ketik(a[0]), k.get("fasl"))


def perintah_pratinjau(a):
    """`pratinjau <folder> [halaman]`: halaman PDF hasil `rakit` jadi gambar PNG grid 2×2 di TEMP, untuk pemeriksa."""
    import pratinjau
    pratinjau.render(folder_bahts(a[0]), jalur_ketik(a[0]), *a[1:])


def perintah_ekspor(a):
    """`ekspor <id|w…> [...] [--ke <folder>]`: --ke boleh di mana saja."""
    import ekspor
    a, k = pisah(a, PERINTAH["ekspor"].bendera)
    if not a or any(x.startswith("--") for x in a):
        raise ValueError(f"argumen tidak dikenal atau kurang: {a}")
    ekspor.ekspor(a, Path(k["ke"]) if "ke" in k else Path.home() / "Downloads")


def perintah_dirasat(a, **k):
    """`dirasat "<kata kunci|W…|DOI>" [maks] [saringan] [--dari t] [--sampai t] [--bahasa b] [--urut u]`."""
    for x in a:
        if x.startswith("--"):
            raise ValueError(f"bendera «{x}» tidak dikenal")
    import dirasat
    dirasat.cari(a[0], *(angka(x, "maks") for x in a[1:2]), *a[2:], **k)


KOLOM = 29  # lebar kolom bentuk di teks bantuan


@dataclass(frozen=True)
class Perintah:
    """Satu baris tabel perintah: yang dicetak bantuan dan yang dijalankan pintu CLI."""
    bentuk: str  # seperti diketik: nama perintah, lalu argumennya
    uraian: str  # antarbaris "\n"; diawali "\n" = uraian mulai di baris sesudah bentuk
    jalankan: Callable | None = None  # None = bentuk lain perintah yang sudah punya baris: hanya bantuan
    paling_sedikit: int = 0  # jumlah argumen
    paling_banyak: int | None = 0  # None = penangannya sendiri yang memisah bendera (`pisah`) dan memeriksa sisanya
    bendera: tuple = ()

    @property
    def nama(self):
        return self.bentuk.split()[0]

    def bantuan(self):
        awal, *lanjut = self.uraian.split("\n")
        kepala = self.bentuk if not awal else self.bentuk.ljust(KOLOM) if len(self.bentuk) < KOLOM else self.bentuk + "   "
        return "\n".join(["  " + kepala + awal] + [" " * (KOLOM + 2) + x for x in lanjut])


DAFTAR = (  # urutan dan judul kelompok = teks bantuan
    "Sekali sesudah mengunduh repo:",
    Perintah("periksa", "apa yang sudah siap di komputer ini, dan perintah untuk tiap yang belum",
             lambda a: periksa(), 0, 0),
    Perintah("siapkan", "unduh katalog kitab, tabel layanan (tafsir, takhrij, rawi, akar) + font mushaf, lalu pasang\n"
             "font itu (Windows)",
             lambda a: siapkan(), 0, 0),
    "Bahts (tiap bahts = satu folder berisi naskah.txt):",
    Perintah('baru <folder> "<judul>"', "buat folder bahts baru + kerangka naskah.txt; <folder> boleh bahts/<orang>/<topik>",
             lambda a: baru(a[0], a[1]), 2, 2),
    Perintah("cek <folder> [--jejak]", "periksa naskah: tanda, ayat, dan semua bukti <<...>> ke kitab lokal;\n"
             "--jejak: teks yang tidak ada di kitabnya dicari di kitab lain yang sudah diunduh",
             perintah_cek, 0, None, (JEJAK,)),
    Perintah("bukti <folder> [baris|awal-akhir]", "untuk pemeriksa: tiap catatan kaki berbukti <<sid|juz|hal>>, <<w…>>, atau\n"
             "<<luar|berkas.pdf|hal>> (kalimat yang dibuktikan, isi catatan kaki, nama kitab/PDF, bab,\n"
             "dan teks halaman itu di sekitar kutipan) dan teks tiap ayat {Q:} persis seperti tercetak,\n"
             "juga tiap paragraf isi tanpa catatan kaki (untuk dinilai: penisbatan tanpa sumber); tiap\n"
             "baris keluaran diawali «baris n». Penunjuk saja, putusan tetap `cek`",
             perintah_bukti, 1, 2),
    Perintah("peta <folder>", "ringkasan opsional untuk penulis dan pemeriksa, tanpa internet:\n"
             "struktur dan jumlah kata/catatan kaki, daftar sumber dan inventaris kitab mazhab,\n"
             "busur argumen (المقدمة ↔ الترجيح/الخلاف ↔ الخاتمة), daftar {H:…}, dan semua `terima` riset.txt",
             perintah_peta, 1, 1),
    Perintah("pustaka <folder>", "susun draf baris #R (المصادر والمراجع) siap tempel langsung dari `kartu` kitab berbukti\n"
             "di catatan kaki (sesuai @pustaka_gaya, tanpa gelar, urut abjad, tanpa internet), sekaligus\n"
             "menunjukkan data cetak yang cocok dan judul yang edisinya perlu dicek",
             perintah_pustaka, 1, 1),
    Perintah("rakit <folder> [--fasl n]", "cek, lalu rakit .docx + .pdf (Word) ke dalam folder itu; --fasl 2 (atau 1-2): hanya #F\n"
             "ke-2, untuk bahts yang dikumpulkan bertahap per فصل (lihat `tanda`); `cek` tetap\n"
             "memeriksa seluruh naskah",
             perintah_rakit, 1, None, (FASL,)),
    Perintah("tahap <folder>", "tahap bahts sekarang dan satu langkah berikutnya: naskah (GAGAL/PERHATIAN/LOLOS), hasil\n"
             "rakit (BELUM/TERKINI/USANG, juga tiap --fasl), rakit yang sedang jalan, folder .rakit-*\n"
             "dan _arsip/rakit-*. Folder bahts tidak disentuh; untuk sesi baru yang tidak tahu bahts\n"
             "ini sampai mana",
             perintah_tahap, 1, 1),
    Perintah("tanda", "daftar tanda yang dipakai di naskah.txt",
             lambda a: print(tanda()), 0, 0),
    Perintah("diagram <folder>", "tiap diagram Mermaid <nama>.mmd di folder itu jadi <nama>.png (butuh Node.js + Chrome/Edge),\n"
             "lalu dicetak dengan «#G <nama>.png | keterangan»; `cek` dan `rakit` hanya memakai PNG-nya",
             lambda a: sys.exit(1 if _mod("diagram").render(folder_bahts(a[0])) else 0), 1, 1),
    Perintah("pratinjau <folder> [halaman]", "halaman PDF hasil `rakit` jadi gambar PNG grid 2×2 di TEMP (atau 1 halaman penuh,\n"
             "mis. «1» atau «1-4»), untuk pemeriksaan tata letak visual (sampul, tabel #J, gambar #G, rumus #E)",
             perintah_pratinjau, 1, 2),
    "Kitab (perpustakaan Shamela lokal, dipakai semua bahts):",
    Perintah("kitab", "daftar kitab yang sudah diunduh",
             lambda a: _mod("shamela").daftar(), 0, 0),
    Perintah('katalog "<pola>"', "cari judul/pengarang di katalog Shamela (regex)",
             lambda a: ketemu(_mod("shamela").katalog(pola(a[0]))), 1, 1),
    Perintah('edisi "<judul|id|w…>" [pengarang]', "cari kandidat cetakan di Shamela dan Waqfeya tanpa internet: pisahkan\n"
             "riwayat lain serta karya terkait (شرح/مختصر/حاشية), dan jembatani\n"
             "judul alternatif («تفسير القرطبي» ↔ «الجامع لأحكام القرآن») dengan filter pengarang anti-kerabat/nisbah",
             perintah_edisi, 1, 2),
    Perintah('temukan "<frasa>" [maks] [--mazhab m,…] [--kitab id,…] [--halaman n]', "\n"
             "cari frasa di isi SEMUA kitab Shamela (turath.io, butuh internet) -> kitab + juz/halaman; 20 hasil\n"
             "tiap halaman. --mazhab: hanya kitab fikih mazhab itu; --kitab: hanya kitab itu, walau belum\n"
             "diunduh; --halaman 2: hasil ke-21 dan seterusnya",
             lambda a: ketemu(_mod("turath").temukan(*bendera_temukan(a[0], a[1:]))), 1, None, SARING),
    Perintah("ambil <id|folder> [...]", "unduh kitab (sekali saja); nama folder bahts = semua kitab yang dirujuk naskahnya",
             ambil, 1, None),
    Perintah("kartu <id>", "data cetak kitab (untuk rujukan pertama & daftar pustaka) + bentuk bukti <<…>> kitab itu",
             lambda a: _mod("waqfeya").kartu(a[0]) if wq(a[0]) else _mod("shamela").kartu(a[0]), 1, 1),
    Perintah('cari <id|semua> "<frasa>" [--potongan]', "\n"
             "cari frasa -> juz/halaman cetak; semua: paling banyak 40 baris, lalu jumlah kitab yang cocok.\n"
             "Frasa dicocokkan sebagai kata utuh (huruf sambung و ف ب ل ك dan «ال» di depan kata pertama\n"
             "boleh): «العربان» tidak cocok dengan «العرب ان». Yang hanya cocok sebagai potongan kata\n"
             "disebut jumlahnya; --potongan: ikut ditampilkan (mis. mencari awal kata)",
             lambda a, **k: ketemu(_cari_waqfeya(a, k) if wq(a[0]) else _mod("shamela").cari(a[0], a[1], **k)), 2, 2, (POTONGAN,)),
    Perintah('teks <id> "<frasa>" [lebar] [maks] [--potongan]', "teks asli di sekitar frasa, untuk disalin persis",
             lambda a, **k: ketemu(_mod("shamela").teks(a[0], a[1], *(angka(x, apa) for x, apa in zip(a[2:], ("lebar", "maks"))), **k)), 2, 4, (POTONGAN,)),
    Perintah('bab <id> "<frasa>" [--potongan]', "rantai judul kitab/bab tempat frasa berada",
             lambda a, **k: ketemu(_mod("shamela").bab(a[0], a[1], **k)), 2, 2, (POTONGAN,)),
    Perintah("halaman <id> <juz> <hal>", 'isi satu halaman (juz "-" untuk kitab satu jilid); <hal> boleh rentang, mis. 10-14\n'
             "(paling banyak 20 halaman sekali panggil)",
             lambda a: ketemu(_mod("waqfeya").halaman(*a) if wq(a[0]) else halaman(*a)), 3, 3),
    Perintah("scan <id> <juz> <hal>", "alamat scan cetakan halaman itu (PDF di turath.io, butuh internet), untuk bacaan yang meragukan",
             lambda a: ketemu(_mod("turath").scan(*a)), 3, 3),
    Perintah("ekspor <id|w…> [...] [--ke <folder>]", "seluruh kitab jadi satu .txt (satu paragraf satu baris, judul bab «#»,\n"
             "penanda juz/halaman, حاشية sesudah halamannya); yang belum diunduh diunduh dulu.\n"
             "Bawaan ke folder Downloads; nama berkas = judul kitab. Bukan bahan bahts",
             perintah_ekspor, 1, None, (KE,)),
    "Kitab Waqfeya (scan cetakan + OCR, untuk kitab yang tidak ada di Shamela; disimpan di kitab/waqfeya, dipakai semua bahts):",
    Perintah('waqfeya "<judul/pengarang>" [maks]', "cari di katalog Waqfeya (±10.000 kitab) -> nomor w… (diunduh sekali, ±17 MB)",
             lambda a: ketemu(_mod("waqfeya").cari_katalog(a[0], *(angka(x, "maks") for x in a[1:]))), 1, 2),
    Perintah("ambil w<nomor> [...]", "unduh OCR + PDF scan kitab itu (sekali saja)"),
    Perintah("kartu w<nomor>", "data katalog + OCR halaman judul (data cetak disalin dari scan-nya) + bentuk bukti"),
    Perintah('cari w<nomor> "<frasa>"', "halaman PDF yang OCR-nya memuat frasa; tidak ada yang persis -> yang paling mirip"),
    Perintah("halaman w<nomor> <berkas> <hal>", "teks OCR halaman PDF ke-hal di berkas itu + nomor cetak yang terbaca + PDF/PNG scan-nya.\n"
             "OCR bisa salah huruf: lafaz dan juz/halaman cetak disalin dari scan, bukti <<w…|berkas|hal>>"),
    "Layanan Shamela (penunjuk jalan tanpa internet, dari dataset yang sama dengan `ambil`):",
    Perintah("tafsir <surat:ayat[-ayat]>", "kitab tafsir yang menafsirkan ayat itu (14 kitab, mis. الطبري، ابن كثير، زاد المسير) +\n"
             "juz/halaman cetak awal pembahasannya, urut dari pengarang yang lebih dulu wafat",
             lambda a: ketemu(_mod("layanan").tafsir(a[0])), 1, 1),
    Perintah("takhrij <id> <juz> <hal>", "hadits di halaman itu ada juga di mana: 8 kitab (البخاري، مسلم، أبو داود، الترمذي، النسائي،\n"
             "الموطأ، الطيالسي، ابن الجارود) + juz/halaman dan nomor haditsnya; edisi lain kitab itu\n"
             "(mis. مسلم 1727) lewat nomor hadits, dengan edisi yang dipakai Shamela (mis. 711) sebagai jembatan",
             lambda a: ketemu(_mod("layanan").takhrij(*a)), 3, 3),
    Perintah("rawi <id> <juz> <hal>", "sanad tiap hadits di halaman itu, berurutan dari pengarang (layanan sanad Shamela di 8 kitab\n"
             "hadits; edisi lain lewat jembatan nomor hadits) + rutbah ringkas: ابن حجر، الذهبي، wafat",
             lambda a: ketemu(_mod("layanan").rawi(*a)) if len(a) != 2 else sys.exit(
                 "Perintah «rawi»: tulis <id> <juz> <hal>, satu nomor rawi, atau satu nama dalam tanda petik."), 1, 3),
    Perintah('rawi <nomor> | rawi "<nama>"', "ucapan جرح وتعديل rawi itu + tempat lafaznya di edisi lokal kitab rijal sumbernya (dicari ulang,\n"
             "bukan juz/halaman tabel); dengan nama: cari nomor rawinya"),
    Perintah('akar <id> "<akar>"', "bentuk kata berakar itu di kitab (kamus akar Shamela) + jumlahnya, dikelompokkan seperti\n"
             "`cari` mencocokkan kata: istilah yang tidak tertangkap frasa («الشفيع» untuk شفع)",
             lambda a: ketemu(_mod("layanan").akar(*a)), 2, 2),
    "Takhrij (penunjuk jalan, «المنصة الحديثية», butuh internet):",
    Perintah('hadits "<طرف>" [maks]', "tempat hadits di 12 kitab hadits + hukum ulama; tetap dibaca di kitabnya sendiri. Kitab yang\n"
             "sudah diunduh: juz/halaman edisi lokal ikut dicetak (juz/halaman layanan bisa edisi lain)",
             lambda a: ketemu(_mod("hadits").cari(a[0], *(angka(x, "maks") for x in a[1:]))), 1, 2),
    "Penelitian terdahulu (الدراسات السابقة, katalog OpenAlex dan DOAJ, butuh internet):",
    Perintah('dirasat "<kata kunci|W…|DOI>" [maks] [saringan] [--dari t] [--sampai t] [--bahasa b] [--urut u]', "\n"
             "judul, peneliti, tahun, jurnal (+ jilid/nomor/halaman), tautan, dan ringkasan; dicari menurut kata\n"
             "dan makna. --dari/--sampai (tahun atau YYYY-MM-DD), --bahasa (ar/en), --urut (terbaru/terlama/dikutip)\n"
             "berlaku di OpenAlex dan DOAJ. Nomor W… atau DOI = tampilkan rincian + ringkasan utuh satu penelitian",
             perintah_dirasat, 1, 3, DIRASAT_BENDERA),
    Perintah("dirasat-pdf <W…|DOI> <folder>", "unduh PDF penelitian (nomor OpenAlex W… atau DOI) ke folder bahts;\n"
             "coba salinan OpenAlex (butuh kunci), lalu otomatis jatuh ke tautan PDF akses terbuka bila ada",
             lambda a: _mod("dirasat").pdf(a[0], folder_bahts(a[1])), 2, 2),
    Perintah("dirasat-cek <folder>", "periksa DOI dan nomor OpenAlex (W…) secara online; tampilkan rekaman, status\n"
             "pencabutan dan petunjuk metadata per baris. Kode 1: ID tidak ditemukan/karya dicabut;\n"
             "kode 2: metadata perlu dicek atau layanan gagal; kode 0: tidak ada temuan.",
             lambda a: sys.exit(_mod("dirasat").cek_rujukan(folder_bahts(a[0]))), 1, 1),
)
PERINTAH = {p.nama: p for p in DAFTAR if isinstance(p, Perintah) and p.jalankan}


def bantuan():
    """Teks bantuan seluruhnya: tiap judul kelompok dan baris DAFTAR."""
    return "Satu pintu mesin bahts:  python mesin/bahts.py <perintah>\n" + "".join(
        f"\n{x}\n" if isinstance(x, str) else x.bantuan() + "\n" for x in DAFTAR)


def tanda():
    """Daftar tanda naskah: ditulis sekali di olah.py (pintu `cek`; penguraiannya di naskah.py), dicetak dari sana."""
    import olah
    return olah.TANDA


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")  # pesan galat memuat «» dan huruf Arab; konsol Windows tidak bisa mencetaknya
    cmd, *a = sys.argv[1:] or [""]
    if cmd in ("", "-h", "--help", "bantuan"):
        print(bantuan()); sys.exit(0)
    if cmd not in PERINTAH:
        import difflib
        mirip = difflib.get_close_matches(cmd, PERINTAH, n=1)
        sys.exit(f"Perintah «{cmd}» tidak dikenal." + (f" Maksudnya «{mirip[0]}»?" if mirip else "")
                 + "\nDaftar perintah: " + perintah(""))
    p = PERINTAH[cmd]
    bentuk = p.bantuan()
    k = {}
    try:
        if p.paling_banyak is not None:  # bendera boleh di mana saja; tidak dihitung sebagai argumen
            a, k = pisah(a, p.bendera)
        if len(a) < p.paling_sedikit:
            sys.exit(f"Perintah «{cmd}» kurang argumen. Bentuknya:\n{bentuk}")
        if p.paling_banyak is not None and len(a) > p.paling_banyak:
            # argumen berlebih ditolak, bukan ditelan: `halaman 1679 - 8 9` jangan diam-diam mengabaikan 9
            bendera = [x for x in a if x.startswith("--")]
            sys.exit(f"Argumen perintah «{cmd}» tidak dikenal atau berlebih: {a[p.paling_banyak:]}"
                     + (f" (perintah «{cmd}» tidak punya bendera {', '.join(bendera)})" if bendera else "")
                     + f"\nBentuknya:\n{bentuk}")
        p.jalankan(a, **k)
    except MemoryError:
        sys.exit(f"Perintah '{cmd}': memori komputer habis. Tutup aplikasi lain, lalu ulangi.")
    except BrokenPipeError:  # keluarannya dipotong pembaca (mis. `| head`): bukan masalah internet
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    except TimeoutError:
        sys.exit(f"Perintah '{cmd}': layanannya terlalu lama menjawab. Ulangi sebentar lagi.")
    except (ValueError, FileNotFoundError, re.error) as e:
        sys.exit(f"Perintah '{cmd}' salah pakai: {e}\nBentuknya:\n{bentuk}")
    except _http_error() as e:
        if not 400 <= e.code < 500 or e.code == 429:
            sys.exit(f"Perintah '{cmd}': layanannya sedang menolak atau sibuk (HTTP {e.code}). Ulangi sebentar lagi.")
        sys.exit(f"Perintah '{cmd}': layanannya menolak permintaan ini (HTTP {e.code}). Periksa kata/angka yang diketik: {a}")
    except _gagal_jaringan() as e:
        sys.exit(f"Perintah '{cmd}' gagal mengunduh (cek internet, lalu ulangi): {e!r}")
