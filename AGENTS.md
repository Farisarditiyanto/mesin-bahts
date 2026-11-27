# Bahts — mesin penulisan bahts (riset ilmiah berbahasa Arab)

Satu bahts = satu folder; yang ditulis cuma `naskah.txt`, sisanya (cek rujukan, Word, PDF) dikerjakan mesin. Bahan bahts jangan masuk `mesin/`; `kitab/` dipakai semua bahts.
Daftar perintah: `python mesin/bahts.py`. Daftar tanda naskah: `python mesin/bahts.py tanda`.

## Peta aturan lanjutan (baca penuh sesuai tahap)

Aturan lengkap dipecah ke berkas terpisah agar tidak terpotong batas baca agent; jangan menebak aturan yang belum dibaca:
- `dok/pemakai-baru.md` — pemasangan awal pemakai baru (unduh repo, `periksa`, daftar & masuk connector `shamela` per agent, connector tanpa akun, kunci OpenAlex).
- `dok/pengaturan-bahts.md` — pembaruan mesin, `sampul_saya.txt`, `@judul`/`@sampul`/`@templat`/`@format`/`@angka`/`@spasi`/`@catatan_kaki`/`@ayat_pembuka`/`@maudhuat_letak`/`@tanpa: anzhur`/`@tahun`, diagram `#G`, rumus `#E`/`{E:}`, bahts bertahap `--fasl`, jumlah halaman, `PERINGATAN` sesudah `rakit`, dan `scan`.
- `dok/riset-alat.md` — urutan pilih alat, cadangan `shamela` → `qurangallery` → `turath`, pencari menurut makna `qaf`, 4 langkah wajib `riset.txt`, Waqfeya (`ambil w…`), aturan «Konteks = bab», dan tabel lengkap alat mesin & connector.
- `dok/pemeriksaan.md` — penanganan `GAGAL` dan `perhatian` (`--jejak`, `shamela_verify_quote`, `terima <kode> <alasan>`), prosedur penuh pemeriksa langkah 5 (Fokus A Isi & Sumber + Fokus B Tata Letak Visual), dan batas `cek`.
- `dok/penulisan-sumber.md` — standar sumber tertinggi (أبو سليمان), aturan takhrij & derajat hadits, bentuk rujukan pertama/ringkas, khilaf, 7 cara menukil & batas ±60 kata, dan الدراسات السابقة (`dirasat`/`dirasat-pdf`).
- `dok/mengubah-mesin.md` — aturan mengubah `mesin/`, `.github/`, README, atau `AGENTS.md`.

## Pemakai baru

Pemakai baru yang belum memasang repo, belum menjalankan `periksa`, belum menyambungkan connector `shamela`, atau belum memasang kunci OpenAlex → **baca penuh `dok/pemakai-baru.md` (langkah 1–6)** sebelum mulai.

## Sebelum tiap bahts

Baca penuh `dok/pengaturan-bahts.md` sebelum memulai bahts baru. Inti wajib yang selalu berlaku:
- Perbarui mesin hanya sebelum mulai bahts baru (`git pull --ff-only` bila `git status --porcelain` kosong), jangan di tengah pengerjaan bahts.
- Cek `sampul_saya.txt` (atau bahts terakhir untuk `bahts/<orang>/<topik>`), tanyakan pembimbing (`@musyrif`, `@jabatan`) tiap bahts, dan beri tahu bahwa sampul bawaan memakai kop جامعة الإمام dan قسم الشريعة.
- `@judul` harus sama persis dengan judul dari dosen, خطة, atau pemakai; jangan mengarang judul atau menambah sub-judul sampul (` - …`) sendiri.
- Jumlah halaman yang disebut pemakai = halaman isi (`HALAMAN_ISI`, المقدمة sampai الخاتمة); seluruh PDF < 25 halaman = perhatian `cek` dan PERINGATAN `rakit` (`@minimal_halaman`).
- Semua opsi tata letak (`@format`, `@templat`, `@sampul`, `@judul_sampul`, `@judul_fasl`, `@tamma`, `@pustaka_gaya`, `@ihda`, `@angka`, `@spasi`, `@catatan_kaki`, `@ayat_pembuka`, `@maudhuat_letak`, `@tanpa: anzhur`, `@tahun`, `@model: jakarta`, `--fasl`, `{N:}`, `{M:}`, `{AT:}`, `{B:}`, `{QB:}`, `{G:}`, `{V:}`, `@fihris_ayat`, `@fihris_hadits`, `@fihris_alam`, `{X}`, `#G`, `#E`/`{E:}`, `#J`, `#V`, draf Word mahasiswa) dirinci di `dok/pengaturan-bahts.md`.
- Sebelum lapor selesai ke pemakai, `tahap <folder>` harus mencetak `NASKAH=LOLOS` dan `TERKINI`, lalu tulis letak lengkap PDF-nya.

## Alur kerja

