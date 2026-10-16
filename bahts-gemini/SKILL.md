---
name: bahts-gemini
description: Menulis بحث (makalah syar'i berbahasa Arab) untuk mahasiswa/mahasiswi معهد العلوم الإسلامية والعربية في جاكرتا (جامعة الإمام). Tiap kutipan dibaca dari halaman kitab Shamela lewat connector, dicocokkan ulang, lalu naskahnya dirakit jadi berkas Word (.docx) berbentuk pedoman جامعة الإمام lengkap dengan sampul, catatan kaki, المصادر والمراجع, dan الفهارس. Pakai setiap kali pemakai meminta bahts, بحث, makalah Arab, atau tugas بحث صفي.
---

# Mesin bahts (versi Gemini)

Ini versi Gemini dari https://github.com/Farisarditiyanto/mesin-bahts. Pemakainya mahasiswa awam: kerjakan semuanya sendiri, pemakai cukup menjawab pertanyaan. Pakai bahasa yang dipakai pemakai, kalimat pendek.

Janji skill ini: **tidak ada kutipan, nomor halaman, penisbatan, atau derajat hadits yang dikarang.** Semuanya harus terbaca di hasil alat connector pada percakapan ini. Yang tidak bisa dibuktikan → jangan ditulis, atau sebut «belum dicek» di laporan.

## 1. Sebelum mulai

0. Python tidak bisa dijalankan di percakapan ini (obrolan biasa) → minta pemakai membuka percakapan baru di mode Task (ikon spark), lalu mengirim permintaannya lagi di sana. Di mode itu `rakit_docx.py` jalan.
1. Lihat alat yang tersedia. Yang dipakai skill ini:
   - `shamela` (alat `shamela_*`, butuh akun shamela.link): mencari dan **memeriksa kutipan** (`shamela_verify_quote`). Paling penting.
   - `turath` (alat `search_turath`, `get_page`, `get_book`, tanpa akun): isi semua kitab Shamela dan kartu kitab (penerbit, cetakan).
   - `tafsir` dan `quran` (tanpa akun): tafsir per ayat dan teks ayat. `quran` minta `fetch_grounding_rules` dulu; nonce-nya diteruskan ke panggilan berikutnya.
2. `shamela` dan `turath` dua-duanya tidak ada → connector-nya belum di-tag. Gemini hanya memakai connector yang dipilih pemakai di kotak pesan. Minta pemakai mengirim ulang permintaannya: ketik `@`, lalu pilih Shamela, Turath, Quran Ai, dan Tafsir MCP dari menu (keempatnya harus jadi tulisan tebal). Jangan diam-diam pindah ke Google Search. Pemakai belum memasang connector-nya → cara menambah: pengaturan Gemini → Apps → Custom apps → tambah, isi «MCP Server URL»:
   - `https://shamela.link/mcp` (masuk dengan akun shamela.link sendiri)
   - `https://mcp.turath.io/mcp/`
   - `https://mcp.tafsir.net/mcp`
   - `https://mcp.quran.ai`
   - `https://hadithunlocked.com/mcp` belum bisa dipasang di Gemini (servernya menolak versi Gemini); lewati.
3. Hanya `turath` yang ada → lanjut, tetapi beri tahu pemakai sekali: pemeriksaan kutipan lebih lemah tanpa `shamela`.

## 2. Tanya pemakai (sekali, satu pesan)

- Judul bahts (huruf Arab) dan susunan yang diminta dosen (مقدمة, فصل/مبحث/مطلب, خاتمة), jumlah halaman isi.
- Nama (huruf Arab), nomor mahasiswa, jenis tugas (mis. بحث صفي للمستوى الرابع), semester (mis. الفصل الدراسي الأول من العام الجامعي 1447), mahasiswa atau mahasiswi.
- Pembimbing (nama dan jabatan); boleh kosong.
- Permintaan khusus dosen: angka 0123 (bawaan ٠١٢٣), tanpa فهرس tertentu, sumber cukup di catatan kaki, الدراسات السابقة.

Beri tahu sekali: sampul mencetak جامعة الإمام محمد بن سعود الإسلامية، معهد العلوم الإسلامية والعربية في جاكرتا، كلية الشريعة. Kampus lain → sampul harus diganti sendiri di Word sesudah berkas jadi.

## 3. Alur kerja

1. Susun خطة sesuai permintaan dosen. Tunjukkan ke pemakai, lanjut tanpa menunggu kecuali pemakai mengubahnya.
2. Untuk tiap مبحث: cari dulu istilah kuncinya. `shamela_search_phrase` (frasa pendek persis seperti di kitab) atau `search_turath`. Hasil kosong bukan bukti tidak ada: coba lafaz lain.
3. Buka halamannya (`shamela_get_page` atau `get_page` turath) dan baca konteksnya. Salin lafaz **persis** dari teks halaman itu, jangan dari ingatan.
4. Catat untuk tiap kutipan: nomor kitab (`book_id`; sama dengan nomor Shamela), juz, dan **nomor halaman cetak**, bukan `page_id`. Shamela: `printed_page` «1/ 3» = juz 1 halaman 3 (juz juga di `part`). Turath: `vol` dan `page`. Kitab satu jilid (kartu kitab tanpa «عدد الأجزاء», atau 1): juz `-`, walaupun turath menulis `vol` «1».
5. Ambil data kitab untuk rujukan pertama dari kartu kitab: `get_book` turath (bagian `info`: المؤلف، المحقق، الناشر، الطبعة). Data yang tidak ada di kartu → tidak ditulis.
6. Tulis naskah dengan tanda di bagian 5. Setiap kutipan dan penisbatan diberi catatan kaki berisi bukti `<<nomor|juz|halaman>>`. Nukilan makna (`انظر:`, tanpa tanda petik) memakai bukti berpotongan `<<nomor|juz|halaman|potongan>>`: potongan = frasa minimal 7 huruf yang disalin persis dari halaman itu. Tanpa potongan, `cek` mesin menolaknya.
7. Periksa (bagian 4), perbaiki, ulangi sampai semua lolos.
8. Rakit jadi Word (bagian 6).

## 4. Pemeriksaan sebelum merakit

Untuk **setiap** kutipan bertanda petik:

1. `shamela` ada → `shamela_verify_quote` dengan `quote` = lafaz di naskah dan `book_id`. Lolos hanya kalau `status` = `verbatim` atau `differs` (perbedaan harakat/hamzah saja) **dan**:
   - `field` = `body`. `foot` = kalimat muhaqqiq: jangan dinisbatkan ke pengarang kitab.
   - `printed_page` sama dengan halaman di bukti. Beda → ganti halamannya.
   - `auto_numbered` = false. True = nomor halaman bukan nomor cetakan: cari edisi lain kitab itu yang «موافق للمطبوع».
2. Tanpa `shamela` → `search_turath` dengan lafaz kutipan dan `book_id`; lafaz harus muncul utuh di `text` halaman itu, `page` dan `vol` sama dengan bukti. Di `text` turath, yang sesudah garis «_________» adalah حاشية (kalimat muhaqqiq): kutipan dari situ tidak boleh dinisbatkan ke pengarang. Tanda baca di `text` turath dibuang; salin tanda bacanya dari `get_page`.
3. Periksa juga: kata nafi (لا/ما/ليس) tepat sebelum kutipan di kitab tidak membalik makna; kutipan yang dipotong `...` tetap sama makna dan pembicaranya; yang berkata memang orang itu, bukan matan yang disyarah, nukilan pihak lain, atau hujah lawan.
4. Tunjukkan tabel hasilnya ke pemakai: kutipan (5 kata pertama), kitab, juz/halaman, hasil. Yang gagal → perbaiki atau buang tanda petiknya dan jadikan `انظر:`.

## 5. Tanda naskah

Naskah = teks biasa. Tanda di bawah ini sebagian dari tanda mesin bahts. Bedanya: ayat ditulis `﴿…﴾` (mesin: `{Q:surah:ayat}`), dan `{P:}`, `@format`, `@rumuz`, `@warna`, `@bentuk` tidak ada di sini. Sesudah ayatnya diganti `{Q:…}`, naskah yang sama bisa dicek `cek` mesin aslinya. Tanda yang salah tulis membuat rakit berhenti dengan `GAGAL`.

```
@judul: …        @jenis: …        @nama: …        @nim: …        @fasl: …      (wajib)
@musyrif: …      @jabatan: …      @thalibah: ya   @angka: latin   @tanpa: ayat, hadits, maudhuat, pustaka   @berkas: nama berkas
#K judul         مقدمة / خاتمة (halaman baru)
#F judul         فصل (halaman baru); bahts tanpa فصل: #F untuk مبحث, #B untuk مطلب
#B judul         مبحث          #M judul   مطلب          #S judul   sub-judul (tidak masuk فهرس)
#T teks          kotak matn merah
#R المصادر والمراجع   sesudahnya satu kitab per baris (diurutkan otomatis, القرآن الكريم paling atas)
**…**            tebal          ((…))   lafaz matn yang disyarah (merah, dalam kurung)
[^ … ]           catatan kaki
<<nomor|juz|hal>>  bukti di dalam catatan kaki (tidak tercetak)
<<nomor|juz|hal|potongan>>   bukti nukilan makna «انظر:»: potongan = frasa ≥7 huruf persis dari halaman itu
﴿نص الآية﴾[^سورة البقرة، آية: 255.]   ayat: teks dari connector quran, langsung diikuti catatan kakinya (masuk فهرس الآيات)
{H:طرف|الراوي|kunci}   daftarkan hadits ke فهرس الأحاديث, tepat sebelum tanda petik pembuka matannya; kunci huruf kecil a-z
{H2:kunci}       tempat lain hadits yang sama (masuk فهرس الأحاديث)
```

- **Setiap** `﴿…﴾`, juga potongan ayat di tengah kalimat atau di الخاتمة, harus langsung diikuti catatan kaki «سورة …، آية: n.». Tanpa itu rakit berhenti dengan `GAGAL`.
- Hadits yang disebut lagi: `{H2:kunci}` di tempat itu, catatan kakinya `[^سبق تخريجه.]`. Pakai `{H2:}` hanya kalau tempatnya di مبحث lain; di مبحث yang sama (kemungkinan halaman yang sama) cukup tanpa `{H2:}`, supaya فهرس tidak mencetak halaman dobel. Ayat yang sama juga cukup ditulis sekali per مبحث.
- Di dalam catatan kaki boleh `**…**` dan `((…))`; catatan kaki di dalam catatan kaki tidak boleh.
- Nama surah di catatan kaki ayat harus persis seperti di `nama_surah.json` (mis. «الفاتحة», bukan «الفاتحه»).

Contoh lengkap: `contoh.txt` di skill ini.

## 6. Aturan penulisan

- Rujukan pertama sebuah kitab: data lengkap (judul، المؤلف، المحقق، الناشر - المدينة، الطبعة - السنة، ج/ص) dari kartu kitab. Berikutnya ringkas: `judul، pengarang، ج/ص.`
- Nukilan lafaz di antara tanda kutip; nukilan makna diawali `انظر:`. Penisbatan lewat perantara harus disebut perantaranya.
- Takhrij hadits: `أخرجه البخاري، كتاب …، باب …، رقم الحديث (n)، ج/ص.`; di luar Shahihain wajib sebut derajatnya beserta siapa yang menghukumi, dari kitab yang dibaca sendiri. Catatan kaki hadits cukup takhrij itu; data cetak kitab haditsnya (المحقق، الناشر، الطبعة) ditulis di المصادر والمراجع saja.
- الدراسات السابقة hanya dari penelitian yang benar-benar dibaca; kutipannya diberi `<<luar>>` dan disebut «belum dicek» di laporan.

## 7. Merakit Word

1. Simpan naskah sebagai `naskah.txt` (UTF-8).
2. Jalankan `rakit_docx.py` dari skill ini: `python rakit_docx.py naskah.txt bahts.docx`. `logo.png` dan `nama_surah.json` harus ada di folder yang sama dengan `rakit_docx.py`. Tanpa internet, tanpa pustaka tambahan.
3. `GAGAL: …` → perbaiki naskah sesuai pesannya, jalankan lagi. `JADI: …` → berikan `bahts.docx` untuk diunduh, beserta `naskah.txt`.
4. Python tetap tidak bisa dijalankan di mode Task → buat dokumen di Canvas dengan urutan sampul, isi, المصادر والمراجع, فهرس الآيات, فهرس الأحاديث, فهرس الموضوعات (nomor halaman فهارس dikosongkan), lalu tawarkan «Export to Docs». Berikan juga `naskah.txt`. Katakan terus terang: bentuk halaman, catatan kaki, dan nomor فهارس tidak dikunci di jalan ini; pemakai merapikannya sendiri.

Cara membuka yang dikatakan ke pemakai:

1. Buka `bahts.docx` dengan Microsoft Word di Windows (huruf Traditional Arabic ada di sana).
2. Supaya angka tercetak ٠١٢٣: Word → File → Options → Advanced → Show document content → Numeral: **Context**. Angka di dekat huruf Latin (tautan, ISBN) tetap 0123. Nomor catatan kaki tetap 1، 2، 3. Naskah `@angka: latin` → Numeral: **Arabic**.
3. Simpan sebagai PDF: File → Save As → PDF. Nomor halaman فهارس terisi waktu PDF disimpan; di layar Word bisa masih «؟».
4. Batas: hadits atau ayat yang muncul dua kali di halaman yang sama tercetak «٢، ٢» di فهرس. Nomornya baru terlihat di PDF, jadi tidak bisa dirapikan di Word.
5. Google Docs (unggah ke Google Drive → Open with Google Docs): belum dicoba. Huruf Traditional Arabic tidak ada di sana, dan nomor halaman فهارس kemungkinan tetap «؟».

## 8. Laporan akhir

- Letak berkas: `bahts.docx` dan `naskah.txt`.
- Alat pencari yang dipakai dan yang tidak.
- Tabel pemeriksaan kutipan (bagian 4), plus yang «belum dicek».
- Batasnya, apa adanya: versi Gemini memeriksa kutipan lewat connector, bukan lewat `cek` mesin bahts. Untuk pemeriksaan penuh dan PDF yang dikunci bentuknya: pakai mesin bahts di agent komputer (README repo, bagian «Mulai»), lalu `cek` naskah yang sama.
- Nama di sampul nama pemakai: isinya tanggung jawabnya. Tanyakan ke dosen apakah bantuan AI dibolehkan.
