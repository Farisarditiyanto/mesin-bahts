# SPDX-License-Identifier: AGPL-3.0-or-later
"""Konstanta dan alat kecil yang dipakai lebih dari satu bagian `cek`: letak mesin, nama surat, pola angka, pola
kutipan, pesan GAGAL bersama, dan TandaRusak (salah tulis naskah, bukan galat mesin)."""
import functools, json, os, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).parent
SURAH = json.loads((HERE / "nama_surah.json").read_text(encoding="utf8"))


@functools.cache
def mushaf():
    """{«surat:ayat»: teks ayat} (riwayat Hafs), urut mushaf; dibaca saat pertama dipakai (±1 MB)."""
    return json.loads((HERE / "quran_hafs_v22.json").read_text(encoding="utf8"))


@functools.cache
def profil_format():
    """Profil bentuk halaman dari format.json (dipilih @format di naskah); dibaca sekali saat pertama dipakai."""
    return json.loads((HERE / "format.json").read_text(encoding="utf8"))


# Pemisah judul utama dan sub-judul sampul «… - …» (dipakai `baru` dan `olah.rencana_cetak`)
SUBJUDUL = re.compile(r"^(.+?)\s+[-–—]\s*(.+)$")
# Ligatur hormat Unicode 14 (﵀-﵏ ﷾ ﷿) tidak ada di huruf cetak (Traditional Arabic, Sakkal Majalla, Arial): kotak kosong di
# Word/PDF. Teks yang dicetak (`rakit`) memakai kalimatnya; `cek` membuangnya (norma.LIGATUR_HORMAT, HORMAT)
HORMAT_CETAK = str.maketrans({
    "﵀": "رحمه الله", "﵁": "رضي الله عنه", "﵂": "رضي الله عنها", "﵃": "رضي الله عنهم",
    "﵄": "رضي الله عنهما", "﵅": "رضي الله عنهن", "﵆": "صلى الله عليه وآله", "﵇": "عليه السلام",
    "﵈": "عليهم السلام", "﵉": "عليهما السلام", "﵊": "عليه الصلاة والسلام", "﵋": "قدس سره",
    "﵌": "صلى الله عليه وآله وسلم", "﵍": "عليها السلام", "﵎": "تبارك وتعالى", "﵏": "رحمهم الله",
    "﷾": "سبحانه وتعالى", "﷿": "عز وجل"})


class TandaRusak(ValueError):
    """Tanda naskah yang salah tulis; pesannya untuk pemakai. ValueError lain dari dalam mesin = GALAT MESIN: tanpa
    pembeda ini, galat mesin di baris jebakan «#S GAGAL» terhitung sebagai galat yang diharapkan dan tidak ketahuan."""


def akhir_rumus(teks, i):
    """Letak «}» penutup «{E:...}» yang isinya mulai di teks[i] (sesudah «{E:»). Kurung kurawal bersarang di dalam
    rumus (\\frac{a}{b}) berpasangan; «\\{» dan «\\}» dilewati sebagai tanda kurawal biasa."""
    dalam, j = 0, i
    while j < len(teks):
        c = teks[j]
        if c == "\\" and j + 1 < len(teks):
            j += 2
            continue
        if c == "{":
            dalam += 1
        elif c == "}":
            if not dalam:
                return j
            dalam -= 1
        j += 1
    raise TandaRusak("tanda {E: tidak ditutup dengan } (pastikan semua kurung kurawal { } di dalam rumus berpasangan)")


def akhir_catatan(teks, i):
    """Letak «]» penutup catatan kaki yang isinya mulai di teks[i] (sesudah «[^»). Isi bukti <<…>> dilewati
    (potongannya boleh memuat «]»), rumus {E:…} dilewati (boleh memuat «[»/«]» tak berpasangan seperti \\left[0,1\\right)),
    dan kurung siku biasa di dalamnya («[هكذا]», kata pembetul) berpasangan, jadi tidak menutup catatan kakinya."""
    dalam, ada, j = 0, False, i
    sebab = lambda: (" (kurung siku [ di dalamnya berpasangan dengan ] sesudahnya: tutup tiap [ dengan ], lalu catatan "
                     "kakinya)" if ada else "")
    while j < len(teks):
        if teks.startswith("[^", j):
            raise TandaRusak("catatan kaki tidak boleh di dalam catatan kaki: tutup yang pertama dengan ] dulu" + sebab())
        if teks.startswith("<<", j):
            tutup = teks.find(">>", j + 2)
            if tutup < 0:
                raise TandaRusak("bukti << di catatan kaki tidak ditutup dengan >>")
            j = tutup + 2
            continue
        if teks.startswith("{E:", j):
            j = akhir_rumus(teks, j + 3) + 1
            continue
        if teks[j] == "[":
            dalam, ada = dalam + 1, True
        elif teks[j] == "]":
            if not dalam:
                return j
            dalam -= 1
        j += 1
    raise TandaRusak("catatan kaki [^ tidak ditutup dengan ]" + sebab())


