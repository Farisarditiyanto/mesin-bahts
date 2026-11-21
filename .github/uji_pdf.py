# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pemeriksaan PDF sesudah rakit (`teks_pdf.periksa`, dipanggil `rakit` sesudah Word menyimpan PDF) pada PDF Word asli
`contoh/jebakan/sumber_word.pdf` (= `rakit contoh`: sampul qism, nomor halaman ٠١٢٣, nim «000000000»). Yang
ditangkap: PDF tercetak 0123 tanpa @angka, sampul templat «بيع العربون» padahal @judul «حكم بيع العربون», sampul
templat mencetak «المجموعة (......)», dan pengantar «أدلة القول الأول:» sendirian di dasar halaman. Teks PDF Word tidak
tersalin persis, jadi yang diuji juga bahwa PDF yang benar tidak diperingatkan."""
import json, sys, tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "mesin"))
import teks_pdf
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject
sys.stdout.reconfigure(encoding="utf8")

PDF = AKAR / "contoh" / "jebakan" / "sumber_word.pdf"
FORMAT = json.loads((AKAR / "mesin" / "format.json").read_text(encoding="utf8"))["imam_ayat16"]
META = {"judul": "مثال: توحيد الربوبية", "nim": "000000000", "angka": "hindi"}   # @… contoh/naskah.txt
LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def tulis(tujuan, tambahan={}, latin=False, gambar={}, halaman_baru=False):
    """Salinan PDF contoh. tambahan = teks Helvetica {halaman (mulai 1): [(x, y, ukuran, teks)]}; latin = semua angka
    ٠-٩ tersalin 0-9, seperti PDF yang nomor halamannya tercetak 0123; gambar = {halaman: (x, y, lebar, tinggi)}
    satu gambar abu-abu 1×1 piksel yang direntang ke kotak itu (seperti #G); halaman_baru = satu halaman kosong
    seukuran isi di akhir (halaman 8) sebelum teks ditambahkan."""
    w = PdfWriter(clone_from=str(PDF))
    if halaman_baru:
        baru = w.add_blank_page(width=w.pages[1].mediabox.width, height=w.pages[1].mediabox.height)
        baru[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject()})
    for n in set(tambahan) | set(gambar):
        isi = tambahan.get(n, [])
        hal = w.pages[n - 1]
        huruf = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                  NameObject("/BaseFont"): NameObject("/Helvetica")})
        hal["/Resources"]["/Font"][NameObject("/FUji")] = w._add_object(huruf)
        s = DecodedStreamObject()
        teks = "".join(f"BT /FUji {u} Tf 1 0 0 1 {x} {y} Tm ({t}) Tj ET\n" for x, y, u, t in isi)
        if n in gambar:
            im = DecodedStreamObject()
            im.set_data(b"\x80")
            im.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                       NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1),
                       NameObject("/ColorSpace"): NameObject("/DeviceGray"), NameObject("/BitsPerComponent"): NumberObject(8)})
            if "/XObject" not in hal["/Resources"]:
                hal["/Resources"][NameObject("/XObject")] = DictionaryObject()
            hal["/Resources"]["/XObject"].get_object()[NameObject("/ImUji")] = w._add_object(im)
            x, y, lb, tg = gambar[n]
            teks += f"q {lb} 0 0 {tg} {x} {y} cm /ImUji Do Q\n"
        s.set_data(teks.encode("latin1"))
        lama = hal.get_contents()   # halaman_baru: belum berisi
        hal[NameObject("/Contents")] = ArrayObject(([w._add_object(lama)] if lama is not None else []) + [w._add_object(s)])
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
    gagal, diuji = [], []

    def uji(nama, pdf, meta, harus, cetak=None):
        """harus: potongan pesan yang wajib ada, satu per peringatan (kosong = tidak boleh ada peringatan).
        cetak = rencana cetak bahan rakit (olah.rencana_cetak), mis. judul bagian sesudah isi."""
        diuji.append(nama)
        pesan = teks_pdf.periksa(pdf, {"meta": {**META, **meta}, "format": FORMAT, **({"cetak": cetak} if cetak else {})})
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
        # #G: pengantar «…الآتي:» yang disusul gambar di bawahnya, di halaman yang sama, tidak terpisah dari isinya
        pdf = tulis(tmp / "gambar.pdf", {3: [(300, 400, 18, "qawlan:")]}, gambar={3: (150, 100, 300, 250)})
        uji("pengantar «:» di atas gambar #G: tanpa peringatan", pdf, {}, [])
        pdf = tulis(tmp / "gambar_atas.pdf", {3: [(300, 120, 18, "qawlan:")]}, gambar={3: (150, 300, 300, 250)})
        uji("gambar di atas pengantar «:» di dasar halaman: tetap diperingatkan", pdf, {}, ["PDF ke-3:"])
        # `rakit --fasl 2`: potongan tanpa sampul, halaman 1 = isi (bukan sampul yang dicari @judul-nya)
        w = PdfWriter(clone_from=str(PDF))
        w.remove_page(0)
        with open(tmp / "tanpa_sampul.pdf", "wb") as h:
            w.write(h)
        uji("potongan --fasl tanpa sampul: halaman 1 bukan sampul", tmp / "tanpa_sampul.pdf",
            {"judul": "مثال: توحيد الألوهية", "tanpa_sampul": True}, [])
        # sampul @templat yang tetap Letter di depan isi A4 (sebelum rakit.ps1 menyetel sampulnya A4)
        w = PdfWriter(clone_from=str(PDF))
        w.pages[0].mediabox.upper_right = (612, 792)
        with open(tmp / "letter.pdf", "wb") as h:
            w.write(h)
        uji("sampul Letter di depan isi A4: ukuran kertas bercampur", tmp / "letter.pdf", {}, ["ukuran kertas"])
        # halaman sisa: halaman sesudah judul bagian belakang (المصادر, فهرس; contoh: hal 5-7) tanpa judul dan dengan
        # sedikit kata = lanjutan tabel/daftar yang meluap (فهرس الموضوعات 5 baris). Judul bagian dari rencana cetak contoh
        cetak = {"bagian": [{"jenis": j, "judul": t} for j, t in (("pustaka", "المصادر والمراجع"), ("ayat", "فهرس الآيات القرآنية"),
                                                                   ("alam", "فهرس الأعلام"), ("maudhuat", "فهرس الموضوعات"))]}
        uji("PDF contoh dengan judul bagian belakang: tanpa halaman sisa", PDF, {}, [], cetak)
        baris = [(200, 760 - 28 * i, 18, f"mawdu {i} fi al-bahth 1{i}") for i in range(9)]   # 5 kata tiap baris
        sisa = tulis(tmp / "sisa.pdf", {8: baris[:5]}, halaman_baru=True)
        penuh = tulis(tmp / "sisa_penuh.pdf", {8: baris}, halaman_baru=True)
        judul = tulis(tmp / "sisa_judul.pdf", {8: [(200, 770, 22, "fihris")] + baris[:5]}, halaman_baru=True)
        pesan_sisa = ["halaman sisa di المصادر/الفهارس (kurang dari 40 kata atau paling banyak 5 baris lanjutan tabel atau "
                      "daftar halaman sebelumnya) di halaman PDF ke-8:"]
        uji("halaman terakhir sesudah فهرس berisi 5 baris lanjutan: halaman sisa", sisa, {}, pesan_sisa, cetak)
        # dua entri المصادر yang panjang: 4 baris, lebih dari 40 kata = tetap halaman sisa
        panjang = tulis(tmp / "sisa_panjang.pdf", {8: [(100, 760 - 28 * i, 12, " ".join(["kata"] * 11)) for i in range(4)]},
                        halaman_baru=True)
        uji("halaman 4 baris berkata banyak: halaman sisa", panjang, {}, pesan_sisa, cetak)
        uji("halaman lanjutan 45 kata: bukan halaman sisa", penuh, {}, [], cetak)
        uji("halaman pendek yang diawali judul bagian: bukan halaman sisa", judul, {}, [], cetak)
        uji("tanpa rencana cetak (judul bagian belakang tidak diketahui): tidak dinilai", sisa, {}, [])
        # halaman kosong (tanpa isi teks maupun gambar): diperingatkan
        w = PdfWriter(clone_from=str(PDF))
        w.add_blank_page(width=w.pages[1].mediabox.width, height=w.pages[1].mediabox.height)
        with open(tmp / "kosong.pdf", "wb") as h:
            w.write(h)
        uji("halaman kosong tanpa isi", tmp / "kosong.pdf", {}, ["halaman kosong (tanpa isi) di halaman PDF ke-8"])
        # halaman berisi gambar #G saja (tanpa teks): tidak dianggap kosong
        w = PdfWriter(clone_from=str(PDF))
        w.add_blank_page(width=w.pages[1].mediabox.width, height=w.pages[1].mediabox.height)
        with open(tmp / "kosong_base.pdf", "wb") as h:
            w.write(h)
        # tambah gambar di halaman 8 melalui tulis()
        w2 = PdfWriter(clone_from=str(tmp / "kosong_base.pdf"))
        hal8 = w2.pages[7]
        im = DecodedStreamObject()
        im.set_data(b"\x80")
        im.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                   NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1),
                   NameObject("/ColorSpace"): NameObject("/DeviceGray"), NameObject("/BitsPerComponent"): NumberObject(8)})
        hal8[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Im8"): w2._add_object(im)})})
        s8 = DecodedStreamObject()
        s8.set_data(b"q 200 0 0 200 150 300 cm /Im8 Do Q\n")
        hal8[NameObject("/Contents")] = w2._add_object(s8)
        with open(tmp / "gambar_saja.pdf", "wb") as h:
            w2.write(h)
        uji("halaman hanya gambar #G tidak dianggap kosong", tmp / "gambar_saja.pdf", {}, [])
        # halaman kosong yang punya logo di kepala halaman (y > tinggi - TEPI) tetap terdeteksi kosong
        w3 = PdfWriter(clone_from=str(tmp / "kosong_base.pdf"))
        hal8_hdr = w3.pages[7]
        im_hdr = DecodedStreamObject()
        im_hdr.set_data(b"\x80")
        im_hdr.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                       NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1),
                       NameObject("/ColorSpace"): NameObject("/DeviceGray"), NameObject("/BitsPerComponent"): NumberObject(8)})
        hal8_hdr[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/ImH"): w3._add_object(im_hdr)})})
        s8_hdr = DecodedStreamObject()
        s8_hdr.set_data(b"q 60 0 0 30 500 790 cm /ImH Do Q\n")
        hal8_hdr[NameObject("/Contents")] = w3._add_object(s8_hdr)
        with open(tmp / "kosong_logo_kepala.pdf", "wb") as h:
            w3.write(h)
        uji("halaman kosong dengan logo kepala tetap terdeteksi kosong", tmp / "kosong_logo_kepala.pdf", {},
            ["halaman kosong (tanpa isi) di halaman PDF ke-8"])
        # teks/rumus meluap mendekati tepi kiri/kanan kertas (< 18 pt dari tepi)
        pdf_kiri = tulis(tmp / "luap_kiri.pdf", {3: [(4, 400, 14, "overflow_left")]})
        uji("teks meluap ke tepi kiri kertas", pdf_kiri, {}, ["meluap ke tepi kertas di halaman PDF ke-3"])
        pdf_kanan = tulis(tmp / "luap_kanan.pdf", {4: [(480, 400, 14, "very_long_formula_overflow_right")]})
        uji("teks/rumus meluap ke tepi kanan kertas", pdf_kanan, {}, ["meluap ke tepi kertas di halaman PDF ke-4"])
        # jalur cadangan tanpa pymupdf tetap aman (tanpa alarm palsu) dan menangkap asal teks di tepi kertas
        pdf_asal_kanan = tulis(tmp / "luap_asal_kanan.pdf", {4: [(582, 400, 14, "X")]})
        asli_meluap = teks_pdf._halaman_meluap
        teks_pdf._halaman_meluap = lambda *a: None
        try:
            uji("tanpa pymupdf: PDF contoh bersih tanpa peringatan", PDF, {}, [])
            uji("tanpa pymupdf: teks di tepi kiri tetap tertangkap", pdf_kiri, {}, ["meluap ke tepi kertas di halaman PDF ke-3"])
            uji("tanpa pymupdf: teks di tepi kanan tetap tertangkap", pdf_asal_kanan, {}, ["meluap ke tepi kertas di halaman PDF ke-4"])
        finally:
            teks_pdf._halaman_meluap = asli_meluap
    if gagal:
        sys.exit(f"{len(gagal)} uji PDF gagal: " + "; ".join(gagal))
    print(f"uji pdf: {len(diuji)} skenario sesuai")


if __name__ == "__main__":
    utama()
