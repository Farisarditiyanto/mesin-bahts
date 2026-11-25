# Panduan Audit Terstruktur (Pra-Tulis & Langkah 5)

Panduan ringkas ini melengkapi `AGENTS.md` (Alur kerja langkah 2 dan 5) untuk model frontier: bukan daftar larangan kata dangkal, melainkan kerangka kerja untuk mendeteksi cacat substansi, argumen, cakupan rencana, dan standar sumber yang tidak mungkin ditangkap `cek` otomatis.

## 1. Pintu Data Deterministik (jalankan sebelum membaca panjang)

1. **`python mesin/bahts.py peta <folder>`** — ringkasan opsional (offline) untuk melihat:
   - **Cakupan rencana vs isi**: pohon `#K/#F/#B/#M/#S`, jumlah kata/catatan kaki/paragraf polos tiap bagian, bagian isi ≥80 kata tanpa satu pun catatan kaki, serta ketimpangan panjang antarbagian setingkat.
   - **Inventaris sumber dan kitab mazhab**: tiap kitab Shamela/Waqfeya/PDF/`<<luar>>` berbukti urut dari pengarang tertua (`ت …هـ`), penanda `[معتمد]`/`[معاصر]`, dan perbandingan mazhab yang disebut di matan terhadap jumlah bukti kitab mazhabnya sendiri di seluruh naskah. Buka bukti tiap masalah untuk menilai cakupan klaimnya.
   - **Busur argumen**: baris rencana/pertanyaan di `المقدمة`, baris `القول الأول/الثاني`/`إجماع`/`الراجح` di isi, dan baris hasil di `الخاتمة` berdampingan untuk menangkap kontradiksi isi↔kesimpulan dan pertanyaan yang belum terjawab (*qaws maftuh*).
   - **Daftar `{H:…}` dan `terima` di `riset.txt`**: semua hadits bertanda, halaman bukti Shamela yang diperiksa, dan semua perhatian yang ditutup `terima` terkumpul di satu layar untuk diperiksa satu per satu.
2. **`bukti <folder> [awal-akhir]`** dan **`pratinjau <folder> [halaman]`** — prosedur lengkap pemeriksaan bukti kitab/PDF/paragraf polos (Fokus A) dan pratinjau visual PDF hasil `rakit` (Fokus B) lihat `dok/pemeriksaan.md`.

## 2. Prinsip Audit Berbasis Disiplin (Paradigm-First)

Jangan menilai bahts fikih/ushul dengan kacamata riset empiris, dan jangan menilai riset keuangan/administrasi dengan kacamata fikih klasik:

- **Fikih, Ushul, Aqidah, Tafsir, Hadits (تأصيلي / مقارن)**: berdalil dengan nash, ijmak, qiyas, dan perkataan imam mazhab dari kitab mu'tamad adalah rukun hujah. Yang diaudit: kesetiaan nisbah ke mazhab/ulama dari sumber primer (`dok/mutamad.md`), ketepatan takhrij & sanad (`rawi <id> <juz> <hal>`), keutuhan syarat & pengecualian (`إلا`/`ما لم`/`بشرط`), dan keselarasan tarjih dengan dalil yang ditampilkan.
- **الإدارة والمالية / Kajian Empiris & Kontemporer**: klaim tren, dampak, atau perbedaan wajib bersandar pada data, rumus (`#E`), laporan resmi, atau penelitian primer yang dibaca penuh (`<<luar|berkas.pdf|hal>>`), bukan lompatan dari korelasi ke kausalitas.

## 3. Mizan *Adab al-Bahts wal-Munazharah* (Audit Argumen & Kesimpulan)

Saat membaca `peta <folder>` dan isi naskah, periksa enam cacat logika/struktur berikut secara eksplisit:

1. **القوس المفتوح (Busur terbuka)**: pertanyaan, tujuan, atau bab/mabhath yang dijanjikan di `المقدمة` tidak hadir di isi atau tidak dijawab di `الخاتمة`.
2. **تناقض الترجيح مع الخاتمة**: pendapat yang dirajihkan di isi (`المطلب الثالث` dsb.) bertentangan dengan hasil yang ditulis di `الخاتمة`.
3. **المصادرة على المطلوب والدور (Begging the question / sirkularitas)**: dalil yang dipakai untuk merajihkan suatu pendapat sebenarnya mengandaikan pendapat itu sendiri tanpa premis bebas.
4. **القياس مع الفارق المؤثر / الاحتجاج بمحل النزاع**: mengqiyaskan kasus baru ke asal yang memiliki perbedaan sifat penentu (*fariq mu'atstsir*), atau menjadikan poin khilaf itu sendiri sebagai dalil.
5. **تحريف قول المخالف (Strawmanning)**: meringkas pendapat mazhab lawan tanpa dalil terkuatnya, membalik pengecualian (`ولو ذهبا معًا` padahal kitab berkata `فالخيار باق`), atau menyandarkan dalil satu pihak ke pihak lain.
6. **الفجوة المعلنة مقابل المنفذة (untuk `الدراسات السابقة`)**: penelitian yang dipaparkan hanya berupa daftar ringkasan terpisah tanpa sintesis, atau klaim «الإضافة العلمية» bertentangan dengan studi yang dikutip sendiri.

## 4. Disiplin Sijil Bukti & Verifikasi Asimetris

- **دليل موثق أو خلو معلن (Bukti tertulis atau pengakuan kosong)**: sebelum menulis bagian khilaf atau sanad, kumpulkan bukti dari kitab mu'tamad/kitab asal (`edisi` untuk menemukan kandidat cetakan di Shamela/Waqfeya, lalu cocokkan data cetaknya; `rawi <id> <juz> <hal>` untuk melihat rantai dan membuka penilaian rawi dari kitab asal). Bila suatu mazhab atau derajat hadits benar-benar tidak ditemukan di sumber yang tersedia, nyatakan terus terang dan sebut di laporan akhir — jangan menambal dari ingatan.
- **Verifikasi asimetris**: pemeriksa hanya membuktikan kesalahan yang tertangkap dengan bukti perintah + potongan keluaran; tidak ditemukannya temuan berarti «belum terlihat cacat pada titik yang diperiksa», bukan sertifikat bebas salah mutlak.
