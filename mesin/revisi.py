# SPDX-License-Identifier: AGPL-3.0-or-later
"""`ubah <folder> [pembanding]`: bandingkan `naskah.txt` sekarang dengan salinan terakhir hasil `rakit` (atau berkas
pembanding / git HEAD) tanpa internet.

Menunjukkan rentang baris yang berubah (untuk pemeriksaan ulang terarah `bukti <folder> <awal-akhir>`) serta token
penting yang hilang atau bertambah saat revisi: bukti <<…>>, penanda ({Q:}, {H:}, {P:}, {A:}, {E:}, #E, {X}), angka,
dan kata syarat/pengecualian/tarjih fikih («إلا», «ما لم», «بشرط», «على الراجح», «في الأصح», …)."""
import difflib, re, subprocess, sys, typing, unicodedata
from collections import Counter
from pathlib import Path

import norma
import produk
from berkas import sementara
from dasar import ANGKA_LATIN, TandaRusak, akhir_rumus, perintah

MESIN = Path(__file__).resolve().parent
AKAR = MESIN.parent
SALINAN_DIR = MESIN / "_tmp" / "revisi"
MAKS_SALINAN = 50

BUKTI = re.compile(r"<<[^<>\n]+>>")
PENANDA_LAIN = re.compile(r"\{(?:Q|H2?|P|A):[^{}\n]*\}|\{X\}")
BARIS_RUMUS = re.compile(r"(?m)^[ \t]*#E[ \t]+(.+)$")
ANGKA = re.compile(r"\d+(?:[.,/%]\d+)?%?")
SAMA_TABEL = str.maketrans(dict(norma.SAMA))

# Syarat, pengecualian, dan kualifikasi fikih yang rawan terhapus diam-diam saat meringkas atau merevisi naskah.
# Diurutkan dari frasa terpanjang agar «إلا إذا» tidak terhitung ganda dengan «إلا».
SYARAT_BAKU = (
    "إلا إذا", "إلا أن", "غير أن", "بشرط أن", "ما لم", "على الراجح", "في الأصح", "في الصحيح", "في المشهور",
    "عند الجمهور", "على خلاف", "في غير", "إلا", "بشرط", "شريطة", "سوى", "غالبا", "أحيانا", "قد",
)
_SYARAT_MAP = {norma.HARAKAT.sub("", s).translate(SAMA_TABEL): s for s in SYARAT_BAKU}
_SYARAT_POLA = re.compile(
    r"(?<![ء-ي])(" + "|".join(re.escape(k) for k in sorted(_SYARAT_MAP, key=len, reverse=True)) + r")(?![ء-ي])"
)


class Perubahan(typing.NamedTuple):
    rentang: tuple[tuple[int, int], ...]
    hilang: dict[str, list[str]]
    tambah: dict[str, list[str]]


