# Penunjuk takhrij: `hadits` dan `hadithunlocked`

Catatan kemampuan dan batas layanan, diperiksa 30 Oktober 2026. Ini bukan perubahan aturan alat di `AGENTS.md`. Keduanya penunjuk jalan; keluaran layanan belum menjadi bukti lafaz, halaman cetakan, atau penisbatan hukum di bahts.

| Kebutuhan | `hadits` (alminasa.ai) | Connector `hadithunlocked` |
|---|---|---|
| Menemukan riwayat | Cakupan 12 kitab menurut modul `mesin/hadits.py`; daftar cocok memakai frasa persis dengan variasi awalan و/ف. | Sampel pencarian juga menemukan البزار، أبو يعلى، الطبراني di luar cakupan itu. |
| Tempat cetakan | Sampel memuat edisi, juz/halaman, kitab/bab, dan nomor hadits. | Rekaman `ibnmajah:224` memuat kitab/bab dan nomor, tetapi tidak memuat data edisi dan juz/halaman cetakan riwayat yang setara. Ini batas sampel, bukan klaim semua rekaman tidak punya halaman. |
| Hukum ulama | Sampel memuat beberapa ulama, lafaz hukum, kitab hukum dan juz/halaman. | Ringkasan menonjolkan satu hukum; `lookup_hadith_detail` profil `full` pada sampel juga memuat `metadata.grades` dari beberapa ulama, `source_name`, `book_page` dan `source_url`. Pernyataan bahwa connector hanya punya satu ulama tanpa halaman tidak tepat. |
| Pendalaman | Bila daftar cocok tidak memuat Shahihain, ada daftar «Riwayat mirip» berbasis kemiripan kata; hubungan riwayat belum dibuktikan. | Detail sampel menautkan empat syarah. Hasil pencarian memiliki `has_more` dan `next_cursor`; halaman pertama belum mencakup semua hasil. |

## Pengamatan yang bisa diulang

- `python mesin/bahts.py hadits "إنما الأعمال بالنيات" 10`: tiga hasil cocok; البخاري 1 ada, مسلم tidak muncul.
- `python mesin/bahts.py hadits "الأعمال بالنية" 10`: 15 hasil cocok, sepuluh ditampilkan; مسلم 1907 dan beberapa nomor البخاري ada, tetapi البخاري 1 tidak ada di daftar yang ditampilkan. Perubahan lafaz memengaruhi hasil; ini bukan bukti suatu riwayat tidak ada di kitab.
- `python mesin/bahts.py hadits "طلب العلم فريضة على كل مسلم" 10`: ابن ماجه 224 dengan edisi الرسالة العالمية 1/151. Layanan menampilkan hukum الألباني yang mengecualikan sebagian matan, serta hukum شعيب الأرنؤوط. Ini keluaran layanan, belum pemeriksaan kitab hukum lokal.
- `search_hadith(query="طلب العلم فريضة على كل مسلم", limit=15)`: ابن ماجه 224 tidak ada pada 15 hasil pertama; respons menyatakan masih ada hasil. Pencarian khusus kitab atau kelanjutan halaman dapat diperlukan untuk pertanyaan tentang kitab tertentu.
- `lookup_hadith_detail(reference="ibnmajah:224", response_profile="full")`: hukum utama «ضعيف» dinisbatkan layanan kepada Zubayr Ali Zai; metadata juga memuat nukilan hukum النووي، المزي، البوصيري dan ابن عدي beserta penunjuk sumber. Detail tersebut tidak membuktikan sendiri bahwa setiap nama, kutipan, atau halaman sudah benar.

## Batas kesimpulan

Uji ini menilai keluaran alat, bukan menetapkan derajat hadits. Kitab hukum lokal dan scan cetakannya tidak diperiksa dalam perbandingan ini. Sampel tidak mengukur akurasi seluruh koleksi, kelengkapan semua riwayat, atau mutu semua syarah. Format dan isi layanan dapat berubah tanpa perubahan mesin; `cek` dan `rakit` tetap tidak bergantung pada kedua layanan ini.
