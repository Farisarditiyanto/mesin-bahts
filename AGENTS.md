# Bahts — mesin penulisan bahts (riset ilmiah berbahasa Arab)

Satu bahts = satu folder; yang ditulis cuma `naskah.txt`, sisanya (cek rujukan, Word, PDF) dikerjakan mesin. Bahan bahts jangan masuk `mesin/`; `kitab/` dipakai semua bahts.
Daftar perintah: `python mesin/bahts.py`. Daftar tanda naskah: `python mesin/bahts.py tanda`.

## Pemakai baru

Anggap pemakai baru pertama kali memakai agent, tidak membaca README, dan hanya memberi tautan repo plus permintaan bahts. Kerjakan semuanya sendiri; pemakai cukup menjawab pertanyaan. Pakai bahasa awam.

1. Repo belum ada di komputer → cek dulu folder `mesin-bahts` di dalam folder Dokumen pemakai. Belum ada → unduh ke sana: `git clone`, atau kalau `git` tidak ada, unduh `https://github.com/Farisarditiyanto/mesin-bahts/archive/refs/heads/main.zip` lalu ekstrak dan namai foldernya `mesin-bahts` (zip itu terekstrak sebagai `mesin-bahts-main`). Folder Dokumen = folder dokumen akun pemakai (di Windows bisa berada di dalam OneDrive). Jangan mengunduh ke folder sistem, folder program, atau folder kerja orang lain. Semua bahts pemakai tinggal di dalam folder itu.
2. Jalankan `python mesin/bahts.py periksa` (di Linux/macOS biasanya `python3`). Bereskan sendiri tiap baris `BELUM` dengan perintah yang disebutnya, lalu ulangi sampai tidak ada lagi yang bisa kamu bereskan. `python` tidak dikenal → pasang Python 3.12 dulu (Windows: `winget install Python.Python.3.12`); kalau sesudah itu `python` masih tidak dikenal di terminalmu, pakai `py`. Beri tahu pemakai bahwa `siapkan` memasang satu font (font mushaf) untuk akunnya.
3. `periksa` bilang `rakit` BELUM karena Windows atau Microsoft Word → beri tahu pemakai SEKARANG, sebelum menulis apa pun: hasilnya berhenti di naskah yang sudah dicek, tanpa Word dan PDF. Tanya: lanjut, atau pasang Word dulu. Jangan memasang Word sendiri dan jangan memakai pengganti Word. Yang BELUM «huruf Traditional Arabic» → jalankan perintah PowerShell admin yang disebut `periksa`, dan beri tahu pemakai dulu bahwa Windows akan menampilkan satu jendela izin: cukup klik Yes. Perintah itu selesai sesudah jendelanya menutup; ulangi `periksa`. Masih BELUM → minta pemakai menambah papan ketik Arab seperti yang disebut `periksa`.
4. Connector `shamela` sangat disarankan. Alat `shamela_*` tidak tersedia → beri tahu pemakai sekali: gunanya (mencari kitab yang membahas suatu masalah, termasuk yang belum diunduh) dan caranya (setujui connector `shamela` yang ditawarkan Claude Code, lalu masuk dengan akun shamela.link sendiri). Pemakai menolak atau belum bisa → lanjut dengan `temukan`, `katalog`, dan `cari` (connector `turath` tidak butuh akun), dan tulis di laporan akhir bahwa pencarian bahan lebih sempit.

## Sebelum tiap bahts

