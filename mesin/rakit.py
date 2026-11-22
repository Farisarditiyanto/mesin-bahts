# SPDX-License-Identifier: AGPL-3.0-or-later
"""Alur `rakit` sisi Python: satu rakit sekali jalan (kunci), folder kerja .rakit-*, `cek`, rakit.ps1 (Word), pemeriksaan
hasil, lalu pemasangan hasil dengan cadangan. Kunci, folder kerja, dan cadangan dibaca juga oleh `tahap`."""
import hashlib, os, re, shutil, subprocess, sys, tempfile, time, zipfile
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import NamedTuple

import dasar, huruf, olah, produk, teks_pdf
from berkas import sementara
from dasar import perintah

MESIN = Path(__file__).resolve().parent
AKAR = MESIN.parent
KELUARAN_SAYA = AKAR / "keluaran_saya.txt"  # opsional, satu baris: folder tempat `rakit` menaruh salinan PDF
ANTRE = 30 * 60  # detik; rakit terlama yang tercatat ±10 menit: dua rakit di depan masih tertampung
PEKERJAAN = MESIN / "_tmp" / "rakit.pekerjaan"  # kunci seluruh pekerjaan rakit (`kunci`): satu rakit sekali jalan
PS_KUNCI = MESIN / "_tmp" / "rakit.kunci"  # dibuka rakit.ps1 tanpa berbagi selama ia hidup (dilepas OS saat mati)
GALAT = "rakit.galat"  # di folder kerja: pesan galat rakit.ps1 (UTF-8), ditulis sebelum PowerShell berhenti


