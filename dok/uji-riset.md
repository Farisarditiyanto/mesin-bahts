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

## MCP resmi Shamela (tidak dipasang)

Diuji sebagai connector `shamela_resmi`, lalu dibuang pada hari yang sama: frasa karangan dan kalimat ngawur tetap memberi hasil, dan yang hanya dia punya (tanpa akun, bab pendek dengan lebih sedikit panggilan) sudah tertutup `turath`, login Command Code ke shamela.link, dan baca bab dari kitab lokal.

Diuji 11 November 2026: `mcp.shamela.ws` (server `shamela` 8.1.0, milik shamela.ws, tanpa akun, 4 alat) langsung dari PC, dan `shamela.link` (34 alat) lewat Toolport. Waktu kedua sisi tidak diukur dari tempat yang sama.

| Uji | `mcp.shamela.ws` | `shamela` (shamela.link) |
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

Pencarian `mcp.shamela.ws` mengurutkan kecocokan kata, bukan frasa persis, dan hampir tidak pernah kosong. Balasan kosong muncul di tengah paging walau `next_cursor` masih ada. `limit` dan `book_ids` paling banyak 20. Alat `silent`, `verify_quote`, wildcard, judul bab, tafsir per ayat, dan data kitab tidak ada. Tidak ada kasus yang hanya bisa di `mcp.shamela.ws` selain tanpa akun; bab pendek dan sedang terbaca dengan panggilan lebih sedikit, bab panjang tidak.

## Connector `qurangallery` (dipasang sebagai cadangan pertama `shamela`)

Diuji 19 November 2026: `qurangallery.com/mcp/shamela` (server `qurangallery-shamela` 0.3.0, peladen pustaka 1.4.0, 15 alat) langsung dari PC dengan kunci gratis, dan `shamela.link` (34 alat) lewat Toolport. Waktu kedua sisi tidak diukur dari tempat yang sama. Angka `shamela` yang tidak diuji ulang hari itu diambil dari tabel 11 November di atas.

| Uji | `qurangallery` | `shamela` (shamela.link) |
|---|---|---|
| Akun | tanpa akun (10 panggilan per menit, 200 per hari); kunci gratis 60 per menit | akun + masuk OAuth |
| Waktu per panggilan | 0,34–2,3 detik, tengah 1,2 (32 panggilan) | 0,3–0,9 detik (4 pencarian) |
| 60 panggilan berurutan dalam 24 detik | 34 dijawab, 26 ditolak (HTTP 429) | 117 berurutan, 0 gagal (11 November) |
| Nomor kitab | sama: 11223, 2186, 6910, 21609 | — |
| Frasa `بيع العربان`, 9 kitab Hanbali `dok/mutamad.md` | 2 halaman: 6910:2941, 776:2035 | 2 halaman yang sama |
| Frasa `بيع العربون`, 34 kitab `dok/mutamad.md` | 17 halaman, 1 panggilan | 17 halaman, 1 panggilan |
| Kata tunggal `العربون`, 34 kitab yang sama | 23 halaman, 16 kitab | 23 halaman |
| Takhrij `البينة على المدعي`, kategori 8 | 85 halaman, 4 panggilan (`limit` 25) | `total_count` 85 halaman |
| Takhrij `كل مسكر حرام`, kategori 8 | 189 halaman, 8 panggilan; `candidate_cap_hit` true | `total_count` 189 halaman |
| `إنما الأعمال بالنيات`, kategori 6 | 228 halaman, 10 panggilan; `candidate_cap_hit` true | 231 halaman |
| Frasa `خيار المجلس`, kategori 16, `limit` 100 | 34 baris dari 100 (sisanya di `rows_dropped`), `total_verified` 200, `candidate_cap_hit` true | 100 baris, `total_count` 895 |
| Frasa karangan `خيار العربون` | 0 | 0 |
| Kalimat karangan `قطار كهربائي فائق السرعة في الصحراء` | `match: "phrase"` 0; `match: "words"` 148 halaman dengan `relaxed_min_match` 3; dengan `relax_when_empty: false` 0 | 0 |
| `shamela_verify_quote` «فالحاصل أن هذا الحديث ضعيف» tanpa kitab | `found`: 2186 ج9 ص335 (`body`) dan حاشية تفسير ابن كثير 1509 | `not_found` (catatan: calon terlalu banyak, hanya sebagian diperiksa) |
| Nomor cetak الإنصاف 21609, `page_id` 1981 | 4/ 357; `shamela_cite` `printed_page` (ج4 ص357) → `page_id` 1981 | 4/ 357 |

