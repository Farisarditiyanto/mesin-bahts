# Bahts — skill Claude untuk menulis بحث

Skill ini membuat Claude menulis bahts (makalah ilmiah syar'i berbahasa Arab ala kampus Saudi) dari judul sampai berkas Word:
خطة, kutipan kitab turats dengan catatan kaki, المصادر والمراجع, فهرس الآيات, فهرس الأحاديث, dan فهرس الموضوعات.

Skill = paket petunjuk dan skrip yang diunggah ke Claude. Cukup akun Claude gratis di web.

## Yang perlu kamu tahu dulu

- Ini alat bantu, bukan jaminan. Claude menyalin halaman kitab dari Shamela, lalu mesin mencocokkan kutipanmu ke salinan itu. Kalau Claude salah menyalin, mesin ikut salah. **Periksa sendiri kutipan utama sebelum mengumpulkan.**
- Mesin hanya membuktikan bahwa teksnya ada di juz dan halaman itu. Mesin tidak bisa menilai siapa yang berkata, benar tidaknya nama kitab yang tercetak, derajat hadits, dan kutipan yang tidak diberi catatan kaki.
- Nomor halaman kadang penomoran Shamela, bukan nomor cetakan. Claude akan memberi tahu kalau begitu.
- Hasil resminya berkas **.docx**. PDF dari Claude kadang tidak ada. Kalau ada dan Claude menyebutnya «PRATINJAU», bentuk dan jumlah halamannya tidak sama dengan pedoman: jangan dikumpulkan.
- Kamu butuh **Microsoft Word di komputer** untuk langkah terakhir. Di Google Docs tampilannya berbeda.
- Bentuk halaman mengikuti pedoman Jāmiʿat al-Imām (Traditional Arabic 18, catatan kaki 14). Tersedia juga pedoman Sakkal Majalla 16, catatan kaki 12: sebutkan saat Claude menanyakan ketentuan dosen.
- Satu bahts bisa menghabiskan kuota akun gratis lebih dari satu kali. Skill ini bisa melanjutkan di chat berikutnya.
- Connector shamela.link bukan layanan resmi المكتبة الشاملة dan punya kuota sendiri.

## Pasang (sekali saja)

1. Unduh [`bahts.zip`](https://github.com/Farisarditiyanto/bahts-skill/raw/main/bahts.zip). Jangan diekstrak: zip-nya diunggah utuh di langkah 4.
2. Buka [claude.ai](https://claude.ai) → Settings → Capabilities. Pastikan **Code execution and file creation** menyala.
3. Buka Customize → Connectors → Add custom connector. Isi nama `shamela` dan alamat `https://shamela.link/mcp`. Setelan lain biarkan. Klik Add, lalu masuk ke shamela.link.
4. Buka Customize → Skills → Add. Unggah `bahts.zip`.

Akun gratis hanya boleh punya satu connector buatan sendiri. Kalau slotnya sudah terpakai, lepas dulu yang lama.

## Pakai

1. Buka chat baru. Pastikan connector shamela menyala di chat itu.
2. Tulis permintaanmu. Contoh:

   > Buatkan bahts tentang الإخلاص وأثره في قبول العمل. Susunannya: مقدمة, satu فصل berisi dua مبحث, خاتمة. Kira-kira 6 halaman.

3. Claude akan menanyakan data sampul dan ketentuan dosen.
   - Wajib: judul, jenis tugas, nama, nomor mahasiswa, dan semester. Selama salah satunya kosong, mesin menolak dengan pesan «data sampul belum diisi».
   - Boleh dilewati: kepala sampul (negara, kampus, fakultas, jurusan) dan dosen pembimbing beserta jabatannya. Yang dilewati tidak tercetak di sampul.
4. Setujui خطة yang diajukan Claude. Setelah itu Claude mencari bahan, menulis, mengecek, dan merakit.
5. Unduh berkas `.docx` yang diberikan Claude.

Kalau chat berhenti di tengah jalan: minta Claude membuat `bahts-lanjut.zip`. Di chat baru, unggah berkas itu dan tulis «lanjutkan bahts».

## Langkah terakhir di Word (wajib)

Sebelum langkah ini, semua nomor halaman di الفهارس tertulis «1». Itu belum benar.

1. Buka `.docx` di Microsoft Word.
2. Tekan Ctrl+A, lalu F9. Nomor halaman الفهارس terisi.
3. Kalau ada catatan kaki «سبق تخريجه، ص…»: klik di dalam salah satu catatan kaki, tekan Ctrl+A, lalu F9 lagi.
4. File → Save As → PDF. PDF inilah yang dikumpulkan.

## Yang belum bisa

- PDF siap kumpul langsung dari Claude.
- Data cetak kitab (muhaqqiq, penerbit, cetakan) sering tidak tersedia di connector. Lengkapi sendiri dari cetakan kitabnya.
- Kalau satu ayat atau hadits dikutip dua kali di halaman yang sama, الفهرس bisa mencetak nomor kembar («2، 2»). Hapus salah satunya di Word.

## Isi bahts.zip

- `SKILL.md`: petunjuk untuk Claude.
- Folder `mesin/`: skrip Python yang mengecek kutipan dan merakit `.docx`. Dua berkas berikut juga ada di dalamnya.
- `mesin/UthmanicHafs_V22.ttf`: huruf mushaf «KFGQPC HAFS Uthmanic Script», hak cipta King Fahd Glorious Quran Printing Complex ([fonts.qurancomplex.gov.sa](http://fonts.qurancomplex.gov.sa/)).
- `mesin/quran_hafs_v22.json`: teks mushaf untuk ayat.

Zip tidak memuat data pribadi.

## Lisensi

- `SKILL.md` dan skrip di `mesin/`: lisensi MIT. Kamu boleh memakai, mengubah, dan membagikannya. Lihat [`LICENSE`](LICENSE).
- Huruf mushaf dan teks mushaf tidak termasuk lisensi itu. Hurufnya milik King Fahd Glorious Quran Printing Complex dan mengikuti ketentuan pemiliknya.

## Lapor masalah

Tulis di [Issues](https://github.com/Farisarditiyanto/bahts-skill/issues). Butuh akun GitHub.