class Pemegang(NamedTuple):
    """Pemegang kunci rakit, dari byte sesudah byte kunci. Ketiganya None = pemegang belum sempat menulis, atau kunci
    versi lama tanpa keterangan."""
    apa: str | None = None  # yang dirakit (nama_kunci)
    pid: str | None = None
    mulai: float | None = None  # time.time() saat kunci dipegang

    def kalimat(self):
        """«bahts/a/b, proses 123, mulai 19:19 (3 menit lalu)»; kosong kalau tidak tercatat."""
        if self.mulai is None:
            return ""
        menit = int((time.time() - self.mulai) // 60)
        return f"{self.apa}, proses {self.pid}, mulai {time.strftime('%H:%M', time.localtime(self.mulai))} ({menit} menit lalu)"


def _pemegang(h):
    h.seek(1)
    try:
        pid, mulai, apa = h.read(1000).decode("utf8").split("|", 2)
        mulai = float(mulai)
        time.localtime(mulai)  # jam yang tidak sah = tidak tercatat
        return Pemegang(apa, pid, mulai)
    except (OSError, ValueError):
        return Pemegang()


def _pegang(h):
    h.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(h.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _lepas(h):
    h.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(h.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(h, fcntl.LOCK_UN)


def lihat_kunci(f):
    """None = bebas; Pemegang = dipegang. Tidak membuat berkas atau menulis metadata pemegang.

    Probe memakai kunci OS yang sama dengan `kunci`, lalu langsung melepasnya. Probe bersamaan boleh melihat probe
    lain sesaat, tetapi tidak pernah menulis identitas rakit palsu atau menghapus metadata pemegang terakhir.
    """
    try:
        h = open(f, "rb")
    except FileNotFoundError:
        return None
    with h:
        try:
            _pegang(h)
        except OSError:
            return _pemegang(h)
        _lepas(h)
    return None


@contextmanager
def kunci(f, tunggu=0, apa=""):
    """Kunci antarproses yang dilepas OS saat proses mati, meliputi seluruh pekerjaan rakit.
    Sedang dipegang proses lain: antre sampai `tunggu` detik (rakit dari beberapa sesi jalan bergiliran).
    Pemegang menulis `apa` (mis. folder bahts), nomor prosesnya, dan jam mulainya sesudah byte kunci; yang antre
    menyebutnya, supaya rakit yang masih bekerja tidak disangka macet lalu dimatikan."""
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a+b") as h:
        if not h.tell():
            h.write(b"\0"); h.flush()
        batas, kabar = time.monotonic() + tunggu, None
        while True:
            try:
                _pegang(h)
                break
            except OSError:
                siapa = _pemegang(h).kalimat()
                if time.monotonic() >= batas:
                    raise RuntimeError(f"Rakit lain sedang jalan{f' ({siapa})' if siapa else ''}: tunggu sampai selesai, "
                                       "lalu ulangi.") from None
                if siapa != kabar:  # sekali per pemegang: rakit berikutnya yang mendapat giliran disebut lagi
                    lama = f"{tunggu // 60} menit" if tunggu >= 60 else f"{tunggu} detik"
                    print(f"Rakit lain sedang jalan (memakai Word yang sama){f': {siapa}' if siapa else ''}; menunggu "
                          f"giliran (paling lama {lama}). Jangan matikan rakit itu: ia masih bekerja.", flush=True)
                    kabar = siapa
                time.sleep(2)
        h.truncate(1)  # mode a: tulisan selalu masuk di akhir berkas, jadi tepat sesudah byte kunci
        h.write(f"{os.getpid()}|{time.time()}|{apa}".encode("utf8")); h.flush()
        try:
            yield
        finally:
            h.truncate(1)
            _lepas(h)


class FolderKerja:
    """Folder kerja .rakit-* di folder bahts. Keadaannya hanya dibaca dari berkas penanda di dalamnya, di sini saja:
      SEMENTARA  bahan sementara rakit versi ini (penanda SEMENTARA)       -> dibuang sendiri oleh rakit berikutnya
      SIMPAN     hasil baru yang belum terpasang (penanda SIMPAN, menang)  -> tidak pernah dibuang mesin
      ASING      tanpa penanda (rakit versi lama, atau dibuat tangan)       -> tidak pernah dibuang mesin
    Perpindahan: buat() -> SEMENTARA; simpan(): keadaan apa pun -> SIMPAN (hanya menambah perlindungan);
    buang(): hanya dari SEMENTARA, keadaan lain ditolak."""
    SEMENTARA = "rakit.sementara"
    SIMPAN = "JANGAN_DIHAPUS.txt"

    class Keadaan(Enum):
        SEMENTARA = "SEMENTARA"
        SIMPAN = "SIMPAN"
        ASING = "ASING"

    KETERANGAN = {
        Keadaan.SEMENTARA: "bahan sementara rakit; dibuang sendiri oleh rakit berikutnya (jangan dihapus selama rakit jalan)",
        Keadaan.SIMPAN: "hasil baru yang belum terpasang (pemulihan rakit gagal): selamatkan isinya, lalu hapus sendiri",
        Keadaan.ASING: "tanpa penanda atau berupa tautan folder: mungkin berisi hasil yang sengaja disimpan; "
                       "periksa isinya, lalu hapus sendiri",
    }

    def __init__(self, path):
        self.path = Path(path)

    @classmethod
    def buat(cls, folder):
        k = cls(tempfile.mkdtemp(prefix=".rakit-", dir=folder))
        (k.path / cls.SEMENTARA).write_text("Bahan sementara `rakit`; dibuang sendiri oleh rakit berikutnya.\n", encoding="utf8")
        return k

    @classmethod
    def semua(cls, folder):
        return [cls(p) for p in sorted(Path(folder).glob(".rakit-*")) if p.is_dir()]

    def keadaan(self):
        if self.path.is_symlink() or self.path.is_junction():
            return self.Keadaan.ASING  # penanda di tujuan tautan tidak memberi izin menghapus isi tujuan itu
        if (self.path / self.SIMPAN).exists():
            return self.Keadaan.SIMPAN
        penanda = self.path / self.SEMENTARA
        return self.Keadaan.SEMENTARA if penanda.is_file() and not penanda.is_symlink() else self.Keadaan.ASING

    def simpan(self):
        (self.path / self.SIMPAN).write_text("Hasil baru yang belum terpasang (pemulihan rakit gagal; lihat pesan rakit).\n"
                                             "`rakit` tidak membuang folder ini: selamatkan isinya, lalu hapus sendiri.\n",
                                             encoding="utf8")
        try:  # SIMPAN sudah melindunginya; penanda sementara dicabut supaya versi lain pun tidak membuangnya
            (self.path / self.SEMENTARA).unlink()
        except OSError:
            pass

    def buang(self):
        """Hapus folder SEMENTARA; True = sudah hilang, False = masih ada (berkas yang masih terbuka). Penandanya dibuang
        paling akhir: yang gagal dibuang sebagian tetap SEMENTARA (dicoba lagi rakit berikutnya), bukan jadi ASING."""
        k = self.keadaan()
        if k is not self.Keadaan.SEMENTARA:
            raise ValueError(f"{self.path.name} ({k.value}) bukan bahan sementara rakit: tidak dibuang")
        for isi in self.path.iterdir():
            if isi.name == self.SEMENTARA:
                continue
            if isi.is_symlink() or isi.is_junction():
                try:  # hanya tautannya yang dibuang, isi tujuannya tidak disentuh
                    os.rmdir(isi) if isi.is_dir() else isi.unlink()
                except OSError:
                    pass
            elif isi.is_dir():
                shutil.rmtree(isi, ignore_errors=True)
            else:
                try:
                    isi.unlink()
                except OSError:
                    pass
        if [x.name for x in self.path.iterdir()] == [self.SEMENTARA]:
            penanda = self.path / self.SEMENTARA
            try:
                penanda.unlink()
                self.path.rmdir()
            except OSError:
                # Windows bisa mengizinkan penghapusan isi, tetapi menahan direktori itu sendiri. Pertahankan
                # keadaan SEMENTARA agar rakit berikutnya mencoba lagi, termasuk saat semua isi sudah terhapus.
                if self.path.is_dir():
                    penanda.touch(exist_ok=True)
        return not self.path.exists()


ARSIP, CADANGAN = "_arsip", "rakit-"  # cadangan hasil lama selama `terbitkan`: <folder>/_arsip/rakit-*


def cadangan_tertinggal(folder):
    """Cadangan _arsip/rakit-* yang tertinggal: `terbitkan` membuangnya sendiri kalau berhasil atau pulih lengkap, jadi
    yang masih ada = PemulihanGagal, atau rakit yang dimatikan di tengah penggantian hasil."""
    arsip = Path(folder) / ARSIP
    return sorted(p.name for p in arsip.glob(CADANGAN + "*") if p.is_dir()) if arsip.is_dir() else []


class PemulihanGagal(RuntimeError):
    """Hasil lama belum bisa dipasang kembali: cadangan dan hasil baru sengaja ditinggalkan untuk diselamatkan."""


def terbitkan(kerja, folder, nama, buang=()):
    """Pindahkan SEMUA hasil lama (termasuk `buang`, mis. salinan khulasah usang) ke cadangan sebelum memasang hasil baru;
    pulihkan bila penggantian gagal. Berhasil = cadangan dibuang (semuanya bisa dirakit ulang dari naskah),
    supaya folder bahts tidak menumpuk satu cadangan tiap rakit. Rename berlaku per berkas, bukan transaksi
    atomik pasangan. Bila proses dimatikan di tengah, hasil dapat belum lengkap, tetapi hasil baru tidak
    dipasangkan dengan hasil lama.
    """
    arsip = folder / ARSIP
    arsip.mkdir(exist_ok=True)
    cadangan = Path(tempfile.mkdtemp(prefix=CADANGAN, dir=arsip))
    lama, baru = [], []
    try:
        for n in dict.fromkeys((*nama, *buang)):
            if (folder / n).exists():
                (folder / n).replace(cadangan / n)
                lama.append(n)
        for n in nama:
            (kerja / n).replace(folder / n)
            baru.append(n)
    except BaseException:
        gagal = []
        for n in reversed(baru):
            try:
                (folder / n).replace(kerja / n)
            except OSError as e:
                gagal.append(str(e))
        # Bila berkas baru terkunci, seluruh generasi lama tetap di cadangan: jangan
        # memasangkan DOCX baru yang belum bisa ditarik dengan PDF/laporan lama.
        if not gagal:
            for n in reversed(lama):
                try:
                    (cadangan / n).replace(folder / n)
                except OSError as e:
                    gagal.append(str(e))
        if gagal:
            raise PemulihanGagal(f"Pemulihan hasil belum lengkap. Cadangan: {cadangan}; hasil baru: {kerja}. " + "; ".join(gagal))
        _buang_cadangan(cadangan)  # pulih lengkap: cadangan sudah kosong
        raise
    _buang_cadangan(cadangan)


def _buang_cadangan(cadangan):
    shutil.rmtree(cadangan, ignore_errors=True)
    if not any(cadangan.parent.iterdir()):
        cadangan.parent.rmdir()


def kosongkan_penulis(docx):
    """Buang nama pengguna Word dari data penulis .docx; isi dokumen tidak disentuh."""
    with sementara(docx) as part:  # di Windows docx harus sudah tertutup saat diganti
        with zipfile.ZipFile(docx) as z, zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as o:
            for i in z.infolist():
                isi = z.read(i.filename)
                if i.filename == "docProps/core.xml":
                    isi = re.sub(rb"(<(dc:creator|cp:lastModifiedBy)\b[^>/]*>).*?(</\2>)", rb"\1\3", isi, flags=re.S)
                o.writestr(i, isi)


def nama_kunci(folder):
    """Nama bahts yang ditulis pemegang kunci rakit: jalur foldernya dari folder mesin."""
    return Path(folder).resolve().relative_to(AKAR).as_posix()


def milik(pemegang, folder):
    """Pemegang kunci rakit itu rakit bahts di `folder`?"""
    return pemegang.apa is not None and os.path.normcase(pemegang.apa) == os.path.normcase(nama_kunci(folder))


def rakit(f, jalur, fasl=None):
    """Rakit bahts di folder `f` (fasl: hanya potongan --fasl itu). jalur = bahts seperti diketik pemakai, untuk
    perintah yang disarankan."""
    try:
        with kunci(PEKERJAAN, tunggu=ANTRE, apa=nama_kunci(f)):
            _tunggu_ps_yatim()
            _rakit(f, jalur, fasl)
    except PermissionError as e:  # hasil lama (atau yang baru) sedang dibuka aplikasi lain; hasil lama tetap utuh
        sys.exit(f"Perakitan GAGAL: {Path(e.filename or '').name or 'hasil'} sedang terbuka di aplikasi lain (Word "
                 f"atau pembaca PDF). Tutup dulu, lalu ulangi `rakit`. Hasil lama tidak berubah.")
    except Exception as e:  # noqa: BLE001 — gerbang CLI teratas: lapor galat ringkas lalu keluar non-nol
        sys.exit(f"Perakitan GAGAL: {type(e).__name__}: {e}")


def _tunggu_ps_yatim():
    """rakit.ps1 milik rakit yang dimatikan (Python-nya mati, PowerShell-nya belum) masih memakai Word dan folder
    kerjanya: tunggu sampai ia berhenti sendiri, supaya Word tidak dipakai berdua dan foldernya tidak dibuang saat masih
    ditulisi. Word-nya dibereskan rakit.ps1 itu sendiri (atau rakit.ps1 berikutnya, lewat catatan Word yatim)."""
    batas, kabar = time.monotonic() + ANTRE, False
    while ps_yatim():
        if time.monotonic() >= batas:
            raise RuntimeError("rakit.ps1 dari rakit yang dimatikan masih jalan: tunggu sampai berhenti, lalu ulangi.")
        if not kabar:
            print("rakit.ps1 dari rakit sebelumnya yang dimatikan masih memakai Word: menunggu sampai berhenti sendiri "
                  "(jangan matikan Word atau PowerShell-nya)...", flush=True)
            kabar = True
        time.sleep(2)


def ps_yatim():
    """rakit.ps1 masih memegang PS_KUNCI (dibuka tanpa berbagi selama ia hidup)? Dipakai rakit dan `tahap`."""
    try:
        with open(PS_KUNCI, "rb"):
            return False
    except FileNotFoundError:
        return False
    except PermissionError:
        return True


def _buang_sisa(f, kerja):
    """Buang folder kerja rakit ini dan folder .rakit-* yang tertinggal rakit yang dimatikan (Python-nya mati sebelum
    membersihkannya). Aman: kunci rakit dipegang rakit ini dan rakit.ps1 sisa rakit lain sudah berhenti (_tunggu_ps_yatim),
    jadi tidak ada rakit lain yang masih memakainya. Dipanggil sesudah rakit.ps1, yang menghentikan Word yatim rakit lama
    (Word itu masih membuka berkas di foldernya). Yang dibuang hanya folder bertanda FolderKerja.SEMENTARA (bahan sementara
    versi ini). Tanpa penanda itu (hasil baru yang belum terpasang, atau folder dari versi lama yang mungkin sengaja
    disimpan) hanya disebut, tidak pernah dibuang. Keadaan dan perpindahannya: FolderKerja."""
    for sisa in FolderKerja.semua(f):
        if sisa.keadaan() is not FolderKerja.Keadaan.SEMENTARA:
            print(f"Folder {sisa.path.name} dibiarkan: mungkin berisi hasil yang sengaja disimpan; periksa isinya, lalu hapus sendiri.")
        elif not sisa.buang():
            print(f"Bahan sementara rakit belum bisa dibuang (ada berkas yang masih terbuka; `rakit` berikutnya mencoba lagi): {sisa.path}")
        elif sisa.path != kerja:
            print(f"Sisa rakit yang terhenti dibuang: {sisa.path.name}")


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


def _rakit(f, jalur, fasl):
    folder_kerja = FolderKerja.buat(f)
    kerja = folder_kerja.path
    try:
        _rakit_di(f, jalur, kerja, fasl)
    except PemulihanGagal:  # hasil baru masih di folder kerja: jangan dibuang, juga oleh rakit berikutnya
        folder_kerja.simpan()
        print(f"Bahan percobaan disimpan: {kerja}")
        raise
    finally:  # berhasil, atau galat cek, Word gagal, berkas terkunci: hasil lama utuh, bahan sementara tidak dibutuhkan
        _buang_sisa(f, kerja)


def _khulasah_pdf(salinan, tujuan, rentang):
    """Paragraf {X} (خلاصة): rakit.ps1 mengekspor salinan PDF berstabilo kuning dan menulis «KHULASAH=a-b,…» (halaman
    fisik awal-akhir tiap paragraf) di laporan. Di sini salinan itu dipotong jadi halaman-halaman itu saja, ke `tujuan`.
    rentang = nilai baris KHULASAH di laporan. False = naskah tidak memuat {X}."""
    if not rentang or not salinan.exists():
        return False
    paragraf = rentang[-1].split(",")
    halaman = set()
    for r in paragraf:
        a, _, b = r.partition("-")
        halaman.update(range(int(a), int(b or a) + 1))
    try:
        teks_pdf.betulkan(salinan)
    except Exception as e:  # noqa: BLE001 — pembenahan ToUnicode opsional: PDF khulasah tetap terbit dengan peringatan
        print(f"PERINGATAN: PDF khulasah jadi, tetapi teks Arabnya belum dibetulkan: {type(e).__name__}: {e}")
    from pypdf import PdfReader, PdfWriter
    r, w = PdfReader(salinan), PdfWriter()
    for h in sorted(halaman):
        if 1 <= h <= len(r.pages):
            w.add_page(r.pages[h - 1])
    with open(tujuan, "wb") as fh:
        w.write(fh)
    salinan.unlink()
    print(f"KHULASAH: {len(paragraf)} paragraf distabilo di {len(halaman)} halaman -> {tujuan.name}")
    return True


def _rakit_di(f, jalur, kerja, fasl):
    cek = olah.periksa(f)
    galat, belum, terima = (len(x) for x in (cek.ctx.galat, cek.ctx.perhatian, cek.ctx.diterima))
    if galat:
        olah.cetak(cek, jalur)
        sys.exit(f"Belum dirakit: {galat} galat di atas harus beres dulu.")
    laporan = produk.laporan(fasl)
    # naskah yang lolos dicetak satu baris; rinciannya tetap di laporan
    print(f"cek: GAGAL 0, perhatian belum ditangani {belum}" + (f", diterima {terima}" if terima else "")
          + (f"; {olah.kepala_tanpa_bukti(len(cek.tanpa_bukti))}" if cek.tanpa_bukti else "")
          + f" (rinciannya: {laporan} sesudah rakit jadi, atau " + perintah(f'cek "{jalur}"') + ")")
    if not huruf.font_terpasang():
        sys.exit(f"Font mushaf belum terpasang: {perintah('siapkan')}, lalu ulangi.")
    d, lap = cek.bahan, cek.laporan
    if fasl:  # seluruh naskah sudah dicek di atas; yang dirakit hanya potongannya
        try:
            lap = [produk.baris_potongan(fasl, olah.potong(d, fasl))] + lap
        except dasar.TandaRusak as e:
            sys.exit(f"Belum dirakit: {e}")
    berkas = d["meta"]["berkas"]
    tabrakan = olah.sumber_tertimpa(f, berkas, d["sumber"], laporan)
    if tabrakan:
        sys.exit(f"Belum dirakit: hasil rakit akan menimpa bahan sumber «{tabrakan[0]}»: ganti @berkas atau nama berkas sumber")
    huruf_profil = d["cetak"]["format"]["huruf"]
    if not huruf.huruf_ada(huruf_profil):  # tanpa huruf profil, Word diam-diam memakai huruf lain
        sys.exit(f"Huruf {huruf_profil} (dipakai @format naskah ini) belum terpasang di Windows.\n       -> {huruf.HURUF_SARAN}\n"
                 f"Sesudah itu: {perintah('periksa')}, lalu ulangi `rakit`.")
    build, galat_ps, salinan_khulasah = kerja / "bahan.json", kerja / GALAT, kerja / f"{berkas}.khulasah.pdf"
    docx, pdf = kerja / produk.docx(berkas), kerja / produk.pdf(berkas)
    olah.tulis_bahan(d, build)
    (kerja / laporan).write_text("\n".join(lap) + "\n", encoding="utf8")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(MESIN / "rakit.ps1"),
                        "-Build", str(build), "-Hasil", str(kerja), "-Laporan", str(kerja / laporan),
                        "-PdfKhulasah", str(salinan_khulasah), "-Kunci", str(PS_KUNCI), "-Galat", str(galat_ps)])
    if r.returncode:
        raise RuntimeError(_word_gagal(r.returncode, galat_ps))
    try:  # supaya teks Arab PDF tersalin dan tercari dengan benar; tampilannya tidak berubah
        teks_pdf.betulkan(pdf)
    except Exception as e:  # noqa: BLE001 — pembenahan ToUnicode opsional: PDF utama tetap terbit dengan peringatan
        print(f"PERINGATAN: PDF jadi, tetapi teks Arabnya belum dibetulkan (salin/cari bisa terbalik): {type(e).__name__}: {e}")
    try:  # sampul, nomor halaman, dan pengantar «:» yang terpisah dari isinya; hasil tetap terbit
        for p in teks_pdf.periksa(pdf, d):
            print(f"PERINGATAN: {p}")
    except Exception as e:  # noqa: BLE001 — pemeriksaan pasca-rakit opsional: PDF tetap terbit dengan peringatan
        print(f"PERINGATAN: PDF jadi, tetapi belum diperiksa (sampul, nomor halaman): {type(e).__name__}: {e}")
    with zipfile.ZipFile(docx) as z:
        if z.testzip() or not {"[Content_Types].xml", "word/document.xml"} <= set(z.namelist()):
            raise RuntimeError("Word menghasilkan DOCX yang tidak utuh; hasil lama belum diganti.")
    kosongkan_penulis(docx)
    from pypdf import PdfReader
    halaman = len(PdfReader(pdf).pages)
    baris = (kerja / laporan).read_text(encoding="utf8").splitlines()  # sekarang berikut baris yang ditambahkan rakit.ps1
    if str(halaman) not in produk.nilai(baris, produk.HALAMAN) or not halaman:
        raise RuntimeError("PDF dan laporan halaman tidak cocok; hasil lama belum diganti.")
    if hashlib.sha256((f / "naskah.txt").read_bytes()).hexdigest() != cek.sidik_naskah:
        raise RuntimeError("Naskah berubah selama rakit; hasil lama belum diganti. Ulangi rakit.")
    terbit, buang = [docx.name, pdf.name, laporan], []
    khulasah = produk.khulasah(berkas)
    if _khulasah_pdf(salinan_khulasah, kerja / khulasah, produk.nilai(baris, produk.KHULASAH)):
        terbit.append(khulasah)
    elif (f / khulasah).exists():  # naskah tidak lagi ber-{X}: salinan lama dibuang bersama penggantian hasil
        buang.append(khulasah)
    terbitkan(kerja, f, terbit, buang)
    for b in baris:
        if b.startswith(produk.HITUNGAN):
            print(b)
    # potongan --fasl memang lebih pendek dari bahts utuh
    kurang = None if fasl else olah.kurang_halaman(d["meta"], halaman)
    if kurang:
        print(f"PERINGATAN: PDF {halaman} halaman, kurang dari {kurang[0]} ({kurang[1]}): tambah pembahasan dari bahan yang "
              "dibaca, atau tulis batas dari dosen di «@minimal_halaman: n»")
    print(f"Jadi: {f / berkas}.docx dan .pdf")
    salin_keluaran(f, berkas)
    if belum:  # PDF tetap terbit (untuk dibaca dan diperiksa), tetapi bahts belum boleh dilaporkan selesai
        print(f"BELUM SELESAI: {belum} perhatian belum ditangani (bereskan, atau «terima <kode> <alasan>» di riset.txt) "
              "-> " + perintah(f'cek "{jalur}"'))


def salin_keluaran(f, berkas):
    """Salinan PDF di folder pilihan pemakai, per orang: bahts/ahmad/ikhlas -> <keluaran>/ahmad/<berkas>.pdf.
    Induknya tetap folder bahts, jadi salinan yang gagal hanya diperingatkan."""
    if not KELUARAN_SAYA.exists():
        return
    induk = KELUARAN_SAYA.read_text(encoding="utf-8-sig").strip()
    if not induk:
        return
    bagian = f.relative_to(AKAR).parts[:-1]
    tujuan = Path(induk, *bagian[bagian[:1] == ("bahts",):]) / produk.pdf(berkas)
    try:
        tujuan.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f / produk.pdf(berkas), tujuan)
        print(f"Salinan: {tujuan}")
    except OSError as e:
        print(f"PERINGATAN: PDF jadi di folder bahts, tetapi salinan ke {tujuan} gagal: {e}")
