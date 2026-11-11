# Uji pendekatan riset

Diuji 2 November 2026 lewat connector asli. Yang diukur: berapa sumber yang dicari benar-benar ketemu, bukan biaya. Angka ini hanya berlaku untuk soal di sini. «Ketemu» berarti frasanya ada di kitab itu, belum berarti kitab itu membahas masalahnya.

## Khilaf fiqih

Dihitung terhadap 34 kitab di `dok/mutamad.md`. Baris `scope.book_ids` berjalan sampai `has_more` false.

| Pendekatan | `خيار المجلس` | `بيع المعاطاة` | `الاستصناع` |
|---|---|---|---|
| Tanpa `scope`, `limit` 100 | 0 | 2 | 4 |
| `scope.book_ids`, satu istilah | 31 | 11 | 11 |
| `scope.book_ids`, dengan istilah lain dan kata tunggal | 32 | 29 | 16 |

Uji pertama memakai kategori mazhab, bukan nomor kitab, dan dihitung terhadap 36 nama kitab yang ditulis sebelum uji, jadi angkanya tidak bisa dibandingkan dengan tabel di atas.

| Pendekatan | `خيار المجلس` | `بيع المعاطاة` | `الاستصناع` |
|---|---|---|---|
| Per kategori mazhab, 20 | 5 | 10 | 7 |
| Per kategori mazhab, 100 | 18 | 13 | 9 |
| Per kategori, tambah satu sinonim | 25 | 24 | 9 |
| Judul bab per kategori saja | 11 | 1 | 4 |
| Sinonim dan judul bab | 29 | 24 | 11 |

Di kategori Hanbali, kitab tafrigh dan syarah modern mengisi hasil teratas. Istilah `الاستصناع` jarang dipakai mazhab Syafi'i dan Hanbali, jadi pilihan istilah per mazhab menentukan hasilnya.

## Uji buta

Soal baru, dikerjakan pemeriksa yang tidak ikut menyusun aturan, terhadap 33 kitab sebelum `21693` ditambahkan.

| Soal | Tanpa `scope`, 100 | Aturan |
|---|---|---|
| `بيع العربون` | 4 dari 33 | 19 dari 33; dengan wildcard 22 |
| `العينة` | 5 dari 33 | 22 dari 33; dengan kata tunggal 31 |
| Biografi `المتنبي` | 0 dari 15 rujukan | 15 dari 15 |
| `الشفعة للجار`, aturan sesudah diperbaiki | 5 dari 34 | 28 dari 34; dengan kata tunggal `الجوار` 34 |

Tiga soal pertama mengubah aturan: takhrij kini selalu memeriksa kategori 8, kata tunggal dan wildcard ditambahkan, dan adab mendahulukan nama lengkap. Soal keempat memakai aturan yang sudah diubah. Pada `الخراج بالضمان`, kategori 8 memberi 71 halaman dari 31 kitab. Kata tunggal hanya berarti kata itu ada, belum dibaca.

## Takhrij

Empat hadits: `كل مسكر حرام`, `لا ضرر ولا ضرار`, `من غشنا فليس منا`, `اختلاف أمتي رحمة`.

| Pendekatan | Hasil |
|---|---|
| `hadits` | 3 dari 4: nomor, juz/halaman, edisi, dan hukum; hadits keempat 0 riwayat |
| `search_hadith` | 4 dari 4 punya calon; nomor tanpa juz/halaman cetak, banyak «No Grade» |
| `shamela_search_phrase`, `category_ids: [8]` | 4 dari 4; hadits keempat 38 halaman di kitab takhrij |
| `shamela_search_hadith` | Kolom `takhrij` kosong di keempatnya |
| `search_turath` | Hasil teratas banyak fatwa dan buku modern |

Pada uji buta `البينة على المدعي`, `hadits` memberi الترمذي, sedangkan kategori 8 memberi 85 halaman, antara lain نصب الراية، البدر المنير، إرواء الغليل.

## Tafsir

Ayat uji: 2:219.

| Pendekatan | Hasil |
|---|---|
| `fetch_tafsir` sumber `qurtubi` | Bagian 1 dari 12; `has_more` true |
| `shamela_list_tafsirs_for_aya` | 738 entri, 78 punya `page_id`; 625 `not_indexed_coverage_unknown` |
| `shamela_get_tafseer_texts` | Satu halaman per kitab; kitab tanpa indeks = `not_found` |

## Adab

Soal: sumber biografi Abu Nuwas, 15 kitab rujukan yang ditulis sebelum uji.

| Pendekatan | Ketemu |
|---|---|
| `shamela_search_phrase` tanpa `scope`, 100 | 1 |
| Per kategori 25, 26, 32, 34, dua halaman | 5 |
| Tambah nama `الحسن بن هانئ` | 8 |
| `shamela_search_titles` tanpa `scope` | 9 |
| Semua digabung | 12 |

Kategori 34 tidak memberi hasil. `الأغاني` tidak ada di katalog Shamela. `الوافي بالوفيات` dan `معجم الأدباء` terlewat.

## Kutipan yang ditanam

Delapan kutipan: satu benar dan tujuh dirusak.

