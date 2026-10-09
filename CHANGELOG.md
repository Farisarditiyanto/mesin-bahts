# Catatan versi

Tiap rilis ditulis di sini: yang baru di atas. Nomor versi = `besar.kecil.tambalan`:
besar naik kalau naskah lama bisa berhenti jalan, kecil naik kalau ada kemampuan baru, tambalan naik kalau hanya perbaikan.

## 0.0.2 — 2026-10-09

- `@tanpa: ayat, hadits, maudhuat` membuang فهرس yang tidak diinginkan; فهرس الآيات dan فهرس الأحاديث yang kosong tidak lagi dicetak.
- `rakit` mencetak `HALAMAN_ISI` (المقدمة sampai الخاتمة).
- `periksa` memberi jalan memasang huruf Traditional Arabic tanpa membuka Settings.
- `periksa`: menyebut apa yang sudah siap di komputer dan perintah untuk tiap yang belum.
- `AGENTS.md` punya bagian «Pemakai baru» untuk orang yang baru pertama kali memakai agent.
- README: gambar hasil, gambar alur, dan «Cara tercepat».
- `siapkan` punya sumber font kedua: salinan di rilis GitHub proyek ini.
- `.mcp.json` mendaftarkan connector `shamela` (pilihan) untuk Claude Code.
- Unduhan yang putus di tengah tidak lagi dianggap jadi: `ambil` mengunduh ulang, `siapkan` pindah ke sumber font berikutnya.
- `@thalibah` selain «ya» ditolak `cek`; `sampul_saya.txt` yang bukan UTF-8 ditolak `baru` dengan pesan jelas.

## 0.0.1 — 2026-10-09

Rilis publik pertama. Nomor 0.x berarti masih tahap awal: bentuk naskah dan perintah masih bisa berubah.

- `siapkan`: mengunduh katalog kitab dan font mushaf, lalu memasang font itu.
- `baru`, `cek`, `rakit`: dari `naskah.txt` sampai `.docx` dan `.pdf` (rakit: Windows + Microsoft Word).
- `katalog`, `ambil`, `kartu`, `cari`, `teks`, `bab`, `halaman`: perpustakaan Shamela lokal.
- `dirasat`: mencari penelitian terdahulu di OpenAlex.
- Pembimbing tercetak di sampul hanya kalau `@musyrif` diisi.
- `@thalibah: ya` membuat sampul mencetak «اسم الطالبة».
- Data sampul pemakai cukup ditulis sekali di `sampul_saya.txt`.
