# Catatan versi

Tiap rilis ditulis di sini: yang baru di atas. Nomor versi = `besar.kecil.tambalan`:
besar naik kalau naskah lama bisa berhenti jalan, kecil naik kalau ada kemampuan baru, tambalan naik kalau hanya perbaikan.

## Belum dirilis

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
