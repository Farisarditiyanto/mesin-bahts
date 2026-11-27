# SPDX-License-Identifier: AGPL-3.0-or-later
"""Penulisan berkas utuh dan nilai turunan isi berkas yang diingat; tanpa layanan luar."""
import functools, json, os, tempfile
from contextlib import contextmanager
from pathlib import Path


@functools.cache
def _win32():
    """(ctypes, msvcrt, FILE_BASIC_INFO, GetFileInformationByHandleEx), dimuat saat dipakai (ctypes ±6 ms impor)."""
    import ctypes, msvcrt
    from ctypes import wintypes

    class InfoDasar(ctypes.Structure):  # FILE_BASIC_INFO
        _fields_ = [("buat", ctypes.c_int64), ("akses", ctypes.c_int64), ("tulis", ctypes.c_int64),
                    ("ubah", ctypes.c_int64), ("atribut", wintypes.DWORD)]

    baca = ctypes.WinDLL("kernel32", use_last_error=True).GetFileInformationByHandleEx
    baca.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    return ctypes, msvcrt, InfoDasar, baca


def _waktu_ubah(fd):
    if os.name != "nt":
        return os.fstat(fd).st_ctime_ns
    ctypes, msvcrt, InfoDasar, baca = _win32()
    info = InfoDasar()
    if not baca(msvcrt.get_osfhandle(fd), 0, ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    return info.ubah


def cap(f, fd=None):
    """(ukuran, mtime_ns, waktu ubah, nomor berkas) f. Waktu ubah = ChangeTime NTFS / st_ctime POSIX: ikut berubah tiap isi
    ditulis dan tidak bisa disetel `os.utime`, jadi isi yang diganti lalu mtime-nya dikembalikan tetap terlihat berubah.
    (`os.stat().st_ctime` Windows = waktu dibuat, tidak berubah saat ditulis.) fd = berkas f yang sudah terbuka."""
    if fd is not None:
        st = os.fstat(fd)
        return [st.st_size, st.st_mtime_ns, _waktu_ubah(fd), st.st_ino]
    fd = os.open(f, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        return cap(f, fd)
    finally:
        os.close(fd)


INGATAN = "sidik.json"  # di folder berkas yang nilainya diingat


def diingat(f, hitung, tulis=True, fd=None):
    """hitung(f) (mis. sha256 isi f), diingat di `INGATAN` folder f bersama `cap(f)`: selama cap-nya sama, isi f tidak
    dibaca lagi (pustaka kitab 5 GB dibaca ulang tiap `cari semua` hanya untuk memastikan isinya belum berubah).
    tulis=False: hanya membaca ingatan (perintah baca-saja). fd = f yang sudah terbuka dan dibaca `hitung` (cap-nya dari
    pegangan itu, bukan dari jalur yang bisa sudah menunjuk berkas pengganti). Ingatan yang rusak atau tidak bisa ditulis
    = dihitung biasa."""
    f = Path(f)
    ingatan = f.parent / INGATAN
    kini = cap(f, fd)
    try:
        semua = json.loads(ingatan.read_bytes())
        lama = semua.get(f.name) if isinstance(semua, dict) else None
        if isinstance(lama, list) and len(lama) == 5 and lama[:4] == kini:
            return lama[4]
    except (OSError, ValueError):
        semua = None
    nilai = hitung(f)
    if tulis and cap(f, fd) == kini:  # berubah selagi dihitung = nilainya belum tentu milik isi yang sekarang
        semua = semua if isinstance(semua, dict) else {}
        semua[f.name] = kini + [nilai]
        try:
            with sementara(ingatan) as part:
                part.write_text(json.dumps(semua), encoding="utf8")
        except OSError:
            pass
    return nilai


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
