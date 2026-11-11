# Eksperimen Rust untuk mesin Bahts

Prototipe ini membandingkan normalisasi Arab Rust melalui PyO3 (jembatan Rust–Python), mesin Python asli, dan cache Python. Ini **bukan migrasi mesin**. Tidak ada impor tambahan di `mesin/`, dependensi pemakai tidak berubah, dan menjalankan `bahts.py` langsung tetap memakai Python asli.

## Cara mencoba

Syarat: Python dan pustaka mesin sudah siap, Rust/Cargo tersedia, serta kitab lokal tersedia. Pembuatan modul pertama mengunduh crate Rust. `cek` dan pengukuran sesudah build tetap bekerja tanpa internet. Windows memerlukan toolchain beserta linker yang sesuai; eksperimen Windows ini memakai GNU dan GCC. Tidak ada wheel siap pakai dalam PR ini.

1. Jalankan `python mesin/bahts.py ambil 11223 1727` dari akar repo.
2. Arahkan `CARGO_TARGET_DIR` ke direktori sementara agar hasil kompilasi tidak masuk repo.
3. Jalankan `cargo build --release --locked --manifest-path dok/eksperimen-rust/Cargo.toml`.
4. Di Windows, salin `release/_bahts_rust.dll` hasil build ke direktori sementara sebagai `_bahts_rust.pyd`.
5. Di Linux, salin `release/lib_bahts_rust.so` sebagai `_bahts_rust.so`; Linux belum diuji dalam eksperimen ini.
6. Jalankan `python dok/eksperimen-rust/ukur.py --library <jalur-modul> --output <jalur-json-sementara>`.

Untuk mencoba lewat pintu pemakai:

```text
python dok/eksperimen-rust/jalankan.py --mode rust --library <jalur-modul> mesin/bahts.py cek contoh
python dok/eksperimen-rust/jalankan.py --mode python mesin/bahts.py cek contoh
python dok/eksperimen-rust/jalankan.py --mode cache mesin/bahts.py cek contoh
python dok/eksperimen-rust/jalankan.py --mode rust-cache --library <jalur-modul> mesin/bahts.py cek contoh
```

`cache` dan `rust-cache` sama-sama membatasi cache `norm` dan `padat` pada 4096 masukan per fungsi. Itu batas percobaan, bukan rekomendasi kebutuhan memori. Pemakaian RAM belum diukur. Peluncur berlaku dalam proses saat ini; subprocess yang dibuat skrip tujuan tidak otomatis memakai Rust.

`--folder <folder-bahts>` pada `ukur.py` menambah pengukuran naskah lokal; boleh diulang. JSON hasil hanya memuat label `manuscript-1`, `manuscript-2`, jumlah, hash kode, dan durasi. Isi, nama, jalur, dan hash naskah tidak disimpan ke hasil publik.

## Yang diuji

- `norm` dan `padat` asli dibandingkan dengan Rust pada sampel teks kitab, presentasi Arab, serta masukan acak dengan seed tetap.
- Seluruh 1.112.064 nilai skalar Unicode dicoba bersama ligatur Arab yang memicu NFKC (penyamaan bentuk kompatibilitas Unicode). Hasil `norm` harus identik.
- `norma.Padat.buat` dipanggil pada seluruh rekaman kitab 1727 dengan objek rekaman baru setiap putaran. Cache kedua mesin harus identik **sampai byte hasil serialisasinya**. Cache pustaka pemakai tidak dihapus atau ditimpa oleh pengukuran ini.
- `norma.cache` juga dipanggil pada salinan kitab di folder sementara tanpa cache. Timer ini mencakup sidik sumber, baca gzip/JSON, normalisasi, dan tulis cache; penyalinan kitab awal berada di luar timer. Cache disk sistem operasi tetap hangat/tidak dikendalikan.
- `cek contoh`, `cek contoh/jebakan`, naskah tambahan, `cari`, dan `halaman` dijalankan melalui CLI asli. Kode keluar, stdout, dan stderr harus identik pada seluruh putaran. `cek contoh/jebakan` memang menghasilkan kode gagal karena berisi jebakan yang sengaja salah.
- Pengukuran fungsi dan pembuatan cache memakai median 5 putaran. CLI memakai median 7 proses baru per mode, dengan urutan mode diacak memakai seed tetap. Cache sistem operasi dibiarkan hangat; ini bukan pengukuran disk dingin.

