# Catatan versi

Yang baru di atas. Satu butir = satu perubahan yang dirasakan pemakai, satu-dua kalimat. Nomor versi = `besar.kecil.tambalan`:
besar naik kalau naskah lama bisa berhenti jalan, kecil naik kalau ada kemampuan baru, tambalan naik kalau hanya perbaikan.
Rincian rilis lama yang diringkas ada di [rilis GitHub](https://github.com/Farisarditiyanto/mesin-bahts/releases).

## Belum dirilis

- Baru: connector `qaf` (qaf.ai, perlu akun gratis) di `.mcp.json` dan `opencode.json` untuk mencari nash menurut makna, termasuk pertanyaan berbahasa Inggris; lafaz dan halamannya tetap dipastikan lewat `shamela`.
- Perbaikan: rujukan berhuruf Latin di catatan kaki dan المصادر والمراجع dicetak kiri-ke-kanan dengan angka 0-9, jadi titik dan potongan judul tidak lagi berpindah tempat; nomor catatan kaki dan «انظر:» tetap Arab di kanan. المصادر kini mendahulukan rujukan Arab, lalu rujukan asing.
- Baru: `@fihris_ayat: titik` mencetak فهرس الآيات tanpa tabel: nama tiap surat tebal, lalu tiap ayat «﴿… n﴾» (nomor ayat bermotif seperti di mushaf, di dalam kurung) dengan titik-titik ke nomor halamannya. Bawaan tetap tabel.
- Performa: perintah rutin (`cek`, `bukti`, `tahap`, `tafsir`, `edisi`, `kitab`, dan `cari semua`) berjalan lebih cepat lewat pembacaan PDF per halaman, cache katalog dan indeks tafsir terverifikasi, pencarian biner katalog dan daftar isi, serta pemindaian pustaka lokal paralel tanpa mengubah hasil pemeriksaan.
- Perbaikan: `tahap` tetap baca-saja meski kutipan salah dan cache kitab belum ada. Cache katalog dengan data rusak dibaca ulang dari katalog asli.
- Baru: `@tahun` menerima dua tahun hijriah satu tahun ajaran (mis. «١٤٤٨/١٤٤٩»), dicetak apa adanya dengan «هـ» di sampul.
- Perbaikan: baris معاني المفردات sesudah bait («الكلمة: معناها.») menempel satu sama lain dan ke syarahnya, jadi daftar مفردات tidak terpotong antarhalaman.
- Perbaikan: bait syair `#V` terakhir dari deretan bait menempel ke paragraf sesudahnya, jadi bait di baris akhir halaman tidak lagi terpisah dari syarahnya; deretan bait yang panjang tetap boleh terpotong antarhalaman.
- Perbaikan: catatan kaki gabungan beberapa kitab kini mengenali judul katalog yang ditempeli nisbah pengarang (mis. «الأعلام للزركلي» ditulis «الزركلي، الأعلام»), jadi halaman tiap kitab dicocokkan dengan buktinya sendiri.
- Baru: `@sampul: tengah` mencetak sampul model خطة dosen معهد العلوم الإسلامية والعربية في إندونيسيا: logo berwarna di tengah atas dengan rasio aslinya, lalu nama المعهد, `@qism`, judul, «إعداد الطالب/الطالبة», «إشراف», dan tahun, semuanya rata tengah; `@judul_sampul` menentukan tempat judul pindah baris di sampul (kata-katanya harus sama dengan `@judul`).
- Baru: `@judul_fasl: dua_baris` mencetak judul «#F الفصل الأول: المقدمة» dua baris di tengah («الفصل الأول» lalu «المقدمة»), sementara فهرس الموضوعات tetap satu baris; `@ihda: tengah` mencetak paragraf الإهداء rata tengah, tebal, berjarak, tanpa awal alinea menjorok.
- Baru: `@format: tatbiqi_16_berjarak` = `tatbiqi_16` dengan matan satu spasi dan celah 6 pt sesudah tiap paragraf, ±satu baris kosong (34 pt) sesudah judul #K/#F, dan celah 24 pt sebelum judul مبحث yang menyusul isi (kunci profil baru `jarak_sebelum_sub`).

## 14.0.0 — 2026-11-22

- Baru: `@ayat_pembuka: s:a` mencetak satu halaman ayat (rasm Utsmani, dengan «[السورة: a]») sesudah sampul, tanpa nomor halaman; `@maudhuat_letak: awal` menaruh فهرس الموضوعات di depan, sesudah الإهداء/الشكر dan tepat sebelum المقدمة; `@tanpa: anzhur` membuang «انظر:»/«ينظر:»/«راجع:» dari catatan kaki yang tercetak, sementara naskah tetap menulisnya untuk `cek`.
- `@tahun` kini menerima tahun hijriah dan masehi sekaligus («١٤٤٨ - ٢٠٢٦»), dicetak di sampul «١٤٤٨هـ – ٢٠٢٦م».
- Perbaikan: persamaan Arab baris sendiri (`#E`) yang lebar (terutama pecahan pada `@format: imam_ayat16`) kini memakai kolom rumus 84% (bukan 76%) dan otomatis diperkecil bertahap sampai muat satu baris, sehingga Word tidak melipatnya lalu membalik urutan huruf Arab di dalam pecahan; kalau tetap melebihi satu baris di 11 pt, `rakit` mencetak PERINGATAN.
- Perbaikan: `dirasat-cek` tidak lagi mencampur tahun di matan atau catatan kaki kitab lain ke pemeriksaan penelitian di baris yang sama, memisahkan dua penelitian yang dipisah «؛» dalam satu catatan kaki, menerima rujukan ulang «المرجع السابق»/«المصدر السابق», mengabaikan perintah LaTeX di dalam `{E:…}`, dan menerima baris `#R` berpenulis Arab dengan judul Inggris di dalam kurung.
- Perbaikan: pencocokan judul kitab di `pustaka`/`cek` kini mengenali judul katalog yang memakai kurung siku di bagian awal (mis. `[العِبَر و] ديوان المبتدأ…` ↔ `العبر وديوان المبتدأ…`), dan draf `#R` dari `pustaka` tidak lagi meninggalkan koma sebelum tanda tutup kurung sesudah tahun wafat dihapus (mis. `[الظاهري]`, bukan `[الظاهري،]`).
- `cek` kini memberi perhatian untuk kitab yang dirujuk di catatan kaki (bukti Shamela, Waqfeya, atau PDF `<<luar>>`) tetapi tidak ditulis di المصادر والمراجع (`#R`), dan menyuruh menjalankan `pustaka <folder>`; `@tanpa: pustaka` tidak dinilai.
- `rakit` dengan `@templat` mengganti penanda «عنوان البحث» di kepala halaman Word itu dengan judul bahts, dan memberi PERINGATAN kalau penanda itu masih tercetak.
- Perbaikan: sampul `@templat` yang meluap ke halaman kedua sesudah diisi tidak lagi kehilangan baris akhirnya (mis. «العام الجامعي») diam-diam: sampul dipotong di pemisah halaman Word itu, dan `rakit` memberi PERINGATAN kalau sampulnya lebih dari satu halaman.
- Pemeriksaan PDF sesudah `rakit` kini memperingatkan halaman sisa di المصادر/الفهارس: halaman tanpa judul berisi kurang dari 40 kata atau paling banyak 5 baris lanjutan tabel atau daftar (mis. فهرس الموضوعات yang meluap beberapa baris), dengan saran `@maudhuat: titik` atau `@fihris: sambung`.
- `AGENTS.md`: judul yang tidak diberikan dosen/خطة/pemakai ditanyakan, bukan dikarang; data sampul yang disalin `baru` dari bahts terakhir orang yang sama ditunjukkan ke pemakai untuk dipastikan, dan `@jenis` ditanyakan ulang; permintaan «jangan mirip bahts lain» dibedakan lewat خطة, isi, dan sumber, bukan `@format`/huruf/gaya.
- Perbaikan: `pustaka` tidak lagi mencetak gelar «د»/«أ د» tanpa titik, kurung kosong, atau tahun wafat muhaqqiq di draf `#R`, dan menilai edisi dari muhaqqiq, nama penerbit, nomor cetakan, serta tahun hijriah dan masehi (angka Latin atau ٠١٢٣, nama pengarang boleh lebih pendek), lalu menyebut bidang yang berbeda. `kartu` dan `cek` juga mengenali gelar «د» tanpa titik di depan nama.
- Perbaikan: `dirasat-cek` menerima rujukan ringkas kedua dan seterusnya (nama keluarga + judul pokok), menilai tiap catatan kaki sendiri kalau satu baris merujuk dua penelitian, dan tidak menyalahkan tahun naskah yang tercetak di kepala PDF penelitian itu walau katalog menulis tahun lain sampai dua tahun.
- Perintah baru `peta <folder>` (tanpa internet, tidak membebani `cek`) untuk melihat peta struktur/kata/catatan kaki, daftar sumber urut wafat dan inventaris kitab mazhab, busur argumen (`المقدمة` ↔ `الترجيح/الخلاف` ↔ `الخاتمة`), daftar `{H:…}`, dan seluruh baris `terima` di `riset.txt` dalam satu layar (didampingi panduan audit langkah 5 `dok/audit.md`).
- Perintah baru `edisi <judul|id|w…> [pengarang]` (tanpa internet) untuk menyatukan pencarian kandidat cetakan lintas katalog Shamela dan Waqfeya, memisahkan riwayat lain dan karya terkait, menjembatani judul alternatif (`=` / `المسمى` / kurung), serta meningkatkan ketepatan pencocokan kitab Shamela pada `waqfeya`.
- `rawi <id> <juz> <hal>` memperlihatkan posisi rawi yang nomornya kosong di indeks sanad Shamela.
- Perintah baru `pustaka <folder>` menyusun draf `#R` (المصادر والمراجع) siap tempel langsung dari `kartu` kitab lokal yang berbukti di catatan kaki (sesuai `@pustaka_gaya`, tanpa gelar, urut abjad). Perintah ini menunjukkan padanan data cetak dan judul yang masih perlu dicocokkan edisinya.
- Perintah baru `dirasat-cek <folder>` menunjukkan status DOI/nomor OpenAlex, pencabutan karya, dan petunjuk metadata per baris. DOI yang tidak tercatat di OpenAlex/Crossref diperiksa registrasinya di doi.org; `dirasat` juga menandai karya yang dicabut.
- Pembaca PDF penelitian (`<<luar|berkas.pdf|hal>>` di `cek` dan `bukti`) kini memulihkan baris PDF Arab yang tersimpan dalam urutan huruf visual terbalik serta ligatur Word yang pasti terbalik («هللا» → «الله»).
- Pesan perhatian `cek` kini selalu menyebut tindakannya (kutipan tanpa catatan kaki sendiri, nomor hadits yang lafaznya tidak cocok, judul tercetak sendirian), dan perhatian 8 kata serta المقدمة menyuruh `terima` untuk yang memang tidak dibereskan; kode kelima jenis perhatian itu ikut berubah, jadi baris `terima` lamanya perlu ditulis ulang dengan kode barunya.
- Perbaikan: PDF bahts tanpa المصادر dan فهرس (mis. `@tanpa: …, pustaka` dan tanpa #R) tidak lagi berakhir dengan halaman kosong bernomor saat baris terakhirnya tepat di tepi bawah halaman.
- `dirasat` kini mendukung saringan tanggal (`--dari`, `--sampai`), bahasa (`--bahasa`), dan perankingan ulang kolam relevan (`--urut terbaru|terlama|dikutip`) di OpenAlex maupun DOAJ, mencetak jilid/nomor/halaman jurnal, menggabungkan duplikat judul lintas sumber, serta menerima nomor `W…` atau DOI langsung untuk melihat rincian dan ringkasan utuh satu penelitian.
- `dirasat-pdf` kini menerima nomor `W…` maupun DOI dan otomatis mencoba tautan PDF akses terbuka karya itu bila salinan OpenAlex tidak tersedia atau tanpa kunci; kalau semuanya gagal, alasan tiap tempat disebut.
- `bukti <folder>` kini mencetak juga cuplikan teks halaman PDF penelitian `<<luar|berkas.pdf|hal>>` (bukan hanya kitab Shamela dan Waqfeya) untuk pemeriksa langkah 5.
- Pemeriksaan PDF sesudah `rakit` kini memperingatkan halaman kosong dan teks/rumus yang meluap mendekati tepi kertas.

## 13.1.0 — 2026-11-20

- Huruf Latin di tengah teks Arab (paragraf, tabel, catatan kaki, المصادر) dicetak Times New Roman dengan ukuran sebanding (matan 18 → 12, catatan kaki 14 → 10), tidak lagi dengan glyph Latin huruf Arab yang lebar dan seukuran teks Arabnya.

## 13.0.0 — 2026-11-20

- `ekspor` sekarang menulis `.txt` (UTF-8), bukan `.docx`: satu paragraf satu baris, judul kitab `#` dan judul bab `##` ke bawah, penanda juz/halaman di baris sendiri, حاشية di bawah garis pemisah. Isinya sekarang urut kitab juga di kitab yang berkas unduhannya tidak urut (mis. صحيح البخاري).
- Rumus LaTeX di naskah: `#E <latex>` (baris sendiri; `\tag{1}` = nomor persamaan di tepi kiri) dan `{E:<latex>}` (sebaris, juga di tabel `#J` dan catatan kaki) dirakit jadi persamaan Word asli tanpa TeX. Rumus tanpa huruf Latin (nama Arab, angka) dicetak kanan-ke-kiri; sintaks yang rusak = `GAGAL` di `cek`.
- Perintah baru `pratinjau <folder> [halaman]`: halaman PDF yang terakhir dirakit (juga potongan `--fasl`) jadi gambar PNG grid 2×2 atau satu halaman penuh di TEMP, untuk memeriksa tata letak.
- `cek` memberi perhatian `sub-bagian tunggal` bila satu `#B` sendirian di bawah `#F` atau satu `#M` sendirian di bawah `#B` (تمهيد/مدخل tidak dihitung; `@bentuk: kitab` tidak dinilai).
- `AGENTS.md`: tabel pilih alat mencakup alat tanpa internet, `waqfeya`, `dirasat`, rumus, diagram, grafik, dan `pratinjau`; pemeriksa langkah 5 menilai isi dan tata letak sebagai dua fokus.

## 12.0.0 — 2026-11-20

- `@malahiq: akhir` tanpa `#R` (`@tanpa: pustaka` atau `@bentuk: kitab`) kini GAGAL di `cek`: الملاحق dicetak sesudah المصادر, jadi tanpa المصادر barisnya tidak berefek. Hapus `@malahiq: akhir` atau tulis `#R`.
- Catatan kaki di dalam tabel `#J` tidak lagi menjatuhkan Word saat `rakit`.
- `rakit --fasl n` untuk potongan sesudah yang pertama kini ikut menghasilkan `<@berkas> - الخلاصات.pdf` kalau potongannya memuat `{X}`.
- `@rujukan_ayat: matan` (juga lewat `@model: jakarta`) kini berlaku di dalam tabel `#J`, dan `bukti` tidak lagi menyebut paragraf ayatnya «tanpa catatan kaki».
- `@logo: berwarna` dengan `@sampul: QISM` (huruf besar) tidak lagi GAGAL.
- `keluaran_saya.txt` yang kosong tidak lagi menyalin PDF ke folder kerja; PDF الخلاصات lama yang sedang terbuka tidak lagi membuat hasil rakit tercampur dengan versi sebelumnya.
- Bendera yang ditulis dua kali (`--jejak --jejak`) dan `cari w… --potongan` kini ditolak dengan pesan yang jelas; `periksa` menyebut huruf judul tiap profil `@format`; gambar JPEG berbyte pengisi terbaca ukurannya.
- Susunan kode mesin dirapikan (keputusan cetak ditulis sekali di Python, satu tabel perintah, bukti dan catatan kaki bertipe); keluaran `cek` untuk naskah yang ada tidak berubah. Letak kode yang baru: AGENTS.md «Untuk yang mengubah mesin».
- Kunci baru `@logo: berwarna`: sampul bawaan (قسم الشريعة) tetap seperti biasa, hanya logonya diganti logo جامعة الإمام berwarna seperti di sampul jakarta.
- Connector baru `qurangallery` (tanpa akun) di `.mcp.json` dan `opencode.json`: seluruh Shamela dengan nomor kitab yang sama, dipakai saat kuota `shamela` habis, layanannya mati, atau `shamela_verify_quote` tidak menemukan kutipan. AGENTS.md kini memuat tabel «butuh apa → alat mana».
- Perintah baru `ekspor <id|w…> [--ke <folder>]`: satu kitab Shamela atau Waqfeya jadi satu .docx yang rapi dibuka di Word (kanan-ke-kiri, judul bab di Navigation Pane, penanda juz/halaman, حاشية sesudah halamannya, lambang ﵁ dan sejenisnya ditulis kalimatnya); bawaan ke folder Downloads. Judul beberapa baris tetap utuh, tanda perbandingan tetap terbaca, dan angka serta aksara lain dalam OCR dipertahankan.
- `#L **Abstract**` yang ditulis sesudah isi (mis. الملخص Arab) kini mulai halaman baru, jadi الملخص dan Abstract tidak tercetak sehalaman; langsung di bawah judul `#K` tetap sehalaman dengan judulnya.
- README utama kini berbahasa Inggris (`README.md`); versi Indonesia pindah ke `README.id.md`. Ketiga README dibuka dengan satu kalimat tentang mesin ini, tabel ringkas, perintah mulai, dan bagian «Batasan».
- `bukti` mencetak paragraf matan tiap catatan kaki berbukti Shamela/Waqfeya beserta isi catatan kaki utuh, supaya pemeriksa dapat membandingkan parafrase dan syaratnya dengan sumber, termasuk bila catatan penjelasan berada di tengah kutipan.
- Pemeriksa langkah 5 kini menyertakan bukti di tiap temuan (perintah yang dijalankan, potongan keluarannya, aturan yang dilanggar); temuan yang tidak terbukti saat dijalankan ulang dibuang dan disebut di laporan akhir.

## 11.0.0 — 2026-11-15

- Kurung siku di dalam catatan kaki («[هكذا]», kata pembetul di kutipan) berpasangan dan tidak menutup catatan kakinya, jadi sisa catatan kaki tidak tercetak di matan; kurung siku yang tidak ditutup di dalam catatan kaki = `GAGAL`.
- Sampul dari `@templat` kini berkertas A4 seperti halaman isi walau Word mahasiswa memakai Letter; bidang teks dan letak gambar sampulnya tetap, jadi PDF tidak lagi bercampur dua ukuran kertas.
- `rakit` memberi PERINGATAN kalau halaman-halaman PDF hasilnya tidak berukuran kertas sama.
- Langkah riset baru di `riset.txt`: `cari <istilah> | <catatan>` mencatat istilah kunci tiap مبحث yang sudah dicari di connector `shamela`. Tiap مبحث (bahts berفصل atau tanpa #F: tiap #B, ditambah #F tanpa #B seperti التمهيد; bahts tanpa فصل: tiap #F) yang belum punya baris `cari` berisi istilah yang tertulis di judul atau matannya jadi perhatian `cek` yang tidak bisa diterima; langkah yang tidak bisa dijalankan ditulis `belum cari <istilah> | <alasan>`. Bahts lama akan mendapat perhatian ini sampai barisnya ditambah.
- Tanda baru `{M:nama}` untuk فهرس الفرق والمذاهب (sama dengan `{N:}` untuk فهرس الأعلام): tidak tercetak, dan `rakit` mencetak فهرس itu sesudah فهرس الأعلام; `@tanpa: firaq` membuangnya.
- Tanda baru `{X}` di awal paragraf خلاصة: tidak tercetak, dan `rakit` kini membuat juga `<@berkas> - الخلاصات.pdf` yang hanya berisi halaman-halaman ber-khulasah, dengan paragraf khulasahnya distabilo kuning; `.docx` dan PDF utama tetap tanpa stabilo. `{X}` di tengah paragraf atau di catatan kaki = `GAGAL`.
- Perakit hanya membersihkan proses Word yang identitasnya cocok dengan jendela Word miliknya; proses Word aplikasi lain dan nomor proses yang sudah dipakai ulang tidak disentuh.
- `diagram` mempertahankan PNG lama kalau perender gagal atau melewati batas waktu, lalu tetap mencoba diagram berikutnya.
- `cek` memberi perhatian kalau `riset.txt` tidak bisa dibaca sebagai UTF-8, termasuk pada `@bentuk: kitab`.
- Sesudah pembaruan ini tiap kitab yang sudah diunduh membangun ulang indeks pencariannya sekali (beberapa detik untuk kitab besar); indeks yang rusak kini dikenali dan dibangun ulang, bukan dipakai.
- Pemeriksaan ayat memakai pustaka `rapidfuzz` yang tercantum di `requirements.txt`; `periksa` menilainya sebagai kebutuhan `cek`.
- `cek` tidak lagi menolak ayat yang dikutip kitab dengan ejaan imla'i persis: ayat yang memuat «سبحانه وتعالى»، «رضي الله عنهم»، atau «سيرحمهم الله» (mis. 16:1, 39:67, 98:8) tidak lagi `GAGAL` «ayat yang tercetak … tidak sama», dan ayat berlafaz «الليل»، «اللاتي»، «اللائي» tidak lagi diberi perhatian «salah ketik?».
- `rawi <id> <juz> <hal>` kini mencetak juga ±800 sanad صحيح البخاري yang dulu terlewat (mis. ٢٨٠٤ يحيى بن بكير عن الليث di ج4 ص19, dan atsar seperti كتاب عمر بن عبد العزيز di ج1 ص31) sebagai rantai lengkap, bukan sekadar daftar rawi «di luar data sanad Shamela».
- Perintah baru tanpa internet: `akar <id> "<akar>"` mencetak bentuk kata berakar itu di satu kitab beserta jumlahnya, dikelompokkan seperti `cari` mencocokkan kata (mis. akar شفع di المغني: kelompok «شفيع» 325×, di antaranya «الشفيع» 244×، lalu «المشفوع»، «الشفعاء»), dengan perintah `cari` untuk tiap kelompok; kata yang di kamus juga berakar lain ditandai «[juga akar …]». Datanya kamus akar Shamela; `siapkan` kini mengunduh ±19 MB tabel layanan.

## 10.0.0 — 2026-11-14

- Jadi `GAGAL`: takhrij di luar Shahihain yang tidak menulis derajat hadits (tulis derajatnya, atau «ولم أقف على حكم …»), dan baris kembar di المصادر والمراجع.
- Perhatian `cek` kini wajib ditangani: tiap perhatian dicetak dengan kode, lalu dibereskan di naskah atau diterima dengan `terima <kode> <alasan>` di `riset.txt` (perhatian `riset.txt` sendiri tidak bisa diterima). `tahap` baru mencetak `NASKAH=LOLOS` dan menyuruh ke pemeriksa sesudah semuanya ditangani, dan `rakit` mencetak «BELUM SELESAI» selama masih ada; perhatian yang diterima didaftar terpisah beserta alasannya.
- `cek` menolak nama hasil perangkat Windows (`NUL`, `CON`, `COM1`, dan yang sejenis) serta karakter kontrol pada `@berkas`, termasuk nama bawaan dari folder bahts.
- Gambar `#G` PNG/JPEG yang terpotong atau berdimensi nol ditolak `cek` sebelum Word dipanggil.
- Kitab yang tidak ada di Shamela bisa diambil dari Waqfeya (±10.000 kitab scan cetakan + OCR): `waqfeya "<judul>"`, `ambil w<nomor>`, `kartu`/`cari`/`halaman w<nomor>` (scan halaman jadi PDF, atau PNG kalau `pymupdf` terpasang); `ambil w…` yang terputus dilanjutkan dengan menjalankannya lagi. Bukti `<<w…|berkas|hal>>`: `cek` hanya menjaga kitab, halaman, dan kutipan yang jelas ada di halaman lain; lafaznya dibaca pemeriksa di scan, karena OCR bisa salah huruf.
- Perintah baru tanpa internet dan tanpa kuota: `tafsir <surat:ayat>` menunjuk kitab tafsir yang menafsirkan ayat itu (14 kitab, mis. الطبري، زاد المسير، ابن كثير) beserta juz/halaman cetaknya; `takhrij <id> <juz> <hal>` menunjuk hadits di halaman itu di 8 kitab hadits (البخاري، مسلم، أبو داود، الترمذي، النسائي، الموطأ، الطيالسي، ابن الجارود) beserta nomor dan juz/halamannya; edisi lain kitab itu (mis. صحيح مسلم ت عبد الباقي) dijembatani lewat nomor hadits. Datanya indeks layanan Shamela sendiri, diunduh `siapkan`.
- Perintah baru tanpa internet: `rawi <id> <juz> <hal>` mencetak sanad tiap hadits di halaman itu berurutan dari pengarang, lalu rutbah ringkas tiap rawi (ابن حجر، الذهبي، wafat); `rawi <nomor>` mencetak ucapan جرح وتعديل rawi itu dan tempat lafaznya di edisi lokal kitab rijalnya (dicari ulang, karena juz/halaman di data Shamela sering dari edisi lain; hanya ditunjuk kalau letaknya di tarjamah rawi itu); `rawi "<nama>"` mencari nomor rawi. `siapkan` kini mengunduh ±8,6 MB tabel layanan.
- Gambar di naskah: `#G berkas.png | keterangan` mencetak PNG/JPG dari folder bahts di tengah halaman, dikecilkan agar muat, dengan keterangan di bawahnya. Diagram Mermaid (`<nama>.mmd`) dijadikan PNG dengan perintah baru `diagram <folder>` (butuh Node.js + Chrome/Edge); `cek` dan `rakit` tetap tanpa internet.
- `@malahiq: akhir` mencetak bagian `#K الملاحق` sesudah المصادر والمراجع dan sebelum فهرس; halamannya tidak masuk `HALAMAN_ISI`.
- `cek --jejak`: kutipan yang tiap potongannya kena salah ketik kini tetap mendapat «Paling mirip» di kitab yang dirujuk (pustaka `rapidfuzz`; belum terpasang → `periksa` menyebut perintahnya, dan petunjuk ini saja yang dilewati).
- Rentang ayat `tafsir` yang tidak ada dan rentang `takhrij` berlebih ditolak sebelum diperluas, termasuk angka yang sangat besar.
- `rakit` tidak lagi gagal («Specified cast is not valid») pada tabel `#J` empat kolom atau lebih.
- Isi sel tabel `#J` kini rata kanan; dulu tercetak rata kiri. Rakit ulang bahts bertabel untuk mendapat PDF yang benar.

## 9.3.0 — 2026-11-13

- `#L` (Abstract bahasa Inggris) dicetak Times New Roman 12, judulnya 14; dulu sebesar matan Arab (18 di `imam`) sehingga Abstract satu halaman luber ke halaman berikutnya. Profil bisa mengubahnya lewat kunci `latin` di `mesin/format.json`.
- `tahap`: naskah yang berubah hanya di yang tidak tercetak (mis. `@minimal_halaman`, baris kosong) tidak membuat PDF USANG: laporan `rakit` kini mencatat `CETAK_SHA256`, jadi tidak perlu rakit ulang. Laporan lama tanpa sidik itu tetap dinilai dari naskah.
- Jumlah halaman dinilai: seluruh PDF kurang dari 25 halaman = perhatian `cek` (perkiraan) dan PERINGATAN sesudah `rakit`; potongan `--fasl` dan `@bentuk: kitab` tidak dinilai. Batas dosen: `@minimal_halaman: n`; `0` = tidak dinilai; kosong atau bukan bilangan = GAGAL.
- Jumlah kitab di المصادر dinilai hanya kalau dosen menulis batasnya: `@minimal_kitab: n`; kosong = GAGAL. Baris `#R` kembar dihitung sekali. Mushaf ditulis «القران الكريم»/«المصحف الشريف» tetap bukan kitab; kitab berjudul «القرآن…» (mis. «القرآن والسنة…») kini dihitung dan diurutkan seperti kitab lain.
- `cek` menjaga cara menukil (أبو سليمان ص112-114، 123، 173): perhatian untuk 8 kata atau lebih yang sama persis dengan kitab di luar tanda petik, nukilan makna tanpa «انظر:», kutipan lafaz yang dirujuk «انظر:», dan kutipan lebih dari 60 kata. Naskah lama bisa mendapat perhatian baru (bukan GAGAL).
- `rakit` lebih cepat ±18% (BarisPendek dan putaran rujukan halaman); PDF sama persis.
- Tabel di isi bahts: `#J sel | sel | sel` (baris pertama = kepala tabel). Baris `#J` dengan satu sel, sel kosong, atau jumlah sel berbeda dari baris sebelumnya di tabel itu = GAGAL.
- `bukti` mencetak tiap paragraf isi tanpa catatan kaki; pemeriksa langkah 5 wajib menilainya.
- Agent wajib membaca seluruh bab sebelum mengutip satu halaman kitab.
- README berbahasa Arab (`README.ar.md`), README ditulis ulang untuk agent; Command Code bisa memakai connector `shamela`.

## 9.2.1 — 2026-11-11

- AGENTS.md: tujuh cara menukil menurut أبو سليمان dengan urutan pemakaiannya. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v9.2.1)

## 9.2.0 — 2026-11-10

- Baru: فهرس الأعلام (`{N:nama}`), `tahap <folder>`, `@qism`, `@format: tatbiqi_16`, `@basmalah: ya`; standar أبو سليمان untuk الدراسات السابقة, rujukan pertama, pemisah sumber, gelar, المقدمة, dan الخاتمة (semua perhatian). Perbaikan rakit (`.rakit-*`, `{P:}`, nomor catatan kaki ulang). [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v9.2.0)

## 9.1.0 — 2026-11-07

- Baru: kaidah أبو سليمان di `cek`, perhatian «standar sumber», `@rujukan_ayat: matan`, tata letak per bagian (`@kepala`, `@fihris_*`, dll.); logo sampul jakarta tidak gepeng. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v9.1.0)

## 9.0.0 — 2026-11-05

- **Naskah lama bisa GAGAL** (ayat diketik tanpa `{Q:}`, juz/halaman tercetak). Baru: `bukti`, `rakit --fasl`, `@catatan_kaki`, `@spasi`, `@nomor: mukadimah`, profil `tatbiqi_15`/`tatbiqi_mulakhas`, `#L **Abstract**`; derajat hadits di takhrij dicek; perkiraan halaman seluruh PDF. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v9.0.0)

