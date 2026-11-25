# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tes `bukti` lewat pintu pemakai (`bahts.py bukti contoh`): penunjuk untuk pemeriksa langkah 5.

Yang diuji (kalau rusak, pemeriksa membaca teks yang salah tanpa sadar):
- teks kitab yang dicetak memang dari halaman yang dirujuk bukti, dan memuat kutipannya;
- bukti yang menunjuk halaman lain: dikatakan «TIDAK ketemu» dan yang dicetak awal halaman yang dirujuk itu,
  bukan halaman lain tempat kutipannya berada;
- ayat {Q:} dicetak persis teks mushaf mesin;
- `bukti contoh <baris>` hanya mencetak baris itu, dan tiap baris keluaran diawali «baris n»;
- paragraf isi tanpa catatan kaki ikut dicetak (pemeriksa menilai klaim yang tidak bersumber), المقدمة/الخاتمة tidak.
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
from bantu import salin_mesin

sys.stdout.reconfigure(encoding="utf-8")  # konsol Windows (cp1252) tidak bisa mencetak huruf Arab
sys.stderr.reconfigure(encoding="utf-8")  # pesan assert juga memuat huruf Arab

REPO = Path(__file__).resolve().parent.parent
AKAR = Path(tempfile.mkdtemp(prefix="bahts-uji-bukti-"))
salin_mesin(AKAR, ("_meta", "11223"))
shutil.copytree(REPO / "contoh", AKAR / "contoh", ignore=shutil.ignore_patterns("*.docx", "*.pdf", "laporan.txt", "jebakan"))
sys.path.insert(0, str(AKAR / "mesin"))
from shamela import padat  # bentuk yang dicocokkan `cek`

KUTIPAN = "توحيد الربوبية وهو إفراد الله تعالى بالخلق والملك والتدبير"  # <<11223|-|5>>
QURAN = json.loads((AKAR / "mesin" / "quran_hafs_v22.json").read_text(encoding="utf8"))
# nomor baris dibaca dari contoh, supaya baris @ baru di kepalanya tidak menggeser tes ini
_BARIS = (AKAR / "contoh" / "naskah.txt").read_text(encoding="utf-8-sig").splitlines()
B_AYAT = next(i for i, b in enumerate(_BARIS, 1) if "{Q:1:2}" in b)
B_KUTIP = next(i for i, b in enumerate(_BARIS, 1) if KUTIPAN in b)
assert B_KUTIP == B_AYAT + 1, (B_AYAT, B_KUTIP)


