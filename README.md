# Mesin Bahts

Alat bantu menulis **بحث** (makalah ilmiah syar'i berbahasa Arab) bersama agent AI seperti Claude Code.
Kamu dan agent hanya menulis satu berkas, `naskah.txt`. Mesin mengerjakan sisanya:

- mencocokkan tiap kutipan ke teks kitab (المكتبة الشاملة) pada juz dan halaman yang kamu tulis;
- menulis ayat dengan rasm Utsmani;
- merakit Word dan PDF: sampul, catatan kaki, المصادر والمراجع, فهرس الآيات, فهرس الأحاديث والآثار, فهرس الموضوعات.

Contoh naskah yang lolos cek: [`contoh/naskah.txt`](contoh/naskah.txt).

## Batasnya, baca dulu

- Ini alat bantu, bukan jaminan. `cek` hanya membuktikan bahwa teksnya ada di juz dan halaman itu.
- `cek` tidak bisa menilai: siapa yang berkata, benar tidaknya nama kitab, derajat hadits, dan kutipan tanpa catatan kaki. **Periksa sendiri kutipan utamamu sebelum mengumpulkan.**
- Teks kitab adalah ketikan Shamela. Ketikan bisa salah.
- Bentuk halaman mengikuti pedoman جامعة الإمام محمد بن سعود الإسلامية. Sampulnya sampul معهد العلوم الإسلامية والعربية في جاكرتا. Kampus lain perlu mengganti `mesin/sampul.doc` dan menambah profil di `mesin/format.json`.
- Proyek ini bukan milik dan tidak mewakili kampus mana pun.

## Yang kamu butuhkan

| Untuk | Butuh |
|---|---|
| Semua perintah | Python 3.12 ke atas, internet saat mengunduh kitab |
| `rakit` (Word + PDF) | Windows dan Microsoft Word versi desktop |
| Menulis bersama agent | Claude Code, atau agent lain yang membaca `AGENTS.md` |

Tanpa Windows dan Word, mesin berhenti di `cek`: naskah terperiksa, tetapi Word dan PDF tidak terbentuk.

Profil bawaan memakai huruf Traditional Arabic. Kalau Word-mu tidak punya huruf itu, pasang fitur Windows «Arabic Script Supplemental Fonts».

## Pasang

Cara cepat: buka folder hasil unduhan di Claude Code, lalu tulis «siapkan mesin bahts ini». Agent menjalankan dua perintah terakhir di bawah.

```bash
git clone https://github.com/Farisarditiyanto/mesin-bahts.git
```

```bash
cd mesin-bahts
```

```bash
pip install -r requirements.txt
```

```bash
python mesin/bahts.py siapkan
```

`siapkan` mengunduh katalog kitab dan font mushaf, lalu memasang font itu untuk akunmu (tanpa hak admin). Aman diulang.

## Pakai

1. Buka folder ini di Claude Code.
2. Tulis permintaanmu. Contoh:

   > Buatkan bahts tentang الإخلاص وأثره في قبول العمل. Susunannya: مقدمة, satu فصل berisi dua مبحث, خاتمة. Kira-kira 6 halaman.

3. Agent menanyakan data sampul. Nama, nomor mahasiswa, jenis tugas, dan semester disimpan di `sampul_saya.txt` supaya tidak ditanya lagi. Pembimbing ditanya tiap bahts.
4. Agent menyusun خطة, mengunduh kitab, menulis `naskah.txt`, menjalankan `cek`, lalu `rakit`.
5. Hasilnya ada di folder bahts itu: `.pdf` untuk dibaca dan dikumpulkan, `.docx` untuk dibuka di Word.

Alur kerja lengkap dan aturan penulisan untuk agent: [`AGENTS.md`](AGENTS.md).

Tanpa agent juga bisa. Daftar perintah:

```bash
python mesin/bahts.py
```

Daftar tanda untuk `naskah.txt`:

```bash
python mesin/bahts.py tanda
```

## Yang tidak ikut repo

- Naskah, Word, dan PDF-mu. Folder bahts hanya ada di komputermu.
- `sampul_saya.txt`, data sampulmu.
- `kitab/`, kitab yang kamu unduh.
- Font mushaf. `siapkan` mengunduhnya.

## Lisensi

Kode dan dokumentasi: MIT, lihat [`LICENSE`](LICENSE).
Teks mushaf, font mushaf, logo kampus, dan teks kitab bukan bagian dari lisensi itu: lihat [`NOTICE`](NOTICE).

## Melapor dan menyumbang

Masalah atau usul: buka issue di GitHub. Sertakan perintah yang kamu jalankan dan pesan yang keluar.
Perubahan kode: kirim pull request. Tes otomatis (`.github/workflows/tes.yml`) harus hijau.
Riwayat perubahan: [`CHANGELOG.md`](CHANGELOG.md).