## 8.0.0 — 2026-11-04

- Lisensi kode MIT → AGPLv3 atau sesudahnya; `riset.txt` mencatat langkah riset connector. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v8.0.0)

## 7.0.0 — 2026-11-03

- `cek`/`cari` jauh lebih cepat dan hemat memori; `rakit` antre; `halaman` membaca rentang; `temukan --mazhab`. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v7.0.0)

## 6.2.0 — 2026-11-02

- `#V` bait syair, `@nomor: abjad`, `@format: tatbiqi`, `@pustaka: akhir`, `bahts/<orang>/<topik>`, `keluaran_saya.txt`. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v6.2.0)

## 6.1.0 — 2026-10-31

- `cek --jejak`; sampul bawaan model قسم الشريعة; kunci OpenAlex wajib untuk الدراسات السابقة. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v6.1.0)

## 6.0.0 — 2026-10-31

- `cek` lebih ketat (nomor takhrij, `@kunci` tidak dikenal, `#H`); sampul `@sampul: qism`; profil `imam_ayat16_bersambung`. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v6.0.0)

## 5.2.0 — 2026-10-29

- Connector `shamela` wajib; `@templat`, `@halaman_baru`; perapatan baris pendek. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v5.2.0)

## 5.1.0 — 2026-10-27

