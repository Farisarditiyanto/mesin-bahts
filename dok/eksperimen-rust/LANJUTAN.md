# Eksperimen lanjutan — 11 November 2026

Rust belum terbukti mempercepat perakitan Word. Wheel normalizer sudah lolos di tiga sistem. Jalur perakit alternatif jauh lebih singkat pada tahap yang dicoba, tetapi belum membuat bahts lengkap yang setara.

Semua angka mentah dan hash source ada di `hasil-lanjutan.json`. Ini eksperimen pada draft PR #166, tanpa merge. `mesin/` dan `main` tidak diubah.

## Paket normalizer

| Sistem runner | Arsitektur | Python pada venv bersih | Wheel |
|---|---|---|---|
| Windows | x86-64 | 3.12.10, 3.14.10 | `win_amd64`, 908.329 byte |
| Linux | x86-64 | 3.12.16, 3.14.10 | `manylinux_2_34_x86_64`, 1.029.641 byte |
| macOS | ARM64 | 3.12.10, 3.14.10 | `macosx_11_0_arm64`, 899.884 byte |

Tiap venv dipasangi wheel lokal lewat `pip --no-index --no-deps`. PATH worker tidak memuat Rust. Tiap pasangan sistem/Python membandingkan 12.004 masukan dan 1.112.064 skalar Unicode; semuanya nol perbedaan. LICENSE repo ikut diperiksa dalam wheel. Build dan hasil runner: [GitHub Actions](https://github.com/Farisarditiyanto/mesin-bahts/actions/runs/43016325013).

PC Windows juga mencoba wheel GNU pada Python 3.12.14, 3.14.10, dan 3.15.2, semuanya lolos. Ini wheel normalizer, bukan executable Bahts mandiri. Data kitab, mesin Python, font, dan Word tidak masuk wheel. Mac Intel, Windows ARM, Linux ARM/musl, serta Linux lama tidak diuji. Tag `manylinux_2_34` mensyaratkan glibc 2.34 atau lebih baru menurut [PEP 600](https://peps.python.org/pep-0600/).

Bug nyata ditemukan sebelum perbaikan: versi 0.1.0 berbeda dari Python 3.12 pada U+1CCF0 bersama pemicu NFKC. Basis Unicode berbeda. Versi 0.2.0 menjalankan langkah NFKC dengan `unicodedata.normalize` Python host; langkah lain tetap Rust. Jadi ini belum normalizer murni Rust. Surrogate tunggal Python tetap di luar kontrak string UTF-8 prototipe.

## RAM cache

Puncak RAM proses asli; MiB = 1.048.576 byte. Setiap beban/mode memakai tiga proses baru. Windows memakai `peak_wset` dari psutil, yang juga menghitung alokasi native Rust; bukan hanya alokasi Python. Lima beban menghasilkan 60 proses, seluruh hasil/status sama.

| Beban | Python | Python + cache | Rust | Rust + cache |
|---|---:|---:|---:|---:|
| Naskah nyata 1 | 182,0 | 188,0 | 186,1 | 191,8 |
| Naskah nyata 2 | 228,8 | 230,5 | 230,8 | 235,0 |
| 8.192 teks unik pendek | 28,1 | 31,5 | 29,8 | 33,5 |
| 8.192 teks unik panjang | 28,6 | 216,4 | 29,9 | 275,6 |
| Teks panjang yang sama diulang | 28,7 | 28,2 | 30,1 | 29,9 |

Teks panjang berisi 8.192 karakter, ditambah awalan identitas pada kasus unik. Kasus sintetis panjang menguji batas, bukan gambaran semua naskah. Cache berisi maksimal 4096 masukan **per fungsi**, sehingga tidak membatasi byte. Rust + cache dibanding Python asli menambah sekitar 6,2–9,8 MiB pada dua naskah nyata. Tambahan cache pada implementasi Rust saja sekitar 4,2–5,7 MiB. RAM dasar modul dan allocator juga ikut dalam angka puncak.

## Word asli

Microsoft Word 16.0.20527.20150. Dua beban, dua mode, tiga rakit per mode: 12 rakit nyata. Pekerjaan diserialkan dengan kunci pekerjaan Bahts yang sudah ada. Naskah asli tidak disentuh; salinannya berada di temp. Kode keluar, teks PDF, jumlah halaman, dan isi catatan kaki identik antar-mode.

| Median, detik | Python | Rust + cache |
|---|---:|---:|
| Contoh publik, 3 halaman/12 catatan: total | 13,037 | 12,925 |
| Naskah nyata, 34 halaman/124 catatan: pemeriksaan | 1,439 | 1,280 |
| Naskah nyata: PowerShell + Word | 114,286 | 122,353 |
| Naskah nyata: tahap lain | 1,829 | 1,914 |
| Naskah nyata: total | 117,557 | 125,546 |

Penghematan pemeriksaan sekitar 0,159 detik kalah dari variasi Word. PowerShell/Word sendiri tidak memakai normalizer Rust. Median sesi ini bahkan lebih lambat pada Rust + cache; itu tidak membuktikan Rust menyebabkan Word melambat. Tidak ada bukti percepatan Word oleh Rust dari percobaan ini. Sekitar 97% waktu baseline ada pada PowerShell/Word.

## docx-rs, araby-book, dan Typst inti

Satu fixture publik berisi judul pembuka, 12 paragraf, 12 catatan, dan pemisah halaman. Naskah nyata juga dicoba: adapter mempertahankan 337 span isi di luar blok R serta 124 teks catatan, persis sebagai daftar string. Tetapi sampul kampus, pustaka/indeks, font Quran, gaya inline, bookmark, dan rujukan halaman belum dipertahankan. Jangan menyamakan waktunya dengan pipeline Bahts penuh.

| Tahap yang diuji | 12 catatan | 124 catatan |
|---|---:|---:|
| docx-rs 0.4.22: bangun DOCX | 0,038 s | 0,166 s |
| Adapter OOXML kecil | 0,003 s | 0,015 s |
| Word ekspor PDF + koreksi teks PDF, sesudah adapter | 4,887 s | 6,985 s |
| araby-book 0.2.0: compile PDF | 0,152 s | 0,285 s |
| Typst inti 0.15.1: compile PDF | 0,194 s | 0,213 s |

Build DOCX dan compile Typst memakai lima putaran; ekspor Word tiga putaran. Angka penjumlahan median tiap tahap bukan pengukuran satu proses ujung-ke-ujung. Input Typst sudah disiapkan dari naskah yang diolah. Putaran pertama araby-book sebelum cache paket hangat tercatat 1,772 detik; angka tabel adalah pengukuran sesudah paket/font hangat.

docx-rs mentah menghasilkan seluruh teks dan referensi catatan, tetapi tidak menyisipkan `w:footnoteRef` di awal entri catatan. XML mentah berisi 0 penanda nomor awal; adapter menghasilkan 12 dan 124, tanpa mengubah daftar `w:t`. Adapter juga menambah arah RTL pada run. Nomor, gaya teks campuran, kepala/kaki halaman, dan tata letaknya tetap belum setara. Ini temuan pada prototipe memakai docx-rs 0.4.22, bukan klaim bahwa seluruh kebutuhan itu mustahil dibuat dengan library tersebut.

araby-book menghasilkan empat halaman untuk fixture, termasuk sampul tambahan. Typst inti menghasilkan tiga halaman. Kedua jalur menyertakan seluruh 12 penanda paragraf dan catatan, A4, tanpa peringatan compiler. araby-book memulai nomor catatan lagi per halaman; nomor isi dan catatannya cocok 1–4 pada halaman yang diperiksa. Itu berbeda dari fixture bersambung, bukan bug semua nomor menjadi satu. Pada naskah nyata, araby-book menghasilkan 29 halaman, Typst inti 24, dan docx-rs sesudah adapter 23; perbedaannya menegaskan bahwa layout belum setara.

PDF fixture dilihat sebagai gambar: contact sheet seluruh 16 halaman, lalu halaman ukuran penuh dari Word asli, docx-rs mentah/adaptasi, serta Typst. Seluruh halaman naskah nyata belum diaudit visual satu per satu. Kesamaan pemetaan teks bukan bukti kesamaan pembicara, kutipan, tata letak, atau penomoran.

## Pemeriksaan dan dua perbaikan keselamatan

- Suite proyek lengkap lokal: `uji semua: 0 gagal`, termasuk Word asli.
- `uji_lanjutan.py`: lima uji CLI, semuanya hijau. Tiga mutasi pada salinan produk di temp membuat pemeriksa merah: status berupa teks, validasi input dihapus, dan catatan kepemilikan Word dihapus.
- Pemeriksa independen menemukan runner RAM dapat mempublikasikan pesan galat berisi jalur pribadi; folder kini diperiksa sebelum worker, status string diubah menjadi integer, dan CLI gagal tidak menerbitkan hasil.
- Exporter Word kini menolak record kepemilikan lama sebelum membuat Word. Uji sentinel membuktikan record utuh, PDF tidak dibuat, set PID Word tidak berubah, dan lock dilepas.
- Audit independen fase kedua menyetujui PR eksperimen tanpa merge. JSON publik hanya berisi label naskah anonim, jumlah, waktu, RAM, hash kode, dan metadata wheel. Tidak ada teks/jalur/nama/hash naskah pribadi.

## Mengulang

`paket.py` memerlukan maturin; `ram.py` dan uji regresi memerlukan psutil. `docx_patch.py` memerlukan lxml. Build docx-rs memakai manifest di `docx/Cargo.toml`. Typst yang diuji adalah 0.15.1. Rakit/ekspor PDF Word hanya dijalankan di Windows ber-Word. Arahkan semua `--out`/`--folder` keluaran percobaan ke temp; jangan masukkan salinan naskah pribadi ke Git.

1. Jalankan `python ram.py --library <modul> --folder <bahts> --out <temp>/ram.json` dari akar eksperimen.
2. Jalankan `python render.py --library <modul> --folder <bahts> --out <temp>/word-baru`; folder kerja harus baru.
3. Jalankan `python alternatif.py --typst <exe> --docx-bin <exe> --out <temp>/alternatif` untuk fixture publik; `--bahan <bahan.json>` memilih isi naskah yang telah diperiksa.
4. Jalankan `python docx_patch.py --folder <temp>/alternatif` untuk adaptasi OOXML.
5. Jalankan `python export_docx.py --variant docx-rs-adapted --folder <temp>/alternatif` untuk PDF Word; runner antre pada kunci Bahts.
6. Jalankan `python uji_lanjutan.py` untuk regresi keselamatan tanpa merender Word.

Referensi: [PyO3](https://pyo3.rs/v0.30.1/building-and-distribution), [Maturin](https://www.maturin.rs/metadata.html), [docx-rs](https://github.com/bokuweb/docx-rs), [araby-book](https://typst.app/universe/package/araby-book/), [PEP 600](https://peps.python.org/pep-0600/).