- `sampul_saya.txt` belum ada → tanya pemakai sekali: nama (huruf Arab), nomor mahasiswa, jenis tugas, semester, dan mahasiswa atau mahasiswi. Simpan sebagai baris `@nama:`, `@nim:`, `@jenis:`, `@fasl:` di berkas itu. `baru` memakainya untuk tiap bahts.
- Pemakainya mahasiswi → tambah baris `@thalibah: ya` di `sampul_saya.txt`: sampul mencetak «اسم الطالبة».
- Pembimbing (`@musyrif`, `@jabatan`) ditanya tiap bahts dan ditulis di naskahnya: dosennya bisa berbeda.
- Sampul mencetak جامعة الإمام محمد بن سعود الإسلامية، معهد العلوم الإسلامية والعربية في جاكرتا، كلية الشريعة. Beri tahu pemakai sekali; kalau kampusnya lain, bilang bahwa sampul perlu diganti dulu (`mesin/sampul.doc`).
- Nama folder untuk `baru`: pendek, huruf Latin, tanpa spasi (mis. `ikhlas`). Nama berkas hasil diatur `@berkas`.
- Jumlah halaman yang disebut pemakai = halaman isi (المقدمة sampai الخاتمة); `rakit` mencetaknya sebagai `HALAMAN_ISI`. مقدمة, tiap فصل, dan خاتمة selalu mulai halaman baru. Jelaskan ke pemakai bahwa PDF juga memuat sampul, المصادر والمراجع, dan الفهارس, lalu sebut `HALAMAN_ISI` dan `HALAMAN` sesudah `rakit`.
- Pemakai tidak mau فهرس tertentu → `@tanpa:` di naskah (`ayat`, `hadits`, `maudhuat`; mis. `@tanpa: ayat, hadits`). Jangan membuangnya tanpa diminta.
- Laporan akhir ke pemakai: tulis letak lengkap berkas PDF-nya.

## Alur kerja

1. `baru`, lalu susun خطة (فصل/مبحث/مطلب) sesuai permintaan dosen.
2. Kumpulkan bahan; kutip hanya dari teks yang benar-benar terbaca di kitab lokal.
   Belum tahu kitab mana yang membahas → `temukan "<frasa>"` (isi semua kitab Shamela lewat turath.io, tanpa akun), `katalog` (judul/pengarang), atau (kalau pemakai menyalakannya; terdaftar di `.mcp.json`) tanya connector `shamela_*` (shamela.link: seluruh kitab Shamela, nomor kitabnya sama dengan `ambil`). Connector hanya penunjuk jalan: kitabnya tetap di-`ambil`, kutipannya tetap harus lolos `cek`. Batasnya: tidak resmi, butuh akun pemakai sendiri, berkuota, hasil kosong di sana bukan bukti tidak ada, dan subjek pencarian harus frasa pendek persis seperti di kitab.
3. Tulis `naskah.txt`. Setiap kutipan/penisbatan diberi catatan kaki berisi bukti `<<...>>`. Contoh yang lolos cek: `contoh/naskah.txt`.
4. `cek` sampai `GAGAL: 0`. Lalu bereskan tiap baris `perhatian`: bukti di حاشية المحقق = kalimat muhaqqiq, jangan dinisbatkan ke pengarang kitab; kitab «مرقم آليا» = nomor halamannya bukan nomor cetakan, `ambil` edisi yang «موافق للمطبوع». Yang tidak bisa dibereskan → sebut di laporan akhir. Lalu `rakit`.
5. Sebelum lapor selesai: minta subagent baru (yang tidak ikut menulis) membuka sendiri halaman kitab tiap catatan kaki dan menilai PDF hasil terhadap permintaan awal + aturan di bawah; perbaiki temuannya; rakit ulang.

`cek` hanya membuktikan bahwa teksnya ada di juz/halaman itu. `cek` TIDAK bisa menilai: apakah yang berkata memang orang itu (bukan matan yang disyarah, bukan nukilan pihak lain, bukan hujah lawan), apakah nama kitab yang tercetak benar, dan kutipan yang tidak diberi catatan kaki. Itu tugas langkah 5.

## Aturan penulisan (tidak dijaga mesin)

