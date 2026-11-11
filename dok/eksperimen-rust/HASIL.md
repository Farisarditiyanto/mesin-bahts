# Hasil eksperimen Rust versi 0.1.0 — 11 November 2026

Data historis fase pertama, sesuai commit `6776124`. Untuk paket versi 0.2.0, RAM, Word, dan perakit alternatif, baca `LANJUTAN.md`.

Rust memberi hasil menjanjikan pada normalisasi padat dan pembuatan cache, tetapi data ini belum membenarkan rewrite seluruh mesin. Implementasi Python asli tetap dipakai oleh perintah normal. Eksperimen bersifat opt-in dan ditujukan untuk PR tanpa merge.

## Lingkungan dan metode

- Basis repo: `f5eb871e3430cc417f001072e9bfc434606d9833`.
- Windows 11, Python 3.14.10, Rust 1.99.1, toolchain `x86_64-pc-windows-gnu`; versi crate ada di `Cargo.lock`.
- Corpus: 2.394 string, 1.955.424 karakter dari 26 kitab lokal. ID dan SHA-256 kitab sampel ada di `hasil.json`. Ini sampel berstrata dari bagian awal maksimal 1.024 rekaman per kitab, bukan seluruh pustaka.
- Dua naskah nyata diukur sebagai `manuscript-1/2`. Tidak ada isi, jalur, identitas, atau hash naskah di hasil publik.
- CLI: median tujuh proses baru per mode; urutan mode diacak dengan seed 20261111. `cache` dan `rust-cache` membatasi kedua fungsi pada 4096 masukan per fungsi.
- Fungsi dan cache: median lima putaran. Cache disk sistem operasi hangat/tidak dikendalikan. Pengukuran lengkap cache dimulai tanpa cache aplikasi di folder sementara baru.
- Semua sampel durasi mentah, hash implementasi dan binary, serta agregat validasi tersimpan di `hasil.json`.

## Hasil CLI

Detik; semua perbandingan melalui peluncur eksperimen yang sama.

| Beban | Python | Rust | Python + cache | Rust + cache |
|---|---:|---:|---:|---:|
| `cek contoh` | 0,4102 | 0,3714 | 0,3523 | 0,3383 |
| `cek contoh/jebakan` | 2,1218 | 1,8608 | 1,9420 | 1,7829 |
| `cek` naskah nyata 1 | 1,7510 | 1,5079 | 1,5333 | 1,4576 |
| `cek` naskah nyata 2 | 2,3903 | 2,0128 | 2,0151 | 1,8779 |
| `cari`, tidak ditemukan | 0,1590 | 0,1632 | 0,1641 | 0,1669 |
| `cari`, ditemukan | 0,1782 | 0,1809 | 0,1757 | 0,1807 |
| `halaman` | 0,1665 | 0,1608 | 0,1633 | 0,1592 |

Rust mengurangi durasi dua `cek` naskah nyata sebesar 13,9–15,8%. Rust + cache menguranginya 16,8–21,4%. Dibanding Python + cache, keuntungan Rust + cache tinggal sekitar 4,9–6,8%. Pencarian lokal tidak membaik pada sampel ini. Selisih kecil perintah pendek tidak layak digeneralisasi dari satu PC.

## Fungsi dan cache kitab

| Beban | Python | Rust | Makna |
|---|---:|---:|---|
| `norm`, corpus sampel | 0,2192 s | 0,2185 s | Hampir imbang. |
| `padat`, corpus sampel | 0,2772 s | 0,2097 s | Durasi turun 24,4%. |
| `Padat.buat`, kitab 1727 | 0,7314 s | 0,4917 s | Isi cache dibangun dari 7.495 rekaman yang telah dibaca; baca/tulis di luar timer. |
| `norma.cache` lengkap, kitab 1727 | 0,8426 s | 0,6369 s | Durasi turun 24,4%; termasuk sidik, gzip, JSON, normalisasi, dan tulis cache. |

Cache lengkap identik sampai byte hasil serialisasinya pada seluruh putaran. Hasil bukan pengukuran disk dingin atau pembangunan seluruh pustaka.

Build release pertama tercatat 21,13 detik. Binary pengujian berukuran 5.488.461 byte. Toolchain dan binary tinggal di temp; tidak ada paket native/wheel yang dipasang ke Python pemakai oleh PR ini.

## Kesamaan hasil dan pemeriksaan

