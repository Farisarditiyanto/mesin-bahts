"""Penulisan berkas utuh dan penerbitan hasil dengan cadangan; tanpa layanan luar."""
import hashlib, os, shutil, tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def sementara(tujuan):
    """Tulis ke nama unik pada volume tujuan; ganti tujuan hanya sesudah penulis selesai."""
    tujuan = Path(tujuan)
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    fd, nama = tempfile.mkstemp(dir=tujuan.parent, prefix=tujuan.name + ".", suffix=".part")
    os.close(fd)
    part = Path(nama)
    try:
        yield part
        part.replace(tujuan)
    finally:
        part.unlink(missing_ok=True)


def bahan(folder):
    """Satu alamat bahan per jalur bahts lengkap, termasuk dua folder bernama akhir sama."""
    kunci = os.path.normcase(str(Path(folder).resolve()))
    sidik = hashlib.sha256(kunci.encode("utf8")).hexdigest()
    return Path(__file__).parent / "_tmp" / (sidik + ".json")


@contextmanager
def kunci(f):
    """Kunci antarproses yang dilepas OS saat proses mati, meliputi seluruh pekerjaan rakit."""
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a+b") as h:
        if not h.tell():
            h.write(b"\0"); h.flush()
        h.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(h.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError("Rakit lain sedang jalan: tunggu sampai selesai, lalu ulangi.") from None
        try:
            yield
        finally:
            h.seek(0)
            if os.name == "nt":
                msvcrt.locking(h.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(h, fcntl.LOCK_UN)


def terbitkan(kerja, folder, nama):
    """Pindahkan SEMUA hasil lama ke cadangan sebelum memasang hasil baru; pulihkan bila penggantian gagal.
    Berhasil = cadangan dibuang (seperti dulu hasil lama ditimpa: semuanya bisa dirakit ulang dari naskah),
    supaya folder bahts tidak menumpuk satu cadangan tiap rakit. Rename berlaku per berkas, bukan transaksi
    atomik pasangan. Bila proses dimatikan di tengah, hasil dapat belum lengkap, tetapi hasil baru tidak
    dipasangkan dengan hasil lama.
    """
    arsip = folder / "_arsip"
    arsip.mkdir(exist_ok=True)
    cadangan = Path(tempfile.mkdtemp(prefix="rakit-", dir=arsip))
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
            raise RuntimeError(f"Pemulihan hasil belum lengkap. Cadangan: {cadangan}; hasil baru: {kerja}. " + "; ".join(gagal))
        _buang_cadangan(cadangan)  # pulih lengkap: cadangan sudah kosong
        raise
    _buang_cadangan(cadangan)


def _buang_cadangan(cadangan):
    shutil.rmtree(cadangan, ignore_errors=True)
    if not any(cadangan.parent.iterdir()):
        cadangan.parent.rmdir()
