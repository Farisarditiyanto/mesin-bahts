# Catatan versi

Tiap rilis ditulis di sini: yang baru di atas. Nomor versi = `besar.kecil.tambalan`:
besar naik kalau naskah lama bisa berhenti jalan, kecil naik kalau ada kemampuan baru, tambalan naik kalau hanya perbaikan.

## 0.2.4 — 2026-10-10

- `cek` menerima juz `-` untuk kitab satu jilid yang di Shamela dibagi menjadi bagian bernama (mis. «الفوائد»: المقدمة + الكتاب): dulu rujukan «ص136» ditolak sebagai «berjilid» dan tidak bisa ditulis dengan benar. Kitab yang punya juz berangka tetap wajib menyebut juznya.
- Aturan kerja: connector `shamela_*` yang tersedia wajib dipakai mencari bahan tiap مبحث, dan laporan akhir menyebut alat pencari yang dipakai.

## 0.2.3 — 2026-10-10

- `dirasat` dan `dirasat-pdf` membaca kunci OpenAlex dari variabel lingkungan `OPENALEX_API_KEY` kalau `kunci_openalex.txt` tidak ada (mis. di cloud). Berkas tetap didahulukan.

## 0.2.2 — 2026-10-10

- `cek` jauh lebih cepat: naskah 1500 bukti dari 2,7 jadi 1,4 detik; naskah yang banyak buktinya salah dari 2 menit jadi 5 detik. `cari semua` dari 4,4 jadi 3,2 detik.
- `cek` memeriksa SELURUH kutipan terakhir sebelum catatan kaki, termasuk kutipan di dalamnya: `«قال: "…" ثم سكت»` diperiksa utuh. Dulu hanya kutipan dalam, atau potongan sesudahnya. Akibatnya `"قال: «…»"` sekarang harus persis ada di kitab berikut «قال»-nya.
- `cek` tidak lagi salah menolak kutipan yang mulai tepat di awal halaman baru (mis. `<<1681|3|144>>` untuk «في العتق وفضله» dulu dibilang «hal 143-144»).
- `cari`, `teks`, `bab`, dan `cek` menyamakan ejaan lama «شئ» dengan «شيء», tetapi «شئت» tidak ikut berubah; angka di frasa pencarian diabaikan.
- Mesin lebih ramping: cara menyamakan huruf Arab dan mencari halaman cetak kini satu, dipakai `cek` dan `cari` bersama. Isi .docx/.pdf hasil `rakit` tidak berubah.

## 0.2.1 — 2026-10-10

- `cek` menolak bukti tanpa juz (`<<id|-|hal>>`) untuk kitab berjilid: dulu lolos walau juznya tidak diketahui.
- `cek` menyebut kalau juz yang ditulis tidak ada di kitab itu, atau kalau kitabnya satu jilid (tulis juz `-`).
- `cek` menolak `<<...>>` di luar catatan kaki: dulu ikut tercetak di naskah.
- `cek` menolak ayat dengan rentang terbalik (mis. `{Q:1:7-1}`): dulu tercetak kosong.
- `cek` mengenali kutipan bersarang, mis. `"قال: «…»"` sebelum catatan kaki: dulu dianggap tanpa kutipan.
- Petunjuk «ketemu di …» menyebut sampai tiga tempat, juz yang ditulis didahulukan: dulu hanya tempat pertama di kitab.
- Catatan kaki «سبق تخريجه» tidak lagi masuk daftar «catatan kaki tanpa bukti».
- `baru` hanya menerima nama folder huruf Latin, angka, `-`, `_`: dulu `../x` membuat folder di luar repo.
- `bab` untuk kitab yang belum diunduh dan `ambil` dengan nomor yang bukan angka memberi pesan jelas.
- Keluaran yang dipotong (mis. `| head`) tidak lagi dilaporkan sebagai gagal mengunduh.

## 0.2.0 — 2026-10-10

- `dirasat` mencari juga menurut makna: pertanyaan panjang menemukan penelitian yang kata-katanya lain. Hasilnya menyebut bahasa, jumlah kutipan, nomor OpenAlex, dan sisa jatah hari itu.
- `dirasat "<kata>" [maks] [saringan]`: saringan OpenAlex, mis. `language:ar,type:dissertation`.
- `dirasat` ikut mencari di kumpulan tambahan OpenAlex, tempat banyak risalah kampus berada; kalau mesin pencari makna OpenAlex sibuk, dicoba lagi sendiri.
- `dirasat-pdf <W…> <folder>`: mengunduh PDF penelitian ke folder bahts (butuh kunci OpenAlex).
- Kunci OpenAlex dikirim lewat kepala permintaan, bukan lewat alamat.
- `temukan` tidak lagi menunggu puluhan menit kalau jatah pencarian turath.io habis: ia berhenti dan menyebut kapan terbuka lagi.
- `.mcp.json` mendaftarkan connector pilihan `hadithunlocked`, `tafsir`, dan `quran`.

## 0.1.0 — 2026-10-10

- `temukan "<frasa>"`: mencari frasa di isi semua kitab Shamela (lewat turath.io, tanpa akun), termasuk kitab yang belum diunduh; hasilnya nomor kitab untuk `ambil` dan juz/halaman.
- `hadits "<طرف>"`: penunjuk takhrij dari «المنصة الحديثية»: kitab, كتاب/باب, nomor, juz/halaman, dan hukum ulama beserta kitabnya. Isinya tetap dibaca di kitabnya sendiri.
- `cek` punya baris `perhatian` untuk yang lolos tetapi harus dilihat: bukti yang hanya ada di حاشية المحقق, dan kitab yang nomor halamannya buatan Shamela («مرقم آليا»).
- `cek`: petunjuk «ketemu di ج… ص…» sekarang juga mencari di حاشية dan menyebut halaman tepatnya.
- `dirasat` mencari di dua katalog (OpenAlex dan DOAJ) dan menerima kunci OpenAlex gratis di `kunci_openalex.txt`; satu katalog mati tidak menghentikan yang lain.
- Perbaikan: ayat 95:1 dan 97:1 tercetak dengan basmalah di depannya, dan `{Q:95:1:i-j}` / `{Q:97:1:i-j}` bergeser empat kata. Naskah yang memakai nomor kata di dua ayat itu perlu disesuaikan.
- `.mcp.json` mendaftarkan connector `turath` (pilihan, tanpa akun).

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
