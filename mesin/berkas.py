# SPDX-License-Identifier: AGPL-3.0-or-later
"""Penulisan berkas utuh dan penerbitan hasil dengan cadangan; tanpa layanan luar."""
import hashlib, os, re, shutil, tempfile, time, zipfile
from contextlib import contextmanager
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
            h.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(h.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
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
            h.seek(0)
            if os.name == "nt":
                msvcrt.locking(h.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(h, fcntl.LOCK_UN)


class PemulihanGagal(RuntimeError):
    """Hasil lama belum bisa dipasang kembali: cadangan dan hasil baru sengaja ditinggalkan untuk diselamatkan."""


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
            raise PemulihanGagal(f"Pemulihan hasil belum lengkap. Cadangan: {cadangan}; hasil baru: {kerja}. " + "; ".join(gagal))
        _buang_cadangan(cadangan)  # pulih lengkap: cadangan sudah kosong
        raise
    _buang_cadangan(cadangan)


def _buang_cadangan(cadangan):
    shutil.rmtree(cadangan, ignore_errors=True)
    if not any(cadangan.parent.iterdir()):
        cadangan.parent.rmdir()
