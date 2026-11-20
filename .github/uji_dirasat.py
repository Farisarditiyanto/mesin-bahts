# SPDX-License-Identifier: AGPL-3.0-or-later
"""Uji `dirasat` dan `dirasat-pdf` lewat pintu CLI (`bahts.py`):
- saringan tanggal (--dari/--sampai), bahasa (--bahasa), dan perankingan ulang kolam relevan (--urut) di OpenAlex & DOAJ;
- pencetakan data bibliografi (jilid, nomor, halaman);
- deduplikasi judul lintas sumber tanpa DOI;
- pembacaan satu karya utuh (ringkasan tanpa dipotong) lewat nomor W… atau DOI;
- `dirasat-pdf` menerima DOI dan jatuh otomatis ke tautan PDF akses terbuka bila OpenAlex 404/401, tanpa membocorkan kunci.
"""
import contextlib, io, json, runpy, sys, tempfile, urllib.error, urllib.parse
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "mesin"))
import dirasat


class _Resp(io.BytesIO):
    def __init__(self, data, headers=None):
        super().__init__(data)
        self.headers = headers or {}


def _cli(*args):
    class Keluaran(io.StringIO):
        def reconfigure(self, **kw):
            pass

    out, err = Keluaran(), Keluaran()
    skrip = REPO / "mesin" / "bahts.py"
    with patch.object(sys, "argv", [str(skrip), *args]), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            runpy.run_path(str(skrip), run_name="__main__")
            kode = 0
        except SystemExit as e:
            kode = e.code if isinstance(e.code, int) else 1
            if isinstance(e.code, str):
                err.write(e.code + "\n")
    return kode, out.getvalue(), err.getvalue()


def _pdf_asli():
    from pypdf import PdfWriter
    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.write(buf)
    return buf.getvalue()


