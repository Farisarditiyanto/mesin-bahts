# Catatan versi

Tiap rilis ditulis di sini: yang baru di atas. Nomor versi = `besar.kecil.tambalan`:
besar naik kalau naskah lama bisa berhenti jalan, kecil naik kalau ada kemampuan baru, tambalan naik kalau hanya perbaikan.

## Belum dirilis

- Sampul: `@jenis: -` = baris jenis tugas tidak tercetak (untuk tugas yang bukan بحث صفي dan nama mata kuliahnya belum diketahui). Dulu `@jenis` selalu tercetak apa adanya, jadi «-» ikut tercetak.
- `rakit`: nomor halaman di فهرس الآيات, فهرس الأحاديث, dan فهرس الموضوعات diisi ulang sampai tidak berubah. Dulu diisi sekali: angka asli («٢٤، ٣٠») lebih lebar daripada isian sementara, baris tabel melipat, judul sesudahnya terdorong ke halaman berikut, tetapi angkanya tetap angka lama (فهرس الموضوعات mencetak ٤١ padahal ada di halaman ٤٢).
- Sampul: judul «… - دراسة …» dicetak dua baris; bagian sesudah « - » jadi baris kedua yang lebih kecil (26). Judul utama dikecilkan dari 36 sampai paling kecil 26 supaya muat satu baris. Dulu judul panjang terpotong di tengah kata ke baris kedua dengan ukuran 36. Kepala halaman tetap memakai judul utuh.
- AGENTS.md: agent wajib mencari alat connector lewat pencari alatnya sebelum menyimpulkan tidak ada (di Claude Code alat connector tersembunyi sampai dicari; lewat gateway MCP seperti Toolport namanya berawalan lain). Tiap ayat yang dibahas dibaca tafsirnya lewat `tafsir`, dan masalah yang diperselisihkan dicari di kitab tiap mazhab. Dulu ada bahts yang selesai tanpa satu pun panggilan connector padahal kelimanya tersambung.

## 5.1.0 — 2026-10-27

- `<<luar|berkas.pdf|hal>>` (baru): kutipan dari PDF penelitian di folder bahts (mis. hasil `dirasat-pdf`) dicari di teks PDF itu, sebagai PENUNJUK halaman, tidak pernah lolos: ditemukan di halaman itu = perhatian «ditemukan di halaman …, cocokkan sendiri»; ada di halaman lain, berkas tidak ada atau di luar folder bahts, halaman di luar PDF, atau bagian kutipan kurang dari 6 huruf = GAGAL; tidak ada di teks PDF atau scan = perhatian. Teks PDF tidak bisa dipercaya seperti Shamela: PDF buatan Word menukar huruf sambungan («املقدمة», «هللا»), sebagian PDF membalik urutan kata per baris, dan angka tidak dicocokkan. `<<luar>>` tanpa berkas tetap seperti dulu.
- `ambil <folder>` (baru): unduh semua kitab yang dirujuk bukti naskah satu bahts; yang sudah ada dilewati.
- `cek`: kitab yang belum diunduh diringkas jadi satu baris di atas daftar GAGAL, berisi satu perintah untuk semuanya («→ 22 kitab belum diunduh; unduh semuanya sekaligus: python mesin/bahts.py ambil zuhd»). Dulu tiap bukti GAGAL sendiri-sendiri tanpa perintah gabungan (naskah dengan 22 kitab hilang = 153 baris GAGAL).
- README «Mulai»: templat permintaan lengkap (data diri, data bahts, angka, فهرس, aturan dosen) untuk ditempel sekaligus, supaya agent jarang berhenti bertanya.
- `@angka_ayat: latin` (baru): angka di catatan kaki rujukan ayat («سورة الفتح، آية: 29.») dicetak 0123, sisanya tetap ٠١٢٣ (nomor halaman, catatan kaki lain, tahun, فهرس). Untuk dosen yang menulis nomor ayat dengan 0123 tetapi tidak minta seluruh PDF 0123. Bawaan: ikut `@angka`.

## 5.0.0 — 2026-10-18

Besar naik dari 4.0.1: `cek` jauh lebih ketat. Naskah lama yang dulu lolos bisa GAGAL, terutama karena juz/halaman yang tercetak kini harus seluruhnya punya bukti (mis. «1/36-37» dengan bukti ص36 saja kini GAGAL «bukti belum mencakup 37»; lebarkan buktinya jadi `<<…|1|36-37>>`), tiap bukti harus tercetak halamannya, dan `{Q:}` di dalam kutipan harus memang ayat yang dikutip kitab di situ. Jalankan `cek` ulang untuk bahts yang sedang dikerjakan.

