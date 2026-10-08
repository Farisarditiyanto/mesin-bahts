---
name: bahts
description: Menulis bahts (بحث, makalah ilmiah syar'i berbahasa Arab ala kampus Saudi) dari tema atau judul sampai berkas .docx siap kumpul, lengkap dengan خطة, kutipan kitab turats yang dibaca lewat connector shamela dan dicocokkan mesin ke halamannya, catatan kaki, المصادر والمراجع, dan الفهارس. Pakai setiap kali pengguna minta dibuatkan atau dilanjutkan bahts, بحث, makalah Arab, atau tugas riset syar'i. Butuh connector shamela.
---

# Bahts

Kamu menulis satu berkas `naskah.txt`; mesin di folder `mesin/` mengecek tiap kutipan dan merakit .docx.
Bicara dengan pengguna dalam bahasa yang ia pakai. Isi bahts selalu bahasa Arab.

## Syarat

- Connector **shamela** (alat bernama `shamela_*`) harus menyala. Kalau tidak ada: berhenti, minta pengguna menyambungkan `https://shamela.link/mcp` di Customize → Connectors. Jangan menulis bahts dari ingatan.
- Kotak kerja (code execution) harus menyala.

## 1. Siapkan mesin (sekali per chat)

Folder skill ini hanya-baca, jadi salin dulu:

```bash
mkdir -p ~/bahts && cp -r --no-preserve=mode "<folder SKILL.md ini>/mesin" ~/bahts/ && chmod -R u+w ~/bahts && cd ~/bahts
python3 mesin/bahts.py          # daftar perintah
python3 mesin/bahts.py tanda    # daftar tanda naskah
```

Semua perintah dijalankan dari `~/bahts`. Perintah `katalog`, `ambil`, `kartu`, `kitab`, `bab`, dan `dirasat` butuh unduhan kitab atau internet yang tidak ada di kotak kerja: jangan dipakai.

Kalau pengguna mengunggah `bahts-lanjut.zip` (lihat langkah 7): buka isinya ke `~/bahts` sesudah menyalin mesin, lalu lanjut dari naskah itu.

## 2. Tanya dulu, jangan mengarang

Kumpulkan dalam satu pesan, lalu tunggu jawabannya. Yang tidak dijawab jangan diisi sendiri.

| Data | Tanda di naskah | Wajib |
|---|---|---|
| Judul bahts (Arab) | `@judul` | ya |
| Jenis tugas, mis. «بحث صفي للمستوى الرابع» | `@jenis` | ya |
| Nama mahasiswa (huruf Arab) | `@nama` | ya |
| Nomor mahasiswa | `@nim` | ya |
| Semester dan tahun, mis. «الفصل الدراسي الأول من العام الجامعي 1448هـ» | `@fasl` | ya |
| Kepala sampul: negara/kampus/fakultas/jurusan, tiap baris dipisah `\|` | `@lembaga` | tidak |
| Dosen pembimbing dan jabatannya | `@musyrif`, `@jabatan` | tidak |

Kalau judulnya lebih dari ±150 huruf, beri tahu pengguna bahwa huruf judul di sampul akan dikecilkan supaya muat satu halaman.

Tanyakan juga ketentuan dosen: susunan خطة (فصول/مباحث/مطالب), kisaran jumlah halaman, perlu الدراسات السابقة atau tidak, dan pedoman huruf. Pedoman huruf yang tersedia ada di `mesin/format.json`; bawaannya `imam_ayat16` (Traditional Arabic 18, catatan kaki 14).

## 3. Alur kerja

1. `python3 mesin/bahts.py baru <folder> "<judul>"`, isi tanda `@` dari jawaban pengguna, susun خطة, lalu minta persetujuan pengguna atas خطة sebelum menulis isi.
2. Kumpulkan bahan lewat connector shamela (bagian 4). Kutip hanya teks yang benar-benar kamu baca di hasil alat.
3. Tulis `naskah.txt`. Setiap kutipan dan penisbatan diberi catatan kaki berisi bukti `<<...>>`.
4. `python3 mesin/bahts.py cek <folder>` sampai `GAGAL: 0`.
5. Periksa ulang (bagian 6), lalu `python3 mesin/bahts.py rakit <folder>`.
6. Serahkan berkas dan laporkan apa adanya (bagian 7).

## 4. Kitab: dari connector shamela ke `simpan`

Kotak kerja tidak bisa mengunduh kitab. `cek` hanya mengenal halaman yang sudah kamu `simpan`. Untuk tiap halaman yang kamu kutip:

1. Cari dengan `shamela_search_phrase` / `shamela_resolve` (subjek pencarian: frasa pendek persis seperti di kitab). Hasil kosong bukan bukti tidak ada.
2. Baca halamannya dengan `shamela_get_page(book_id, page_id)`. Catat `printed_page` (mis. «2/ 12» = juz 2 halaman 12) dan `body_total_parts`; kalau lebih dari satu bagian, baca semuanya.
3. Tulis `body` **huruf demi huruf seperti hasil alat** ke SATU berkas teks; halaman yang terbagi beberapa bagian digabung berurutan di berkas itu. Penanda ganti halaman seperti `⦗١٢٣⦘` ikut disalin apa adanya. Kalau `foot` tidak kosong, tambahkan baris `ـــــ` lalu isi `foot`. Jangan merapikan, jangan meringkas, jangan memotong, jangan menulis dari ingatan.
4. `python3 mesin/bahts.py simpan <book_id> <juz> <hal> <berkas>` (juz `-` untuk kitab satu jilid; juz dan halaman ditulis dengan angka Latin, mis. `2 12`). Satu halaman = satu kali `simpan`; `simpan` kedua untuk halaman yang sama mengganti yang pertama.
5. Di naskah, buktinya: `<<book_id|juz|hal>>`.

Kalau `citation_auto_numbered` bernilai true, nomor halamannya penomoran Shamela, bukan cetakan: katakan itu kepada pengguna dan jangan menyebutnya nomor cetakan.
`foot` biasanya ucapan muhaqqiq, bukan pengarang: jangan dinisbatkan ke pengarang. Kecuali kitab yang syarahnya memang ditaruh di `foot` (tandanya: `body` kosong atau hanya matan pendek): baca konteksnya dulu, dan sebutkan siapa yang berkata.
Data cetak untuk rujukan pertama (muhaqqiq, penerbit, kota, cetakan, tahun) sering TIDAK tersedia di connector: lihat `notes` di `shamela_get_book` / `shamela_get_citation`. Yang tidak tersedia tidak boleh dikarang. Minta pengguna melihatnya di cetakan kitabnya; kalau ia tidak memberi, tulis yang ada saja dan laporkan kekurangannya.
Pesan cek «kitab N belum diunduh» artinya halaman itu belum kamu `simpan`.

## 5. Aturan penulisan

Di aturan berikut, «kitab lokal» = halaman yang sudah di-`simpan`, `kartu` = `shamela_get_book` / `shamela_get_citation`, dan `dirasat` = alat pencarian web milikmu (kalau ada). الدراسات السابقة hanya ditulis kalau kamu punya alat pencarian web dan benar-benar membaca ringkasan atau PDF penelitiannya; kalau tidak, katakan kepada pengguna bahwa bagian itu dilewati.

{{ATURAN}}

Ayat tidak perlu di-`simpan`: `{Q:surat:ayat}` mengambil teks mushaf dari mesin.

## 6. Periksa ulang sebelum merakit

`cek` hanya membuktikan bahwa teksnya ada di juz/halaman itu, dan di sini halaman itu kamu sendiri yang menyalinnya. Maka untuk tiap catatan kaki, panggil lagi `shamela_get_page` (jangan mengandalkan ingatan atau berkas salinanmu) dan pastikan:

- lafaz kutipan sama dengan hasil alat;
- yang berkata memang orang yang kamu sebut: bukan matan yang disyarah, bukan nukilan pihak lain, bukan hujah lawan;
- nama kitab, pengarang, juz, dan halaman yang tercetak benar;
- derajat hadits di luar Shahihain punya sumber yang terbaca, bukan penilaianmu;
- tidak ada kutipan tanpa catatan kaki.

Yang tidak lolos: perbaiki atau buang. Yang tidak sempat diperiksa: laporkan sebagai «belum dicek».

## 7. Serahkan dan laporkan

`rakit` menghasilkan `<folder>/<berkas>.docx`, dan .pdf kalau kotak kerja punya LibreOffice. Salin keduanya ke tempat yang bisa diunduh pengguna. Baca baris laporannya dan teruskan ke pengguna apa adanya:

- Yang resmi adalah **.docx**. Minta pengguna membukanya di Microsoft Word, menekan Ctrl+A lalu F9, lalu File → Save As → PDF. Sebelum F9, semua nomor halaman di الفهارس tampil «1»: itu belum benar, jadi .docx jangan dikumpulkan sebelum langkah ini. Di Google Docs tampilannya pasti berbeda.
- Kalau laporan menyebut PDF «PRATINJAU», katakan bahwa PDF itu bukan untuk dikumpulkan dan sebutkan alasannya.
- Kalau laporan menyebut «سبق تخريجه», teruskan langkah tambahannya (klik di catatan kaki, Ctrl+A, F9).
- Kalau laporan memuat «PERHATIAN: … halaman salinan», teruskan juga: kutipan dicocokkan ke salinan yang kamu ketik, bukan ke kitab unduhan.
- Jumlah halaman yang pasti baru terlihat di Word; jangan menyebut jumlah halaman PDF pratinjau sebagai jumlah halaman bahts.
- Kalau satu ayat atau hadits dikutip dua kali di halaman yang sama, الفهرس bisa mencetak nomor kembar («2، 2»): minta pengguna menghapus salah satunya di Word.
- Sebutkan: jumlah catatan kaki, catatan kaki tanpa bukti, apa saja yang «belum dicek», dan data cetak yang tidak tersedia.
- Sarankan pengguna memeriksa sendiri kutipan-kutipan utama sebelum mengumpulkan: mesin ini membantu, bukan menjamin.

Pekerjaan sering tidak selesai dalam satu chat. Sebelum berhenti di tengah jalan, bungkus dan serahkan supaya bisa dilanjutkan:

```bash
cd ~/bahts && zip -r bahts-lanjut.zip <folder>/naskah.txt kitab
```

Katakan kepada pengguna: di chat baru, unggah `bahts-lanjut.zip` dan tulis «lanjutkan bahts».

## Daftar tanda naskah

```
{{TANDA}}
```