- `<<luar|berkas.pdf|hal>>`, `ambil <folder>`, `@angka_ayat: latin`. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v5.1.0)

## 5.0.0 — 2026-10-18

- `cek` lebih ketat mencocokkan kata, angka, ayat, dan juz/halaman tercetak. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v5.0.0)

## 4.0.1 — 2026-10-18

- `cek` dan `rakit` lebih cepat. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v4.0.1)

## 4.0.0 — 2026-10-17

- `scan`, OpenCode, `@bentuk: kitab`, `#T`, `((…))`, `@rumuz`, `@warna`. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v4.0.0)

## 3.1.0 — 2026-10-15

- Angka PDF seragam ٠١٢٣; teks Arab PDF benar saat disalin. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v3.1.0)

## 3.0.0 — 2026-10-15

- `cek` menutup celah makna terbalik dan menyebut barisnya; tes di Windows dan Ubuntu. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v3.0.0)

## 2.1.0 — 2026-10-15

- `<<luar>>`, `@tanpa: pustaka`, baris `perhatian`. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v2.1.0)

## 0.2.4 — 2026-10-10

- Juz `-` untuk kitab satu jilid bernama bagian. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v0.2.4)

## 0.2.3 — 2026-10-10

- Kunci OpenAlex dari `OPENALEX_API_KEY`. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v0.2.3)

