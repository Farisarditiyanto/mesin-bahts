"""Tes `cek --jejak` lewat pintu pemakai: kutipan yang tidak ada di kitab yang dirujuk dicari di kitab lain
yang sudah diunduh. Kitab yang dipakai sama dengan `tes.yml` (11223 dan 2348).

Yang diuji:
- tanpa `--jejak`, putusan `cek` dan pesan GAGAL-nya tetap seperti sekarang (GAGAL 1, «TIDAK KETEMU di kitab 2348»);
  yang bertambah hanya satu baris perintah untuk mencari di kitab lain;
- dengan `--jejak`, teks yang sebenarnya ada di kitab 11223 halaman 5 ditunjuk di sana (juz "-" kitab satu jilid);
- dua kutipan yang tertukar kitabnya tidak saling menghalangi (kitab yang dirujuk satu kutipan hanya dilewati
  untuk kutipan itu);
- kutipan ber-`...` yang sebagian karangan tidak ditunjuk ke kitab mana pun;
- teks yang tidak ada di kitab mana pun dilaporkan «tidak ditemukan», bukan ditebak;
- `cek contoh` tetap lolos (GAGAL 0), supaya penunjuk ini tidak mengubah putusan bukti;
- `cek --jejak` tanpa folder = kurang argumen, bukan nama folder.
"""
import shutil, subprocess, sys, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # konsol Windows (cp1252) tidak bisa mencetak ✗ dan huruf Arab

AKAR = Path(__file__).resolve().parent.parent
BAHTS = AKAR / "mesin" / "bahts.py"
ASLI = AKAR / "contoh" / "naskah.txt"
KUTIPAN = "توحيد الربوبية وهو إفراد الله تعالى بالخلق والملك والتدبير"
KUTIPAN_NU = "فإنها دار نفاد لا محل إخلاد، ومركب عبور لا منزل حبور"
PALSU = "هذا نص مخترع لا يوجد في أي كتاب من كتب الشاملة التي نزلت"


def jalan(folder, *tambahan):
    r = subprocess.run([sys.executable, str(BAHTS), "cek", str(folder), *tambahan], cwd=AKAR,
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def tulis(folder, bukti, kutipan=KUTIPAN):
    isi = ASLI.read_text(encoding="utf-8-sig").replace(KUTIPAN, kutipan).replace("<<11223|-|5>>", bukti)
    (folder / "naskah.txt").write_text(isi, encoding="utf-8")


def tulis_dua(folder, satu, bukti_satu, dua, bukti_dua):
    """Dua kutipan dalam satu naskah, masing-masing dengan bukti kitabnya sendiri."""
    isi = (f"@judul: uji jejak\n@jenis: uji\n@nama: uji\n@nim: 0\n@fasl: uji\n@tanpa: pustaka\n\n"
           f"#K المقدمة\nقال الأول: \"{satu}\"[^مصدر. {bukti_satu}].\n"
           f"قال الثاني: \"{dua}\"[^مصدر. {bukti_dua}].\n")
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

    # 2. Bukti berpotongan: potongan bukti ada di halaman yang dirujuk, tetapi kutipannya dari kitab lain (2348 halaman 5).
    tulis(folder, "<<11223|-|5|توحيد الربوبية>>", KUTIPAN_NU)
    kode, keluar = jalan(folder, "--jejak")
    print(keluar)
    assert kode == 1, kode
    assert "2348 ج- ص5" in keluar, keluar

    # 3. Dua kutipan tertukar kitabnya: A ada di 11223 (dirujuk 2348), B ada di 2348 (dirujuk 11223).
    #    Kitab yang dilewati harus per kutipan, bukan gabungan semua kegagalan.
    tulis_dua(folder, KUTIPAN, "<<2348|-|5>>", KUTIPAN_NU, "<<11223|-|5>>")
    kode, keluar = jalan(folder, "--jejak")
    print(keluar)
    assert kode == 1, kode
    saran = keluar.split("petunjuk dari kitab lain", 1)[-1]
    assert "11223 ج- ص5" in saran, "kutipan A ada di 11223 halaman 5"
    assert "2348 ج- ص5" in saran, "kutipan B ada di 2348 halaman 5, jangan dilewati karena kutipan lain"

    # 4. Kutipan ber-... yang sebagian karangan: semua bagian harus ada di kitab yang sama.
    tulis(folder, "<<2348|-|5>>", "كلام فاسد ... الرحمن الرحيم")
    kode, keluar = jalan(folder, "--jejak")
    print(keluar)
    assert kode == 1, kode
    assert "tidak ditemukan di" in keluar, keluar
    assert "ketemu di kitab" not in keluar, "bagian yang umum tidak boleh dianggap kutipan lengkap"

    # 5. Teks yang tidak ada di kitab mana pun: jangan menebak kitab.
    tulis(folder, "<<2348|-|5>>", PALSU)
    kode, keluar = jalan(folder, "--jejak")
    print(keluar)
    assert kode == 1, kode
    assert "tidak ditemukan di" in keluar, keluar
    assert "ketemu di kitab" not in keluar, "teks yang tidak ada tidak boleh ditunjuk ke kitab sembarang"

    # 6. Putusan lama tidak berubah: contoh yang benar tetap GAGAL 0 tanpa petunjuk.
    kode, keluar = jalan(AKAR / "contoh")
    print(keluar)
    assert kode == 0, keluar
    assert "GAGAL: 0" in keluar, keluar
    assert "petunjuk dari kitab lain" not in keluar, keluar

    # 7. Bendera saja = kurang argumen, bukan nama folder.
    r = subprocess.run([sys.executable, str(BAHTS), "cek", "--jejak"], cwd=AKAR,
                       capture_output=True, text=True, encoding="utf-8")
    pesan = (r.stdout or "") + (r.stderr or "")
    assert r.returncode != 0 and "kurang argumen" in pesan, pesan
finally:
    shutil.rmtree(folder, ignore_errors=True)

print("uji jejak: semua sesuai")
