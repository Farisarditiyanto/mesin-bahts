"""Satu pintu mesin bahts:  python mesin/bahts.py <perintah>

Bahts (tiap bahts = satu folder berisi naskah.txt):
  baru <folder> "<judul>"      buat folder bahts baru + kerangka naskah.txt
  cek <folder>                 periksa naskah: tanda, ayat, dan semua bukti <<...>> ke kitab lokal
  rakit <folder>               cek, lalu rakit .docx + .pdf ke dalam folder itu (Windows: Word asli; selain itu: rakit_docx.py)
  tanda                        daftar tanda yang dipakai di naskah.txt

Kitab (perpustakaan Shamela lokal, dipakai semua bahts):
  kitab                        daftar kitab yang sudah diunduh
  katalog "<pola>"             cari judul/pengarang di katalog Shamela (regex)
  ambil <id> [<id> ...]        unduh kitab (sekali saja)
  kartu <id>                   data cetak kitab (untuk rujukan pertama & daftar pustaka)
  cari <id|semua> "<frasa>"    cari frasa -> juz/halaman cetak
  teks <id> "<frasa>" [lebar] [maks]   teks asli di sekitar frasa, untuk disalin persis
  bab <id> "<frasa>"           rantai judul kitab/bab tempat frasa berada
  halaman <id> <juz> <hal>     isi satu halaman (juz "-" untuk kitab satu jilid)
  simpan <id> <juz> <hal> <berkas>   catat satu halaman dari berkas teks (hanya di tempat yang tidak bisa `ambil`)

Penelitian terdahulu (الدراسات السابقة, katalog OpenAlex, butuh internet):
  dirasat "<kata kunci>" [maks]   judul, peneliti, tahun, jurnal, tautan, dan ringkasan
"""
import json, os, re, subprocess, sys
from pathlib import Path

MESIN = Path(__file__).parent
AKAR = MESIN.parent
FONT = "UthmanicHafs_V22.ttf"


def folder_bahts(nama):
    f = AKAR / nama.strip("/\\")
    if not (f / "naskah.txt").exists():
        sys.exit(f"Tidak ada {f.name}/naskah.txt. Bahts baru: python mesin/bahts.py baru {f.name} \"<judul>\"")
    return f


def baru(nama, judul):
    f = AKAR / nama.strip("/\\")
    if f.exists():
        sys.exit(f"Folder {f.name} sudah ada.")
    f.mkdir()
    isi = (MESIN / "naskah_baru.txt").read_text(encoding="utf8")
    (f / "naskah.txt").write_text(isi.replace("{judul}", judul).replace("{folder}", f.name), encoding="utf8")
    print(f"Siap: {f.name}/naskah.txt")


def cek(nama):
    import olah
    f = folder_bahts(nama)
    galat, lap = olah.utama(f)
    tiruan = shamela().salinan()
    if tiruan:
        lap.append(f"PERHATIAN: {len(tiruan)} kitab di sini berisi halaman salinan (`simpan`), bukan unduhan asli: "
                   "bukti di atas hanya sekuat salinannya. Bandingkan lagi tiap kutipan dengan sumbernya.")
    print("\n".join(lap))
    return f, galat, lap


def rakit(nama):
    f, galat, lap = cek(nama)
    if galat:
        sys.exit(f"Belum dirakit: {galat} galat di atas harus beres dulu.")
    (f / "laporan.txt").write_text("\n".join(lap) + "\n", encoding="utf8")
    build = MESIN / "_tmp" / f"{f.name}.json"
    if os.name != "nt":  # tanpa Word (Linux, kotak kerja Claude web)
        import rakit_docx
        print("\n".join(rakit_docx.rakit(build, f, MESIN / FONT)))
        return
    if not any((Path(d) / FONT).exists() for d in (os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"), r"C:\Windows\Fonts")):
        sys.exit(f"Font mushaf belum terpasang: klik kanan mesin\\{FONT} > Install, lalu ulangi.")
    ps1 = MESIN / "rakit.ps1"
    # Windows PowerShell 5.1 hanya membaca huruf Arab di skrip kalau berkasnya ber-BOM
    if not ps1.read_bytes().startswith(b"\xef\xbb\xbf"):
        ps1.write_bytes(b"\xef\xbb\xbf" + ps1.read_bytes())
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1),
                        "-Build", str(build), "-Folder", str(f)])
    if r.returncode:
        sys.exit("Perakitan Word GAGAL (lihat pesan di atas). Kalau .docx/.pdf-nya sedang terbuka, tutup dulu.")
    berkas = json.load(open(build, encoding="utf8"))["meta"]["berkas"]
    for baris in (f / "laporan.txt").read_text(encoding="utf8").splitlines():
        if baris.startswith(("HALAMAN", "CATATAN_KAKI", "KATA")):
            print(baris)
    print(f"Jadi: {f.name}/{berkas}.docx dan .pdf")


PERINTAH = {  # nama: (jumlah argumen minimal, pemanggil)
    "baru": (2, lambda a: baru(a[0], a[1])),
    "cek": (1, lambda a: sys.exit(1 if cek(a[0])[1] else 0)),
    "rakit": (1, lambda a: rakit(a[0])),
    "tanda": (0, lambda a: print(tanda())),
    "kitab": (0, lambda a: shamela().daftar()),
    "katalog": (1, lambda a: shamela().katalog(a[0])),
    "ambil": (1, lambda a: [shamela().ambil(x) for x in a]),
    "kartu": (1, lambda a: shamela().kartu(a[0])),
    "cari": (2, lambda a: shamela().cari(a[0], a[1])),
    "teks": (2, lambda a: shamela().teks(a[0], a[1], *map(int, a[2:4]))),
    "bab": (2, lambda a: shamela().bab(a[0], a[1])),
    "halaman": (3, lambda a: shamela().halaman(*a[:3])),
    "simpan": (4, lambda a: shamela().simpan(*a[:4])),
    "dirasat": (1, lambda a: dirasat().cari(a[0], *map(int, a[1:2]))),
}


def tanda():
    """Daftar tanda naskah: ditulis sekali di kepala olah.py (tempat tanda itu diurai), dicetak dari sana."""
    import olah
    return olah.__doc__[olah.__doc__.index("Tanda di naskah"):].rstrip()


def shamela():
    import shamela
    return shamela


def dirasat():
    import dirasat
    return dirasat


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd, *a = sys.argv[1:] or [""]
    if cmd not in PERINTAH or len(a) < PERINTAH[cmd][0]:
        sys.exit(__doc__)
    try:
        PERINTAH[cmd][1](a)
    except (ValueError, FileNotFoundError, re.error) as e:
        sys.exit(f"Perintah '{cmd}' salah pakai: {e}\nLihat: python mesin/bahts.py")
