# SPDX-License-Identifier: AGPL-3.0-or-later
"""Uji perilaku perintah muqorror: tata letak kitab/lembar, anotasi, diagram, daftar isi, tautan, dan validasi."""

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf

from bantu import REPO, bahts

ANGKA_ARAB = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _rencana_lengkap():
    return {
        "judul": "مقرر النحو الاختباري",
        "subjudul": "شرح ابن عقيل على ألفية ابن مالك",
        "keterangan": "مذكرة دراسية شاملة مع تعليقات المحاضرات.",
        "sumber": [
            {"id": "م١", "judul": "المحاضرة الأولى", "tautan": "https://example.org/muqorror/lec-1"},
            {"id": "م٢", "judul": "المحاضرة الثانية", "tautan": "https://example.org/muqorror/lec-2"},
            {"id": "م٣", "judul": "ورقة المراجعة"},
        ],
        "bagian": [
            {
                "judul": "المفعول المطلق",
                "jenis": "kitab",
                "hal_kitab": "١٤١–١٤٥",
                "catatan_pangkas": "اختُصرت الحواشي الطويلة غير الداخلة.",
                "sumber": ["م١", "م٢"],
                "blok": [
                    {"jenis": "hal", "nomor": "١٤١"},
                    {"jenis": "subjudul", "teks": "تعريف المصدر", "sumber": ["م١"]},
                    {
                        "jenis": "bait",
                        "nomor": "٢٩١",
                        "kanan": "المصدر اسم ما سوى الزمان من",
                        "kiri": "مدلولي الفعل كأمن من أمن",
                        "gaya": "alfiyah",
                        "catatan": {
                            "label": "مفتاح البيت",
                            "warna": "biru",
                            "isi": "المصدر يدل على الحدث وحده.",
                            "sumber": ["م١"],
                        },
                    },
                    {
                        "jenis": "matan",
                        "teks": (
                            "الفعل يدل على {hl:حدث وزمان}؛ فـ{o:قام} يدل على {ul:قيام ماض}، "
                            "و{ur:الحدث} هو {b:المصدر} و{hl2:أصل المشتقات}{fn:١}."
                        ),
                        "catatan": [
                            {"label": "سؤال مهم", "warna": "merah", "isi": "لماذا سمي مفعولا مطلقا؟"},
                            {"label": "فائدة", "warna": "hijau", "isi": "الحدث مجرد عن الزمن.", "sumber": ["م١"]},
                        ],
                    },
                    {
                        "jenis": "sela",
                        "label": "تعليق الأستاذ",
                        "warna": "hijau",
                        "sumber": ["م١"],
                        "isi": "قاعدة سريعة للتمييز:",
                        "butir": ["المؤكد لا يثنى.", "المبين للعدد يثنى."],
                        "catatan": {"isi": "احفظ هذه القاعدة للاختبار.", "warna": "merah"},
                    },
                    {
                        "jenis": "bait",
                        "kanan": "وقد يجمع الله الشتيتين بعدما",
                        "kiri": "يظنان كل الظن أن لا تلاقيا",
                        "gaya": "syahid",
                    },
                    {
                        "jenis": "diagram",
                        "judul": "شجرة أقسام المفعول",
                        "tipe": "pohon",
                        "sumber": ["م١"],
                        "akar": "أقسام {b:المفعول} المطلق",
                        "cabang": [
                            {"judul": "المؤكد", "warna": "biru", "isi": ["{hl:يقرر} المعنى", "لا يثنى"]},
                            {"judul": "المبين للنوع", "warna": "hijau", "isi": ["موصوف أو مضاف"]},
                            {"judul": "المبين للعدد", "warna": "merah", "isi": ["ضربت ضربتين"]},
                        ],
                    },
                    {
                        "jenis": "hasyiah",
                        "butir": [{"nomor": "١", "teks": "أي أحد مدلولي الفعل بالوضع."}],
                        "catatan_pangkas": "حذفت الحاشية الثانية للاختصار.",
                    },
                    {"jenis": "halaman_baru"},
                    {"jenis": "hal", "nomor": "١٤٥"},
                    {"jenis": "subjudul", "teks": "النوائب عن المصدر", "sumber": ["م٢"]},
                    {
                        "jenis": "diagram",
                        "judul": "مسار إعراب النائب",
                        "tipe": "alur",
                        "sumber": ["م٢"],
                        "langkah": [
                            {"judul": "تحديد العامل", "isi": "ابحث عن الفعل.", "warna": "biru"},
                            {"judul": "تعيين النائب", "isi": "كل أو العدد أو الآلة.", "warna": "hijau"},
                            {"judul": "النصب", "isi": "نائب منصوب.", "warna": "ungu"},
                        ],
                    },
                    {
                        "jenis": "diagram",
                        "judul": "جدول مقارنة النوائب",
                        "tipe": "tabel",
                        "sumber": ["م٢"],
                        "kolom": ["النائب", "المثال"],
                        "baris": [
                            ["كل وبعض", "كل الميل"],
                            ["اسم الآلة", "ضربته سوطا"],
                        ],
                    },
                ],
            },
            {
                "judul": "ورقة مراجعة سريعة",
                "jenis": "lembar",
                "sumber": ["م٣"],
                "blok": [
                    {"jenis": "subjudul", "teks": "خلاصة ليلة الامتحان"},
                    {"jenis": "matan", "teks": "راجع أمثلة {hl:المفعول المطلق} قبل القاعة."},
                    {"jenis": "halaman_baru"},
                    {"jenis": "subjudul", "teks": "تدريبات الإعراب"},
                    {"jenis": "matan", "teks": "أعرب: ضربته سوطا."},
                ],
            },
        ],
    }


