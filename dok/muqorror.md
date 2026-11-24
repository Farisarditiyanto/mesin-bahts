# Muqorror kelas

`muqorror` menata ulang bab kitab pilihan bergaya klasik (`Amiri`) beserta anotasi catatan kuliah bergaya tulisan tangan (`Playpen Sans Arabic`) langsung di halaman yang sama, lembar ringkasan terpisah, daftar isi Arab (`فهرس المقرر`) bernomor halaman nyata, bookmark PDF, dan halaman `مصادر المحاضرات`. Perintah berjalan offline memakai Chrome/Edge/Chromium lokal (`BAHTS_CHROME` bila perlu) dan `pymupdf`, tanpa Microsoft Word atau internet.

```sh
python mesin/bahts.py muqorror "rencana.json" "muqorror.pdf"
```

## Struktur rencana JSON

Simpan rencana sebagai JSON UTF-8. Semua kunci asing, karakter kontrol, ID sumber yang belum didaftar, serta keluaran selain `.pdf` atau yang menimpa berkas rencana ditolak sebelum PDF lama disentuh.

```json
{
  "judul": "مقرر النحو العربي",
  "subjudul": "شرح ابن عقيل على ألفية ابن مالك",
  "keterangan": "ملخص المقرر المختار مع تعليقات المحاضرات.",
  "sumber": [
    {"id": "م١", "judul": "المحاضرة الأولى", "tautan": "https://example.org/lec-1"}
  ],
  "bagian": [
    {
      "judul": "المفعول المطلق",
      "jenis": "kitab",
      "hal_kitab": "١٤١–١٥٣",
      "catatan_pangkas": "اختُصرت الحواشي غير المطلوبة.",
      "sumber": ["م١"],
      "blok": [
        {"jenis": "hal", "nomor": "١٤١"},
        {"jenis": "subjudul", "teks": "تعريف المصدر", "sumber": ["م١"]},
        {
          "jenis": "bait",
          "nomor": "٢٩١",
          "kanan": "المَصْدَرُ اسْمُ مَا سِوَى الزَّمَانِ مِنْ",
          "kiri": "مَدْلُولَيِ الفِعْلِ كَأَمْنٍ مِنْ أَمِنْ",
          "gaya": "alfiyah",
          "catatan": {"label": "مفتاح", "warna": "biru", "isi": "الحدث المجرّد عن الزمان."}
        },
        {
          "jenis": "matan",
          "teks": "الفعل يدلّ على شيئين: {hl:حدث وزمان}؛ فـ{o:قام} يدلّ على {ul:قيام في زمن ماض}{fn:١}.",
          "catatan": [{"label": "تنبيه", "warna": "merah", "isi": "القيام هو الحدث.", "sumber": ["م١"]}]
        },
        {
          "jenis": "sela",
          "label": "خلاصة المحاضرة",
          "warna": "hijau",
          "sumber": ["م١"],
          "isi": "ثلاثة أنواع للمفعول المطلق:",
          "butir": ["مؤكّد لعامله", "مبيّن للنوع", "مبيّن للعدد"]
        },
        {
          "jenis": "diagram",
          "judul": "أقسام المفعول المطلق",
          "tipe": "pohon",
          "akar": "المفعول المطلق",
          "cabang": [
            {"judul": "المؤكّد", "warna": "biru", "isi": ["لا يُثنّى"]},
            {"judul": "المبيّن", "warna": "hijau", "isi": ["نوع أو عدد"]}
          ]
        },
        {
          "jenis": "hasyiah",
          "butir": [{"nomor": "١", "teks": "أي: أحد الأمرين اللذين دلّ عليهما الفعل."}],
          "catatan_pangkas": "حُذفت بقية الحواشي."
        },
        {"jenis": "halaman_baru"}
      ]
    }
  ]
}
```

### Bidang tingkat atas

- `judul` (wajib): judul utama muqorror.
- `subjudul`, `keterangan` (opsional): keterangan kitab dan catatan pembuka di halaman `فهرس المقرر`.
- `sumber` (wajib, boleh `[]`): daftar `{id, judul, tautan?}` dengan `id` unik; `tautan` harus URL `http` atau `https`.
- `bagian` (wajib, tidak kosong): daftar bab/lembar:
  - `judul` (wajib), `blok` (wajib, tidak kosong).
  - `jenis` (opsional, bawaan `"kitab"`): `"kitab"` (tata letak satu kolom selebar kitab asli dengan catatan langsung di bawah blok terkait) atau `"lembar"` (lembar ringkasan berlatar kertas krem).
  - `hal_kitab`, `catatan_pangkas`, `sumber` (opsional; setiap ID `sumber` harus terdaftar).

### Jenis blok (`blok[].jenis`)

| `jenis` | Kunci wajib | Kunci opsional | Fungsi |
| --- | --- | --- | --- |
| `hal` | `nomor` | — | Lencana halaman kitab asli (`ص ١٤١`). |
| `subjudul` | `teks` | `sumber` | Subjudul bab; ikut masuk bookmark PDF tingkat 2. |
| `bait` | `kanan`, `kiri` | `nomor`, `gaya` (`alfiyah`/`syahid`), `catatan` | Bait dua syatr (`alfiyah` marun tebal, `syahid` hitam rapat). |
| `matan` | `teks` | `catatan` | Paragraf matan kitab; mendukung marka anotasi sebaris. |
| `sela` | `isi` dan/atau `butir` | `label`, `warna` (`biru`/`merah`/`hijau`), `sumber`, `catatan` | Kotak catatan kuliah sebaris bergaya tulisan tangan. |
| `hasyiah` | `butir` (`[{nomor, teks}]`) | `catatan_pangkas` | Catatan kaki kitab yang sudah diringkas. |
| `diagram` | `judul`, `tipe`, kunci tipe | `sumber`, `catatan` | Diagram pohon, alur, atau tabel perbandingan selebar penuh; ikut bookmark tingkat 2. |
| `halaman_baru` | — | — | Pindah halaman paksa. |

### Kartu `catatan` di bawah blok

Diperbolehkan pada `bait`, `matan`, `sela`, dan `diagram`, berupa satu objek (tampil selebar penuh tepat di bawah blok) atau daftar objek (tampil berdampingan dua kolom di bawah blok): `{isi, label?, warna?, sumber?}` dengan `warna` salah satu dari `"biru"` (bawaan), `"merah"`, `"hijau"`.

### Marka anotasi sebaris

Dipakai di dalam `teks`, `isi`, `butir`, bait, dan sel tabel:

- `{hl:...}` stabilo kuning lembut
- `{hl2:...}` stabilo hijau lembut
- `{ul:...}` garis bawah biru bergelombang
- `{ur:...}` garis bawah merah tegas
- `{o:...}` lingkar pena biru
- `{b:...}` tebal
- `{fn:...}` angka catatan kaki superskrip marun, mis. `{fn:١}` → `(١)`

### Tipe diagram (`diagram.tipe`)

Warna diagram (`warna`, opsional): `"biru"`, `"hijau"`, `"merah"`, `"ungu"`.

- `pohon`: `akar` (teks) dan `cabang` (2–4 objek `{judul, isi: [teks, ...], warna?}`) → SVG pohon bertulis tangan RTL.
- `alur`: `langkah` (2–5 objek `{judul, isi?, warna?}`) → kartu langkah berurutan kanan-ke-kiri dengan panah.
- `tabel`: `kolom` (2–5 judul kolom) dan `baris` (minimal 1 baris, panjang tiap baris sama dengan jumlah `kolom`) → tabel perbandingan bergaya catatan tangan.
