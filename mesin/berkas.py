# SPDX-License-Identifier: AGPL-3.0-or-later
"""Penulisan berkas utuh; tanpa layanan luar."""
import os, tempfile
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
