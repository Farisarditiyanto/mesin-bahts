# SPDX-License-Identifier: AGPL-3.0-or-later
"""Konstanta dan alat kecil yang dipakai lebih dari satu bagian `cek`: letak mesin, nama surat, pola angka, pola
kutipan, pesan GAGAL bersama, dan TandaRusak (salah tulis naskah, bukan galat mesin)."""
import json, os, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).parent
SURAH = json.loads((HERE / "nama_surah.json").read_text(encoding="utf8"))


class TandaRusak(ValueError):
    """Tanda naskah yang salah tulis; pesannya untuk pemakai. ValueError lain dari dalam mesin = GALAT MESIN: tanpa
    pembeda ini, galat mesin di baris jebakan «#S GAGAL» terhitung sebagai galat yang diharapkan dan tidak ketahuan."""


AD = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
MERUJUK_KATA = "[أا]نظر|ينظر|ي?راجع"  # tanda nukilan makna di catatan kaki (أبو سليمان، كتابة البحث العلمي، ص114)
TAKHRIJ_AWAL = re.compile(r"\s*و?(?:أخرج|رواه)")  # catatan kaki takhrij: «أخرجه …», «رواه …»
BUKAN_RUJUKAN = ("سورة", "سبق تخريجه")
TINGKAT_JUDUL = {"K": 0, "F": 0, "R": 0, "B": 1, "M": 2, "S": 3}
ANGKA_LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)  # angka Arab dan Persia -> 0-9
KUTIPAN_MIN = 6  # huruf (bentuk `padat`) paling sedikit tiap bagian kutipan yang dicek
POTONGAN_MIN = 7  # huruf paling sedikit potongan sendiri <<sid|juz|hal|potongan>> (potongan sah terpendek di bahts nyata: 7)
# pengganti {Q:s:a} di tengah kutipan («﴿s:a﴾», «﴿s:a:i-j﴾»: penanda_ayat; ﴿﴾ yang diketik = ayat tanpa nomor): kutipannya
# dicek per bagian, dan celah di kitab di antara bagiannya harus memang ayat, sama dengan ayat yang tercetak
AYAT_DI_KUTIPAN = re.compile(r"﴿(?:[0-9]+:[0-9]+(?:-[0-9]+)?(?::[0-9]+-[0-9]+)?)?﴾")  # bukan «﴿٢٨﴾» yang diketik penulis
DIPOTONG = re.compile(r"\.{2,}|…")  # potongan oleh penulis: yang dilompati tidak dicek mesin, jadi selalu perhatian
ELIPSIS = re.compile(f"{DIPOTONG.pattern}|{AYAT_DI_KUTIPAN.pattern}")  # pemisah bagian kutipan: tiap bagiannya dicek, berurutan
AYAT_KITAB = re.compile(r"﴿[^﴾]*﴾|\{[^{}]*\}")  # ayat bertanda di teks kitab Shamela
RUJUKAN_AYAT = re.compile(r"\[[^\]\n]*[ء-ي][^\]\n]*[0-9٠-٩][^\]\n]*\]")  # «[التكوير:٢٨]», «[آل عمران ١٥٢]»
LUAR = "luar"  # <<luar>>: sumbernya bukan kitab Shamela (jurnal, PDF penelitian, kamus); tidak bisa dicek mesin
WAQFEYA = re.compile(r"[wW][0-9a-zA-Z]*\|")  # bukti kitab Waqfeya <<w…|…>> (bentuknya diperiksa WAQFEYA_BUKTI)
WAQFEYA_BUKTI = re.compile(r"(w[0-9a-f]{8})\|(\d+)\|(\d+(?:-\d+)?)")  # <<w…|berkas|hal PDF>>
BELUM_DIUNDUH = "kitab {} belum diunduh"  # pesan GAGAL per bukti; ringkasan laporan `cek` (olah._laporan) mengumpulkan nomornya dari pesan ini
# kutipan yang tidak ada di kitab buktinya; pesan yang sama dikenali `urai` untuk Pemeriksaan.tertolak (`cek --jejak`)
TIDAK_KETEMU = "teks TIDAK KETEMU di kitab {}"
RENTANG_MAKS = 50  # halaman paling banyak satu bukti (dan satu rentang tercetak)
HURUF_LATIN = "A-Za-zÀ-ɏḀ-ỿ"  # huruf Latin, juga transliterasi (ā ī ū ḥ)
QAUL = re.compile(r"(?:^|\s)[وف]?(?:قال|قالت|يقول|تقول)(?:\s+[^\s:]+){0,4}\s*:?\s*$")  # pengantar nukilan «قال الشيخ:»


def perintah(argumen):
    """Perintah mesin yang bisa ditempel apa adanya: jalur lengkap kalau dijalankan dari folder lain, Python yang sedang dipakai.
    Semua pesan yang menyuruh menjalankan perintah memakai ini (bahts, shamela, olah, dirasat)."""
    py = "python"
    w = shutil.which("python")
    try:
        if not (w and os.path.samefile(w, sys.executable)):
            py = f'"{sys.executable}"'
    except OSError:
        py = f'"{sys.executable}"'
    try:
        disini = Path.cwd().resolve() == HERE.parent.resolve()
    except OSError:
        disini = False
    skrip = "mesin/bahts.py" if disini else f'"{HERE / "bahts.py"}"'
    return f"{py} {skrip} {argumen}".rstrip()
