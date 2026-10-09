# Bahts — mesin penulisan bahts (riset ilmiah berbahasa Arab)

Satu bahts = satu folder; yang ditulis cuma `naskah.txt`, sisanya (cek rujukan, Word, PDF) dikerjakan mesin. Bahan bahts jangan masuk `mesin/`; `kitab/` dipakai semua bahts.
Daftar perintah: `python mesin/bahts.py`. Daftar tanda naskah: `python mesin/bahts.py tanda`.

## Alur kerja

1. `baru`, lalu susun خطة (فصل/مبحث/مطلب) sesuai permintaan dosen.
2. Kumpulkan bahan; kutip hanya dari teks yang benar-benar terbaca di kitab lokal.
   Belum tahu kitab mana yang membahas → tanya dulu connector `shamela_*` (shamela.link: seluruh 8.598 kitab, nomor kitabnya sama dengan `ambil`). Ia hanya penunjuk jalan: kitabnya tetap di-`ambil`, kutipannya tetap harus lolos `cek`. Batasnya: tidak resmi, berkuota, hasil kosong di sana bukan bukti tidak ada, dan subjek pencarian harus frasa pendek persis seperti di kitab.
3. Tulis `naskah.txt`. Setiap kutipan/penisbatan diberi catatan kaki berisi bukti `<<...>>`.
4. `cek` sampai `GAGAL: 0`, lalu `rakit`.
5. Sebelum lapor selesai: minta subagent baru (yang tidak ikut menulis) membuka sendiri halaman kitab tiap catatan kaki dan menilai PDF hasil terhadap permintaan awal + aturan di bawah; perbaiki temuannya; rakit ulang.

`cek` hanya membuktikan bahwa teksnya ada di juz/halaman itu. `cek` TIDAK bisa menilai: apakah yang berkata memang orang itu (bukan matan yang disyarah, bukan nukilan pihak lain, bukan hujah lawan), apakah nama kitab yang tercetak benar, dan kutipan yang tidak diberi catatan kaki. Itu tugas langkah 5.

## Aturan penulisan (tidak dijaga mesin)

- Ayat selalu lewat `{Q:…}`; catatan kakinya: `سورة …، آية: n.`
- Takhrij hadits: `أخرجه البخاري، كتاب …، باب …، رقم الحديث (n)، juz/hal.`; di luar Shahihain wajib sebut derajatnya beserta siapa yang menghukumi.
- Rujukan pertama sebuah kitab: data lengkap (judul, pengarang, muhaqqiq, penerbit-kota, cetakan-tahun, juz/hal) — ambil dari `kartu`. Berikutnya ringkas: `judul، pengarang، juz/hal.`
- Nukilan lafaz di antara tanda kutip; nukilan makna diawali `انظر:`. Penisbatan lewat perantara harus disebut perantaranya.
- الدراسات السابقة (kalau dosen minta): `#S` di المقدمة; tiap penelitian disebut judul, peneliti, jurnal/kampus, tahun, lalu وجه الاتفاق والاختلاف dengan bahts ini. Hanya dari `dirasat` yang ringkasan atau PDF-nya benar-benar dibaca.
- Dilarang mengarang: nomor halaman, lafaz, penisbatan pendapat, dan derajat hadits harus terbaca di kitab lokal. Yang tidak bisa dibuktikan → jangan ditulis, atau laporkan sebagai «belum dicek».

## Yang perlu diketahui

- Bentuk halaman dan huruf dikunci mesin menurut pedoman Jāmiʿat al-Imām («القواعد المنظمة لتسجيل الرسالة العلمية وكتابتها وطباعتها وتقديمها»، 1442هـ, yang dirujuk catatan د. سليمان). Dosen minta lain → profil baru di `mesin/format.json`, pilih dengan `@format:`; jangan ubah `imam`. Bahts baru memakai `imam_ayat16` (lewat `mesin/naskah_baru.txt`): sama dengan `imam`, ayat 16 supaya tidak tampak lebih besar daripada matan; naskah tanpa `@format` tetap `imam`.
- Sampul = template د. سليمان بن زعل العنزي dan nama beliau tercetak sebagai pembimbing kalau dibiarkan; tugas dosen lain wajib isi `@musyrif`/`@jabatan`.
- `rakit` satu-satu, jangan dua sekaligus (memakai Word yang sama).
- Teks kitab = ketikan Shamela, jadi bisa salah ketik. Bacaan yang meragukan: `ambil` edisi lain kitab yang sama lalu bandingkan; kalau masih ragu, cocokkan ke scan cetakan (mis. archive.org).
- Faroos membaca dan mengumpulkan PDF. `.docx` hanya untuk Word (di Google Docs tampilannya pasti beda). Perubahan isi selalu lewat `naskah.txt`, bukan lewat .docx.