Yang hanya ada di `shamela`: `shamela_research_scope` (status `silent`), `shamela_scan_consensus`, dan paging tanpa batas huruf. Yang hanya ada di `qurangallery`: juz/halaman cetak → `page_id` (`shamela_cite`), daftar rawi dan sanad (`shamela_lookup_rijal`; mutunya belum diuji), dan tanpa akun. `shamela_search` mode `batch` (satu panggilan, satu `scope` per soal) memberi jumlah halaman per kategori mazhab, tetapi mencocokkan kata sehalaman (bukan frasa) dan tidak memberi status `silent`.

## Connector `qaf` (dipasang sebagai pencari menurut makna)

Diuji 26 November 2026 lewat API Qaf v1 (`api.qaf.ai/v1`, kunci akun gratis; isinya sama dengan MCP resmi `api.qaf.ai/mcp`) dan `shamela.link` lewat Toolport, dari PC yang sama.

| Uji | `qaf` | `shamela` (shamela.link) |
|---|---|---|
| Akun | akun Qaf gratis (MCP: masuk OAuth); 60 permintaan per menit, 2.500 `search` per minggu | akun + masuk OAuth |
| 75 permintaan serentak (`lookup_catalog`) | 60 dijawab, 12 ditolak HTTP 429 (`reason: minute`, `retryAfter` 59), 3 sambungan putus | — |
| Waktu `search` | 0,34–1,19 detik (12 kueri); 20 serentak: tengah 0,6, paling lama 0,82 | `shamela_search_pages`: 0,47–10,5 detik per 3 kueri serentak |
| Nomor kitab | `versionId` = nomor Shamela di 15 kitab (21731, 767, 913, 931, 900, 107, 142264, 30065, 9979, 32535, 14596, 37793, 7687, 12293, 2300) | — |
| Halaman | perkiraan: 9979 «1/500» (Shamela «500»); 12293 «15/15, 15/17» (awal nash di 15/17); 142264 kitab audio «1/7447» = nomor urut Shamela | `printed_page` |
| Kutipan الكافي 21731 «ومن ادعى الجهل بتحريم الزنا…» | 4/87 | `shamela_verify_quote`: `verbatim`, 4/ 87 |
| «حكم صلاة الجماعة للرجال» | tanpa saringan: 5 kitab kontemporer (الطيار، ابن عثيمين، الفوزان، ابن جبرين); `deathYearAH` < 900: شرح المقنع، الإنصاف، الممتع، الشرح الكبير، المبدع | `search_pages`: المبسوط، المحيط البرهاني، مختصر المزني، روضة الطالبين، النهاية |
| «حجية قول الصحابي», `deathYearAH` < 900 | شرح تنقيح الفصول، شرح العضد، نفائس الأصول، رفع الحاجب، إعلام الموقعين | `search_pages`: الروايتين والوجهين (2)، مسند أبي يعلى، الإشارة (2) |
| «أثر الجهل بالتحريم في سقوط الحد», `deathYearAH` < 1000 | المحلى، الكافي 4/87، اختلاف العلماء، القواعد للحصني، المنثور، البيان | — |
| Kalimat المغني «وجملة ذلك أن من باع سلعة بثمن مؤجل…» | المغني 4/132 teratas | `search_phrase`: المغني 4/132 dan 6/260, 6 halaman; `search_pages`: المغني tidak di 5 teratas |
| Kalimat Inggris tentang menjual kredit lalu membeli kembali lebih murah | المغني 4/132 teratas | — |
| «is zakat due on monthly salary income» | fatwa ابن باز، الشبكة الإسلامية | `search_pages`: 0 |
| «ترجمة عكرمة مولى ابن عباس», `deathYearAH` < 900 | جزء المنذري، الكوثر الجاري، عمدة القاري; تهذيب/ميزان tidak di 5 teratas | `search_pages`: العدة، الاستغناء، شعب الإيمان |
| «لا ضرر ولا ضرار», `deathYearAH` < 900 | syarah الأربعين (الطوفي، ابن دقيق العيد، ابن الملقن) | `search_pages`: السنن الكبرى للبيهقي (5), 3.978 halaman |

Yang hanya ada di `qaf`: pencarian menurut makna (nash dengan lafaz lain) dan pertanyaan berbahasa Inggris. Yang tidak ada di `qaf`: frasa persis, jumlah hasil, status `silent`, `verify_quote`, halaman cetak pasti, dan lebih dari 20 hasil per panggilan (lanjutan lewat `excludeIds`, paling banyak 200).

## Jebakan alat

- `shamela_resolve` hasil pertama salah kitab pada empat judul: `مواهب الجليل`, `تحفة المحتاج`, `أسنى المطالب`, `حاشية الدسوقي`.

## Belum diuji

- Pengaruh aturan ini pada mutu naskah yang ditulis agent.
- Soal di luar fiqih mu'amalah, hadits, tafsir 2:219, dan biografi dua penyair.