Sesi baru, atau tidak tahu bahts ini sampai mana → `tahap <folder>` dulu, jangan menebak dari berkas di folder: ia membaca ulang naskah (`NASKAH=` GAGAL/PERHATIAN/LOLOS), hasil rakit (`HASIL=` BELUM/TERKINI/USANG/TIDAK_DIKETAHUI, juga tiap `--fasl`), rakit yang sedang jalan (`RAKIT=`), folder `.rakit-*`, dan cadangan `_arsip/rakit-*`, lalu mencetak satu `BERIKUTNYA`. Baris `PERLU PEMAKAI` → sebut ke pemakai, jangan dihapus sendiri.

1. `baru`, lalu susun خطة (فصل/مبحث/مطلب) sesuai permintaan dosen. خطة dosen menyebut isi المقدمة (mis. تساؤلات الدراسة) → sub-judul المقدمة ikut itu; «حدود البحث» menyebut yang dibahas dan yang sengaja tidak (أبو سليمان ص61-62). المقدمة dan الخاتمة ditulis terakhir, sesudah isi (ص192، 196). Pisahkan peran المقدمة (konteks makro & kesenjangan masalah) dari الدراسات السابقة (pengelompokan tematik, celah kritis, dan jembatan ke bahts ini — bukan sekadar ringkasan berurutan). Jangan memecah bagian jadi satu sub-bagian tunggal (`#B` sendirian di bawah `#F`, atau `#M` sendirian di bawah `#B`: `cek` memberi perhatian `sub-bagian tunggal`). Sebelum mengumpulkan bahan, catat dalam rencanamu dua lapis sumber: **P0 (wajib)** — kitab mu'tamad tiap mazhab, nash pokok, standar resmi (mis. AAOIFI/IFRS), metode/indikator/dataset inti yang dibahas — dan **P1 (pendukung)** — konteks umum.

2. Kumpulkan bahan; kutip hanya dari teks yang benar-benar terbaca di sumber lokal (kitab lokal atau PDF yang diunduh), jangan dari ingatan pelatihan. **Wajib baca `dok/riset-alat.md` sebelum riset** untuk urutan alat (`mesin` offline → `shamela` → cadangan `qurangallery`/`turath`/`temukan` → `waqfeya` → `dirasat`/`dirasat-pdf`; `qaf` untuk menemukan kitab yang membahas suatu makna, lalu dipastikan di `shamela`), aturan «Konteks = bab», batas & jebakan connector, dan tabel lengkap alat.
   Catat 4 langkah wajib di `riset.txt` begitu dijalankan (`takhrij8`, `tafsir`, `khilaf`, `cari`; atau `belum <langkah> <objek> <alasan>` bila layanan mati/kuota habis; bentuk baris dan aturan lengkapnya di `mesin/riset_baru.txt`, `python mesin/bahts.py tanda`, dan `dok/riset-alat.md`). Yang belum tercatat jadi perhatian `cek`.
3. Tulis `naskah.txt` dengan alat sunting agentmu (Edit/Write), bukan skrip Python buatan sendiri: skrip seperti itu sering rusak di konsol Windows (UnicodeEncodeError). `bahts.py` sudah mencetak UTF-8 sendiri; `PYTHONIOENCODING` tidak perlu. Setiap kutipan/penisbatan diberi catatan kaki berisi bukti `<<...>>`, termasuk nukilan makna tanpa tanda petik («انظر:»): kalimat yang menyebut pendapat mazhab, ulama, «الأصوليون»، «الجمهور»، ijmak, dalil, atau ta'lil dari kitab. Paragraf tanpa catatan kaki hanya untuk analisis penulis sendiri (الترجيح، النتيجة، pengantar bab), dan sebaiknya ditandai («ويظهر للباحث…»). `cek` tidak melihat kalimat tanpa catatan kaki; pemeriksa langkah 5 yang menilainya. Contoh yang lolos cek: `contoh/naskah.txt`.
4. `cek` sampai `GAGAL: 0`, tangani tiap baris `perhatian` (bereskan di naskah, atau `terima <kode> <alasan>` konkret ≥3 kata di `riset.txt` hanya bila tidak bisa dibereskan/salah tangkap; perhatian `riset.txt` tidak bisa diterima), lalu `rakit`. Prosedur lanjutan (`cek --jejak`, `shamela_verify_quote`, aturan `terima`) dan batas `cek` ada di `dok/pemeriksaan.md`.
5. Sebelum lapor selesai: minta subagent baru (yang tidak ikut menulis) menjalankan pemeriksaan penuh dua fokus — **(A) Isi & Sumber** (lewat `bukti <folder>`, cek kitab asal, konteks bab, paragraf tanpa catatan kaki, nukilan makna, `terima`, `riset.txt`, `@judul`) dan **(B) Tata Letak Visual** (lewat `pratinjau <folder>`) — lalu perbaiki temuan dan `cek` + `rakit` ulang. **Pemeriksa wajib membaca `dok/pemeriksaan.md` dan `dok/penulisan-sumber.md` seluruhnya sebelum menilai.**

## Standar sumber (selalu yang tertinggi)