def jalan(*argumen):
    r = subprocess.run([sys.executable, str(AKAR / "mesin" / "bahts.py"), *argumen], cwd=AKAR,
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    return r.returncode, r.stdout + r.stderr


def teks_kitab(keluar, hal):
    """Teks kitab yang dicetak `bukti` untuk halaman itu (tanpa «…» dan penanda ⦗n⦘)."""
    baris = [b for b in keluar.splitlines() if f" ج- ص{hal}: " in b]
    assert len(baris) == 1, keluar
    return baris[0].split(f" ج- ص{hal}: ", 1)[1]


try:
    kode, keluar = jalan("bukti", "contoh")
    print(keluar)
    assert kode == 0, kode
    assert all(b.startswith("baris ") for b in keluar.splitlines()), "ada baris keluaran tanpa «baris n»"
    _, halaman5 = jalan("halaman", "11223", "-", "5")
    teks = teks_kitab(keluar, 5)
    assert padat(KUTIPAN) in padat(teks), "kutipan tidak ada di teks yang dicetak"
    assert padat(teks) in padat(halaman5), "teks yang dicetak bukan dari halaman 5"
    assert f"baris {B_AYAT} ayat {{Q:1:2}}: ﴿{QURAN['1:2']}﴾" in keluar.splitlines(), "teks ayat tidak persis mushaf"
    print("lolos: teks dari halaman yang dirujuk, ayat persis")

    for b, tidak in ((B_AYAT, B_KUTIP), (B_KUTIP, B_AYAT)):
        kode, keluar = jalan("bukti", "contoh", str(b))
        assert kode == 0 and keluar.strip(), keluar
        assert all(x.startswith(f"baris {b} ") for x in keluar.splitlines()), f"bukti contoh {b}:\n{keluar}"
        assert f"baris {tidak} " not in keluar
    kode, keluar = jalan("bukti", "contoh", f"{B_KUTIP + 1}-{B_KUTIP + 15}")
    assert kode == 1 and f"baris {B_KUTIP} " not in keluar, keluar
    print("lolos: hanya baris yang diminta")

    naskah = AKAR / "contoh" / "naskah.txt"
    asli = naskah.read_text(encoding="utf-8-sig")
    matan = "إن توحيد الربوبية هو إفراد الله بالخلق والملك والتدبير، وليس هو توحيد الألوهية."
    sisipan = " ولا يجوز حذف هذا القيد عند نقل المعنى. "
    panjang = "بيان السياق " * 40 + sisipan + "شرح المسألة " * 40
    catatan = "انظر: " + "شرح المصدر " * 30 + sisipan + "تفصيل النقل " * 30
    baris = f"{matan} {panjang}[^ {catatan} <<11223|-|5|{KUTIPAN}>>][^انظر: المصدر نفسه. <<11223|-|5|{KUTIPAN}>>]"
    naskah.write_text(asli.replace(_BARIS[B_KUTIP - 1], baris), encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh", str(B_KUTIP))
    print(keluar)
    dirujuk = (matan + " " + panjang).strip()
    assert kode == 0, keluar
    assert f"baris {B_KUTIP} #1 matan: {dirujuk}" in keluar.splitlines(), "kalimat yang dinilai hilang atau dipotong"
    assert not any(x.startswith(f"baris {B_KUTIP} #2 matan:") for x in keluar.splitlines()), "matan satu paragraf dicetak dua kali"
    assert any(x.startswith(f"baris {B_KUTIP} #2 catatan:") for x in keluar.splitlines()), "catatan kedua hilang"
    assert f"baris {B_KUTIP} #1 catatan: {catatan.strip()}" in keluar.splitlines(), "catatan kaki dipotong"
    assert all(x.startswith(f"baris {B_KUTIP} ") for x in keluar.splitlines()), keluar
    print("lolos: parafrase dan catatan kaki utuh; matan satu paragraf dicetak sekali untuk dua catatannya")

    pecah = KUTIPAN.index(" تعالى")
    awal, akhir = KUTIPAN[:pecah], KUTIPAN[pecah:]
    matan_sisip = f"قال: «{awal}[^المراد بهذا اللفظ معلوم.]{akhir}»[^رسالة في القضاء والقدر، ص5. <<11223|-|5>>] والله أعلم."
    naskah.write_text(asli.replace(_BARIS[B_KUTIP - 1], matan_sisip), encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh", str(B_KUTIP))
    assert kode == 0, keluar
    assert f"baris {B_KUTIP} #1 matan: قال: «{KUTIPAN}» والله أعلم." in keluar.splitlines(), keluar
    print("lolos: catatan penjelasan di tengah kutipan tidak memotong paragraf matan")

    bait = "#V بيت الشعر الأول ... شطره الثاني // البيت الثاني بعده"
    naskah.write_text(asli.replace(_BARIS[B_KUTIP - 1], f"{bait}[^انظر: رسالة في القضاء والقدر، ص5. <<11223|-|5|{KUTIPAN}>>]"),
                      encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh", str(B_KUTIP))
    assert kode == 0, keluar
    assert all(x.startswith(f"baris {B_KUTIP} ") for x in keluar.splitlines()), keluar
    assert f"baris {B_KUTIP} #1 matan: {bait[3:]}" in keluar.splitlines(), keluar
    print("lolos: bait #V dicetak satu baris dengan « // » dan « ... » seperti di naskah")

    naskah.write_text(asli.replace("\n\n#K الخاتمة", "\nوذهب الجمهور إلى ذلك.\n\n#K الخاتمة"), encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh")
    tanpa = [b for b in keluar.splitlines() if " tanpa catatan kaki: " in b]
    assert tanpa == [f"baris {B_KUTIP + 1} tanpa catatan kaki: «وذهب الجمهور إلى ذلك.»"], keluar
    print("lolos: paragraf isi tanpa catatan kaki dicetak; المقدمة dan الخاتمة tidak")

    # @rujukan_ayat: matan mengubah catatan kaki ayat menjadi [السورة: الآية] di matan: paragraf ayat tetap dianggap bersumber
    naskah.write_text("@rujukan_ayat: matan\n" + asli, encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh")
    assert kode == 0 and " tanpa catatan kaki: " not in keluar, keluar
    print("lolos: paragraf ayat di bawah @rujukan_ayat: matan tidak ditandai tanpa catatan kaki")

    naskah.write_text(asli.replace("<<11223|-|5>>", "<<11223|-|6>>"), encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh", str(B_KUTIP))
    print(keluar)
    _, halaman6 = jalan("halaman", "11223", "-", "6")
    teks = teks_kitab(keluar, 6)
    assert "TIDAK ketemu" in teks, teks
    assert padat(KUTIPAN) not in padat(teks), "halaman lain tempat kutipan berada ikut dicetak"
    assert padat(teks.split("awal halaman: ", 1)[1])[:200] == padat(halaman6)[:200], "yang dicetak bukan awal halaman 6"
    print("lolos: halaman yang salah dikatakan, tidak diganti halaman lain")

    # bukti PDF penelitian <<luar|berkas.pdf|hal>> ikut dicetak cuplikan teks halamannya untuk pemeriksa
    shutil.copyfile(REPO / "contoh" / "jebakan" / "sumber_word.pdf", AKAR / "contoh" / "riset.pdf")
    baris_pdf = "وذكر الباحث مسألة التوحيد[^انظر: دراسة اختبار، ص3. <<luar|riset.pdf|3>>]."
    naskah.write_text(asli.replace(_BARIS[B_KUTIP - 1], baris_pdf), encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh", str(B_KUTIP))
    assert kode == 0, keluar
    assert all(x.startswith(f"baris {B_KUTIP} ") for x in keluar.splitlines()), keluar
    assert "<<luar|riset.pdf|3>> riset.pdf [PDF hal 3;" in keluar, keluar
    assert "⦗3⦘" in keluar, keluar
    # halaman PDF kosong (tanpa lapisan teks) ditandai sebagai scan/tanpa teks
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=595, height=842)
    with open(AKAR / "contoh" / "scan.pdf", "wb") as fh:
        w.write(fh)
    naskah.write_text(asli.replace(_BARIS[B_KUTIP - 1], "وذكر مسألة[^انظر: دراسة، ص1. <<luar|scan.pdf|1>>]."), encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh", str(B_KUTIP))
    assert kode == 0 and "halaman gambar/scan" in keluar, keluar
    # kutipan di tengah halaman PDF yang panjang (> 700 huruf) tidak boleh terpotong di tengah oleh `_ringkas`
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    w_pj = PdfWriter()
    p_pj = w_pj.add_blank_page(width=595, height=842)
    hf = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                           NameObject("/BaseFont"): NameObject("/Helvetica")})
    p_pj[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): w_pj._add_object(hf)})})
    kata_pj = [f"awal{i:03d}" for i in range(70)] + ["KEYPHRASE_UNIQUE_IN_MIDDLE"] + [f"akhir{i:03d}" for i in range(70)]
    baris_pj = [" ".join(kata_pj[i:i + 10]) for i in range(0, len(kata_pj), 10)]
    st = DecodedStreamObject()
    st.set_data("".join(f"BT /F1 10 Tf 1 0 0 1 40 {780 - 15 * idx} Tm ({b}) Tj ET\n"
                        for idx, b in enumerate(baris_pj)).encode("latin1"))
    p_pj[NameObject("/Contents")] = w_pj._add_object(st)
    with open(AKAR / "contoh" / "panjang.pdf", "wb") as fh:
        w_pj.write(fh)
    naskah.write_text(asli.replace(_BARIS[B_KUTIP - 1], 'قال الباحث: "KEYPHRASE_UNIQUE_IN_MIDDLE"[^دراسة طويلة، ص1. <<luar|panjang.pdf|1>>].'), encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh", str(B_KUTIP))
    assert kode == 0 and "KEYPHRASE_UNIQUE_IN_MIDDLE" in keluar.splitlines()[-1], keluar
    assert "sekitar kutipan" in keluar.splitlines()[-1], keluar
    # kutipan yang tidak ada di teks PDF: yang dicetak awal halaman, dan itu dikatakan
    naskah.write_text(asli.replace(_BARIS[B_KUTIP - 1], 'قال الباحث: "ZZZ_TIDAK_ADA_DI_PDF"[^دراسة طويلة، ص1. <<luar|panjang.pdf|1>>].'), encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh", str(B_KUTIP))
    assert kode == 0 and "kutipan TIDAK ditemukan di teks PDF, awal halaman" in keluar.splitlines()[-1], keluar
    print("lolos: bukti PDF <<luar|berkas.pdf|hal>> mencetak cuplikan teks utuh (tanpa memotong kutipan) dan menandai halaman scan")

    # Pelokalan parafrase tanpa tanda petik (`ambang 60%`) tetap menunjuk letak pada halaman bukti (dan tetap menjaga `11223|-|6` gagal)
    paraf = "والمراد بتوحيد الربوبية عند أهل السنة هو إفراد الله سبحانه بالخلق والملك والتدبير وحده[^انظر: رسالة في القضاء والقدر، ص5. <<11223|-|5>>]."
    naskah.write_text(asli.replace(_BARIS[B_KUTIP - 1], paraf), encoding="utf-8")
    kode, keluar = jalan("bukti", "contoh", str(B_KUTIP))
    assert kode == 0 and "perkiraan letak parafrase" in keluar and "بالخلق" in keluar, keluar
    print("lolos: parafrase tanpa tanda petik dilokalkan oleh `bukti` ke letak yang relevan")
finally:
    print("arsip uji:", AKAR)

print("uji bukti: semua sesuai")
