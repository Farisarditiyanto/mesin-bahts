"""Tes `cek --jejak` lewat pintu pemakai: kutipan yang tidak ada di kitab yang dirujuk dicari di kitab lain
yang sudah diunduh. Kitab yang dipakai sama dengan `tes.yml` (11223 dan 2348).

Yang diuji:
- tanpa `--jejak`, putusan `cek` dan pesan GAGAL-nya tetap seperti sekarang (GAGAL 1, «TIDAK KETEMU di kitab 2348»);
  yang bertambah hanya satu baris perintah untuk mencari di kitab lain;
- dengan `--jejak`, teks yang sebenarnya ada di kitab 11223 halaman 5 ditunjuk di sana (juz "-" kitab satu jilid);
- ID kitab berawalan nol («02348») tidak mematikan jejak;
- dua kutipan yang tertukar kitabnya tidak saling menghalangi (kitab yang dirujuk satu kutipan hanya dilewati
  untuk kutipan itu), dan tiap kutipan ditunjuk ke kitabnya sendiri;
- kutipan ber-`...` yang sebagian karangan tidak ditunjuk ke kitab mana pun;
- teks yang tidak ada di kitab mana pun dilaporkan «tidak ditemukan», bukan ditebak;
- `cek contoh` tetap lolos (GAGAL 0), supaya penunjuk ini tidak mengubah putusan bukti;
- `cek --jejak` tanpa folder = kurang argumen, bukan nama folder.
- regresi audit: bagian pendek di samping ayat, perintah saran pada folder berspasi, argumen salah,
  bendera di depan folder, jumlah kitab yang dicari, kutipan berawalan sama, dan sumber kitab lain yang rusak.
"""
import gzip, shlex, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # konsol Windows (cp1252) tidak bisa mencetak ✗ dan huruf Arab

REPO = Path(__file__).resolve().parent.parent
# Perpustakaan dan naskah percobaan terpisah dari data pemakai, tetap di TEMP sebagai arsip uji.
AKAR = Path(tempfile.mkdtemp(prefix="bahts-uji-jejak-"))
shutil.copytree(REPO / "mesin", AKAR / "mesin", ignore=shutil.ignore_patterns("_tmp", "__pycache__"))
for sid in ("_meta", "11223", "2348"):
    shutil.copytree(REPO / "kitab" / sid, AKAR / "kitab" / sid)
shutil.copytree(REPO / "contoh", AKAR / "contoh", ignore=shutil.ignore_patterns("*.docx", "*.pdf", "laporan.txt"))
BAHTS = AKAR / "mesin" / "bahts.py"
ASLI = AKAR / "contoh" / "naskah.txt"
KUTIPAN = "توحيد الربوبية وهو إفراد الله تعالى بالخلق والملك والتدبير"
KUTIPAN_NU = "فإنها دار نفاد لا محل إخلاد، ومركب عبور لا منزل حبور"
PALSU = "هذا نص مخترع لا يوجد في أي كتاب من كتب الشاملة التي نزلت"