## 0.2.2 — 2026-10-10

- `cek` lebih cepat dan memeriksa seluruh kutipan terakhir. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v0.2.2)

## 0.2.1 — 2026-10-10

- `cek` menolak bukti tanpa juz dan `<<...>>` di luar catatan kaki. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v0.2.1)

## 0.2.0 — 2026-10-10

- `dirasat` mencari menurut makna; `dirasat-pdf`. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v0.2.0)

## 0.1.0 — 2026-10-10

- `temukan "<frasa>"`: mencari frasa di isi semua kitab Shamela (lewat turath.io, tanpa akun), termasuk kitab yang belum diunduh; hasilnya nomor kitab untuk `ambil` dan juz/halaman.
- `hadits "<طرف>"`: penunjuk takhrij dari «المنصة الحديثية»: kitab, كتاب/باب, nomor, juz/halaman, dan hukum ulama beserta kitabnya. Isinya tetap dibaca di kitabnya sendiri.
- `cek` punya baris `perhatian` untuk yang lolos tetapi harus dilihat: bukti yang hanya ada di حاشية المحقق, dan kitab yang nomor halamannya buatan Shamela («مرقم آليا»).
- `cek`: petunjuk «ketemu di ج… ص…» sekarang juga mencari di حاشية dan menyebut halaman tepatnya.
- `dirasat` mencari di dua katalog (OpenAlex dan DOAJ) dan menerima kunci OpenAlex gratis di `kunci_openalex.txt`; satu katalog mati tidak menghentikan yang lain.
- Perbaikan: ayat 95:1 dan 97:1 tercetak dengan basmalah di depannya, dan `{Q:95:1:i-j}` / `{Q:97:1:i-j}` bergeser empat kata. Naskah yang memakai nomor kata di dua ayat itu perlu disesuaikan.
- `.mcp.json` mendaftarkan connector `turath` (pilihan, tanpa akun).

## 0.0.2 — 2026-10-09

- `@tanpa`, `HALAMAN_ISI`, bagian «Pemakai baru». [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v0.0.2)

## 0.0.1 — 2026-10-09

- `siapkan`, `baru`, `cek`, `rakit`, perpustakaan Shamela lokal, `dirasat`. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v0.0.1)
