# Mesin Bahts

**Bahasa:** Indonesia · [العربية](README.ar.md)

<img src="dok/banner.jpg" width="100%" alt="Mahasiswi berjilbab di perpustakaan, kitab-kitab beterbangan di sekitarnya">

[![tes](https://github.com/Farisarditiyanto/mesin-bahts/actions/workflows/tes.yml/badge.svg)](https://github.com/Farisarditiyanto/mesin-bahts/actions/workflows/tes.yml)
[![rilis](https://img.shields.io/github/v/release/Farisarditiyanto/mesin-bahts?label=rilis)](https://github.com/Farisarditiyanto/mesin-bahts/releases)
[![lisensi](https://img.shields.io/badge/lisensi-AGPLv3%2B-blue)](LICENSE)

Agent menulis **بحث** (makalah syar'i berbahasa Arab) di `naskah.txt`, satu folder per bahts. `cek` menolak kutipan yang tidak ada di halaman kitab Shamela yang dirujuk, lalu `rakit` menjadikan naskah itu Word dan PDF.

README ini peta untuk agent. Pemakai cukup menempel tautan repo ini ke [coding agent](#agent-dan-connector), lalu menjawab pertanyaannya.

## Mulai

1. Baca [`AGENTS.md`](AGENTS.md) seluruhnya. Itu aturan kerjanya. Mulai dari «Pemakai baru».
2. Jalankan `python mesin/bahts.py periksa` (Linux/macOS: `python3`). Bereskan tiap baris `BELUM` dengan perintah yang disebutnya.
3. Pastikan connector `shamela` tersambung: ada alat `shamela_search_phrase`. Cara mendaftarkan dan masuk per agent: `AGENTS.md` «Pemakai baru» langkah 4.
4. Sesi lanjutan, atau tidak tahu bahts sampai mana: `python mesin/bahts.py tahap <folder>`. Ikuti baris `BERIKUTNYA`.

Kebutuhan komputer dan cara membereskannya ada di satu tempat: `python mesin/bahts.py periksa`. `rakit` butuh Windows + Microsoft Word desktop; Linux/macOS bisa menulis dan `cek`, tanpa Word dan PDF. Bahan butuh connector `shamela` (akun shamela.link); الدراسات السابقة butuh kunci OpenAlex (`AGENTS.md` «Pemakai baru» langkah 6).

### Agent dan connector

| Agent | Membaca daftar connector dari |
|---|---|
| [Claude Code](https://claude.com/claude-code) (juga tab Code aplikasi Claude) | `.mcp.json`, plus menu Connectors aplikasi Claude |
| [OpenCode](https://opencode.ai) (gratis) | `opencode.json` |
| [Command Code](https://commandcode.ai) | `.mcp.json`, plus entri `shamela` lokal yang membawa `clientId` |
| Codex (CLI dan aplikasinya) | didaftarkan agent |
| [Hermes Agent](https://hermes-agent.nousresearch.com) (gratis) | didaftarkan agent |

- Perintah mendaftarkan dan masuk `shamela` per agent: `AGENTS.md` «Pemakai baru» langkah 4 (satu-satunya tempat).
- Mode obrolan biasa (Claude chat, ChatGPT) tidak bisa menjalankan mesin. Model gratis lebih sering salah langkah, jadi pemeriksa langkah 5 makin penting.
- Connector: `shamela` wajib; `turath`, `hadithunlocked`, `tafsir`, `quran` tanpa akun. Gunanya dan urutan cadangannya: `AGENTS.md` langkah 4-5 dan Alur kerja langkah 2. Angka uji tiap connector, termasuk MCP resmi shamela.ws yang sengaja tidak dipasang: [`dok/uji-riset.md`](dok/uji-riset.md).
- Semua connector hanya penunjuk jalan: kitabnya tetap di-`ambil`, kutipannya tetap harus lolos `cek`.

### Sampaikan ke pemakai

- Nama di sampul nama pemakai: isinya tanggung jawabnya. Ia perlu bertanya ke dosen apakah bantuan AI dibolehkan.
- `cek` tidak menggantikan membaca: minta pemakai memeriksa sendiri kutipan utamanya.
- Sebagian model gratis memakai isi obrolan untuk melatih modelnya.
- Proyek ini tidak mewakili kampus mana pun.

## Cara kerja

| Langkah | Perintah | Hasil |
|---|---|---|
| Buat folder | `baru <folder> "<judul>"` | `naskah.txt` (kerangka), `riset.txt` |
| Cari bahan | connector `shamela_*`, `temukan`, `katalog`, `hadits`, `dirasat` | nomor kitab + juz/halaman (penunjuk) |
| Unduh kitab | `ambil <id>` atau `ambil <folder>` | `kitab/<id>/` |
| Data cetak | `kartu <id>` | rujukan pertama dan المصادر |
| Baca teks | `cari`, `teks`, `bab`, `halaman` | teks lokal untuk disalin persis |
| Periksa | `cek <folder>` (`--jejak` untuk kutipan yang tidak ketemu) | `GAGAL: n`, perhatian, `NASKAH_SHA256` |
| Pemeriksa | `bukti <folder> [awal-akhir]` | teks halaman di sekitar tiap catatan kaki, dan paragraf isi tanpa catatan kaki |
| Rakit | `rakit <folder> [--fasl n]` (Windows + Word) | `.docx` + `.pdf` (sampul, catatan kaki, المصادر والمراجع, الفهارس), `HALAMAN_ISI`, `HALAMAN` |
| Status | `tahap <folder>` | `NASKAH=`, `HASIL=`, `RAKIT=`, `BERIKUTNYA` |

Semua perintah = `python mesin/bahts.py <perintah>`. Daftar lengkap dan argumennya: `python mesin/bahts.py`. Daftar tanda naskah (`#F`, `{Q:}`, `{H:}`, `@format`, …): `python mesin/bahts.py tanda`. Naskah contoh yang lolos `cek`: [`contoh/naskah.txt`](contoh/naskah.txt) (`ambil 11223`, lalu `cek contoh`).

### Yang dibuktikan `cek`

- Tiap kutipan bertanda petik harus terbaca di juz/halaman kitab yang dirujuk. Tidak ada di sana, atau tanpa alamat = `GAGAL`.
- Juz/halaman yang tercetak di catatan kaki dicocokkan dengan alamat buktinya. Nama kitab di catatan kaki harus sesuai buktinya, dan derajat hadits di takhrij harus terbaca di halaman bukti. Kutipan di حاشية المحقق, atau yang di kitab diantar «قال …» orang lain, jadi perhatian.
- Ayat dan angka di kutipan dicocokkan pada kemunculan berkata utuh di halaman bukti; angka dari halaman tetangga tidak dihitung.
- Ayat dicetak dari mushaf Hafs rasm Utsmani (`mesin/quran_hafs_v22.json`) lewat `{Q:surah:ayat}`. Ayat yang diketik sendiri dalam ﴿…﴾ dengan rujukan «سورة …» = `GAGAL`; tanpa rujukan = perhatian. Ayat tanpa ﴿…﴾ sesudah «قال الله تعالى» yang dirujuk «سورة …» juga `GAGAL`.
- `<<sid|juz|hal|#123>>` lolos hanya kalau 123 kepala hadits di awal baris halaman itu («123 - حدثنا», «36 - (123)», «(123) - حدثنا»); nomor ayat dan nomor catatan ditolak. Ini membuktikan nomornya ada, bukan lafaznya.
- Takhrij «رقم الحديث (123)، 4/56.» yang langsung diikuti bukti: nomornya harus kepala hadits di sekitar halaman itu, lafaz buktinya harus di hadits bernomor itu. Hasilnya perhatian, bukan `GAGAL`.
- `cek --jejak`: kutipan yang tidak ketemu dicari di kitab lain yang sudah diunduh, paling banyak 3 kitab per teks; lafaz yang sedikit berbeda ditunjuk sebagai «Paling mirip»; kutipan yang menyambung ke halaman berikutnya ditunjuk rentangnya (ص21-22). Hanya petunjuk. Kitab yang tidak terbaca dilewati dengan peringatan «jejak belum lengkap». Pencarian pertama menyiapkan teks kitab, jadi bisa lama.
- Sumber di luar Shamela: `<<luar|berkas.pdf|hal>>` hanya ditunjuk halamannya, tidak pernah diloloskan.
- Cara menukil (perhatian, bukan `GAGAL`): kalimat di luar tanda petik yang 8 kata atau lebih berurutan sama persis dengan halaman buktinya, nukilan makna tanpa «انظر:», kutipan lafaz yang dirujuk «انظر:», dan kutipan lebih dari 60 kata. Apakah nukilan makna setia pada halaman buktinya tidak dinilai: bukti berpotongan hanya membuktikan potongannya.
- Yang tidak bisa dinilai `cek` (pembicara, mu'tamad tidaknya kitab, kutipan tanpa catatan kaki): akhir «Alur kerja» di `AGENTS.md`. Itu tugas pemeriksa langkah 5.

`cek` dan `rakit` tidak memakai internet atau connector: hasilnya harus sama tanpa jaringan.

### Standar halaman

- Dasarnya «[القواعد المنظمة لتسجيل الرسالة العلمية وكتابتها وطباعتها وتقديمها](https://units.imamu.edu.sa/colleges/cmc/AcademicDepts/SiteAssets/Pages/d_j_e_p/%D8%A7%D9%84%D9%82%D9%88%D8%A7%D8%B9%D8%AF%20%D8%A7%D9%84%D9%85%D9%86%D8%B8%D9%85%D8%A9%20%D9%84%D8%AA%D8%B3%D8%AC%D9%8A%D9%84%20%D8%A7%D9%84%D8%B1%D8%B3%D8%A7%D9%84%D8%A9%20%D8%A7%D9%84%D8%B9%D9%84%D9%85%D9%8A%D8%A9.pdf)» (جامعة الإمام, 1442 H) dan catatan dosen bahts kelas معهد العلوم الإسلامية والعربية في جاكرتا. Asal tiap aturan: [`dok/standar.svg`](dok/standar.svg).
- Dosen minta bentuk lain: lihat `AGENTS.md` «Sebelum tiap bahts» (`@format`, `@templat`, `@sampul`, `@spasi`, `@catatan_kaki`). Di folder pemakai jangan mengubah berkas `mesin/`; profil baru di `mesin/format.json` = perubahan mesin.
- Angka: aturan kampus dan catatan dosen tidak menyebut jenis angka. Contoh resmi kampus memakai ٠١٢٣ di nomor halaman, catatan kaki, rujukan, tahun, nomor ayat, dan فهرس: «[دليل إعداد وكتابة الرسائل العلمية](https://units.imamu.edu.sa/shis/sij/FilesLibrary/Documents/Guide%20to%20preparing%20and%20writing%20scientific%20theses.pdf)» (جامعة الإمام, cetakan kedua) dan «[مجلة العلوم الشرعية](https://journals.imamu.edu.sa/index.php/jis)». Jadi PDF mencetak ٠١٢٣ di semua tempat itu, apa pun angka yang diketik di naskah. Tautan dan DOI (`https://…`, `www.…`, `doi.org/…`, `10.xxxx/…`) dicetak kiri-ke-kanan apa adanya.
- Dosen minta 0123 → `@angka: latin`. Hanya nomor ayat di catatan kaki → `@angka_ayat: latin`.

## Repo

| Letak | Isi |
|---|---|
| `mesin/bahts.py` | satu-satunya pintu perintah |
| `mesin/olah.py`, `naskah.py`, `cek_*.py`, dan modul pembantunya | `cek`; pembagian tiap berkas: `AGENTS.md` «Letak kode `cek`» |
| `mesin/quran_hafs_v22.json`, `nama_surah.json` | teks mushaf dan nama surat |
| `mesin/shamela.py` | unduh kitab, katalog, `temukan`, `scan` |
| `mesin/hadits.py`, `dirasat.py` | penunjuk takhrij, penelitian terdahulu |
| `mesin/tahap.py`, `berkas.py` | keadaan bahts dan folder `.rakit-*` |
| `mesin/rakit.ps1`, `teks_pdf.py` | perakit Word/PDF dan teks PDF |
| `mesin/format.json` | profil bentuk halaman (`@format`) |
| `mesin/sampul_qism.docx`, `sampul.doc`, `sampul_jakarta.docx`, `kepala_kotak.docx` | templat sampul dan kepala halaman |
| `mesin/naskah_baru.txt`, `riset_baru.txt` | kerangka dari `baru` |
| `contoh/` | `naskah.txt` + `riset.txt` contoh dan `jebakan/` untuk tes |
| `.mcp.json`, `opencode.json` | daftar connector (`opencode.json` = salinan untuk OpenCode) |
| `dok/` | `mutamad.md` (kitab mu'tamad tiap mazhab), `uji-riset.md`, `takhrij.md`, audit |
| `.github/` | `uji_*.py`, `workflows/tes.yml` |
| `kitab/`, `bahts/`, `sampul_saya.txt`, `keluaran_saya.txt`, `kunci_openalex.txt` | data pemakai di komputernya, tidak di git |

### Mengubah mesin

- Aturannya: `AGENTS.md` «Untuk yang mengubah mesin».
- Tes: `python .github/uji_semua.py` (daftar dibaca dari `.github/workflows/tes.yml`; kitab tes: baris `ambil` di berkas itu).
- Perubahan yang dirasakan pemakai masuk [`CHANGELOG.md`](CHANGELOG.md) bagian «Belum dirilis».
- [`README.ar.md`](README.ar.md) = terjemahan berkas ini: ubah keduanya bersamaan.
- Masalah: issue berisi keluaran `periksa`, perintahnya, dan pesannya.

### Lisensi

Kode: GNU AGPLv3 atau versi sesudahnya ([`LICENSE`](LICENSE)); versi sampai 94d62d3 (termasuk rilis 7.0.0) tetap MIT. Bahts hasil mesin milik penulisnya; templat yang tersalin ke bahts boleh dipakai tanpa syarat (izin tambahan di `NOTICE`). Teks mushaf, font, logo, dan teks kitab: [`NOTICE`](NOTICE).
