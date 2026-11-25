Kamu pemeriksa langkah 5 (`AGENTS.md` Alur kerja langkah 5; baca penuh `dok/pemeriksaan.md`, `dok/penulisan-sumber.md`, dan `dok/audit.md` sebelum menilai) untuk bahts di `{folder}`. Kamu tidak ikut menulisnya.

Permintaan awal pemakai, kata per kata:
<<<
{permintaan}
>>>

Bahtsnya belum dirakit: nilai naskah yang sudah lolos `cek` (fokus A Isi & Sumber; fokus B Tata Letak dilewati). Jalankan putaran penuh sesuai langkah 5 AGENTS.md. Jangan mengubah `naskah.txt` dan `riset.txt`.

Tulis temuanmu ke `{temuan}` (JSON UTF-8):
{{"temuan": [{{"berkas": "naskah.txt" atau "riset.txt", "baris": <nomor baris>, "masalah": "<apa yang salah dan aturan yang dilanggar>", "perintah": "<perintah atau alat yang dijalankan>", "keluaran": "<potongan keluaran yang menunjukkan salahnya>"}}]}}
Temuan yang tidak menempel ke satu baris (mis. bagian yang tidak ada di naskah) ditulis dengan "baris": 0. Tidak ada temuan = daftar kosong. Sebelum selesai, pastikan berkas itu JSON yang sah (tanda petik di dalam teks di-escape): `python -c "import json; json.load(open(r'{temuan}', encoding='utf-8'))"`.
