# Mesin Bahts

<img src="dok/banner.jpg" width="100%" alt="Mahasiswi berjilbab di perpustakaan, kitab-kitab beterbangan di sekitarnya">

[![tes](https://github.com/Farisarditiyanto/mesin-bahts/actions/workflows/tes.yml/badge.svg)](https://github.com/Farisarditiyanto/mesin-bahts/actions/workflows/tes.yml)
[![rilis](https://img.shields.io/github/v/release/Farisarditiyanto/mesin-bahts?label=rilis)](https://github.com/Farisarditiyanto/mesin-bahts/releases)
[![lisensi](https://img.shields.io/badge/lisensi-MIT-blue)](LICENSE)

Tulis **بحث** (makalah syar'i berbahasa Arab) bersama agent AI. **Tiap kutipan dicocokkan ke halaman kitabnya** sebelum jadi PDF.

Agent AI pandai menulis, tetapi bisa mengarang kutipan. Di mesin ini:

- Agent mengutip kitab المكتبة الشاملة yang sudah diunduh ke komputermu. Sumber lain (jurnal, PDF penelitian) ditandai untuk kamu periksa sendiri.
- Tiap kutipan membawa alamat di catatan kakinya: kitab, juz, halaman.
- Mesin membuka alamat itu. Kutipan yang tidak ada di sana, atau tanpa alamat, ditolak.
- Ayat ditulis dari mushaf مجمع الملك فهد. Word dan PDF dirakit lengkap: sampul, catatan kaki, المصادر والمراجع, dan الفهارس.

## Mulai

1. Buka agent yang membaca `AGENTS.md`: [Claude Code](https://claude.com/claude-code) (butuh akun Claude berbayar), Codex, Hermes, dll.
2. Tempel kalimat ini, ganti judulnya:

   > Pakai https://github.com/Farisarditiyanto/mesin-bahts untuk membuatkan saya bahts tentang الإخلاص وأثره في قبول العمل. Susunannya: مقدمة, satu فصل berisi dua مبحث, خاتمة. Kira-kira 6 halaman.

3. Jawab pertanyaan agent: nama, nomor mahasiswa, jenis tugas, semester, pembimbing. Kamu tidak perlu mengetik perintah.

Hasilnya ada di folder `mesin-bahts` di dalam folder Dokumen-mu.

Catatan untuk agent AI: lanjutkan dari [`AGENTS.md`](AGENTS.md), bagian «Pemakai baru».

## Cara kerjanya

<img src="dok/alur.svg" width="100%" alt="Sepuluh langkah: kamu meminta, agent menyiapkan komputer dan menulis naskah, mesin mengecek kutipan dan merakit, agent kedua memeriksa ulang, kamu mengumpulkan">

<img src="dok/bukti.svg" width="100%" alt="Cara cek bekerja: alamat di catatan kaki menunjuk kitab, juz, dan halaman; hasilnya lolos, tidak ketemu, atau ketemu di halaman lain">

## Batasnya

- `cek` hanya membuktikan bahwa teksnya ada di halaman itu. Ia tidak menilai siapa yang berkata, derajat hadits, kutipan tanpa catatan kaki, atau sumber di luar Shamela. Itu diperiksa agent kedua (tanpa subagent: buka sesi agent baru), lalu kamu. **Periksa sendiri kutipan utamamu.**
- Teks kitab adalah ketikan Shamela, jadi bisa salah ketik.
- Nama di sampul namamu: isinya tanggung jawabmu. Tanyakan ke dosen apakah bantuan AI dibolehkan.
- Proyek ini tidak mewakili kampus mana pun.

## Yang dibutuhkan

| Untuk | Butuh |
|---|---|
| Semua perintah | Python 3.12 ke atas, internet saat mengunduh kitab |
| Word dan PDF (`rakit`) | Windows dan Microsoft Word desktop |

Mac/Linux bisa menulis dan `cek`, tanpa Word dan PDF. `python mesin/bahts.py periksa` menyebut apa yang kurang dan cara membereskannya.

## Pilihan

- **Connector `shamela`** (sangat disarankan): agent bisa mencari kitab yang belum diunduh. Sudah terdaftar di `.mcp.json`; masuk dengan akun shamela.link sendiri. Connector lain tanpa akun: `turath`, `hadithunlocked`, `tafsir`, `quran`. Semuanya layanan orang lain; tanpa itu mesin tetap jalan.
- **Agent selain Claude Code**: daftarkan connector sendiri (mis. `codex mcp add shamela --url https://shamela.link/mcp`, lalu `codex mcp login shamela`).
- **Kunci OpenAlex** untuk `dirasat` (penelitian terdahulu): tanpa kunci jatahnya kecil dan `dirasat-pdf` tertutup. Daftar di https://openalex.org, salin dari Settings > API key, simpan di `kunci_openalex.txt` (atau variabel `OPENALEX_API_KEY`).

## Tanpa agent

```bash
git clone https://github.com/Farisarditiyanto/mesin-bahts.git
```

```bash
cd mesin-bahts
```

```bash
python mesin/bahts.py periksa
```

Daftar perintah: `python mesin/bahts.py`. Daftar tanda naskah: `python mesin/bahts.py tanda`. Contoh: [`contoh/naskah.txt`](contoh/naskah.txt); coba dengan `python mesin/bahts.py ambil 11223`, lalu `python mesin/bahts.py cek contoh`.

## Standar halaman

<img src="dok/standar.svg" width="100%" alt="Asal tiap aturan bentuk halaman: aturan kampus, catatan dosen, atau pilihan mesin">

Dasarnya «[القواعد المنظمة لتسجيل الرسالة العلمية وكتابتها وطباعتها وتقديمها](https://units.imamu.edu.sa/colleges/cmc/AcademicDepts/SiteAssets/Pages/d_j_e_p/%D8%A7%D9%84%D9%82%D9%88%D8%A7%D8%B9%D8%AF%20%D8%A7%D9%84%D9%85%D9%86%D8%B8%D9%85%D8%A9%20%D9%84%D8%AA%D8%B3%D8%AC%D9%8A%D9%84%20%D8%A7%D9%84%D8%B1%D8%B3%D8%A7%D9%84%D8%A9%20%D8%A7%D9%84%D8%B9%D9%84%D9%85%D9%8A%D8%A9.pdf)» (جامعة الإمام, 1442 H) dan catatan dosen bahts kelas معهد العلوم الإسلامية والعربية في جاكرتا. Kampus atau dosen lain: ganti `mesin/sampul.doc` dan tambah profil di `mesin/format.json`.

## Lain-lain

- Naskah, PDF, `sampul_saya.txt`, dan `kitab/` tetap di komputermu, tidak ikut repo.
- Lisensi kode: MIT ([`LICENSE`](LICENSE)). Teks mushaf, font, logo, dan teks kitab: [`NOTICE`](NOTICE).
- Masalah: buka issue dengan keluaran `periksa`, perintahnya, dan pesannya. Perubahan: pull request dengan tes hijau. Riwayat: [`CHANGELOG.md`](CHANGELOG.md).