| Kasus | `cek` | `shamela_verify_quote` tanpa `book_id` |
|---|---|---|
| Benar | Lolos | Tidak diuji |
| Halaman salah | GAGAL, menunjuk ج3 ص480 | Hasil teratas kitab lain |
| Kitab salah | GAGAL; `--jejak` menunjuk 8463 ج3 ص481 | `verbatim`; hasil teratas kitab penukil |
| Lafaz hafalan | GAGAL, menyebut kata yang beda | Hasil teratas حاشية kitab lain |
| Kalimat muhaqqiq | `perhatian` | Tidak diuji |
| Kutipan karangan | GAGAL | `not_found` |
| Mazhab ditukar | GAGAL, menyebut kata yang beda | `partial` |
| Lintas dua halaman | GAGAL, menunjuk ص480-481 | Hasil teratas kitab lain |

`cek` tetap putusan utama. `shamela_verify_quote` tanpa `book_id` berguna saat kitab belum diunduh, tetapi hasil teratasnya bisa kitab penukil.

## MCP resmi Shamela (`shamela_resmi`)

Diuji 11 November 2026: `mcp.shamela.ws` (server `shamela` 8.1.0, milik shamela.ws, tanpa akun, 4 alat) langsung dari PC, dan `shamela.link` (34 alat) lewat Toolport. Waktu kedua sisi tidak diukur dari tempat yang sama.

| Uji | `shamela_resmi` | `shamela` (shamela.link) |
|---|---|---|
| Waktu per panggilan | 0,6–2,4 detik (`shamela_find`, rata-rata 1,6) | 0,27–1,7 detik, tengah 0,4 (`search_phrase`) |
| Panggilan berurutan | 120, 0 gagal | 117, 0 gagal |
| 20 / 60 pencarian sekaligus | 16 / 56 dibalas `busy` | tidak bisa diuji: Toolport mengantre satu-satu |
| Nomor cetak الإنصاف 21609, `page_id` 1981 | ٤/ ٣٥٧ | 4/ 357 (`cari` lokal: ج4 ص357) |
| Kata tunggal `العربون`, 34 kitab `dok/mutamad.md` | 23 halaman, 16 kitab | 23 halaman |
| Frasa `بيع العربون`, 34 kitab yang sama | 14 halaman memuat frasa, 60 panggilan | 17 halaman, 1 panggilan |
| Takhrij `البينة على المدعي`, kategori 8 | 35 halaman sesudah 40 panggilan, belum habis | `total_count` 85 halaman |
| Takhrij `كل مسكر حرام`, kategori 8 | 65 halaman sesudah 40 panggilan, belum habis | `total_count` 189 halaman |
| Frasa karangan `خيار العربون` | 20 hasil, 0 memuat frasa | 0 |
| Kalimat karangan `قطار كهربائي فائق السرعة في الصحراء` | 30 kitab | 0 |
| `إنما الأعمال بالنيات`, kategori 6 | berharakat 1 hasil; tanpa harakat 33 halaman sesudah 15 panggilan, belum habis | 231 halaman, berharakat atau tidak |
| `بيع العربون` tanpa kategori | teratas fatwa ابن عثيمين، المنجد | teratas الإشراف لابن المنذر، التنبيه، المقنع |
| Sumber tertua `لا ضرر ولا ضرار` | `date_to: 300`: الموطأ، مسند الشافعي، مسند أحمد; `sort: date_asc`: ديوان عمرو بن قميئة tanpa frasa | `period_to: 300`: teratas الخراج، الموطأ (49 halaman; `period_basis` bawaan ikut memuat kitab baru seperti التعليق الممجد) |
| Satu bab: الإنصاف «باب الشروط في البيع» (23 halaman) | panggilan pertama 15 halaman, 27.745 huruf; seluruh bab 3 panggilan; `end_page_id` lebih satu halaman (1987 = باب الخيار) | `get_toc` + `get_book_section` (6 halaman, 10.870 huruf) + 3× `get_pages_range` = 5 panggilan; `end_page_id` 1986 benar |
| Bab panjang: الإنصاف `page_id` 600 (باب صفة الصلاة) | 1 halaman, tanpa `section`, tanpa `partial`: gagal tanpa pesan | `get_toc` menemukan bab-nya |
| Bab `المجموع` 2186, `page_id` 4000 | `skipped` tidak memuat 4022-4024 padahal masih dalam `section` | belum diuji |

Pencarian `shamela_resmi` mengurutkan kecocokan kata, bukan frasa persis, dan hampir tidak pernah kosong. Balasan kosong muncul di tengah paging walau `next_cursor` masih ada. `limit` dan `book_ids` paling banyak 20. Alat `silent`, `verify_quote`, wildcard, judul bab, tafsir per ayat, dan data kitab tidak ada. Tidak ada kasus yang hanya bisa di `shamela_resmi` selain tanpa akun; bab pendek dan sedang terbaca dengan panggilan lebih sedikit, bab panjang tidak.

## Jebakan alat

- `shamela_resolve` hasil pertama salah kitab pada empat judul: `مواهب الجليل`, `تحفة المحتاج`, `أسنى المطالب`, `حاشية الدسوقي`.

## Belum diuji

- Pengaruh aturan ini pada mutu naskah yang ditulis agent.
- Soal di luar fiqih mu'amalah, hadits, tafsir 2:219, dan biografi dua penyair.