Manifest hasil mencatat ID kitab dan SHA-256 `pages.jsonl.gz` setiap kitab sampel. Isi corpus mengikuti pustaka lokal saat pengukuran; seed yang sama tanpa pustaka yang sama tidak menentukan corpus yang sama.

Normalisasi Rust membaca pola regex, tabel huruf, dan tabel ejaan dari `mesin/norma.py`. Urutan algoritme serta langkah ligatur dalam Rust merupakan port eksperimen; kesamaan hasil harus diuji ulang setiap kali mesin atau dependensi berubah. Unicode Rust dan Python dapat berbeda versinya. Pembacaan masukan Rust menerima string UTF-8 yang sah, bukan surrogate tunggal Python.

## Batas keputusan

Angka satu PC tidak membuktikan kecepatan di semua komputer. PR ini tidak membuktikan port seluruh mesin, paket satu executable, pengganti Word, atau distribusi wheel Windows/Linux/macOS. Hasil Word tetap dibentuk perakit Word yang sama. Tidak ada klaim bahwa waktu `rakit` berkurang berdasarkan pengukuran normalisasi.

`hasil.json` menyimpan ukuran tanpa teks pribadi. `HASIL.md` mencatat keputusan dan pemeriksaan. Keduanya adalah hasil eksperimen yang diminta, bukan aturan baru untuk mesin.

## Referensi alat

- [PyO3 0.30.1: build dan distribusi](https://pyo3.rs/v0.30.1/building-and-distribution)
- [regex](https://docs.rs/regex/), [fancy-regex](https://docs.rs/fancy-regex/), dan [unicode-normalization](https://docs.rs/unicode-normalization/)

Crate normalisasi Arab umum tidak dipakai sebagai pengganti aturan mesin: aturan ejaan, penghormatan, serta batas kata mesin harus tetap teruji terhadap implementasi lama.

## Riset paket siap pakai

| Paket/sistem | Pemeriksaan | Keputusan eksperimen |
|---|---|---|
| PyO3, regex, fancy-regex, unicode-normalization | Dikompilasi dan dipakai prototipe ini; versi terkunci di Cargo.lock. | Pakai komponen komunitas untuk jembatan, pencocokan pola, dan Unicode. |
| [arabic-normalize 0.1.0](https://github.com/AbdeldjalilChougui/arabic-normalize) | Source dan dokumentasi dibaca; crate preset `search` dikompilasi pada delapan contoh kompatibilitas terpilih. | Bukan pengganti langsung: kedelapan contoh berbeda; perlu adapter untuk aturan mesin. Angka ini bukan frekuensi perbedaan pada seluruh kitab. |
| [orjson](https://github.com/ijl/orjson) | Wheel Rust untuk Python dipasang di temp; seluruh objek JSON kitab 1727 dibandingkan dengan `json.loads`, lalu waktu parse diukur. | Kandidat pembaca JSON siap pakai; hasil ini belum membuktikan percepatan CLI atau kesamaan seluruh perilaku parser. |
| [docx-rs](https://github.com/bokuweb/docx-rs) | README, source paragraf, dan contoh footnote diperiksa. | Penulis DOCX yang patut diuji; belum dibuktikan memenuhi semua aturan halaman bahts atau menghasilkan PDF setara. |
| [araby-book 0.2.0](https://typst.app/universe/package/araby-book/) | Dokumentasi resmi template Typst dibaca: RTL, catatan kaki, nomor Arab, kepala halaman. | Titik awal uji render alternatif; belum dirender atau dicocokkan ke pedoman kampus di eksperimen ini. |
| [Typstream](https://github.com/ikramhasan/typstream) | README resmi dan PR dukungan Arab diperiksa; README menyatakan belum dirilis. | Belum dipilih sebagai komponen distribusi. |

Semua status riset di atas diperiksa 11 November 2026. Pembungkus Python Rust regex `rure` dan `regex-rs` juga ditinjau lewat halaman paket; keduanya tidak diuji sebagai pengganti semua regex mesin. `regex` tidak menyediakan lookaround yang dipakai aturan mesin; prototipe memakai `fancy-regex` untuk pola tersebut.