- 20.057 string × dua fungsi: nol perbedaan, termasuk teks kitab, presentasi Arab, dan masukan acak.
- Seluruh 1.112.064 nilai skalar Unicode bersama pemicu NFKC: nol perbedaan hasil `norm`. Surrogate tunggal Python berada di luar masukan UTF-8 sah yang diterima prototipe.
- Tujuh beban CLI × empat mode × tujuh putaran: kode keluar, stdout, dan stderr sama. Jebakan dan pencarian kosong memang mengembalikan kode 1; dua naskah nyata mengembalikan 0.
- `python .github/uji_semua.py` pada mesin asli: 0 gagal.
- Suite yang sama dengan hook impor sementara yang memasang Rust setiap kali `norma` dimuat, termasuk subprocess: 0 gagal; 388 pemuatan modul tercatat. Hook tidak dikirim sebagai perubahan produksi.
- Kedua suite menjalankan `uji_rujukan_word.py` memakai Word asli pada dua mode nomor catatan kaki. Tidak ada pengukuran pembanding waktu `rakit`; tidak ada klaim percepatan Word.
- Uji merah: penggantian `IBNU` Rust sengaja dirusak dalam salinan sementara (`بن` menjadi `ابن`). Pemeriksa keluar 1 dan menemukan 1.884 perbedaan. Binary asli tetap hijau.
- Pemeriksa independen menemukan kesalahan pengikatan global pada alat ukur `padat` Python. Source diperbaiki, seluruh angka fungsi di atas diukur ulang; angka CLI dan `Padat.buat` tidak terdampak.
- Audit ulang independen: lolos untuk PR eksperimen tanpa merge; lima uji CLI tambahan juga sama persis, termasuk halaman yang tidak ada.

## Riset paket komunitas

Prototipe memakai PyO3, regex, fancy-regex, dan unicode-normalization. Pembungkus normalisasi Rust hanya 74 baris; mesin regex dan Unicode tidak dibangun sendiri.

- [arabic-normalize 0.1.0](https://github.com/AbdeldjalilChougui/arabic-normalize) preset `search` dikompilasi. Delapan contoh kompatibilitas yang sengaja dipilih menghasilkan delapan perbedaan. Contoh: `﷽` tetap ligatur di crate, tetapi mesin menjabarkannya; `محمد ابن يحيى` tetap memakai `ابن` di crate, tetapi mesin memakai `بن`. Ini bukan pengganti langsung; adapter masih diperlukan. Source dan [dokumentasi crate](https://docs.rs/arabic-normalize/0.1.0/arabic_normalize/) diperiksa.
- [orjson 3.13.0](https://github.com/ijl/orjson) dipasang sebagai wheel ke temp. Semua 7.495 objek kitab 1727 sama dengan `json.loads`. Median sembilan putaran parse saja: 0,03238 → 0,02370 detik, hemat sekitar 8,67 milidetik. Belum layak menjadi perubahan dependensi hanya dari data ini; CLI dan seluruh perbedaan semantik parser belum diuji.
- [docx-rs](https://github.com/bokuweb/docx-rs), [araby-book](https://typst.app/universe/package/araby-book/), dan [Typstream](https://github.com/ikramhasan/typstream) diperiksa dari sumber resminya. Dua yang pertama menyediakan dasar DOCX atau tata letak Arab; kecocokan PDF kampus belum diuji. README Typstream menyatakan belum dirilis. Ketiganya belum dirender dalam eksperimen ini.

## Keputusan

Buka PR eksperimen tanpa merge untuk menyimpan prototipe dan data yang dapat diuji ulang. Jangan mengganti normalisasi produksi dulu. Keuntungan tambahan terhadap cache Python hanya sekitar 5–7% pada dua naskah; distribusi wheel lintas platform dan biaya perawatan belum dibuktikan. RAM cache belum diukur. Port seluruh mesin serta perubahan sistem render belum diuji.

File baru hanya di `dok/eksperimen-rust/`: `Cargo.toml` dan `Cargo.lock` untuk build terkunci; `src/lib.rs` untuk normalisasi Rust; `jalankan.py` untuk peluncur opt-in; `ukur.py` untuk pemeriksaan dan pengukuran ulang; `.gitignore` untuk hasil build; `README.md` untuk metode dan referensi; `hasil.json` untuk bukti mentah yang telah dianonimkan; `HASIL.md` untuk keputusan ini. `mesin/`, `.github/`, `contoh/`, dan branch `main` tidak berubah.
