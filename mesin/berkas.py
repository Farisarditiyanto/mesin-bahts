# SPDX-License-Identifier: AGPL-3.0-or-later
"""Penulisan berkas utuh dan penerbitan hasil dengan cadangan; tanpa layanan luar."""
import hashlib, os, re, shutil, tempfile, time, zipfile
from contextlib import contextmanager
from enum import Enum
from pathlib import Path


@contextmanager
def sementara(tujuan):
    """Tulis ke nama unik pada volume tujuan; ganti tujuan hanya sesudah penulis selesai."""
    tujuan = Path(tujuan)
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    fd, nama = tempfile.mkstemp(dir=tujuan.parent, prefix=tujuan.name + ".", suffix=".part")
    # mkstemp membuat berkas 0600; tanpa ini kitab, cache, dan PDF hasil di Linux/macOS hanya terbaca pemiliknya
    # (berkas biasa = 0666 dikurangi umask, seperti open()). Windows tidak memakai bit ini.
    if os.name != "nt":
        umask = os.umask(0); os.umask(umask)
        os.fchmod(fd, 0o666 & ~umask)
    os.close(fd)
    part = Path(nama)
    try:
        yield part
        part.replace(tujuan)
    finally:
        part.unlink(missing_ok=True)


def kosongkan_penulis(docx):
    """Buang nama pengguna Word dari data penulis .docx; isi dokumen tidak disentuh."""
    with sementara(docx) as part:  # di Windows docx harus sudah tertutup saat diganti
        with zipfile.ZipFile(docx) as z, zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as o:
            for i in z.infolist():
                isi = z.read(i.filename)
                if i.filename == "docProps/core.xml":
                    isi = re.sub(rb"(<(dc:creator|cp:lastModifiedBy)\b[^>/]*>).*?(</\2>)", rb"\1\3", isi, flags=re.S)
                o.writestr(i, isi)


def bahan(folder):
    """Satu alamat bahan per jalur bahts lengkap, termasuk dua folder bernama akhir sama."""
    kunci = os.path.normcase(str(Path(folder).resolve()))
    sidik = hashlib.sha256(kunci.encode("utf8")).hexdigest()
    return Path(__file__).parent / "_tmp" / (sidik + ".json")


def _pemegang(h):
    """Siapa yang memegang kunci, dari byte sesudah byte kunci: «proses 123, bahts/a/b, mulai 19:19 (3 menit lalu)»."""
    h.seek(1)
    try:
        pid, mulai, apa = h.read(1000).decode("utf8").split("|", 2)
        menit = int((time.time() - float(mulai)) // 60)
        return f"{apa}, proses {pid}, mulai {time.strftime('%H:%M', time.localtime(float(mulai)))} ({menit} menit lalu)"
    except (OSError, ValueError):  # pemegang belum sempat menulis, atau kunci versi lama tanpa keterangan
        return ""


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
    """None = bebas; string (boleh kosong) = dipegang. Tidak membuat berkas atau menulis metadata pemegang.

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
                siapa = _pemegang(h)
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


def terbitkan(kerja, folder, nama):
    """Pindahkan SEMUA hasil lama ke cadangan sebelum memasang hasil baru; pulihkan bila penggantian gagal.
    Berhasil = cadangan dibuang (seperti dulu hasil lama ditimpa: semuanya bisa dirakit ulang dari naskah),
    supaya folder bahts tidak menumpuk satu cadangan tiap rakit. Rename berlaku per berkas, bukan transaksi
    atomik pasangan. Bila proses dimatikan di tengah, hasil dapat belum lengkap, tetapi hasil baru tidak
    dipasangkan dengan hasil lama.
    """
    arsip = folder / ARSIP
    arsip.mkdir(exist_ok=True)
    cadangan = Path(tempfile.mkdtemp(prefix=CADANGAN, dir=arsip))
    lama, baru = [], []
    try:
        for n in nama:
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