def _uji_validasi_gagal(folder, dasar, hasil, lama, ubah, fragmen_galat, tujuan_khusus=None):
    data = copy.deepcopy(dasar)
    ubah(data)
    rencana = folder / "rencana_gagal.json"
    rencana.write_text(json.dumps(data, ensure_ascii=False), encoding="utf8")
    tujuan = tujuan_khusus if tujuan_khusus is not None else hasil
    r = bahts(REPO, "muqorror", rencana, tujuan)
    assert r.returncode != 0, f"seharusnya gagal ({fragmen_galat}): {r.stdout}"
    assert fragmen_galat in r.stderr, (fragmen_galat, r.stderr)
    assert hasil.read_bytes() == lama, "hasil PDF lama berubah saat validasi gagal"


def utama(folder: Path) -> None:
    dasar = _rencana_lengkap()
    rencana = folder / "rencana.json"
    hasil = folder / "muqorror.pdf"
    rencana.write_text(json.dumps(dasar, ensure_ascii=False), encoding="utf8")

    r = bahts(REPO, "muqorror", rencana, hasil)
    assert r.returncode == 0 and "PDF=" in r.stdout and "HALAMAN=" in r.stdout, (r.returncode, r.stdout, r.stderr)

    with pymupdf.open(hasil) as doc:
        assert len(doc) >= 5, f"halaman terlalu sedikit: {len(doc)}"
        assert doc.metadata["title"] == dasar["judul"]
        assert doc.metadata["subject"] == dasar["subjudul"]

        semua_font = {f[3] for p in doc for f in p.get_fonts()}
        assert any("Amiri" in f for f in semua_font), semua_font
        assert any("PlaypenSansArabic" in f for f in semua_font), semua_font

        toc = doc.get_toc()
        toc_l1 = {judul: hal for tingkat, judul, hal in toc if tingkat == 1}
        toc_l2 = {judul: hal for tingkat, judul, hal in toc if tingkat == 2}
        assert toc_l1["فهرس المقرر"] == 1, toc
        assert "المفعول المطلق" in toc_l1 and "ورقة مراجعة سريعة" in toc_l1 and "مصادر المحاضرات" in toc_l1, toc
        for tanda_l2 in (
            "تعريف المصدر", "شجرة أقسام المفعول", "النوائب عن المصدر",
            "مسار إعراب النائب", "جدول مقارنة النوائب", "خلاصة ليلة الامتحان", "تدريبات الإعراب",
        ):
            assert tanda_l2 in toc_l2, (tanda_l2, toc_l2)

        p_bab1 = toc_l1["المفعول المطلق"] - 1
        p_bab2 = toc_l1["ورقة مراجعة سريعة"] - 1
        p_sumber = toc_l1["مصادر المحاضرات"] - 1
        assert 0 < p_bab1 < p_bab2 < p_sumber == len(doc) - 1, (p_bab1, p_bab2, p_sumber, len(doc))

        # Cek teks fihris + nomor halaman Arab nyata + tautan internal klik-langsung
        teks_fihris = doc[0].get_text()
        assert "فهرس المقرر" in teks_fihris and "المفعول المطلق" in teks_fihris and "مصادر المحاضرات" in teks_fihris
        for hal_target in (p_bab1 + 1, p_bab2 + 1, p_sumber + 1):
            assert str(hal_target).translate(ANGKA_ARAB) in teks_fihris, (hal_target, teks_fihris)
        tujuan_fihris = {
            t["page"] for t in doc[0].get_links() if t["kind"] in (pymupdf.LINK_GOTO, pymupdf.LINK_NAMED) and "page" in t
        }
        assert {p_bab1, p_bab2, p_sumber} <= tujuan_fihris, (tujuan_fihris, p_bab1, p_bab2, p_sumber)

        # Cek halaman_baru memisahkan dua blok singkat dalam bagian yang sama
        p_sub1 = toc_l2["خلاصة ليلة الامتحان"] - 1
        p_sub2 = toc_l2["تدريبات الإعراب"] - 1
        assert p_sub2 == p_sub1 + 1, (p_sub1, p_sub2)
        assert "تدريبات" in doc[p_sub2].get_text() and "تدريبات" not in doc[p_sub1].get_text()

        # Cek teks kitab, anotasi (tanpa bocor marka mentah), margin, sela, diagram, hasyiah, lembar
        teks_bab1 = "\n".join(doc[i].get_text() for i in range(p_bab1, p_bab2))
        for wajib in (
            "١٤١", "تعريف المصدر", "مدلولي الفعل", "مفتاح البيت",
            "حدث وزمان", "قيام ماض", "أصل المشتقات", "سؤال مهم", "قاعدة سريعة للتمييز",
            "الشتيتين", "شجرة أقسام", "يقرر", "حذفت الحاشية الثانية",
            "تحديد العامل", "جدول", "ضربته سوطا",
        ):
            assert wajib in teks_bab1, f"tidak ketemu di bab 1: {wajib}"
        for mentah in ("{", "}", "hl:", "hl2:", "ul:", "ur:", "fn:"):
            assert mentah not in teks_bab1, f"marka mentah bocor ke PDF: {mentah}"

        teks_lembar = "\n".join(doc[i].get_text() for i in range(p_bab2, p_sumber))
        assert "ورقة مراجعة سريعة" in teks_lembar and "ليلة" in teks_lembar and "قبل القاعة" in teks_lembar

        # Cek tautan URI eksternal di halaman sumber + tautan chip sumber dari isi ke halaman sumber
        uri_sumber = {t.get("uri") for t in doc[p_sumber].get_links() if t["kind"] == pymupdf.LINK_URI}
        assert {"https://example.org/muqorror/lec-1", "https://example.org/muqorror/lec-2"} <= uri_sumber, uri_sumber
        tautan_isi = {
            t["page"]
            for i in range(p_bab1, p_sumber)
            for t in doc[i].get_links()
            if t["kind"] in (pymupdf.LINK_GOTO, pymupdf.LINK_NAMED) and "page" in t
        }
        assert p_sumber in tautan_isi, (tautan_isi, p_sumber)

    # Uji ketahanan terhadap injeksi </style><script> pada subjudul dan alur 5 langkah
    injeksi = {
        "judul": "مقرر آمن",
        "subjudul": '</style><script>document.body.innerHTML="PW"+"N_EXEC"</script><style>',
        "sumber": [],
        "bagian": [
            {
                "judul": "باب اختبار الأمان",
                "blok": [
                    {"jenis": "matan", "teks": "متن أصلي محفوظ."},
                    {
                        "jenis": "diagram",
                        "judul": "مسار خماسي",
                        "tipe": "alur",
                        "langkah": [
                            {"judul": "الأولى", "isi": "خطوة أولى"},
                            {"judul": "الثانية", "isi": "كلمةطويلةجدامتصلةبلاتوقف"},
                            {"judul": "الثالثة", "isi": "ثالثة"},
                            {"judul": "الرابعة", "isi": "رابعة"},
                            {"judul": "الخامسة", "isi": "خامسة"},
                        ],
                    },
                ],
            }
        ],
    }
    rencana_inj = folder / "injeksi.json"
    hasil_inj = folder / "injeksi.pdf"
    rencana_inj.write_text(json.dumps(injeksi, ensure_ascii=False), encoding="utf8")
    r_inj = bahts(REPO, "muqorror", rencana_inj, hasil_inj)
    assert r_inj.returncode == 0, (r_inj.stdout, r_inj.stderr)
    with pymupdf.open(hasil_inj) as doc_inj:
        teks_inj = "\n".join(p.get_text() for p in doc_inj)
        assert "PWN_EXEC" not in teks_inj, teks_inj
        assert "متن أصلي محفوظ" in teks_inj, teks_inj

    # Uji rencana sah tanpa sumber (sumber: [])
    tanpa_sumber = {
        "judul": "مقرر بلا مصادر",
        "sumber": [],
        "bagian": [{"judul": "الباب الأول", "blok": [{"jenis": "matan", "teks": "نص مختصر للمقرر."}]}],
    }
    rencana_ts = folder / "tanpa_sumber.json"
    hasil_ts = folder / "tanpa_sumber.pdf"
    rencana_ts.write_text(json.dumps(tanpa_sumber, ensure_ascii=False), encoding="utf8")
    r_ts = bahts(REPO, "muqorror", rencana_ts, hasil_ts)
    assert r_ts.returncode == 0, (r_ts.stdout, r_ts.stderr)
    with pymupdf.open(hasil_ts) as doc_ts:
        judul_toc = [j for _, j, _ in doc_ts.get_toc()]
        assert "مصادر المحاضرات" not in judul_toc, judul_toc
        assert "الباب الأول" in judul_toc, judul_toc

    # Uji validasi batas & keselamatan berkas lama
    lama = hasil.read_bytes()
    _uji_validasi_gagal(folder, dasar, hasil, lama, lambda d: d.__setitem__("asing", 1), "asing")
    _uji_validasi_gagal(folder, dasar, hasil, lama, lambda d: d["bagian"][0]["blok"].append({"jenis": "aneh"}), "harus salah satu")
    _uji_validasi_gagal(folder, dasar, hasil, lama, lambda d: d["bagian"][0].__setitem__("sumber", ["م٩٩"]), "belum didaftar: م٩٩")
    _uji_validasi_gagal(folder, dasar, hasil, lama, lambda d: d.__setitem__("judul", "عنوان\x00فاسد"), "karakter kontrol")
    _uji_validasi_gagal(folder, dasar, hasil, lama, lambda d: d["sumber"][0].__setitem__("tautan", "javascript:alert(1)"), "HTTP atau HTTPS")
    _uji_validasi_gagal(
        folder, dasar, hasil, lama,
        lambda d: d["bagian"][0]["blok"].append({"jenis": "sela", "label": "فارغ"}),
        "isi atau butir",
    )
    _uji_validasi_gagal(
        folder, dasar, hasil, lama,
        lambda d: d["bagian"][0]["blok"].append({
            "jenis": "diagram", "judul": "قليل", "tipe": "pohon", "akar": "أصل",
            "cabang": [{"judul": "واحد", "isi": ["نقطة"]}],
        }),
        "2 sampai 4",
    )
    _uji_validasi_gagal(
        folder, dasar, hasil, lama,
        lambda d: d["bagian"][0]["blok"].append({
            "jenis": "diagram", "judul": "خلل", "tipe": "tabel", "kolom": ["أ", "ب"], "baris": [["ناقص"]],
        }),
        "2 sel",
    )
    _uji_validasi_gagal(folder, dasar, hasil, lama, lambda _d: None, "berakhiran .pdf", tujuan_khusus=folder / "bukan.txt")

    # Pastikan rencana.json tidak pernah tertimpa walau dipaksa sebagai tujuan
    isi_rencana = rencana.read_bytes()
    r_timpa = bahts(REPO, "muqorror", rencana, rencana)
    assert r_timpa.returncode != 0, r_timpa
    assert rencana.read_bytes() == isi_rencana

    rencana_pdf = folder / "rencana.pdf"
    rencana_pdf.write_text(json.dumps(tanpa_sumber, ensure_ascii=False), encoding="utf8")
    isi_rp = rencana_pdf.read_bytes()
    r_timpa2 = bahts(REPO, "muqorror", rencana_pdf, rencana_pdf)
    assert r_timpa2.returncode != 0 and "tidak boleh menimpa" in r_timpa2.stderr, r_timpa2
    assert rencana_pdf.read_bytes() == isi_rp


if __name__ == "__main__":
    with TemporaryDirectory(prefix="uji-muqorror-") as d:
        utama(Path(d))
    print("muqorror: tata letak, font, anotasi, diagram, daftar isi, tautan, dan validasi lolos")