def jalan(folder, *tambahan):
    r = subprocess.run([sys.executable, str(BAHTS), "cek", str(folder), *tambahan], cwd=AKAR,
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def tulis(folder, bukti, kutipan=KUTIPAN):
    isi = ASLI.read_text(encoding="utf-8-sig").replace(KUTIPAN, kutipan).replace("<<11223|-|5>>", bukti)
    (folder / "naskah.txt").write_text(isi, encoding="utf-8")


def tulis_dua(folder, satu, bukti_satu, dua, bukti_dua):
    """Dua kutipan dalam satu naskah, masing-masing dengan bukti kitabnya sendiri."""
    isi = (f"@judul: uji jejak\n@jenis: uji\n@nama: uji\n@nim: 0\n@fasl: uji\n@tanpa: pustaka\n\n"
           f"#K المقدمة\nقال الأول: \"{satu}\"[^مصدر، ص{bukti_satu.removesuffix('>>').split('|')[2]}. {bukti_satu}].\n"
           f"قال الثاني: \"{dua}\"[^مصدر، ص{bukti_dua.removesuffix('>>').split('|')[2]}. {bukti_dua}].\n")
    (folder / "naskah.txt").write_text(isi, encoding="utf-8")


folder = AKAR / "naskah uji"
folder.mkdir()
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

    # 2. ID kitab berawalan nol = kitab yang sama; jangan sampai jejak berhenti karena pesannya menulis 2348.
    tulis(folder, "<<02348|-|5>>")
    kode, keluar = jalan(folder, "--jejak")
    print(keluar)
    assert kode == 1, kode
    assert "11223 ج- ص5" in keluar, keluar

    # 3. Bukti berpotongan: potongan bukti ada di halaman yang dirujuk, tetapi kutipannya dari kitab lain (2348 halaman 5).
    tulis(folder, "<<11223|-|5|توحيد الربوبية>>", KUTIPAN_NU)
    kode, keluar = jalan(folder, "--jejak")
    print(keluar)
    assert kode == 1, kode
    assert "2348 ج- ص5" in keluar, keluar

    # 4. Dua kutipan tertukar kitabnya: A ada di 11223 (dirujuk 2348), B ada di 2348 (dirujuk 11223).
    #    Kitab yang dilewati harus per kutipan, bukan gabungan semua kegagalan.
    tulis_dua(folder, KUTIPAN, "<<2348|-|5>>", KUTIPAN_NU, "<<11223|-|5>>")
    kode, keluar = jalan(folder, "--jejak")
    print(keluar)
    assert kode == 1, kode
    saran = keluar.split("petunjuk dari kitab lain", 1)[-1]
    baris = [b.strip() for b in saran.splitlines() if "ketemu di kitab" in b]
    satu = next((b for b in baris if "توحيد" in b), "")
    dua = next((b for b in baris if "فإنها" in b), "")
    assert "11223 ج- ص5" in satu, satu
    assert "2348 ج- ص5" in dua, dua

    # 5. Kutipan ber-... yang sebagian karangan: semua bagian harus ada di kitab yang sama.
    tulis(folder, "<<2348|-|5>>", "كلام فاسد ... الرحمن الرحيم")
    kode, keluar = jalan(folder, "--jejak")
    print(keluar)
    assert kode == 1, kode
    assert "tidak ditemukan di" in keluar, keluar
    assert "ketemu di kitab" not in keluar, "bagian yang umum tidak boleh dianggap kutipan lengkap"

    # 6. Teks yang tidak ada di kitab mana pun: jangan menebak kitab.
    tulis(folder, "<<2348|-|5>>", PALSU)
    kode, keluar = jalan(folder, "--jejak")
    print(keluar)
    assert kode == 1, kode
    assert "tidak ditemukan di" in keluar, keluar
    assert "ketemu di kitab" not in keluar, "teks yang tidak ada tidak boleh ditunjuk ke kitab sembarang"

    # 7. Putusan lama tidak berubah: contoh yang benar tetap GAGAL 0 tanpa petunjuk.
    kode, keluar = jalan(AKAR / "contoh")
    print(keluar)
    assert kode == 0, keluar
    assert "GAGAL: 0" in keluar, keluar
    assert "petunjuk dari kitab lain" not in keluar, keluar

    # 8. Bendera saja = kurang argumen, bukan nama folder.
    r = subprocess.run([sys.executable, str(BAHTS), "cek", "--jejak"], cwd=AKAR,
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    pesan = (r.stdout or "") + (r.stderr or "")
    assert r.returncode != 0 and "kurang argumen" in pesan, pesan

    # Regresi audit: lanjutkan semua kasus agar setiap celah terlihat merah sendiri.
    gagal = []
    def uji(nama, fn):
        try:
            fn()
            print("lolos:", nama)
        except AssertionError as e:
            gagal.append(nama)
            print("GAGAL:", nama, str(e))

    def potongan_pendek():
        # Cek mengizinkan bagian pendek yang menempel ayat; jejak wajib tetap mencarinya.
        tulis(folder, "<<2348|-|5>>", KUTIPAN + " {Q:1:2} ززز")
        kode, keluar = jalan(folder, "--jejak")
        assert kode == 1 and "GAGAL: 1" in keluar, keluar
        assert "tidak ditemukan di" in keluar and "ketemu di kitab" not in keluar, keluar

    def petunjuk_spasi():
        tulis(folder, "<<2348|-|5>>")
        kode, keluar = jalan(folder)
        assert kode == 1 and f'cek "{folder}" --jejak' in keluar, keluar
        # Jalankan perintah yang dicetak, persis seperti ditempel pemakai ke terminal.
        perintah = next(b.split("cari di kitab lain yang sudah diunduh: ", 1)[1]
                        for b in keluar.splitlines() if "cari di kitab lain" in b)
        r = subprocess.run(perintah if sys.platform == "win32" else shlex.split(perintah),
                           cwd=AKAR, capture_output=True, encoding="utf8", timeout=60)
        assert r.returncode == 1 and "11223 ج- ص5" in r.stdout, r.stdout + r.stderr

    def argumen_salah():
        (folder / "naskah.txt").write_bytes(ASLI.read_bytes())
        for tambahan in (("--jejka",), ("--jeja",), ("folder-lain",)):
            kode, keluar = jalan(folder, *tambahan)
            assert kode != 0 and "argumen" in keluar.lower(), (tambahan, keluar)
            assert "NASKAH_SHA256" not in keluar, "Argumen salah harus ditolak sebelum naskah diperiksa"

    def bendera_di_depan():
        tulis(folder, "<<2348|-|5>>")
        r = subprocess.run([sys.executable, str(BAHTS), "cek", "--jejak", str(folder)], cwd=AKAR,
                           capture_output=True, encoding="utf8", timeout=60)
        assert r.returncode == 1 and "11223 ج- ص5" in r.stdout, r.stdout + r.stderr

    def hitungan_kitab():
        tulis(folder, "<<2348|-|5>>", PALSU)
        kode, keluar = jalan(folder, "--jejak")
        assert kode == 1 and "tidak ditemukan di 1 kitab lain yang berhasil dibaca" in keluar, keluar

    def awalan_sama():
        panjang = KUTIPAN + " ... " + PALSU
        tulis_dua(folder, KUTIPAN, "<<2348|-|5>>", panjang, "<<2348|-|5>>")
        kode, keluar = jalan(folder, "--jejak")
        assert kode == 1 and "GAGAL: 2" in keluar, keluar
        assert f"«{KUTIPAN}» ketemu di kitab" in keluar, keluar
        assert f"«{panjang}» tidak ditemukan di" in keluar, keluar

    def kitab_rusak():
        rusak = AKAR / "kitab" / "1"
        rusak.mkdir()
        halaman = rusak / "pages.jsonl.gz"
        for data in (b"gzip rusak", gzip.compress(b"{}")[:-4], gzip.compress(b"bukan json"),
                     gzip.compress(b"[]"), gzip.compress(b'{"body":42}')):
            halaman.write_bytes(data)
            tulis(folder, "<<2348|-|5>>")
            kode, keluar = jalan(folder, "--jejak")
            assert kode == 1 and "GAGAL: 1" in keluar, keluar
            assert "11223 ج- ص5" in keluar and "Traceback" not in keluar, keluar
            assert "jejak belum lengkap" in keluar and "kitab 1" in keluar, keluar
            tulis(folder, "<<2348|-|5>>", PALSU)
            kode, keluar = jalan(folder, "--jejak")
            assert kode == 1 and "tidak ditemukan di 1 kitab lain yang berhasil dibaca" in keluar, keluar
            assert "jejak belum lengkap" in keluar, keluar

    for nama, fn in (("bagian pendek di samping ayat", potongan_pendek),
                     ("perintah saran bisa ditempel pada folder berspasi", petunjuk_spasi),
                     ("argumen salah ditolak sebelum cek", argumen_salah),
                     ("bendera sebelum folder", bendera_di_depan),
                     ("jumlah kitab yang benar-benar dicari", hitungan_kitab),
                     ("kutipan berawalan sama tetap dapat dibedakan", awalan_sama),
                     ("kitab lain rusak tidak menghentikan jejak", kitab_rusak)):
        uji(nama, fn)
    assert not gagal, gagal
finally:
    print("arsip uji:", AKAR)

print("uji jejak: semua sesuai")