- `cek` lebih ketat mencocokkan kata: kutipan yang mengambil potongan kata kitab kini GAGAL. «أن القدر» tidak lagi lolos dari «فلو كان القدر» (huruf ك di depan kata hanya dianggap huruf sambung kalau sesudahnya «ال», mis. «كالله» → «الله»; ب dan ل tetap huruf sambung, mis. «لأن»/«بأن» → «أن», kecuali di «لكن», «لله» → «له», dan di depan kata nafi; و ف tetap seperti dulu), dan «بل أشك» tidak lagi lolos dari «بلا شك» (pembagian kata yang bergeser dari kitab; kata yang disambung atau dipisah di satu pihak saja, mis. «عبد الله»/«عبدالله», tetap lolos).
- GAGAL palsu yang diperbaiki: frasa yang muncul dua kali dalam satu rekaman banyak halaman kini dicari di halaman yang dirujuk, bukan hanya kemunculan pertamanya; «عليها السلام» disamakan dengan lambang ﵍; basmalah ﷽ di kitab dibaca «بسم الله الرحمن الرحيم»; «الرحمن» = «الرحمان»; «شيء» = ketikan «شي» tanpa hamzah. Cache teks kitab dibuat ulang sekali.
- `{Q:}` di tengah kutipan kini dicocokkan ke kitab: di tempat itu kitab harus memang mengutip ayat (bertanda ﴿﴾, atau teks ayatnya). Kalau tidak ada ayat (ayat sisipan, atau kata kitab seperti «ليس» yang diganti ayat), atau ayat di kitab ayat lain (nomor di rujukan [سورة: n], atau nama suratnya dan teks ayatnya sama-sama berbeda), `cek` GAGAL. Ayat lain (nomor di rujukan, rentang «[ق:٢٣- ٢٩]» dibaca utuh) atau surat lain juga GAGAL untuk `{Q:}` di awal/akhir kutipan kalau kitab menulis ayatnya tepat di sebelahnya; ayat panjang di kitab ikut dicek, ayat yang ditulis kitab dengan ejaan imla'i («الصراط», «تجارة») tetap dikenali, dan ayat yang sama persis di dua tempat («مرضى أو على سفر») tidak dianggap ayat lain, rujukan kitab yang salah nomor padahal teks ayatnya memang ayat `{Q:}` cukup perhatian, dan `{Q:}` yang bersebelahan dengan «...» tetap harus ada ayatnya di bagian kitab yang dilompati. Kalau selain ayat ada lebih dari 20 huruf kitab yang dilompati: perhatian. Bagian pendek yang menempel ayat (mis. «{Q:22:70} [الحج:٧٠]») tidak lagi GAGAL «terlalu pendek», asal di kitab ia kata utuh yang tepat menempel ayatnya (kata pendek karangan seperti «لا» di samping `{Q:}` tetap GAGAL). «﴿٢٨﴾» yang diketik sendiri di kutipan dicek sebagai teks biasa, bukan GALAT MESIN.
- Angka di kutipan kini dicocokkan dengan angka kitab di tempat kutipan itu, bukan di mana saja di halaman: angka yang diganti angka lain GAGAL, angka yang dibuang atau ditambah jadi perhatian. «و٢٦٧» di kitab tidak lagi dibuang sebagai nomor catatan kaki. Kutipan yang mulai dengan nomor hadits tanpa angka sebelumnya («١٩/ ٤٧ - وعن» dikutip «47 - وعن») tidak diberi perhatian angka.
- Perhatian kata nafi kini juga untuk لم/ولم/فلم, لن/ولن/فلن, وليس/فليس, ليست, بلا, untuk kata nafi di akhir halaman sebelumnya, dan untuk kutipan yang menyambung ke halaman berikutnya.
- «…» milik kitab sendiri yang ikut disalin tidak lagi membuat kutipan GAGAL «terlalu pendek» kalau kutipan utuhnya bersambung di kitab.
- Celah tanda naskah yang ditutup (kini GAGAL): kutipan bertanda petik (empat kata atau lebih, selain judul kitab) di dalam catatan kaki berbukti kini dicek ke halaman bukti catatan kaki itu (`{Q:}` di dalamnya dicek seperti di matan; GAGAL hanya untuk nukilan yang diantar «…:» atau «قال …», mis. «قال الشيخ: "…"، المصدر» dan «قال ابن عثيمين "…"»; judul, istilah, judul yang disusul koma, dan catatan kaki ber-`<<luar>>` cukup perhatian; judul kitab Shamela, boleh disusul pengarang, mis. «"شرح … لابن عثيمين"، ص6», dilewati, begitu juga judul cetak lengkap kitab buktinya sendiri («رياض الصالحين من كلام سيد المرسلين»), tetapi teks lain yang hanya diawali atau diselipi judul tetap dicek); catatan kaki bukti saja `[^<<sid|juz|hal|potongan>>]` kini mengecek seluruh paragraf, bukan hanya potongannya; «سورة …» hanya membebaskan kutipan yang isinya ayat saja, bukan kutipan lain yang ditulis sesudah `{Q:}` atau prosa di samping `{Q:}` di dalam tanda petik (juga yang dibungkus «﴿…﴾» ketikan sendiri); «سبق تخريجه، ص{P:kunci}» kini mengecek kutipannya ke halaman bukti catatan kaki pertama `{H:…|kunci}` (potongan lain hadits yang sama lolos; potongan kata GAGAL, kata nafi yang dibuang dan hadits bernomor lain di halaman itu jadi perhatian); bukti nomor kosong `<<…|#>>`; `{Q:s:a-b:i-j}` (kata ke-i s.d. j hanya untuk satu ayat).
- GAGAL palsu yang diperbaiki: kutipan yang dibungkus lafaz matn `(("…"))`, dan tanda arah tak terlihat (RLM, ZWNJ, U+202A–U+202E, BOM, dan sejenisnya) di antara tanda petik penutup dan `[^`, tidak lagi membuat kutipan tak dikenali («[tanpa kutipan]»); `{Q:1:٢}` dan `{Q:1:02}` dibaca ayat 2, bukan GALAT MESIN.
- Juz/halaman yang tercetak kini dicocokkan lebih ketat (kini GAGAL): tiap bukti di catatan kaki harus tercetak halamannya, bukan cukup salah satunya; di catatan kaki yang merujuk beberapa kitab, halaman yang tercetak sesudah judul suatu kitab dicocokkan dengan bukti kitab itu sendiri (halaman dua kitab yang tertukar tidak lagi lolos); rentang yang tercetak harus di dalam rentang bukti (ص5-55 untuk bukti ص5 tidak lagi lolos; pesannya menyebut halaman yang belum punya bukti: «bukti belum mencakup 6-55»); «j/n» juz lain dan «صn» yang tidak punya bukti ikut dicek; «ص» hanya dibaca nomor halaman kalau berdiri sendiri atau disambung و/ف («النص 5» bukan halaman, «وص6» halaman); rentang «ص5–55» (tanda pisah Word) dan daftar «ص5، 55», «ص5 و55», «1/55، 66» ikut dicek (daftar seperti «ص5 و6» dan «1/37، 38» untuk dua bukti lolos). Nomor hadits «رقم (5/ 103)», halaman bahts sendiri «ص3 من هذا البحث» / «ص3-4 من هذا البحث», dan tahun «1423ه» / «ص5، 1423» bukan halaman kitab; «للحديث (1/ 222)» dan «1/102، 103» (satu bukti 102-103) tetap terbaca sebagai halaman bukti. Judul kitab yang termuat di judul kitab lain («زاد المستقنع» di «الشرح الممتع على زاد المستقنع») tidak lagi memotong catatan kaki di tempat yang salah; nama pengarang juga menandai tempat kitabnya (takhrij «أخرجه البخاري، …، 7/2، ومسلم، …، 2/1020» walau judul lengkapnya baru di data cetak di ujung, «المغني، ابن قدامة»); catatan kaki beberapa kitab yang judul dan pengarangnya tidak dikenali kini perhatian. Satu catatan kaki yang halamannya salah kini satu galat saja.
- Ayat bertanda ﴿﴾ di kitab yang tidak termuat persis di `{Q:}` kini ditandingkan dengan seluruh mushaf: ayat lain yang memuatnya persis, atau yang lebih dekat baik kerangkanya (tanpa alif, waw, ya, dan hamzah, supaya beda ejaan imla'i dan utsmani tidak dihitung) maupun huruf lengkapnya, membuat `cek` GAGAL («مهتدون» 43:22 untuk `{Q:43:23}`; «وأوحينا إليه» 12:15 untuk `{Q:23:27}` «فأوحينا»). Yang sama dekatnya, atau lebih dekat hanya di salah satu ukuran, jadi perhatian yang menyebut ayat saingannya. Ayat pendek yang salah ketik di kitab («﴿وَءَاثُوا الزَّكَاةَ﴾» untuk `{Q:2:43:3-4}`) tidak lagi GAGAL palsu «surat lain», cukup perhatian «salah ketik?»; «العزيز القحيم» dibaca 26:9 «الرحيم» (satu huruf beda), bukan «الحكيم». Batasnya: potongan ayat yang kerangkanya kurang dari 5 huruf tidak ditandingkan, dan ayat lain yang kerangka serta huruf lengkapnya sama dekat dengan ejaan imla'i kitab bisa tetap lolos. GAGAL/perhatian palsu lain yang ketemu di naskah bahts asli: angka catatan kaki kitab «(١)» sesudah kurung penutup kutipan «(…).» tidak lagi dianggap angka kutipan.
- Bukti halaman 0 (teks Shamela tanpa nomor halaman: mukadimah, sampul jilid) dan rentang bukti lebih dari 50 halaman kini GAGAL dengan pesan jelas; rentang raksasa (mis. `4-99999999`) dulu membuat `cek` mati kehabisan memori tanpa laporan.
- Kutipan yang menyambung lintas rekaman kini dirangkai menurut urutan halaman, dan hanya rekaman yang halamannya bersambung: sambungan dua halaman yang tidak bersambung di cetakan tidak lagi lolos, dan kutipan lintas halaman di kitab yang urutan rekamannya berselang-seling (mis. سبل السلام) tidak lagi GAGAL palsu. Kutipan dari حاشية yang bersambung ke halaman berikutnya kini lolos dengan perhatian حاشية, bukan «TIDAK KETEMU».
- Perhatian baru: nomor halaman Shamela yang menyendiri jauh dari halaman lain juz itu (mis. ص3110 di antara ص310 dan ص312), biasanya salah ketik Shamela: cocokkan ke cetakan.
- Jalur bahts relatif kini dibaca dulu dari folder tempat perintah dijalankan, baru dari folder mesin: `cek .` di dalam folder bahts, `cek mesin-bahts/contoh` dari folder di atasnya, dan `cek ../<bahts>` dari bahts lain kini jalan. Folder di luar folder mesin tetap ditolak. `baru` mencetak letak lengkap naskahnya.
- `periksa` di Python bawaan Linux/macOS yang menolak `pip` (Ubuntu 23.04+, Debian 12, Homebrew; «externally managed») kini menyuruh memasang pustaka di `.venv` dalam folder mesin, lalu memakai Python `.venv` itu. Pesan «pustaka belum terpasang» perintah lain menunjuk ke `periksa`.
- Pintu pemakai: `temukan` dan `hadits` yang kosong keluar dengan kode 1 seperti pencarian lain; `hadits` tanpa huruf Arab ditolak tanpa memakai jatah layanan; `scan` dengan nomor kitab bukan angka memberi pesan yang sama dengan perintah lain; `katalog` dengan pengulangan raksasa (mis. `a{99999999999}`) dicari sebagai teks biasa, bukan galat Python; pesan naskah bukan UTF-8 di Linux/macOS tidak lagi menyuruh membuka Notepad.

## 4.0.1 — 2026-10-18

Tambalan naik dari 4.0.0: hanya percepatan dan perbaikan; naskah lama tetap jalan tanpa diubah.

- `cek` jauh lebih cepat untuk bahts yang merujuk banyak kitab besar: hanya halaman yang dirujuk yang dibaca, bukan seluruh kitab. Diukur (median 5 jalan): bahts 32 kitab 7,8 → 1,7 detik; bahts lain 5,9 → 1,0 dan 2,2 → 0,45 detik. Hasil `cek` tidak berubah. `cek` pertama sesudah memperbarui mesin sekali lebih lama: tiap kitab dibuatkan `indeks.json` di foldernya.
- Cache teks kitab (`padat-….json.gz`) tidak lagi dibuat ulang tiap kali `mesin/shamela.py` berubah (juga untuk perubahan yang tidak menyentuh penyamaan huruf); hanya kalau aturan penyamaan huruf (`mesin/norma.py`) berubah.
- `rakit` lebih cepat untuk bahts bercatatan kaki: Word menyusun dalam tampilan Draft, dan nomor catatan kaki dicocokkan ke halaman tanpa menyusun ulang halaman dari awal dokumen tiap catatan kaki. Diukur (median 3 jalan, bergantian dengan versi lama): bahts 28 halaman 111 catatan kaki 136 → 75 detik, bahts 11 halaman 12 catatan kaki 34 → 24 detik; bentuk kitab 187 halaman tanpa catatan kaki tetap ±200 detik. Naskah sangat pendek tidak lebih cepat: `contoh` (7 halaman, 2 catatan kaki) 14,0 → 15,6 detik. PDF dan laporan sama persis dengan sebelumnya (dibandingkan per piksel tiap halaman).
- .docx hasil `rakit` terbuka dalam tampilan Print Layout (dulu Draft).
- `cek`: kesalahan di dalam mesin tidak lagi dilaporkan sebagai «tanda rusak» naskah, tetapi «GALAT MESIN … laporkan barisnya ke pengurus mesin bahts».

## 4.0.0 — 2026-10-17

Besar naik dari 3.1.0: `((` dan `))` kini tanda lafaz matn. Naskah lama yang memakai `((` tanpa `))` dulu lolos, kini GAGAL («tanda (( tidak ditutup dengan ))»); `((…))` yang berpasangan kini tercetak merah. Kalau maksudnya kurung biasa, tulis satu kurung `(…)` atau «…».

- Perintah baru `scan <id> <juz> <hal>`: alamat scan cetakan (PDF di turath.io) untuk halaman itu, dengan nomor halaman PDF-nya, untuk mencocokkan bacaan Shamela yang meragukan. Butuh internet; tidak semua kitab punya scan. Kitab bernomor halaman buatan Shamela diberi peringatan bahwa halaman scan bisa meleset.
- Agent gratis: OpenCode membaca daftar connector dari `opencode.json` baru (termasuk masuk `shamela`), Command Code membaca `.mcp.json`, Hermes mendaftarkannya dengan `hermes mcp add`. README menyebut agent mana yang gratis dan bahwa aplikasi desktopnya memakai connector yang sama.
- Bentuk baru `@bentuk: kitab` untuk karya yang bukan bahts (mis. muqarrar gabungan dua syarah): tanpa sampul bahts, wajib hanya `@judul`, `#R` tidak wajib, dan hanya `#K` mulai halaman baru. Kepala halaman bergaris bawah seperti cetakan kitab: halaman genap mencetak `@judul`, halaman ganjil judul bab (`#K` atau فهرس) yang sedang berjalan.
- `#T teks` = kotak matn: paragraf dalam bingkai merah tipis, teksnya merah.
- `((…))` = lafaz matn di dalam syarah: tercetak merah tebal di dalam kurung, seperti cetakan syarah.
- `@rumuz: sid=ض، sid=ف`: catatan kaki yang buktinya dari kitab itu dicetak dengan rumuznya ض (huruf kecil cokelat terangkat). Catatan kaki berisi bukti saja (`[^<<sid|juz|hal>>]`, semua sid-nya di `@rumuz`) tidak dicetak; yang tercetak hanya rumuznya, dan `cek` mencocokkan SELURUH paragraf sebelumnya kata per kata ke halaman itu (paragraf syarah yang disalin dari kitabnya). `sid=-` = dicek tanpa rumuz (mis. kitab matn).
- `@warna: sid=biru`: paragraf yang buktinya dari kitab itu saja (`[^<<sid|..>>]`, sid juga di `@rumuz`) dicetak biru tua dengan garis biru tegak di sisi kanannya (tetap terlihat di fotokopi hitam putih), mis. ziyadah syarah kedua yang diselipkan di dalam syarah pertama. Warnanya diambil dari bukti, jadi tidak bisa berbeda dengan sumbernya; lafaz matn `((…))` di dalamnya tetap merah.
- Lambang hormat ﵀ ﵁ ﵃ ﷾ ﷿ dan sejenisnya (Unicode 14) kini dicetak dengan kalimatnya («رضي الله عنهم»). Dulu jadi kotak kosong di PDF: huruf cetak (Traditional Arabic, Sakkal Majalla) tidak punya glyph-nya. ﷺ tetap dicetak sebagai lambang.
- `rakit`: garis paragraf (bingkai, garis kepala halaman) kini ikut ke PDF. Dulu Word membuang garis itu saat menyimpan PDF selama layarnya dimatikan.

## 3.1.0 — 2026-10-15

Kecil naik dari 3.0.0: kemampuan baru `@angka`; naskah lama tetap jalan tanpa diubah, tetapi PDF-nya kini mencetak angka ٠١٢٣ (tulis `@angka: latin` untuk 0123).

- Angka di PDF seragam ٠١٢٣ (bawaan): nomor halaman, nomor catatan kaki di matan dan di bawah, juz/halaman rujukan, tahun, nomor ayat, isi المصادر dan الفهارس, juga sampul. Dulu campur: «آية: ٢» tapi «ص5», «1423هـ», (1), dan nomor halaman 1. Angka di teks Latin (tautan, DOI, judul berbahasa Latin) tetap 0123. Naskah boleh diketik dengan angka mana saja. Dosen minta 0123: `@angka: latin`. Dasarnya di README bagian «Standar halaman».
- Teks Arab PDF jauh lebih benar saat disalin atau dicari: dulu «الله» tersalin «هللا», «المقدمة» «املقدمة», «في» «يف», ligatur «نا» «نًّ», dan syaddah jadi «ن». Tampilan halaman tidak berubah. Diukur pada bahts 32 halaman (berapa kata berbeda di naskah yang muncul utuh di teks salinan), lewat mesin baca PDF masing-masing: PDFium (Chrome/Edge) 65% → 94%, pdf.js (Firefox) 68% → 97%, MuPDF (SumatraPDF) 69% → 99%; pemeriksa dengan cara hitung lain mendapat 84%, 91%, 91%. Yang masih salah: ﷺ tersalin terbalik di MuPDF (benar di PDFium dan pdf.js), harakat yang terpisah dari hurufnya, kata yang terpotong di ujung baris, dan teks ayat mushaf. Pembaca tanpa pembalik urutan (mis. pustaka pypdf) justru turun (98% → 69%); Acrobat dan pembaca PDF Apple belum dicoba. Butuh dua pustaka Python baru (`pypdf`, `fonttools`): `periksa` menyebut perintah pasangnya.
- Nomor catatan kaki kini ditulis mesin sendiri, karena nomor otomatis Word selalu 0123. Akibatnya `KATA` di laporan `rakit` tidak lagi menghitung nomor catatan kaki (bahts 120 catatan kaki: 240 kata lebih sedikit).
- Sampul memakai logo resmi جامعة الإمام yang terbaru (halaman الهوية البصرية kampus, April 2025): bingkai emas, tulisan «١٣٩٤هـ / 1974» dan nama kampus berbahasa Inggris. Dulu logo versi lama dari Wikipedia.
- `rakit` meminjam pengaturan «Numeral» Word selama merakit dan mengembalikannya sesudahnya.

## 3.0.0 — 2026-10-15

Besar naik dari 2.1.0: naskah lama yang dulu lolos bisa kini GAGAL di dua celah yang ditutup (kutipan «ما/لا» yang di kitab tertulis «كما/لما/بلا», dan `<<luar>>` untuk kitab yang sudah diunduh). Sebaliknya, beberapa GAGAL palsu hilang. Isinya hasil riset proyek sejenis di GitHub dan audit tiap perintah.

- `cek` tidak lagi GAGAL palsu untuk:
  - angka Arab di catatan kaki («آية: ٢», «٢/١٥», «2/ 100»);
  - kalimat hormat bentuk panjang («رضي الله تعالى عنه», «رحمه الله تعالى», «صلى الله عليه وعلى آله وسلم», «عليه الصلاة والسلام»);
  - kursi hamzah (مسئول/مسؤول، رءوس/رؤوس، التساءلات/التساؤلات) dan ejaan ganda (السماوات/السموات، إسحاق/إسحق، داوود/داود);
  - huruf Urdu/Persia yang terbawa dari PDF;
  - kutipan yang menyambung ke halaman berikutnya (`<<…|5-6>>`).
- `cek` menutup celah: «ما …» yang dikutip dari «كما …»/«لما …» (maknanya terbalik); bukti `#nomor` yang cocok dengan nomor catatan kaki; `<<luar>>` untuk kitab yang sudah diunduh. Kitab مخطوط/غير مطبوع jadi `perhatian`: nomornya nomor lembar, bukan halaman cetak.
- Pesan `cek` menyebut barisnya («baris 15: …»). Kutipan yang hampir cocok ditunjuk kata pertama yang berbeda: «cocok 8 dari 9 kata …, lalu naskah «والتدابير», kitab «والتدبير»».
- `cari`, `teks`, `bab`, dan `cek` jauh lebih cepat di kitab besar (فتح الباري: ±9 dtk → ±1 dtk). Teks yang sudah dinormalisasi disimpan sekali di folder kitabnya saat `ambil`.
- `hadits`: «من غشنا» juga menemukan «ومن غشنا» (riwayat مسلم dulu terlewat). Kalau البخاري/مسلم tidak muncul, dicetak «riwayat mirip, lafaznya berbeda».
- `dirasat`: pencarian makna OpenAlex yang kehabisan waktu tidak diulang lagi (±37 dtk → ±12 dtk), dan alasannya dicetak.
- Permintaan ke layanan luar dicoba lagi sendiri kalau koneksi putus sesaat.
- Perintah: jalur lengkap folder bahts diterima; `halaman` membaca «05»/«٥»; `katalog` paling banyak 30 baris; pencarian yang kosong keluar dengan kode 1; salah pakai mencetak bentuk perintahnya; `ambil` lebih cepat.
- Tes otomatis jalan di Windows dan Ubuntu, memeriksa naskah jebakan per baris (bukan hanya jumlahnya), dan mengurai `rakit.ps1`. Gambar «cara cek bekerja» di README memakai keluaran `cek` yang baru.

## 2.1.0 — 2026-10-15

Besar naik dari 0.2.4: naskah lama yang dulu lolos bisa kini GAGAL, karena `cek` menutup celah kutipan karangan.

- `cek` lebih ketat: kutipan bertanda petik selalu dicek ke halaman buktinya (juga kalau buktinya membawa potongan sendiri), harus utuh per kata, dan kutipan tanpa bukti GAGAL. Petik “ ”, ‘ ’, dan ' dikenali; kutipan boleh dipotong `...` (masuk `perhatian`).
- Tanda baru `<<luar>>` untuk sumber di luar Shamela (jurnal, PDF penelitian): lolos sebagai `perhatian`; kalau judulnya kitab Shamela, GAGAL.
- `@tanpa: pustaka`: PDF tanpa المصادر والمراجع untuk dosen yang minta sumber cukup di catatan kaki.
- `perhatian` baru: kutipan tanpa catatan kaki sendiri, kata nafi (لا/ما/ليس) sebelum kutipan di kitab, angka yang tidak terbaca di halaman itu. `cek` juga mencetak perkiraan halaman isi.
- Pencarian kitab menyamakan huruf Persia, ligatur, kalimat hormat, dan «ابن/بن»; halaman حاشية benar; `teks`, `bab`, dan `katalog` lebih tepat; `ambil` mencoba ulang unduhan yang putus.
- Pemakai baru: usulan untuk salah ketik, jalur lengkap di tiap petunjuk, pesan bahasa Indonesia tanpa traceback, cek huruf sebelum Word dibuka.
- `dirasat` dan `hadits` memberi pesan jelas saat layanannya rusak; satu sumber rusak tidak menghapus hasil sumber lain.
- PDF: dua `{P:}` dalam satu catatan kaki terisi; pustaka tanpa القرآن bernomor dari 1; Word ditutup rapi; dua `rakit` bersamaan ditolak.
- README diringkas dan gambar diperbarui. Tes otomatis memeriksa naskah jebakan: tiap celah yang ditutup harus GAGAL.

## 0.2.4 — 2026-10-10

- `cek` menerima juz `-` untuk kitab satu jilid yang di Shamela dibagi menjadi bagian bernama (mis. «الفوائد»: المقدمة + الكتاب): dulu rujukan «ص136» ditolak sebagai «berjilid» dan tidak bisa ditulis dengan benar. Kitab yang punya juz berangka tetap wajib menyebut juznya.
- Aturan kerja: connector `shamela_*` yang tersedia wajib dipakai mencari bahan tiap مبحث, dan laporan akhir menyebut alat pencari yang dipakai.

## 0.2.3 — 2026-10-10

- `dirasat` dan `dirasat-pdf` membaca kunci OpenAlex dari variabel lingkungan `OPENALEX_API_KEY` kalau `kunci_openalex.txt` tidak ada (mis. di cloud). Berkas tetap didahulukan.

## 0.2.2 — 2026-10-10

- `cek` jauh lebih cepat: naskah 1500 bukti dari 2,7 jadi 1,4 detik; naskah yang banyak buktinya salah dari 2 menit jadi 5 detik. `cari semua` dari 4,4 jadi 3,2 detik.
- `cek` memeriksa SELURUH kutipan terakhir sebelum catatan kaki, termasuk kutipan di dalamnya: `«قال: "…" ثم سكت»` diperiksa utuh. Dulu hanya kutipan dalam, atau potongan sesudahnya. Akibatnya `"قال: «…»"` sekarang harus persis ada di kitab berikut «قال»-nya.
- `cek` tidak lagi salah menolak kutipan yang mulai tepat di awal halaman baru (mis. `<<1681|3|144>>` untuk «في العتق وفضله» dulu dibilang «hal 143-144»).
- `cari`, `teks`, `bab`, dan `cek` menyamakan ejaan lama «شئ» dengan «شيء», tetapi «شئت» tidak ikut berubah; angka di frasa pencarian diabaikan.
- Mesin lebih ramping: cara menyamakan huruf Arab dan mencari halaman cetak kini satu, dipakai `cek` dan `cari` bersama. Isi .docx/.pdf hasil `rakit` tidak berubah.

## 0.2.1 — 2026-10-10

- `cek` menolak bukti tanpa juz (`<<id|-|hal>>`) untuk kitab berjilid: dulu lolos walau juznya tidak diketahui.
- `cek` menyebut kalau juz yang ditulis tidak ada di kitab itu, atau kalau kitabnya satu jilid (tulis juz `-`).
- `cek` menolak `<<...>>` di luar catatan kaki: dulu ikut tercetak di naskah.
- `cek` menolak ayat dengan rentang terbalik (mis. `{Q:1:7-1}`): dulu tercetak kosong.
- `cek` mengenali kutipan bersarang, mis. `"قال: «…»"` sebelum catatan kaki: dulu dianggap tanpa kutipan.
- Petunjuk «ketemu di …» menyebut sampai tiga tempat, juz yang ditulis didahulukan: dulu hanya tempat pertama di kitab.
- Catatan kaki «سبق تخريجه» tidak lagi masuk daftar «catatan kaki tanpa bukti».
- `baru` hanya menerima nama folder huruf Latin, angka, `-`, `_`: dulu `../x` membuat folder di luar repo.
- `bab` untuk kitab yang belum diunduh dan `ambil` dengan nomor yang bukan angka memberi pesan jelas.
- Keluaran yang dipotong (mis. `| head`) tidak lagi dilaporkan sebagai gagal mengunduh.

## 0.2.0 — 2026-10-10

- `dirasat` mencari juga menurut makna: pertanyaan panjang menemukan penelitian yang kata-katanya lain. Hasilnya menyebut bahasa, jumlah kutipan, nomor OpenAlex, dan sisa jatah hari itu.
- `dirasat "<kata>" [maks] [saringan]`: saringan OpenAlex, mis. `language:ar,type:dissertation`.
- `dirasat` ikut mencari di kumpulan tambahan OpenAlex, tempat banyak risalah kampus berada; kalau mesin pencari makna OpenAlex sibuk, dicoba lagi sendiri.
- `dirasat-pdf <W…> <folder>`: mengunduh PDF penelitian ke folder bahts (butuh kunci OpenAlex).
- Kunci OpenAlex dikirim lewat kepala permintaan, bukan lewat alamat.
- `temukan` tidak lagi menunggu puluhan menit kalau jatah pencarian turath.io habis: ia berhenti dan menyebut kapan terbuka lagi.
- `.mcp.json` mendaftarkan connector pilihan `hadithunlocked`, `tafsir`, dan `quran`.

## 0.1.0 — 2026-10-10

- `temukan "<frasa>"`: mencari frasa di isi semua kitab Shamela (lewat turath.io, tanpa akun), termasuk kitab yang belum diunduh; hasilnya nomor kitab untuk `ambil` dan juz/halaman.
- `hadits "<طرف>"`: penunjuk takhrij dari «المنصة الحديثية»: kitab, كتاب/باب, nomor, juz/halaman, dan hukum ulama beserta kitabnya. Isinya tetap dibaca di kitabnya sendiri.
- `cek` punya baris `perhatian` untuk yang lolos tetapi harus dilihat: bukti yang hanya ada di حاشية المحقق, dan kitab yang nomor halamannya buatan Shamela («مرقم آليا»).
- `cek`: petunjuk «ketemu di ج… ص…» sekarang juga mencari di حاشية dan menyebut halaman tepatnya.
- `dirasat` mencari di dua katalog (OpenAlex dan DOAJ) dan menerima kunci OpenAlex gratis di `kunci_openalex.txt`; satu katalog mati tidak menghentikan yang lain.
- Perbaikan: ayat 95:1 dan 97:1 tercetak dengan basmalah di depannya, dan `{Q:95:1:i-j}` / `{Q:97:1:i-j}` bergeser empat kata. Naskah yang memakai nomor kata di dua ayat itu perlu disesuaikan.
- `.mcp.json` mendaftarkan connector `turath` (pilihan, tanpa akun).

## 0.0.2 — 2026-10-09

- `@tanpa: ayat, hadits, maudhuat` membuang فهرس yang tidak diinginkan; فهرس الآيات dan فهرس الأحاديث yang kosong tidak lagi dicetak.
- `rakit` mencetak `HALAMAN_ISI` (المقدمة sampai الخاتمة).
- `periksa` memberi jalan memasang huruf Traditional Arabic tanpa membuka Settings.
- `periksa`: menyebut apa yang sudah siap di komputer dan perintah untuk tiap yang belum.
- `AGENTS.md` punya bagian «Pemakai baru» untuk orang yang baru pertama kali memakai agent.
- README: gambar hasil, gambar alur, dan «Cara tercepat».
- `siapkan` punya sumber font kedua: salinan di rilis GitHub proyek ini.
- `.mcp.json` mendaftarkan connector `shamela` (pilihan) untuk Claude Code.
- Unduhan yang putus di tengah tidak lagi dianggap jadi: `ambil` mengunduh ulang, `siapkan` pindah ke sumber font berikutnya.
- `@thalibah` selain «ya» ditolak `cek`; `sampul_saya.txt` yang bukan UTF-8 ditolak `baru` dengan pesan jelas.

## 0.0.1 — 2026-10-09

Rilis publik pertama. Nomor 0.x berarti masih tahap awal: bentuk naskah dan perintah masih bisa berubah.

- `siapkan`: mengunduh katalog kitab dan font mushaf, lalu memasang font itu.
- `baru`, `cek`, `rakit`: dari `naskah.txt` sampai `.docx` dan `.pdf` (rakit: Windows + Microsoft Word).
- `katalog`, `ambil`, `kartu`, `cari`, `teks`, `bab`, `halaman`: perpustakaan Shamela lokal.
- `dirasat`: mencari penelitian terdahulu di OpenAlex.
- Pembimbing tercetak di sampul hanya kalau `@musyrif` diisi.
- `@thalibah: ya` membuat sampul mencetak «اسم الطالبة».
- Data sampul pemakai cukup ditulis sekali di `sampul_saya.txt`.
