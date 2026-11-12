# Catatan versi

Yang baru di atas. Satu butir = satu perubahan yang dirasakan pemakai, satu-dua kalimat. Nomor versi = `besar.kecil.tambalan`:
besar naik kalau naskah lama bisa berhenti jalan, kecil naik kalau ada kemampuan baru, tambalan naik kalau hanya perbaikan.
Rincian tiap rilis lama ada di [rilis GitHub](https://github.com/Farisarditiyanto/mesin-bahts/releases).

## Belum dirilis

- `tahap`: naskah yang berubah hanya di bagian yang tidak tercetak (mis. `@minimal_halaman`) tidak membuat PDF USANG: laporan `rakit` kini mencatat `CETAK_SHA256`, jadi tidak perlu rakit ulang.
- Jumlah halaman dinilai: seluruh PDF kurang dari 25 halaman = perhatian `cek` (perkiraan) dan PERINGATAN sesudah `rakit`. Batas dosen: `@minimal_halaman: n`; `0` = tidak dinilai.
- Jumlah kitab di المصادر dinilai hanya kalau dosen menulis batasnya: `@minimal_kitab: n`. Baris `#R` kembar dihitung sekali; mushaf ditulis «القران الكريم»/«المصحف الشريف» tetap bukan kitab.
- `cek` menjaga cara menukil (أبو سليمان ص112-114، 123، 173): perhatian untuk 8 kata atau lebih yang sama persis dengan kitab di luar tanda petik, nukilan makna tanpa «انظر:», kutipan lafaz yang dirujuk «انظر:», dan kutipan lebih dari 60 kata. Naskah lama bisa mendapat perhatian baru; GAGAL tidak berubah.
- `rakit` lebih cepat ±18% (BarisPendek dan putaran rujukan halaman); PDF sama persis.
- Tabel di isi bahts: `#J sel | sel | sel` (baris pertama = kepala tabel).
- `bukti` mencetak tiap paragraf isi tanpa catatan kaki; pemeriksa langkah 5 wajib menilainya.
- Agent wajib membaca seluruh bab sebelum mengutip satu halaman kitab.
- README berbahasa Arab (`README.ar.md`), README ditulis ulang untuk agent; Command Code bisa memakai connector `shamela`.

## 9.2.1 — 2026-11-11

- AGENTS.md: tujuh cara menukil menurut أبو سليمان dengan urutan pemakaiannya.

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

- `temukan`, `hadits`, baris `perhatian` di `cek`, `dirasat` di OpenAlex dan DOAJ.

## 0.0.2 — 2026-10-09

- `@tanpa`, `HALAMAN_ISI`, bagian «Pemakai baru». [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v0.0.2)

## 0.0.1 — 2026-10-09

- `siapkan`, `baru`, `cek`, `rakit`, perpustakaan Shamela lokal, `dirasat`. [Rincian](https://github.com/Farisarditiyanto/mesin-bahts/releases/tag/v0.0.1)