- Ayat selalu lewat `{Q:…}`; catatan kakinya: `سورة …، آية: n.`
- Mencari tempat hadits dan siapa yang menghukuminya: `hadits "<طرف>"`. Itu penunjuk jalan dan datanya bisa salah: كتاب, باب, nomor, juz/halaman, dan derajat tetap ditulis dari kitab yang dibaca sendiri.
- Takhrij hadits: `أخرجه البخاري، كتاب …، باب …، رقم الحديث (n)، juz/hal.`; di luar Shahihain wajib sebut derajatnya beserta siapa yang menghukumi. Catatan kaki hadits cukup takhrij itu; data cetak kitab haditsnya (muhaqqiq, penerbit, cetakan) ditulis di المصادر والمراجع.
- Rujukan pertama sebuah kitab selain kitab hadits yang ditakhrij: data lengkap (judul, pengarang, muhaqqiq, penerbit-kota, cetakan-tahun, juz/hal) — ambil dari `kartu`. Berikutnya ringkas: `judul، pengarang، juz/hal.`
- Nukilan lafaz di antara tanda kutip; nukilan makna diawali `انظر:`. Penisbatan lewat perantara harus disebut perantaranya.
- الدراسات السابقة (kalau dosen minta): `#S` di المقدمة; tiap penelitian disebut judul, peneliti, jurnal/kampus, tahun, lalu وجه الاتفاق والاختلاف dengan bahts ini. Hanya dari `dirasat` yang ringkasan atau PDF-nya benar-benar dibaca.
- Dilarang mengarang: nomor halaman, lafaz, penisbatan pendapat, dan derajat hadits harus terbaca di kitab lokal. Yang tidak bisa dibuktikan → jangan ditulis, atau laporkan sebagai «belum dicek».

## Yang perlu diketahui

- Bentuk halaman dan huruf dikunci mesin menurut pedoman Jāmiʿat al-Imām («القواعد المنظمة لتسجيل الرسالة العلمية وكتابتها وطباعتها وتقديمها»، 1442هـ). Dosen minta lain → profil baru di `mesin/format.json`, pilih dengan `@format:`; jangan ubah `imam`. Bahts baru memakai `imam_ayat16` (lewat `mesin/naskah_baru.txt`): sama dengan `imam`, ayat 16 supaya tidak tampak lebih besar daripada matan; naskah tanpa `@format` tetap `imam`.
- Sampul = `mesin/sampul.doc`, sampul معهد العلوم الإسلامية والعربية في جاكرتا. Pembimbing tercetak hanya kalau `@musyrif` diisi; `@jabatan` kosong = baris jabatan tidak tercetak.
- `rakit` butuh Windows + Microsoft Word. `rakit` satu-satu, jangan dua sekaligus (memakai Word yang sama).
- Teks kitab = ketikan Shamela, jadi bisa salah ketik. Bacaan yang meragukan: `ambil` edisi lain kitab yang sama lalu bandingkan; kalau masih ragu, cocokkan ke scan cetakan (mis. archive.org).
- Yang dibaca dan dikumpulkan = PDF. `.docx` hanya untuk Word (di Google Docs tampilannya pasti beda). Perubahan isi selalu lewat `naskah.txt`, bukan lewat .docx.

## Untuk yang mengubah mesin

- Repo ini publik: nama orang, nomor mahasiswa, dan naskah siapa pun jangan masuk berkas yang dilacak git.
- Yang ada di `main` langsung dilihat semua orang. Perubahan dikerjakan di cabang lain (mis. `kerja`), dicoba dulu lewat pintu pemakai (`periksa`, `cek contoh`, `rakit contoh`), baru digabung ke `main` sebagai satu commit (`git merge --squash`). Cabang kerja dibuat baru dari `main` tiap putaran; cabang yang sudah digabung jangan dipakai lagi.
- `temukan`, `hadits`, `dirasat`, dan connector di `.mcp.json` memakai layanan orang lain (turath.io, alminasa.ai, OpenAlex, DOAJ, shamela.link) yang bisa berubah atau mati tanpa kabar. Semuanya hanya penunjuk jalan: `cek` dan `rakit` tidak boleh bergantung padanya.
- Tes otomatis = `.github/workflows/tes.yml`: `siapkan`, `ambil`, lalu `cek contoh`. Nomor kitab di berkas itu harus sama dengan bukti di `contoh/naskah.txt` (salinan terpaksa).
- Perubahan yang dirasakan pemakai dicatat di `CHANGELOG.md`.
- `CLAUDE.md` hanya menunjuk ke berkas ini.
- Kebutuhan komputer dan cara membereskannya ditulis di satu tempat: `periksa` di `mesin/bahts.py`. README dan berkas ini hanya menyuruh menjalankannya.
- `dok/hasil.png` = sampul, halaman isi kedua, dan halaman terakhir PDF hasil `rakit contoh` (salinan terpaksa): buat ulang kalau sampul atau bentuk halaman berubah. `dok/alur.svg` = gambar alur di README.