Selalu pakai sumber asli tertua (أبو سليمان، كتابة البحث العلمي): pendapat mazhab dari kitab mu'tamad mazhabnya (`dok/mutamad.md`), ijmak/jumhur dari penukil tertuanya, ucapan ulama dari kitabnya sendiri, hadits dari kitab asal + derajat dari muhaddits, tafsir dari kitab tafsir, makna kata dari معاجم اللغة, masalah kontemporer dari keputusan المجامع/هيئة asli atau penelitian. Perantara hanya bila asalnya tidak bisa didapat dan ditandai «مقتبس من …» / «نقلا عن …». Rincian lengkap dan tabel aturan `cek`: baca `dok/penulisan-sumber.md`.

## Aturan penulisan

Dilarang mengarang nomor halaman, lafaz, penisbatan pendapat, atau derajat hadits: semua wajib terbaca di sumber lokal (Waqfeya: dari scan, bukan OCR). Ayat selalu `{Q:…}`; takhrij di luar Shahihain wajib berderajat yang terbaca di bukti; rujukan pertama kitab non-hadits memuat data cetak lengkap dari `kartu` tanpa gelar; kutipan utuh dibatasi ±60 kata di luar nash pokok; nukilan makna diawali `انظر:` dan setia pada asalnya. **Wajib baca `dok/penulisan-sumber.md` sebelum menulis `naskah.txt`** untuk rincian takhrij, khilaf, 7 cara menukil, dan الدراسات السابقة.

## Yang perlu diketahui

- Bentuk halaman dan huruf dikunci mesin menurut pedoman Jāmiʿat al-Imām («القواعد المنظمة لتسجيل الرسالة العلمية وكتابتها وطباعتها وتقديمها»، 1442هـ). Dosen minta lain → beri tahu pemakai: profil baru di `mesin/format.json` adalah perubahan mesin (bagian «Untuk yang mengubah mesin»), bukan pekerjaan bahts. Di folder pemakai jangan mengubah berkas `mesin/`: `git status` jadi tidak kosong, lalu pembaruan mesin berhenti (Sebelum tiap bahts, langkah 2). Jangan ubah `imam` (= isi pedoman dan bawaan). Yang berbeda hanya nomor catatan kaki atau spasi matan → `@catatan_kaki`/`@spasi` (di atas), bukan profil baru. Bahts baru memakai `imam_ayat16` (lewat `mesin/naskah_baru.txt`): sama dengan `imam`, ayat 16 supaya tidak tampak lebih besar daripada matan; naskah tanpa `@format` tetap `imam`.
- Sampul bawaan = `mesin/sampul_qism.docx` (dan `@sampul: jakarta` = `mesin/sampul_jakarta.docx`: huruf judul dibaca dari paragraf «عنوان البحث» di templat, bawaannya `PT Bold Heading`; kalau belum terpasang memakai huruf profil tebal); `@sampul: mahad` = `mesin/sampul.doc`, sampul معهد العلوم الإسلامية والعربية في جاكرتا (teks penandanya diganti `rakit.ps1`, lalu seluruh paragrafnya disetel ke huruf profil `@format` tebal dengan ukuran judul 36/26 pt). Pembimbing tercetak hanya kalau `@musyrif` diisi; `@jabatan` kosong = baris jabatan tidak tercetak.
- `PERINGATAN` sesudah `rakit` (sampul, nomor halaman, judul kepala halaman yang tidak muat satu baris, halaman sisa/kosong, teks/rumus meluap, baris akhir «:») dan pemeriksaan teks kitab lewat `scan` → lihat `dok/pengaturan-bahts.md`.
- `rakit` butuh Windows + Microsoft Word. `rakit` satu-satu (memakai Word yang sama); yang terlanjur dijalankan bersamaan antre sendiri sampai 30 menit, jadi jalankan di latar, bukan dengan batas waktu alat yang lebih pendek. Pesan antre menyebut rakit yang sedang jalan (folder, proses, jam mulai). Jangan mematikan Word, PowerShell, atau Python rakit, dan jangan menghapus atau memindahkan folder `.rakit-*`: rakit yang dimatikan gagal tanpa hasil, dan sisanya (Word, `.rakit-*`) dibereskan sendiri oleh `rakit` berikutnya. Folder `.rakit-*` bukan tanda rakit sedang jalan; yang benar `tahap <folder>` (`RAKIT=JALAN` beserta folder, proses, dan jam mulainya). `rakit` menyebut «Folder .rakit-… dibiarkan» (tanpa penanda bahan sementara; mis. berisi `JANGAN_DIHAPUS.txt` = hasil baru yang belum terpasang, atau disimpan versi lama) → lapor ke pemakai, jangan dihapus sendiri.
- Yang dibaca dan dikumpulkan = PDF. `.docx` hanya untuk Word (di Google Docs tampilannya pasti beda). Perubahan isi selalu lewat `naskah.txt`, bukan lewat .docx.

## Untuk yang mengubah mesin
Mengubah apa pun di `mesin/`, `.github/`, README, atau berkas ini → baca dulu `dok/mengubah-mesin.md` (tes, CHANGELOG, letak kode, salinan terpaksa).