def simpan_salinan(sidik, naskah):
    """Simpan salinan `naskah.txt` berdasarkan `NASKAH_SHA256` di `mesin/_tmp/revisi/` (terpakai `ubah`).
    Galat IO diabaikan agar tidak pernah mengganggu `rakit`."""
    if not re.fullmatch(r"[0-9a-f]{64}", sidik or ""):
        return
    try:
        SALINAN_DIR.mkdir(parents=True, exist_ok=True)
        tujuan = SALINAN_DIR / f"{sidik}.txt"
        if not tujuan.exists():
            isi = Path(naskah).read_bytes()
            with sementara(tujuan) as part:
                part.write_bytes(isi)
        lama = sorted(SALINAN_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in lama[MAKS_SALINAN:]:
            p.unlink(missing_ok=True)
    except OSError:
        pass


def _ambil_rumus_sebaris(teks):
    """(daftar token `{E:...}`, teks tanpa `{E:...}`) per baris, dengan kurung kurawal bersarang."""
    token, baris_sisa = [], []
    for baris in teks.splitlines():
        sisa, i = [], 0
        while (j := baris.find("{E:", i)) >= 0:
            sisa.append(baris[i:j])
            try:
                k = akhir_rumus(baris, j + 3) + 1
            except TandaRusak:
                token.append(re.sub(r"\s+", " ", baris[j:]).strip().translate(ANGKA_LATIN))
                sisa.append(" ")
                i = len(baris)
                break
            token.append(re.sub(r"\s+", " ", baris[j:k]).strip().translate(ANGKA_LATIN))
            sisa.append(" ")
            i = k
        sisa.append(baris[i:])
        baris_sisa.append("".join(sisa))
    return token, "\n".join(baris_sisa)


def ekstrak_token(teks):
    """Kembalikan {kategori: Counter} token yang perlu dijaga konservasinya selama revisi."""
    teks = unicodedata.normalize("NFKC", teks or "")
    baris_isi = "\n".join(b for b in teks.splitlines() if not b.lstrip().startswith("@"))

    bukti = Counter(re.sub(r"\s+", " ", m.group(0).translate(ANGKA_LATIN)).strip() for m in BUKTI.finditer(baris_isi))
    tanpa_bukti = BUKTI.sub(" ", baris_isi)

    rumus_baris = [
        f"#E {re.sub(r'\s+', ' ', m.group(1)).strip().translate(ANGKA_LATIN)}"
        for m in BARIS_RUMUS.finditer(tanpa_bukti)
    ]
    tanpa_e_baris = BARIS_RUMUS.sub(" ", tanpa_bukti)
    rumus_sebaris, tanpa_rumus = _ambil_rumus_sebaris(tanpa_e_baris)
    penanda_lain = [m.group(0).translate(ANGKA_LATIN) for m in PENANDA_LAIN.finditer(tanpa_rumus)]
    penanda = Counter(penanda_lain + rumus_sebaris + rumus_baris)

    prosa = PENANDA_LAIN.sub(" ", tanpa_rumus)
    prosa_angka = prosa.translate(ANGKA_LATIN).translate(str.maketrans("٪٫٬", "%.,"))
    angka = Counter(ANGKA.findall(prosa_angka))

    prosa_arab = norma.HARAKAT.sub("", prosa).translate(SAMA_TABEL)
    syarat = Counter(_SYARAT_MAP[m.group(1)] for m in _SYARAT_POLA.finditer(prosa_arab))
    return {"bukti": bukti, "penanda": penanda, "angka": angka, "syarat": syarat}


def _rentang_baris(lama, baru):
    """Rentang baris 1-based inklusif yang berubah pada `baru`, digabung bila berjarak <= 2 baris."""
    a, b = lama.splitlines(), baru.splitlines()
    mentah = []
    for tag, _i1, _i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        if j1 < j2:
            mentah.append((j1 + 1, j2))
        elif b:
            pos = min(j1 + 1, len(b))
            mentah.append((pos, pos))
    gabung = []
    for x, y in sorted(mentah):
        if gabung and x <= gabung[-1][1] + 3:
            gabung[-1] = (gabung[-1][0], max(gabung[-1][1], y))
        else:
            gabung.append((x, y))
    return tuple(gabung)


def _format_selisih(counter):
    out = []
    for k, n in sorted(counter.items()):
        out.append(f"{k} (x{n})" if n > 1 else k)
    return out


def bandingkan(lama, baru):
    """Bandingkan teks naskah `lama` dan `baru`; kembalikan `Perubahan`."""
    t_lama, t_baru = ekstrak_token(lama), ekstrak_token(baru)
    hilang, tambah = {}, {}
    for kat in ("bukti", "penanda", "angka", "syarat"):
        h = t_lama[kat] - t_baru[kat]
        t = t_baru[kat] - t_lama[kat]
        if h:
            hilang[kat] = _format_selisih(h)
        if t:
            tambah[kat] = _format_selisih(t)
    return Perubahan(_rentang_baris(lama, baru), hilang, tambah)


def _asal_pembanding(folder, jalur, pembanding=None):
    """(label_asal, teks_lama) dari argumen berkas, salinan `rakit` terakhir, atau git HEAD."""
    folder = Path(folder)
    if pembanding is not None:
        p = Path(pembanding)
        if not p.is_file() and not p.is_absolute():
            alt = folder / pembanding
            if alt.is_file():
                p = alt
        if not p.is_file():
            raise FileNotFoundError(f"berkas pembanding «{pembanding}» tidak ditemukan")
        return str(p), p.read_text(encoding="utf-8-sig")

    laporan_ada = [p for p in [folder / produk.laporan(), *(lap for _, lap in produk.potongan(folder))] if p.is_file()]
    if laporan_ada:
        terbaru = max(laporan_ada, key=lambda p: p.stat().st_mtime)
        sidik = produk.sidik(terbaru.read_text(encoding="utf8", errors="replace").splitlines())
        if sidik:
            salinan = SALINAN_DIR / f"{sidik}.txt"
            if salinan.is_file():
                return f"rakit terakhir ({terbaru.name}, {sidik[:10]})", salinan.read_text(encoding="utf-8-sig")

    try:
        rel = (folder / "naskah.txt").resolve().relative_to(AKAR.resolve()).as_posix()
        r = subprocess.run(["git", "-C", str(AKAR), "show", f"HEAD:{rel}"],
                           capture_output=True, encoding="utf-8-sig", timeout=10)
        if r.returncode == 0:
            return f"git HEAD ({rel})", r.stdout.removeprefix("\ufeff")
    except (OSError, ValueError, subprocess.SubprocessError):
        pass

    sys.exit(
        f"Belum ada salinan pembanding untuk «{jalur}».\n"
        f"Jalankan `rakit` dulu (menyimpan salinan otomatis di mesin/_tmp/revisi/), atau berikan berkas pembanding: "
        + perintah(f'ubah "{jalur}" <naskah_lama.txt>')
    )


def cetak(folder, jalur, pembanding=None):
    """Cetak laporan perubahan baris dan konservasi token revisi untuk `folder`."""
    folder = Path(folder)
    asal, lama = _asal_pembanding(folder, jalur, pembanding)
    baru = (folder / "naskah.txt").read_text(encoding="utf-8-sig")
    if lama.splitlines() == baru.splitlines():
        print(f"Tidak ada perubahan sejak {asal}.")
        return 0
    hasil = bandingkan(lama, baru)
    rentang_str = ", ".join(f"{a}-{b}" if a != b else str(a) for a, b in hasil.rentang) or "-"
    print(f"Pembanding: {asal}")
    print(f"Baris berubah: {rentang_str}")
    for a, b in hasil.rentang:
        arg = f"{a}-{b}" if a != b else str(a)
        print("  -> " + perintah(f'bukti "{jalur}" {arg}'))
    label = {"bukti": "bukti <<…>>", "penanda": "penanda {Q/H/P/A/E/X}", "angka": "angka", "syarat": "syarat/qayd fikih"}
    if hasil.hilang:
        print("Token HILANG (pastikan bukan terhapus tak sengaja):")
        for kat, daftar in hasil.hilang.items():
            print(f"  - {label[kat]}: {', '.join(daftar)}")
    else:
        print("Token HILANG: tidak ada.")
    if hasil.tambah:
        print("Token TAMBAH:")
        for kat, daftar in hasil.tambah.items():
            print(f"  + {label[kat]}: {', '.join(daftar)}")
    return 0
