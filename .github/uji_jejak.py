"""Tes `cek --jejak` lewat pintu pemakai: kutipan yang tidak ada di kitab yang dirujuk dicari di kitab lain
yang sudah diunduh. Kitab yang dipakai sama dengan `tes.yml` (11223 dan 2348).

Yang diuji:
- tanpa `--jejak`, keluaran dan putusan `cek` tetap seperti sekarang (GAGAL 1, pesan «TIDAK KETEMU di kitab 2348»)
  dan pemakai diberi tahu perintah yang bisa mencari di kitab lain;
- dengan `--jejak`, teks yang sebenarnya ada di kitab 11223 halaman 5 ditunjuk di sana (juz "-" kitab satu jilid);
- teks yang tidak ada di kitab mana pun dilaporkan «tidak ditemukan», bukan ditebak;
- `cek contoh` tetap lolos (GAGAL 0), supaya penunjuk ini tidak mengubah putusan bukti.
"""
import shutil, subprocess, sys, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # konsol Windows (cp1252) tidak bisa mencetak ✗ dan huruf Arab

AKAR = Path(__file__).resolve().parent.parent
BAHTS = AKAR / "mesin" / "bahts.py"
ASLI = AKAR / "contoh" / "naskah.txt"
KUTIPAN = "توحيد الربوبية وهو إفراد الله تعالى بالخلق والملك والتدبير"
PALSU = "هذا نص مخترع لا يوجد في أي كتاب من كتب الشاملة التي نزلت"


def jalan(folder, *tambahan):
    r = subprocess.run([sys.executable, str(BAHTS), "cek", str(folder), *tambahan], cwd=AKAR,
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def tulis(folder, bukti, kutipan=KUTIPAN):
    isi = ASLI.read_text(encoding="utf-8-sig").replace(KUTIPAN, kutipan).replace("<<11223|-|5>>", bukti)
    (folder / "naskah.txt").write_text(isi, encoding="utf-8")


folder = Path(tempfile.mkdtemp(prefix="uji-jejak-", dir=AKAR))
try:
    # 1. Kitab yang dirujuk salah: kutipan asli 11223 halaman 5, tetapi buktinya menunjuk 2348.
    tulis(folder, "<<2348|-|5>>")
    kode, keluar = jalan(folder)
    print(keluar)
    assert kode == 1, kode
    assert "GAGAL: 1" in keluar, keluar
    assert "teks TIDAK KETEMU di kitab 2348" in keluar, keluar
    assert "--jejak" in keluar, "tanpa --jejak pemakai tidak diberi tahu cara mencari di kitab lain"
    assert "ketemu di kitab" not in keluar, "penunjuk lintas kitab tidak boleh muncul tanpa --jejak"

    kode, keluar = jalan(folder, "--jejak")
    print(keluar)
    assert kode == 1, kode
    assert "petunjuk dari kitab lain" in keluar, keluar
    assert "11223 ج- ص5" in keluar, "kutipan asli ada di 11223 halaman 5 (kitab satu jilid)"
    assert "✗" not in keluar.split("petunjuk dari kitab lain", 1)[1], "petunjuk tidak boleh menambah GAGAL"

    # 2. Teks yang tidak ada di kitab mana pun: jangan menebak kitab.
    tulis(folder, "<<2348|-|5>>", PALSU)
    kode, keluar = jalan(folder, "--jejak")
    print(keluar)
    assert kode == 1, kode
    assert "tidak ditemukan di" in keluar, keluar
    assert "ketemu di kitab" not in keluar, "teks yang tidak ada tidak boleh ditunjuk ke kitab sembarang"

    # 3. Putusan lama tidak berubah: contoh yang benar tetap GAGAL 0 tanpa petunjuk.
    kode, keluar = jalan(AKAR / "contoh")
    print(keluar)
    assert kode == 0, keluar
    assert "GAGAL: 0" in keluar, keluar
    assert "petunjuk dari kitab lain" not in keluar, keluar
finally:
    shutil.rmtree(folder, ignore_errors=True)

print("uji jejak: semua sesuai")
