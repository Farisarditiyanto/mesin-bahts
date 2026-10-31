# Mesin Bahts

<img src="dok/banner.jpg" width="100%" alt="Mahasiswi berjilbab di perpustakaan, kitab-kitab beterbangan di sekitarnya">

[![tes](https://github.com/Farisarditiyanto/mesin-bahts/actions/workflows/tes.yml/badge.svg)](https://github.com/Farisarditiyanto/mesin-bahts/actions/workflows/tes.yml)
[![rilis](https://img.shields.io/github/v/release/Farisarditiyanto/mesin-bahts?label=rilis)](https://github.com/Farisarditiyanto/mesin-bahts/releases)
[![lisensi](https://img.shields.io/badge/lisensi-MIT-blue)](LICENSE)

Mesin untuk menulis **بحث** (makalah syar'i berbahasa Arab) bersama agent AI. Agent AI bisa mengarang kutipan, jadi tiap kutipan dicocokkan ke halaman kitabnya sebelum jadi Word dan PDF.

## Untuk agent

1. Aturan kerja ada di [`AGENTS.md`](AGENTS.md). Mulai dari bagian «Pemakai baru». Pemakai cukup menjawab pertanyaan; semua perintah kamu yang jalankan.
2. **Connector `shamela` wajib.** Jangan mengumpulkan bahan sebelum alat `shamela_*` tersedia. Cara mencari, mendaftarkan, dan masuk akunnya: `AGENTS.md` «Pemakai baru» langkah 4.
3. Perintah: `python mesin/bahts.py` (daftar perintah), `python mesin/bahts.py tanda` (daftar tanda naskah), `python mesin/bahts.py periksa` (kebutuhan komputer dan cara membereskannya). Contoh naskah yang lolos `cek`: [`contoh/naskah.txt`](contoh/naskah.txt).

## Untuk pemakai: mulai

1. Buka agent AI yang membaca `AGENTS.md` (pilihannya di «[Agent AI](#agent-ai)»; ada yang gratis).
2. Tempel kalimat ini, ganti judulnya:

   > Pakai https://github.com/Farisarditiyanto/mesin-bahts untuk membuatkan saya bahts tentang الإخلاص وأثره في قبول العمل. Susunannya: مقدمة, satu فصل berisi dua مبحث, خاتمة. Kira-kira 6 halaman.

   Supaya agent tidak banyak bertanya, tempel templat ini dan isi semampumu. Baris kosong ditanyakan agent atau memakai bawaan.

   ```
   Pakai https://github.com/Farisarditiyanto/mesin-bahts untuk membuatkan saya bahts.

   Data diri:
   - Nama (Arab):
   - Nomor mahasiswa:
   - Jenis tugas (Arab): بحث صفي للمستوى ...
   - Semester (Arab): الفصل الدراسي ...
   - Mahasiswa/mahasiswi:
   - Kampus: معهد العلوم الإسلامية والعربية في جاكرتا، كلية الشريعة (ya/tidak)

   Bahts:
   - Judul (Arab):
   - Pembimbing (Arab) dan jabatannya:
   - Halaman isi (المقدمة sampai الخاتمة): kira-kira ... halaman
   - Susunan: مقدمة، ... فصل/مبحث، خاتمة (atau: terserah agent)
   - Isi المقدمة yang diminta dosen:
   - الدراسات السابقة: ya/tidak
   - Kitab yang wajib atau dilarang dipakai:
   - Angka: ٠١٢٣ / 0123 / hanya nomor ayat di catatan kaki 0123
   - فهرس yang tidak dicetak: tidak ada / ayat / hadits / maudhuat
   - Sumber cukup di catatan kaki (tanpa المصادر والمراجع): ya/tidak
   - Aturan bentuk halaman lain dari dosen: tidak ada / ...
   - Nama folder (huruf Latin, tanpa spasi):
   ```

3. Siapkan akun [shamela.link](https://shamela.link): agent memintamu masuk sekali.
4. Jawab pertanyaan agent yang tersisa. Kamu tidak perlu mengetik perintah.

Hasilnya ada di folder `mesin-bahts` di dalam folder Dokumen-mu.

## Cara kerjanya

- Agent mengutip kitab المكتبة الشاملة yang sudah diunduh ke komputer pemakai. Sumber lain (jurnal, PDF penelitian) ditandai untuk diperiksa sendiri.
- Tiap kutipan membawa alamat di catatan kakinya: kitab, juz, halaman.
- `cek` membuka alamat itu. Kutipan yang tidak ada di sana, atau tanpa alamat, ditolak. Ayat dan angka di dalam kutipan, juga juz/halaman yang tercetak, ikut dicocokkan.
- Kutipan yang tidak ditemukan di kitab yang dirujuk bisa dicari di kitab lain yang sudah diunduh: `python mesin/bahts.py cek <folder> --jejak`. Hasilnya petunjuk (kitab + juz/halaman), bukan bukti; putusan tetap dari `cek`. Pencarian pertama membaca teks semua kitab, jadi bisa lama.
- Ayat ditulis dari mushaf مجمع الملك فهد. `rakit` membuat Word dan PDF lengkap: sampul, catatan kaki, المصادر والمراجع, dan الفهارس.

<img src="dok/alur.svg" width="100%" alt="Sepuluh langkah: kamu meminta, agent menyiapkan komputer dan menulis naskah, mesin mengecek kutipan dan merakit, agent kedua memeriksa ulang, kamu mengumpulkan">

<img src="dok/bukti.svg" width="100%" alt="Cara cek bekerja: alamat di catatan kaki menunjuk kitab, juz, dan halaman; hasilnya lolos, tidak ketemu (dengan kata yang berbeda bila hampir cocok), atau ketemu di halaman lain; kalau ketemu di kitab lain, cek --jejak menunjuknya">

## Batasnya

- `cek` hanya membuktikan bahwa teksnya ada di halaman itu. Ia tidak menilai siapa yang berkata, derajat hadits, kutipan tanpa catatan kaki, atau sumber di luar Shamela (PDF penelitian di folder bahts, `<<luar|berkas.pdf|hal>>`, hanya ditunjukkan halamannya). Itu diperiksa agent kedua (tanpa subagent: sesi agent baru), lalu kamu. **Periksa sendiri kutipan utamamu.**
- `<<sid|juz|hal|#123>>` hanya lolos kalau 123 berdiri sebagai kepala hadits di awal baris halaman itu («123 - حدثنا», «36 - (123)», «(123) - حدثنا»). Nomor ayat dan catatan ditolak. Nomor hadits lain atau daftar bernomor di halaman yang sama tetap bisa tertukar, jadi `#123` membuktikan nomornya ada, bukan lafaznya.
- Takhrij `رقم الحديث (123)، 4/56.` yang langsung diikuti bukti halaman itu dicocokkan otomatis: nomornya harus kepala hadits di sekitar halaman itu, dan lafaz buktinya harus ada di hadits bernomor itu. Hasilnya `perhatian`, bukan GAGAL.
- Teks kitab = ketikan Shamela, jadi bisa salah ketik. Ayat kitab yang salah ketik biasanya ditandai `cek` sebagai perhatian: cocokkan ke scan cetakannya.
- Model AI gratis lebih sering salah langkah; pemeriksaan ulang makin penting.
- Nama di sampul namamu: isinya tanggung jawabmu. Tanyakan ke dosen apakah bantuan AI dibolehkan.
- Proyek ini tidak mewakili kampus mana pun.

## Yang dibutuhkan

| Untuk | Butuh |
|---|---|
| Menulis bahts | Agent AI yang membaca `AGENTS.md`, dengan connector `shamela` (akun shamela.link) untuk mengumpulkan bahan |
| Semua perintah | Python 3.12 ke atas; internet saat mengunduh kitab |
| Word dan PDF (`rakit`) | Windows dan Microsoft Word desktop |

Mac/Linux bisa menulis dan `cek`, tanpa Word dan PDF. `cek` dan `rakit` sendiri tidak butuh connector.

### Agent AI

| Agent | Biaya | Connector |
|---|---|---|
| [OpenCode](https://opencode.ai) | Gratis. Punya model gratis; daftarnya berganti-ganti (`/models`) | Terbaca sendiri dari `opencode.json` |
| [Hermes Agent](https://hermes-agent.nousresearch.com) | Gratis, sumber terbuka. Modelnya disambungkan sendiri | Agent mendaftarkannya sesudah minta izin |
| [Claude Code](https://claude.com/claude-code) | Berbayar | Terbaca sendiri dari `.mcp.json` |
| Codex | Akun ChatGPT | Agent mendaftarkannya sesudah minta izin |
| [Command Code](https://commandcode.ai) | Mulai $1/bulan (paket Go), termasuk model gratis; daftarnya berganti-ganti | **Belum bisa dipakai**: `shamela` belum bisa masuk di sana |

- Sebagian model gratis memakai isi obrolan untuk melatih modelnya. Baca keterangan modelnya sebelum memilih.
- Semua agent di atas membaca `AGENTS.md`, jadi caranya sama. Connector = sambungan MCP.
- Aplikasi Claude: tab Code = Claude Code, jadi `.mcp.json` terbaca, begitu juga connector dari menu Connectors aplikasi Claude. Aplikasi Codex memakai pengaturan connector yang sama dengan Codex di terminal. Aplikasi desktop OpenCode dan Command Code belum dicoba.
- Mode obrolan biasa (Claude chat, ChatGPT) tidak bisa menjalankan mesin: pilih mode yang membuka folder dan menjalankan perintah.

### Connector dan kunci

- **`shamela`** (wajib, butuh akun shamela.link): mencari di seluruh kitab Shamela, termasuk yang belum diunduh.
- **Tanpa akun, pilihan:** `turath` (isi semua kitab), `hadithunlocked` (hadits, derajat, syarah), `tafsir` (tafsir per ayat), `quran` (teks ayat).
- Semua connector = layanan orang lain dan hanya penunjuk jalan: kitabnya tetap di-`ambil`, kutipannya tetap harus lolos `cek`.
- **Kunci OpenAlex** (pilihan) untuk `dirasat` (penelitian terdahulu): tanpa kunci jatahnya kecil dan `dirasat-pdf` tertutup. Daftar di https://openalex.org, salin dari Settings > API key, simpan sebagai satu baris di `kunci_openalex.txt` (atau variabel `OPENALEX_API_KEY`).

## Tanpa agent

```bash
git clone https://github.com/Farisarditiyanto/mesin-bahts.git
cd mesin-bahts
python mesin/bahts.py periksa
```

Coba contohnya: `python mesin/bahts.py ambil 11223`, lalu `python mesin/bahts.py cek contoh`.

## Standar halaman

<img src="dok/standar.svg" width="100%" alt="Asal tiap aturan bentuk halaman: aturan kampus, catatan dosen, atau pilihan mesin">

- Dasarnya «[القواعد المنظمة لتسجيل الرسالة العلمية وكتابتها وطباعتها وتقديمها](https://units.imamu.edu.sa/colleges/cmc/AcademicDepts/SiteAssets/Pages/d_j_e_p/%D8%A7%D9%84%D9%82%D9%88%D8%A7%D8%B9%D8%AF%20%D8%A7%D9%84%D9%85%D9%86%D8%B8%D9%85%D8%A9%20%D9%84%D8%AA%D8%B3%D8%AC%D9%8A%D9%84%20%D8%A7%D9%84%D8%B1%D8%B3%D8%A7%D9%84%D8%A9%20%D8%A7%D9%84%D8%B9%D9%84%D9%85%D9%8A%D8%A9.pdf)» (جامعة الإمام, 1442 H) dan catatan dosen bahts kelas معهد العلوم الإسلامية والعربية في جاكرتا.
- Kampus atau dosen lain: ganti `mesin/sampul_qism.docx` dan tambah profil di `mesin/format.json`. Sampul bawaan = model قسم الشريعة; sampul معهد العلوم الإسلامية والعربية: `@sampul: mahad`.
- Angka: aturan kampus dan catatan dosen tidak menyebut jenis angka. Contoh resmi kampus memakai ٠١٢٣ di nomor halaman, catatan kaki, rujukan, tahun, nomor ayat, dan فهرس: «[دليل إعداد وكتابة الرسائل العلمية](https://units.imamu.edu.sa/shis/sij/FilesLibrary/Documents/Guide%20to%20preparing%20and%20writing%20scientific%20theses.pdf)» (جامعة الإمام, cetakan kedua) dan «[مجلة العلوم الشرعية](https://journals.imamu.edu.sa/index.php/jis)». Jadi PDF mencetak ٠١٢٣ di semua tempat itu, apa pun angka yang diketik di naskah.
- Dosen minta 0123 → `@angka: latin` di naskah. Cuma nomor ayat di catatan kaki («سورة الفتح، آية: 29.») yang 0123 → `@angka_ayat: latin`.

## Lain-lain

- Naskah, PDF, `sampul_saya.txt`, dan `kitab/` tetap di komputer pemakai, tidak ikut repo.
- Lisensi kode: MIT ([`LICENSE`](LICENSE)). Teks mushaf, font, logo, dan teks kitab: [`NOTICE`](NOTICE).
- Masalah: buka issue dengan keluaran `periksa`, perintahnya, dan pesannya. Perubahan: pull request dengan tes hijau. Riwayat: [`CHANGELOG.md`](CHANGELOG.md).