def tanpa_catatan(teks):
    """Teks tanpa catatan kaki [^…], dibaca seperti `akhir_catatan`. Catatan kaki yang rusak (sudah GAGAL di
    pengurai) dibuang sampai akhir baris."""
    hasil, i = [], 0
    while (awal := teks.find("[^", i)) >= 0:
        hasil.append(teks[i:awal])
        try:
            i = akhir_catatan(teks, awal + 2) + 1
        except TandaRusak:
            return "".join(hasil)
    return "".join(hasil) + teks[i:]


AD = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
ARAH = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
MERUJUK_KATA = "[أا]نظر|ينظر|ي?راجع"  # tanda nukilan makna di catatan kaki (أبو سليمان، كتابة البحث العلمي، ص114)
MERUJUK_AWAL = re.compile(rf"^(?:{MERUJUK_KATA})(?![ء-ي])")
# @tanpa: anzhur: kata MERUJUK_KATA di awal catatan kaki, sesudah «؛»/titik, atau «، و…» tidak dicetak; pemisah dan
# spasinya tetap. Rujukan silang «انظر: ص{P:…}» tetap: tanpa kata itu nomor halamannya tidak terbaca sebagai rujukan
TANPA_ANZHUR = re.compile(rf"(?P<pra>^\s*|[؛.]\s*|،\s*(?=و))و?(?:{MERUJUK_KATA})\s*:(?!\s*ص\s*\{{P:)\s*")


def daftar(meta, kunci):
    """Butir @kunci yang nilainya daftar («ayat, hadits»: dipisah koma atau spasi)."""
    return [t for t in re.split(r"[,، ]+", meta.get(kunci, "")) if t]


TAKHRIJ_AWAL = re.compile(r"\s*و?(?:أخرج|رواه)")  # catatan kaki takhrij: «أخرجه …», «رواه …»
BUKAN_RUJUKAN = ("سورة", "سبق تخريجه")
TINGKAT_JUDUL = {"K": 0, "F": 0, "R": 0, "B": 1, "M": 2, "S": 3}
JUDUL_BAB = ("K", "F")  # judul tingkat teratas isi (مقدمة/خاتمة, فصل): selalu mulai halaman baru
JUDUL_FIHRIS = (*JUDUL_BAB, "B", "M")  # judul tengah, masuk فهرس الموضوعات; #S (sub-judul kanan) tidak
JUDUL_ISI = (*JUDUL_FIHRIS, "S")  # tiap judul bagian isi; #R (المصادر) bukan isi
BATAS_BAB = (*JUDUL_BAB, "R")  # yang menutup isi satu bab: bab berikutnya atau المصادر
ANGKA_LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)
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
TIDAK_KETEMU = "teks TIDAK KETEMU di kitab {}"
RENTANG_MAKS = 50  # halaman paling banyak satu bukti (dan satu rentang tercetak)
HALAMAN_MAKS = 20  # halaman paling banyak sekali panggil `halaman` dan `takhrij`
HURUF_LATIN = "A-Za-zÀ-ɏḀ-ỿ"  # huruf Latin, juga transliterasi (ā ī ū ḥ)
QAUL = re.compile(r"(?:^|\s)[وف]?(?:قال|قالت|يقول|تقول)(?:\s+[^\s:]+){0,4}\s*:?\s*$")  # pengantar nukilan «قال الشيخ:»


def ekor(isi, *, rapat=False, lebar=45, apa="fn"):
    """Ekor pesan `cek`: catatan kaki (apa="fn") atau tempat lain mana yang dimaksud, yaitu awal teksnya.
    Spasi di depan «||» (rapat = satu, selain itu dua) dan lebar potongannya berbeda-beda antarpesan dan sengaja
    dibiarkan begitu: kode «terima» di riset.txt pemakai = sidik kalimat pesan, jadi menyeragamkannya membasikan semuanya."""
    return f"{' ' if rapat else '  '}|| {apa}: {isi[:lebar]}"


def judul_baris(baris, tanda):
    """Baris naskah mentah itu judul bertanda salah satu `tanda` («#F الفصل…» untuk "F")."""
    return bool(re.match(rf"#[{''.join(tanda)}]\s", baris))


def angka(x):
    """Juz atau halaman yang diketik pemakai: «05» dan «٥» = 5 (int() membaca angka Arab ٠-٩ juga); bukan angka = apa adanya."""
    return int(x) if str(x).isdigit() else x


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