def utama():
    sys.stdout.reconfigure(encoding="utf-8")
    panggilan = []
    ringkasan_panjang = " ".join(f"kata{i}" for i in range(120))  # > 400 huruf: bukti tidak dipotong di mode info
    oa_items = [
        {
            "id": "https://openalex.org/W100",
            "title": "دراسة الفقه المالي المعاصر",
            "publication_year": 2020,
            "publication_date": "2020-05-10",
            "type": "article",
            "language": "ar",
            "cited_by_count": 5,
            "biblio": {"volume": "12", "issue": "3", "first_page": "45", "last_page": "70"},
            "authorships": [{"author": {"display_name": "أحمد محمد"}}],
            "primary_location": {"source": {"display_name": "مجلة الشريعة"}, "landing_page_url": "https://example.org/100"},
            "best_oa_location": {"pdf_url": "https://oa.example.org/w100.pdf"},
            "doi": None,
            "has_content": {"pdf": False},
            "abstract_inverted_index": {k: [i] for i, k in enumerate(ringkasan_panjang.split())},
        },
        {
            "id": "https://openalex.org/W200",
            "title": "أحكام المعاملات الرقمية",
            "publication_year": 2024,
            "publication_date": "2024-02-01",
            "type": "article",
            "language": "ar",
            "cited_by_count": 42,
            "biblio": {"volume": "8", "issue": "1", "first_page": "10", "last_page": "30"},
            "authorships": [{"author": {"display_name": "خالد علي"}}],
            "primary_location": {"source": {"display_name": "مجلة الدراسات"}, "landing_page_url": "https://example.org/200"},
            "best_oa_location": {},
            "doi": "https://doi.org/10.1234/w200",
            "has_content": {"pdf": True},
            "abstract_inverted_index": {"ملخص": [0], "حديث": [1]},
        },
        {
            "id": "https://openalex.org/W300",
            "title": "بحث بدون تاريخ محدد",
            "publication_year": None,
            "publication_date": None,
            "type": "article",
            "language": "ar",
            "cited_by_count": 100,
            "biblio": {},
            "authorships": [],
            "primary_location": {},
            "best_oa_location": {},
            "doi": None,
            "has_content": {"pdf": False},
            "abstract_inverted_index": {},
        },
    ]
    doaj_items = [
        {  # judul sama persis dengan W100 tanpa DOI -> harus terdeduplikasi lintas sumber
            "bibjson": {
                "title": "دِرَاسَة الفقه المالي المعاصر!",
                "author": [{"name": "أحمد محمد"}],
                "year": "2020",
                "journal": {"title": "مجلة الشريعة", "volume": "12", "number": "3", "language": ["AR"]},
                "start_page": "45",
                "end_page": "70",
                "identifier": [],
                "link": [{"url": "https://doaj.example.org/dup"}],
                "abstract": "نسخة مكررة",
            }
        },
        {  # bahasa Inggris -> gugur saat --bahasa ar
            "bibjson": {
                "title": "English Islamic Finance Paper",
                "author": [{"name": "Jane Doe"}],
                "year": "2023",
                "journal": {"title": "Journal of Finance", "volume": "5", "number": "2", "language": ["EN"]},
                "start_page": "1",
                "end_page": "15",
                "identifier": [],
                "link": [{"url": "https://doaj.example.org/en"}],
                "abstract": "English abstract",
            }
        },
        {  # tahun 2015 -> gugur saat --dari 2019
            "bibjson": {
                "title": "دراسة قديمة قبل النطاق",
                "author": [{"name": "سالم"}],
                "year": "2015",
                "journal": {"title": "مجلة قديمة", "volume": "2", "number": "1", "language": ["AR"]},
                "start_page": "1",
                "end_page": "20",
                "identifier": [],
                "link": [{"url": "https://doaj.example.org/old"}],
                "abstract": "قديم",
            }
        },
        {  # sah lolos saringan DOAJ (AR, 2022, judul baru)
            "bibjson": {
                "title": "بحث فريد من مجلة عربية مفتوحة",
                "author": [{"name": "فاطمة حسن"}],
                "year": "2022",
                "journal": {"title": "مجلة البحوث الفقهية", "volume": "46", "number": "2", "language": ["AR"]},
                "start_page": "101",
                "end_page": "140",
                "identifier": [],
                "link": [{"url": "https://doaj.example.org/unique.pdf"}],
                "abstract": "ملخص فريد",
            }
        },
    ]

    pdf_bytes = _pdf_asli()

    def palsu_buka(url, kepala=None, waktu=60):
        panggilan.append((url, dict(kepala or {})))
        u = urllib.parse.urlsplit(url)
        if u.hostname == "api.openalex.org" and u.path == "/works":
            return _Resp(json.dumps({"meta": {"count": len(oa_items)}, "results": oa_items}).encode("utf8"))
        if u.hostname == "api.openalex.org" and u.path in ("/works/W100", "/works/doi:10.1234/w100"):
            return _Resp(json.dumps(oa_items[0]).encode("utf8"))
        if u.hostname == "api.openalex.org" and u.path in ("/works/W200", "/works/doi:10.1234/w200"):
            return _Resp(json.dumps(oa_items[1]).encode("utf8"))
        if u.hostname == "doaj.org":
            return _Resp(json.dumps({"total": len(doaj_items), "results": doaj_items}).encode("utf8"))
        if u.hostname == "content.openalex.org" and u.path == "/works/W100.pdf":
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b"not found"))
        if u.hostname == "content.openalex.org" and u.path == "/works/W200.pdf":
            raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, io.BytesIO(b"no key"))
        if url == "https://oa.example.org/w100.pdf":
            return _Resp(pdf_bytes)
        raise AssertionError(f"URL tak terduga: {url}")

    with patch.object(dirasat, "buka", side_effect=palsu_buka), \
            patch.object(dirasat, "_kunci", return_value="KUNCI-UJI"), \
            patch.object(dirasat.time, "sleep"):
        # 1. --dari, --sampai, --bahasa, --urut terbaru: kolam OpenAlex lebar, DOAJ tersaring, duplikat judul dibuang, biblio tercetak
        panggilan.clear()
        kode, out, err = _cli("dirasat", "الفقه المالي", "5", "--dari", "2019", "--sampai", "2025", "--bahasa", "ar", "--urut", "terbaru")
        assert kode == 0, err + out
        oa_reqs = [urllib.parse.parse_qs(urllib.parse.urlsplit(u).query) for u, _ in panggilan if "api.openalex.org/works?" in u]
        qs_kata = next(q for q in oa_reqs if "search" in q)
        qs_makna = next(q for q in oa_reqs if "search.semantic" in q)
        assert int(qs_kata["per_page"][0]) >= 50, qs_kata  # kolam relevan diperlebar sebelum diranking ulang
        assert "from_publication_date:2019-01-01" in qs_kata["filter"][0], qs_kata
        assert "to_publication_date:2025-12-31" in qs_kata["filter"][0], qs_kata
        assert "language:ar" in qs_kata["filter"][0], qs_kata
        # OpenAlex search.semantic hanya menerima publication_year, bukan from/to_publication_date
        assert "publication_year:2019-2025" in qs_makna["filter"][0], qs_makna
        assert "from_publication_date" not in qs_makna["filter"][0], qs_makna
        # urutan terbaru: W200 (2024) sebelum W100 (2020), dan tanpa tanggal (W300) paling akhir di OpenAlex
        assert out.index("أحكام المعاملات الرقمية") < out.index("دراسة الفقه المالي المعاصر") < out.index("بحث بدون تاريخ محدد"), out
        # biblio OpenAlex dan DOAJ tercetak
        assert "مج 12، ع 3، ص 45-70" in out, out
        assert "مج 46، ع 2، ص 101-140" in out, out
        # deduplikasi judul lintas sumber: versi DOAJ yang judulnya sama (dengan harakat) tidak dicetak lagi
        assert "نسخة مكررة" not in out, out
        # saringan DOAJ bekerja: paper EN dan 2015 dibuang, paper AR 2022 lolos
        assert "English Islamic Finance Paper" not in out, out
        assert "دراسة قديمة قبل النطاق" not in out, out
        assert "بحث فريد من مجلة عربية مفتوحة" in out, out

        # 2. --urut terlama & --urut dikutip
        kode, out_lama, err = _cli("dirasat", "الفقه المالي", "5", "--urut", "terlama")
        assert kode == 0, err
        assert out_lama.index("دراسة الفقه المالي المعاصر") < out_lama.index("أحكام المعاملات الرقمية") < out_lama.index("بحث بدون تاريخ محدد"), out_lama
        kode, out_kutip, err = _cli("dirasat", "الفقه المالي", "5", "--urut", "dikutip")
        assert kode == 0, err
        assert out_kutip.index("بحث بدون تاريخ محدد") < out_kutip.index("أحكام المعاملات الرقمية") < out_kutip.index("دراسة الفقه المالي المعاصر"), out_kutip

        # 3. Single-paper lookup lewat W… maupun DOI mencetak ringkasan UTUH (> 400 huruf)
        for pengenal in ("W100", "https://openalex.org/W100", "10.1234/w100", "https://doi.org/10.1234/w100"):
            kode, out_info, err = _cli("dirasat", pengenal)
            assert kode == 0, (pengenal, err)
            assert "kata119" in out_info, f"ringkasan terpotong pada {pengenal}: {out_info}"
            assert "مج 12، ع 3، ص 45-70" in out_info, out_info

        # 4. dirasat-pdf: fallback OA PDF saat OpenAlex 404, dan terima DOI tanpa membocorkan kunci ke host OA
        with tempfile.TemporaryDirectory(prefix="bahts-uji-dirasat-") as tmp:
            # folder bahts harus berada di dalam repo untuk CLI -> uji via dirasat.pdf langsung & CLI lewat folder sementara di dalam _tmp
            t = Path(tmp)
            panggilan.clear()
            dirasat.pdf("W100", t)
            assert (t / "W100.pdf").is_file() and dirasat._pdf_terbaca(t / "W100.pdf")
            oa_hdrs = [h for u, h in panggilan if u == "https://oa.example.org/w100.pdf"]
            assert oa_hdrs and "Authorization" not in oa_hdrs[0], f"kunci OpenAlex bocor ke host OA: {oa_hdrs}"

            # DOI -> resolve W100 -> unduh OA PDF
            (t / "W100.pdf").unlink()
            dirasat.pdf("https://doi.org/10.1234/w100", t)
            assert (t / "W100.pdf").is_file()

        # 5. Validasi argumen salah dan bendera tak dikenal ditolak bersih tanpa Traceback
        for buruk in (
            ("dirasat", "uji", "--urut", "acak"),
            ("dirasat", "uji", "--dari", "2025", "--sampai", "2020"),
            ("dirasat", "uji", "--dari", "bukan-tanggal"),
            ("dirasat", "uji", "5", "--typo"),
            ("dirasat", "uji", "--tahun", "2020"),
        ):
            kode, out, err = _cli(*buruk)
            assert kode != 0 and "Traceback" not in err, (buruk, kode, out, err)
            if "--typo" in buruk or "--tahun" in buruk:
                assert "tidak dikenal" in err, (buruk, err)

        # 6. Keamanan: skema file:// pada pdf_url OA wajib ditolak (tidak boleh menyalin berkas lokal)
        with tempfile.TemporaryDirectory(prefix="bahts-uji-file-") as tmp:
            t = Path(tmp)
            rahasia = t / "rahasia.pdf"
            rahasia.write_bytes(pdf_bytes)
            tujuan = t / "W999.pdf"
            assert not dirasat._unduh_oa([rahasia.as_uri()], tujuan, "W999")
            assert not tujuan.exists(), "file:// lokal tersalin oleh _unduh_oa!"

        # 7. Edge case id_karya & _masuk_rentang
        assert dirasat.id_karya("10.1234/...") is None
        assert dirasat.id_karya("10.1000/foo(bar)") == ("doi:10.1000/foo(bar)", "10.1000/foo(bar)")
        assert dirasat.id_karya("https://doi.org/10.1234/abc?utm=1#sec") == ("doi:10.1234/abc", "10.1234/abc")
        assert not dirasat._masuk_rentang({"tahun": 999}, "2020-01-01", "")

        # 8. DOAJ yang tersaring habis jadi 0 tidak boleh mematikan peringatan MAKNA_SAJA
        def buka_makna_saja(url, kepala=None, waktu=60):
            u = urllib.parse.urlsplit(url)
            qs = urllib.parse.parse_qs(u.query)
            if u.hostname == "api.openalex.org" and "search" in qs:
                return _Resp(json.dumps({"meta": {"count": 0}, "results": []}).encode("utf8"))
            if u.hostname == "api.openalex.org" and "search.semantic" in qs:
                return _Resp(json.dumps({"meta": {"count": 1}, "results": [oa_items[1]]}).encode("utf8"))
            if u.hostname == "doaj.org":
                return _Resp(json.dumps({"total": 500, "results": [doaj_items[1]]}).encode("utf8"))  # hanya bahasa EN
            raise AssertionError(f"URL tak terduga: {url}")

        with patch.object(dirasat, "buka", side_effect=buka_makna_saja):
            kode, out_ms, err = _cli("dirasat", "kata-kosong", "5", "--bahasa", "ar")
            assert kode == 0, err
            assert "DOAJ: 0 penelitian cocok" in out_ms, out_ms
            assert "PERINGATAN: semua hasil di atas hanya MIRIP MAKNANYA" in out_ms, out_ms

        # 9. Tanpa kunci OpenAlex: info W200 mencetak cara kunci, dan dirasat-pdf DOI melaporkan butuh kunci (bukan «tidak menyimpan»)
        with patch.object(dirasat, "_kunci", return_value=""):
            kode, out_nk, err = _cli("dirasat", "W200")
            assert kode == 0 and "kunci_openalex.txt" in out_nk, out_nk + err
            with tempfile.TemporaryDirectory(prefix="bahts-uji-nokey-") as tmp:
                try:
                    dirasat.pdf("10.1234/w200", Path(tmp))
                except SystemExit as e:
                    pesan = str(e)
                    assert "butuh kunci" in pesan and "tidak menyimpan" not in pesan, pesan
                else:
                    raise AssertionError("dirasat-pdf DOI tanpa kunci seharusnya gagal")

    print("lolos uji dirasat (tanggal, bahasa, urut kolam, biblio, dedup judul, info W/DOI, fallback OA PDF, keamanan)")


if __name__ == "__main__":
    utama()
