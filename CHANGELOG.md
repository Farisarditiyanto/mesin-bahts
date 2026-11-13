# Catatan versi

Yang baru di atas. Satu butir = satu perubahan yang dirasakan pemakai, satu-dua kalimat. Nomor versi = `besar.kecil.tambalan`:
besar naik kalau naskah lama bisa berhenti jalan, kecil naik kalau ada kemampuan baru, tambalan naik kalau hanya perbaikan.
Rincian rilis lama yang diringkas ada di [rilis GitHub](https://github.com/Farisarditiyanto/mesin-bahts/releases).

## Belum dirilis

- Perintah baru tanpa internet dan tanpa kuota: `tafsir <surat:ayat>` menunjuk kitab tafsir yang menafsirkan ayat itu (14 kitab, mis. الطبري، زاد المسير، ابن كثير) beserta juz/halaman cetaknya; `takhrij <id> <juz> <hal>` menunjuk hadits di halaman itu di 8 kitab hadits (البخاري، مسلم، أبو داود، الترمذي، النسائي، الموطأ، الطيالسي، ابن الجارود) beserta nomor dan juz/halamannya; edisi lain kitab itu (mis. صحيح مسلم ت عبد الباقي) dijembatani lewat nomor hadits. Datanya indeks layanan Shamela sendiri, diunduh `siapkan` (±0,6 MB).
- Gambar di naskah: `#G berkas.png | keterangan` mencetak PNG/JPG dari folder bahts di tengah halaman, dikecilkan agar muat, dengan keterangan di bawahnya. Diagram Mermaid (`<nama>.mmd`) dijadikan PNG dengan perintah baru `diagram <folder>` (butuh Node.js + Chrome/Edge); `cek` dan `rakit` tetap tanpa internet.
- `@malahiq: akhir` mencetak bagian `#K الملاحق` sesudah المصادر والمراجع dan sebelum فهرس; halamannya tidak masuk `HALAMAN_ISI`.

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
