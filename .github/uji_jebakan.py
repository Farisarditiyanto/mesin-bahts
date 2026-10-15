"""Tes contoh/jebakan lewat pintu pemakai (`bahts.py cek`): tiap baris di bawah judul #S harus menghasilkan
persis yang disebut judulnya. «#S GAGAL …» = satu galat, «#S perhatian …» = satu perhatian, «#S lolos …» = tidak
ada keduanya. Baris lain (kepala, judul) tidak boleh menghasilkan apa pun. Mencocokkan per baris, bukan jumlah:
satu jebakan yang berhenti ditolak dan satu baris benar yang jadi GAGAL palsu tidak bisa saling menutupi."""
import collections, re, subprocess, sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
NASKAH = AKAR / "contoh" / "jebakan" / "naskah.txt"
HARUS = {"GAGAL": (1, 0), "perhatian": (0, 1), "lolos": (0, 0)}  # (galat, perhatian) tiap baris

keluar = subprocess.run([sys.executable, str(AKAR / "mesin" / "bahts.py"), "cek", "contoh/jebakan"], cwd=AKAR,
                        capture_output=True, text=True, encoding="utf-8").stdout
print(keluar)
if not re.search(r"^perhatian \(lolos", keluar, re.M):
    sys.exit("cek jebakan berhenti sebelum laporan selesai")
ada = {"✗": collections.Counter(), "!": collections.Counter()}
salah = []
for tanda, isi in re.findall(r"^  ([✗!]) (.*)$", keluar, re.M):
    m = re.match(r"baris (\d+): ", isi)
    if not m:
        salah.append(f"{tanda} tanpa nomor baris: {isi[:80]}")
    else:
        ada[tanda][int(m.group(1))] += 1
bagian, diuji = None, 0
for n, baris in enumerate(NASKAH.read_text(encoding="utf-8-sig").splitlines(), 1):
    if baris.startswith("#S"):
        bagian = baris.split()[1]
        if bagian not in HARUS:
            salah.append(f"baris {n}: judul #S harus diawali {', '.join(HARUS)}")
        harus = (0, 0)
    else:
        harus = HARUS.get(bagian, (0, 0)) if bagian and baris.strip() else (0, 0)
        diuji += bool(bagian and baris.strip())
    dapat = (ada["✗"][n], ada["!"][n])
    if dapat != harus:
        salah.append(f"baris {n}: galat/perhatian {dapat}, harusnya {harus} :: {baris[:60]}")
if salah:
    sys.exit("cek jebakan SALAH:\n" + "\n".join(salah))
print(f"cek jebakan: {diuji} baris sesuai judul #S-nya")
