# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pemeriksaan PDF sesudah rakit (`teks_pdf.periksa`, dipanggil `rakit` sesudah Word menyimpan PDF) pada PDF Word asli
`contoh/jebakan/sumber_word.pdf` (= `rakit contoh`: sampul qism, nomor halaman ٠١٢٣, nim «000000000»). Yang pernah
terjadi: PDF tercetak 0123 tanpa @angka, sampul templat «بيع العربون» padahal @judul «حكم بيع العربون», sampul
templat mencetak «المجموعة (......)», dan pengantar «أدلة القول الأول:» sendirian di dasar halaman. Teks PDF Word tidak
tersalin persis, jadi yang diuji juga bahwa PDF yang benar tidak diperingatkan."""
import json, sys, tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "mesin"))
import teks_pdf
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject
sys.stdout.reconfigure(encoding="utf8")

PDF = AKAR / "contoh" / "jebakan" / "sumber_word.pdf"
FORMAT = json.loads((AKAR / "mesin" / "format.json").read_text(encoding="utf8"))["imam_ayat16"]
META = {"judul": "مثال: توحيد الربوبية", "nim": "000000000", "angka": "hindi"}   # @… contoh/naskah.txt
LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def tulis(tujuan, tambahan={}, latin=False):
    """Salinan PDF contoh. tambahan = teks Helvetica {halaman (mulai 1): [(x, y, ukuran, teks)]}; latin = semua angka
    ٠-٩ tersalin 0-9, seperti PDF yang nomor halamannya tercetak 0123."""
    w = PdfWriter(clone_from=str(PDF))
    for n, isi in tambahan.items():
        hal = w.pages[n - 1]
        huruf = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                  NameObject("/BaseFont"): NameObject("/Helvetica")})
        hal["/Resources"]["/Font"][NameObject("/FUji")] = w._add_object(huruf)
        s = DecodedStreamObject()
        s.set_data("".join(f"BT /FUji {u} Tf 1 0 0 1 {x} {y} Tm ({t}) Tj ET\n" for x, y, u, t in isi).encode("latin1"))
        hal[NameObject("/Contents")] = ArrayObject([w._add_object(hal.get_contents()), w._add_object(s)])
    if latin:
        for hal in w.pages:
            for f in hal["/Resources"]["/Font"].values():
                tu = f.get_object().get("/ToUnicode")
                if tu is not None:
                    peta = teks_pdf._peta(tu.get_object().get_data().decode("latin1"))
                    tu.get_object().set_data(teks_pdf._cmap({g: s.translate(LATIN) for g, s in peta.items()}))
    with open(tujuan, "wb") as h:
        w.write(h)
    return tujuan


def utama():
    gagal = []

    def uji(nama, pdf, meta, harus):
        """harus: potongan pesan yang wajib ada, satu per peringatan (kosong = tidak boleh ada peringatan)."""
        pesan = teks_pdf.periksa(pdf, {"meta": {**META, **meta}, "format": FORMAT})
        if len(pesan) != len(harus) or not all(any(h in p for p in pesan) for h in harus):
            gagal.append(nama)
            print(f"GAGAL {nama}: harus {harus}, dapat {pesan}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        uji("PDF contoh benar: tanpa peringatan (nim 000000000 bukan isian kosong)", PDF, {}, [])
        uji("@angka latin, nomor halaman tercetak ٠١٢٣", PDF, {"angka": "latin"}, ["tercetak bukan 0123"])
        uji("nomor halaman tercetak 0123 tanpa @angka", tulis(tmp / "latin.pdf", latin=True), {}, ["tercetak 0123"])
        uji("@judul yang tidak ada di sampul", PDF, {"judul": "مثال: توحيد الألوهية"}, ["الالوهيه"])
        # «تجريبي» (@jenis contoh, tercetak di sampul) tersalin «جترييب» dari PDF Word
        uji("@judul yang hurufnya tersalin tertukar tetap ada di sampul", PDF, {"judul": "مثال تجريبي"}, [])
        uji("@judul yang hurufnya lebih dari sampul", PDF, {"judul": "مثال: توحيد الربوبيات"}, ["الربوبيات"])
        pdf = tulis(tmp / "isian.pdf", {1: [(250, 400, 14, "(......)")], 3: [(300, 120, 18, "qawlan:")],
                                        4: [(300, 120, 18, "qawlan.")]})
        uji("titik-titik isian di sampul, pengantar «:» di dasar halaman 3 (bukan «.» di halaman 4)", pdf, {},
            ["titik-titik isian", "PDF ke-3:"])
        # `rakit --fasl 2`: potongan tanpa sampul, halaman 1 = isi (bukan sampul yang dicari @judul-nya)
        w = PdfWriter(clone_from=str(PDF))
        w.remove_page(0)
        with open(tmp / "tanpa_sampul.pdf", "wb") as h:
            w.write(h)
        uji("potongan --fasl tanpa sampul: halaman 1 bukan sampul", tmp / "tanpa_sampul.pdf",
            {"judul": "مثال: توحيد الألوهية", "tanpa_sampul": True}, [])
    if gagal:
        sys.exit(f"{len(gagal)} uji PDF gagal: " + "; ".join(gagal))
    print("uji pdf: 8 skenario sesuai")


if __name__ == "__main__":
    utama()
