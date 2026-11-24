# Muqorror kelas

`muqorror` menyusun halaman PDF kitab asli dan lembar catatan kelas. Gunakan PDF edisi yang dipakai dosen. Baca transkrip per pertemuan untuk memilih halaman dan mencatat penjelasan lisan, contoh tambahan, dan pembahasan soal. Tulis bagian yang belum punya rekaman di `keterangan`. Perintah bekerja dari berkas lokal dengan PyMuPDF.

```sh
python mesin/bahts.py muqorror "rencana.json" "muqorror.pdf"
```

Simpan rencana sebagai JSON UTF-8. Jalur `kitab` boleh mutlak atau relatif terhadap folder rencana.

```json
{
  "judul": "Muqorror Nahwu",
  "kitab": "kitab.pdf",
  "kitab_label": "شرح ابن عقيل على ألفية ابن مالك",
  "keterangan": "Catatan ini mencakup pertemuan yang tercantum di daftar sumber kelas.",
  "sumber": [
    {"id": "01", "judul": "Pertemuan 1", "tautan": "https://example.org/rekaman-1"}
  ],
  "bagian": [
    {
      "judul": "Bentuk dan fungsi المفعول المطلق",
      "halaman": [[5, 8], [10, 10]],
      "catatan": [
        {
          "judul": "Cara membedakan fungsi",
          "sumber": ["01"],
          "butir": [
            "Perhatikan informasi yang ditambahkan masdar.",
            "ضربتُ ضربتينِ menunjukkan jumlah kejadian."
          ]
        }
      ]
    }
  ]
}
```

- `kitab_label` menggantikan nama berkas pada halaman daftar bagian. `keterangan` dan `tautan` boleh dihilangkan.
- Hitung halaman mulai dari halaman pertama PDF, termasuk sampul. Tiap pasangan `[awal, akhir]` mencakup kedua ujung. Urutkan rentang dari kecil ke besar di seluruh rencana. Untuk satu halaman, gunakan pasangan dengan angka yang sama.
- `halaman` boleh kosong bila bagian itu hanya memuat catatan. `catatan` boleh kosong bila bagian itu hanya memuat halaman kitab.
- Pakai ID `sumber` yang unik. Tiap catatan dapat merujuk beberapa sumber. `sumber: []` pada catatan dicetak sebagai «Catatan penyusun».
- Tulis satu gagasan per anggota `butir`. Istilah dan contoh Arab boleh dicampur dengan teks Latin. Untuk diagram teks, pisahkan baris dengan `\n`.

PDF membuka daftar bagian yang menautkan halaman kitab dan catatan. Catatan disisipkan setelah halaman kitab pada bagian yang sama. Nomor cetak asli tetap terlihat pada halaman kitab. Nomor di kaki lembar catatan mengikuti urutan halaman PDF hasil.

Huruf Arab bergaya tulisan tangan terbaca di layar dan di cetak. Untuk menyalin atau mencari teks Arab catatan, gunakan rencana JSON karena pemetaan huruf sambung di PDF bisa kehilangan karakter.
