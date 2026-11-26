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
import dirasat, jaringan


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
        {  # judul sama dengan W100, tahun lain: penelitian lain, tidak boleh terbuang sebagai duplikat
            "bibjson": {
                "title": "دراسة الفقه المالي المعاصر",
                "author": [{"name": "باحث آخر"}],
                "year": "2010",
                "journal": {"title": "مجلة أخرى", "language": ["AR"]},
                "identifier": [],
                "link": [{"url": "https://doaj.example.org/2010"}],
                "abstract": "دراسة أخرى بالعنوان نفسه",
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
        assert "دراسة أخرى بالعنوان نفسه" in out_lama and "نسخة مكررة" not in out_lama, out_lama  # judul + tahun
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

            # PDF dengan sisa bait sesudah %%EOF tetap tersimpan, tetapi mencetak PERINGATAN struktur PDF
            (t / "W100.pdf").unlink()
            pdf_cacat = pdf_bytes + b"\nSISA_TIDAK_SAH"
            out_cacat = io.StringIO()
            with patch.object(dirasat, "buka", side_effect=lambda u, kepala=None, waktu=60: (
                _Resp(pdf_cacat) if u == "https://oa.example.org/w100.pdf" else palsu_buka(u, kepala, waktu)
            )), contextlib.redirect_stdout(out_cacat):
                dirasat.pdf("W100", t)
            assert (t / "W100.pdf").is_file()
            assert "PERINGATAN: struktur PDF" in out_cacat.getvalue() and "%%EOF" in out_cacat.getvalue(), out_cacat.getvalue()

        # 5. Validasi argumen salah dan bendera tak dikenal ditolak bersih tanpa Traceback
        for buruk in (
            ("dirasat", "uji", "--urut", "acak"),
            ("dirasat", "uji", "--dari", "2025", "--sampai", "2020"),
            ("dirasat", "uji", "--dari", "bukan-tanggal"),
            ("dirasat", "uji", "5", "--typo"),
            ("dirasat", "uji", "--tahun", "2020"),
            ("dirasat", "uji", "--bahasa", "arabic"),
            ("dirasat", "uji", "--bahasa", "ar,en"),
            ("dirasat", "uji", "--bahasa", ""),
        ):
            kode, out, err = _cli(*buruk)
            assert kode != 0 and "Traceback" not in err, (buruk, kode, out, err)
            if "--bahasa" in buruk:
                assert "kode bahasa dua huruf" in err or "--bahasa butuh nilai" in err, (buruk, err)
            if "--typo" in buruk or "--tahun" in buruk:
                assert "tidak dikenal" in err, (buruk, err)

        # 6. pdf_url dari data layanan berskema file:// tidak pernah dibuka (urllib membuka berkas lokal), dan tiap
        #    tempat yang gagal disebut alasannya
        with tempfile.TemporaryDirectory(prefix="bahts-uji-file-") as tmp:
            t = Path(tmp)
            rahasia = t / "rahasia.pdf"
            rahasia.write_bytes(pdf_bytes)
            w400 = dict(oa_items[0], id="https://openalex.org/W400", best_oa_location={"pdf_url": rahasia.as_uri()})

            def buka_file(url, kepala=None, waktu=60):
                if urllib.parse.urlsplit(url).path == "/works/W400":
                    return _Resp(json.dumps(w400).encode("utf8"))
                return jaringan.buka(url, kepala=kepala, waktu=waktu)  # pintu jaringan asli yang menolak file://

            with patch.object(dirasat, "buka", side_effect=buka_file):
                try:
                    dirasat.pdf("W400", t)
                except SystemExit as e:
                    pesan = str(e)
                else:
                    raise AssertionError("file:// lokal dianggap unduhan")
            assert not (t / "W400.pdf").exists(), "file:// lokal tersalin oleh dirasat-pdf!"
            assert rahasia.as_uri() in pesan and "bukan http/https" in pesan, pesan
            # salinan OpenAlex ditolak (401) dan tidak ada tautan lain: alasannya tercetak, bukan ditelan
            try:
                dirasat.pdf("W200", t)
            except SystemExit as e:
                assert "salinan OpenAlex https://content.openalex.org/works/W200.pdf" in str(e) and "ditolak" in str(e), e
            else:
                raise AssertionError("W200 tanpa salinan yang bisa diunduh dianggap berhasil")

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

        # 8b. Judul sama: dua DOI berbeda = dua penelitian (keduanya tercetak); judul Latin yang sama tanpa DOI di DOAJ
        #     = penelitian yang sama (dibuang)
        def karya(nomor, judul, doi):
            return dict(oa_items[0], id=f"https://openalex.org/{nomor}", title=judul, doi=doi,
                        abstract_inverted_index={nomor: [0]})
        kembar = [karya("W501", "التورق المصرفي المنظم", "https://doi.org/10.1/a"),
                  karya("W502", "التورق المصرفي المنظم", "https://doi.org/10.2/b"),
                  karya("W503", "Islamic Banking in Indonesia", "https://doi.org/10.3/c"),
                  karya("W504", "رسالة جامعية بعنوان عام", None), karya("W505", "رسالة جامعية بعنوان عام", None)]
        doaj_latin = [{"bibjson": dict(doaj_items[0]["bibjson"], title="Islamic banking in Indonésia",
                                       abstract="SALINAN-DOAJ")}]

        def buka_kembar(url, kepala=None, waktu=60):
            u = urllib.parse.urlsplit(url)
            if u.hostname == "api.openalex.org":
                hasil = kembar if "search" in urllib.parse.parse_qs(u.query) else []
                return _Resp(json.dumps({"meta": {"count": len(hasil)}, "results": hasil}).encode("utf8"))
            return _Resp(json.dumps({"total": 1, "results": doaj_latin}).encode("utf8"))

        with patch.object(dirasat, "buka", side_effect=buka_kembar):
            kode, out_k, err = _cli("dirasat", "التورق", "5")
        assert kode == 0, err
        assert "W501" in out_k and "W502" in out_k, f"penelitian ber-DOI lain terbuang sebagai duplikat: {out_k}"
        assert "W504" in out_k and "W505" in out_k, f"nomor W… lain tanpa DOI terbuang sebagai duplikat: {out_k}"
        assert "W503" in out_k and "SALINAN-DOAJ" not in out_k, f"judul Latin yang sama tanpa DOI tidak digabung: {out_k}"

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

        # 10. `dirasat-cek`: metadata per baris, Crossref, pencabutan, registrasi DOI, dan layanan tidak tersedia.
        assert dirasat.tahun_masehi_hijriah(1442) == {2020, 2021}, dirasat.tahun_masehi_hijriah(1442)
        retracted = dict(oa_items[1], id="https://openalex.org/W999", doi="https://doi.org/10.9999/ret",
                         title="دراسة مسحوبة في التمويل", is_retracted=True)
        alias_oa = dict(oa_items[0], id="https://openalex.org/W100000", doi="https://doi.org/10.5555/alias")
        hoo_oa = dict(oa_items[0], id="https://openalex.org/W5000001", publication_year=2019, language="en",
                      title="Biometric Attendance Tracking System for Education: A Survey on Hardware",
                      authorships=[{"author": {"display_name": "Seng Chun Hoo"}},
                                   {"author": {"display_name": "Haidi Ibrahim"}}])
        lawal_oa = dict(oa_items[0], id="https://openalex.org/W6000001", publication_year=2026, language="en",
                        title="A Mobile Fingerprint Attendance System for University Lectures",
                        authorships=[{"author": {"display_name": "Aderonke Rasheedat Lawal"}},
                                     {"author": {"display_name": "Aina Segun"}}])

        def buka_cek(url, kepala=None, waktu=60):
            u = urllib.parse.urlsplit(url)
            if u.hostname == "api.openalex.org":
                if "10.5555/alias" in u.path:
                    return _Resp(json.dumps(alias_oa).encode("utf8"))
                if "10.5555/offline" in u.path:
                    raise urllib.error.URLError("layanan tidak tersedia")
                if "10.1234/w200" in u.path or u.path.endswith("/W200"):
                    return _Resp(json.dumps(oa_items[1]).encode("utf8"))
                if "10.1234/w100" in u.path or u.path.endswith("/W100") or u.path.endswith("/W2741809807"):
                    return _Resp(json.dumps(oa_items[0]).encode("utf8"))
                if "10.9999/ret" in u.path:
                    return _Resp(json.dumps(retracted).encode("utf8"))
                if u.path.endswith("/W5000001"):
                    return _Resp(json.dumps(hoo_oa).encode("utf8"))
                if u.path.endswith("/W6000001"):
                    return _Resp(json.dumps(lawal_oa).encode("utf8"))
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))
            if u.hostname == "api.crossref.org":
                if "10.5555%2Fcr1" in u.path or "10.5555/cr1" in u.path:
                    return _Resp(json.dumps({"message": {
                        "DOI": "10.5555/cr1",
                        "title": ["Islamic Finance Governance"],
                        "author": [{"given": "Ali", "family": "Hassan"}],
                        "published-print": {"date-parts": [[2021]]},
                        "container-title": ["Arab Finance Review"],
                    }}).encode("utf8"))
                if "10.5555%2Fcr-ret" in u.path or "10.5555/cr-ret" in u.path:
                    return _Resp(json.dumps({"message": {
                        "DOI": "10.5555/cr-ret",
                        "title": ["Retracted Crossref Paper"],
                        "author": [{"given": "Nadia", "family": "Salim"}],
                        "published-print": {"date-parts": [[2022]]},
                        "updated-by": [{"type": "retraction"}],
                    }}).encode("utf8"))
                if "10.5555%2Fnotice" in u.path:
                    return _Resp(json.dumps({"message": {
                        "DOI": "10.5555/notice",
                        "title": ["Retraction Notice"],
                        "update-to": [{"type": "retraction", "DOI": "10.5555/cr-ret"}],
                    }}).encode("utf8"))
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))
            if u.hostname == "doi.org" and u.path.startswith("/api/handles/"):
                if u.path.endswith("registered"):
                    return _Resp(b'{"responseCode":1}')
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b'{"responseCode":100}'))
            raise AssertionError(f"URL tak terduga: {url}")

        with patch.object(dirasat, "buka", side_effect=buka_cek):
            # info karya dicabut mencetak peringatan RETRACTED
            kode, out_r, err = _cli("dirasat", "10.9999/ret")
            assert kode == 0 and "DICABUT / RETRACTED" in out_r, out_r + err

            # folder uji di dalam REPO sementara agar folder_bahts menerimanya
            uji_dir = Path(tempfile.mkdtemp(prefix="_uji_dirasat_cek_", dir=REPO))
            try:
                # a) semua cocok: Hijriah 1442هـ -> 2020/2021 cocok dengan W100 (2020), Crossref fallback 10.5555/cr1 (2021),
                #    ringkasan Arab atas makalah Inggris & tahun wafat (ت 1421هـ) tidak salah tangkap,
                #    PDF lokal <<luar|w1.pdf|5>> tidak dianggap ID OpenAlex, sedangkan <<luar|W2741809807.pdf|2>> diperiksa.
                (uji_dir / "naskah.txt").write_text(
                    "@judul: تجربة\n@nama: طالب\n#K المقدمة\n"
                    "دراسة الفقه المالي المعاصر، أحمد محمد، ١٤٤٢هـ[^انظر: https://openalex.org/W100 <<luar>>].\n"
                    "وقد أثبتت دراسة علي حسن الحديثة، مقارنة بفتوى ابن عثيمين (ت 1421هـ)، استقرار التمويل الإسلامي[^doi:10.5555/cr1 <<luar>>].\n"
                    "مرجع محلي في ملف عادي[^دراسة محلية، ص5. <<luar|w1.pdf|5>>].\n"
                    "دراسة الفقه المالي المعاصر، 2020م[^انظر: ص2. <<luar|W2741809807.pdf|2>>].\n",
                    encoding="utf8",
                )
                kode, out_ok, err = _cli("dirasat-cek", uji_dir.name)
                assert kode in (0, 2), out_ok + err
                assert "ID DITEMUKAN" in out_ok and "[Crossref]" in out_ok and "0 fatal" in out_ok, out_ok
                assert "TIDAK COCOK" not in out_ok, out_ok
                assert "W2741809807" in out_ok and "W1]" not in out_ok, out_ok

                # b) ketidakcocokan tahun & judul + karya dicabut (OpenAlex & Crossref updated-by) + phantom DOI -> exit 1
                (uji_dir / "naskah.txt").write_text(
                    "@judul: تجربة\n@nama: طالب\n#K المقدمة\n"
                    "بحث في البلاغة العربية، مؤلف آخر، 2015م[^https://doi.org/10.1234/w200 <<luar>>].\n"
                    "دراسة مسحوبة في التمويل[^https://doi.org/10.9999/ret <<luar>>].\n"
                    "دراسة مسحوبة في كروسريف[^https://doi.org/10.5555/cr-ret <<luar>>].\n"
                    "مرجع مختلق تماما[^https://doi.org/10.9999/phantom-xyz <<luar>>].\n",
                    encoding="utf8",
                )
                kode, out_bad, err = _cli("dirasat-cek", uji_dir.name)
                assert kode == 1, out_bad + err
                assert "TIDAK COCOK" in out_bad and "tahun di naskah" in out_bad, out_bad
                assert out_bad.count("DICABUT (RETRACTED)") == 2, out_bad
                assert "TIDAK DITEMUKAN" in out_bad and "3 fatal" in out_bad, out_bad

                # c) Judul yang salah tetap perlu diperiksa walau nama peneliti dan tahun cocok.
                #    Tahun pada kemunculan kedua tidak boleh tertutupi tahun benar pada kemunculan pertama.
                kasus = uji_dir / "naskah.txt"
                kasus.write_text("An Entirely Different Title. Ali Hassan. 2021. doi:10.5555/cr1\n"
                                 "Islamic Finance Governance. Ali Hassan. 1995. doi:10.5555/cr1\n"
                                 "Retraction Notice. doi:10.5555/notice\n"
                                 "doi:10.5555/registered\n"
                                 "doi:10.5555/offline\n", encoding="utf8")
                kode, out_sebagian, err = _cli("dirasat-cek", uji_dir.name)
                assert kode == 2, out_sebagian + err
                assert "baris 1: PERIKSA METADATA (judul" in out_sebagian, out_sebagian
                assert "baris 2: TIDAK COCOK (tahun di naskah (1995" in out_sebagian, out_sebagian
                assert "baris 3 [10.5555/notice]: ID DITEMUKAN" in out_sebagian, out_sebagian
                assert "baris 4 [10.5555/registered]: DOI TERDAFTAR" in out_sebagian, out_sebagian
                assert "baris 5 [10.5555/offline]: GAGAL MEMERIKSA" in out_sebagian and "0 fatal" in out_sebagian, out_sebagian
                kasus.write_text("doi:10.5555/offline\n", encoding="utf8")
                kode, out_offline, err = _cli("dirasat-cek", uji_dir.name)
                assert kode == 2 and "1 gagal memeriksa" in out_offline, out_offline + err

                kasus.write_text("دراسة الفقه المالي المعاصر، أحمد محمد، 1442هـ"
                                 "[^doi:10.5555/alias <<luar|W100000.pdf|1>>]\n", encoding="utf8")
                kode, out_alias, err = _cli("dirasat-cek", uji_dir.name)
                assert kode == 0 and "beberapa pengenal" not in out_alias and "0 perlu dicek" in out_alias, out_alias + err

                # d) Rujukan berikutnya boleh ringkas (nama keluarga + judul pokok), dua penelitian di dua catatan kaki
                #    satu baris dinilai sendiri-sendiri, dan tahun cetak PDF menang atas katalog yang beda setahun.
                #    Nama, judul, atau tahun yang memang salah tetap ditandai; rujukan pertama tetap harus utuh.
                import pymupdf
                doc = pymupdf.open()
                doc.new_page().insert_text((50, 100), "Ife Journal of ICT, Volume 9, 2025\nReceived: 3 May 2024\n"
                                                      "As of December 2024, 160 ATMs were installed")
                doc.save(uji_dir / "W6000001.pdf")
                doc.close()
                hoo = "Hoo & Ibrahim, Biometric Attendance Tracking System for Education"
                lawal = "Lawal & Aina, A Mobile Fingerprint Attendance System for University Lectures"
                kasus.write_text(
                    "ودراسة Hoo[^انظر: Hoo, Seng Chun & Ibrahim, Haidi, Biometric Attendance Tracking System for "
                    "Education: A Survey on Hardware, 2019, p. 1. <<luar|W5000001.pdf|1>>] ودراسة Lawal[^انظر: Lawal, "
                    "Aderonke R. & Aina, Segun, A Mobile Fingerprint Attendance System for University Lectures, vol. 9, "
                    "2025, p. 27. <<luar|W6000001.pdf|1>>].\n"
                    f"وفيه[^انظر: {hoo}, p. 4. <<luar|W5000001.pdf|4>>].\n"
                    f"وفيه[^انظر: {lawal}, p. 34. <<luar|W6000001.pdf|1>>].\n"
                    "وفيه[^انظر: Smith & Jones, Biometric Attendance Tracking System for Education, p. 5. "
                    "<<luar|W5000001.pdf|5>>].\n"
                    "وفيه[^انظر: Hoo & Ibrahim, Cloud Security for Hospitals, p. 5. <<luar|W5000001.pdf|5>>].\n"
                    f"وفيه[^انظر: {lawal}, 2021, p. 3. <<luar|W6000001.pdf|1>>].\n"
                    f"وفيه[^انظر: {lawal}, 2024, p. 3. <<luar|W6000001.pdf|1>>].\n"
                    "وفيه[^انظر: Aderonke & Faith, A Mobile Fingerprint Attendance System for University Lectures, "
                    "p. 3. <<luar|W6000001.pdf|1>>].\n", encoding="utf8")
                kode, out_ringkas, err = _cli("dirasat-cek", uji_dir.name)
                assert kode == 2, out_ringkas + err
                for n in (1, 2, 3):
                    assert f"! baris {n}:" not in out_ringkas, out_ringkas
                assert "baris 4: PERIKSA METADATA (nama peneliti" in out_ringkas, out_ringkas
                assert "baris 5: PERIKSA METADATA (judul" in out_ringkas, out_ringkas
                assert "baris 6: TIDAK COCOK (tahun di naskah (2021" in out_ringkas, out_ringkas
                # Tahun di tanggal terima dan kalimat isi PDF bukan tahun terbit; nama depan bukan nama keluarga.
                assert "baris 7: TIDAK COCOK (tahun di naskah (2024" in out_ringkas, out_ringkas
                assert "baris 8: PERIKSA METADATA (nama peneliti" in out_ringkas, out_ringkas
                assert "5 perlu dicek" in out_ringkas, out_ringkas
                kasus.write_text(f"وفيه[^انظر: {hoo}, p. 4. <<luar|W5000001.pdf|4>>].\n"
                                 f"وفيه[^انظر: {hoo}, p. 5. <<luar|W5000001.pdf|5>>].\n", encoding="utf8")
                kode, out_pertama, err = _cli("dirasat-cek", uji_dir.name)
                assert "baris 1: PERIKSA METADATA (judul" in out_pertama, out_pertama
                assert "! baris 2:" not in out_pertama and "1 perlu dicek" in out_pertama, out_pertama

                # e) Tahun kejadian di matan dan catatan kaki kitab lain tidak bocor ke penilaian penelitian,
                #    dua penelitian dipisah «؛» dalam satu catatan kaki dinilai masing-masing, «المرجع السابق»
                #    di rujukan ulang diterima, rumus {E:…} tidak dianggap teks Inggris, dan baris #R berpenulis
                #    Arab + judul Inggris di dalam kurung tidak menuntut nama peneliti Latin.
                kasus.write_text(
                    "دراسة الفقه المالي المعاصر، أحمد محمد، 2020م[^انظر: دراسة الفقه المالي المعاصر، أحمد محمد، ص1. <<luar|W2741809807.pdf|1>>].\n"
                    "وقعت أحداث تاريخية عام 1990م وعام 2004م[^انظر: كتاب تراثي، 2001م. <<11223|-|4>>] ثم[^انظر: دراسة الفقه المالي المعاصر، أحمد محمد، ص5. <<luar|W2741809807.pdf|5>>].\n"
                    "وتواصلت الأحداث عام 2014م[^انظر: المرجع السابق، ص9. <<luar|W2741809807.pdf|9>>].\n"
                    "وفي المقارنة[^انظر: دراسة الفقه المالي المعاصر، أحمد محمد، ص3 <<luar|W2741809807.pdf|3>>؛ "
                    "Hoo & Ibrahim, Biometric Attendance Tracking System for Education: A Survey on Hardware, 2019, p. 2 <<luar|W5000001.pdf|2>>.].\n"
                    "#J النسبة | {E:\\text{الربح} \\times 10\\%} | قول معاصر[^انظر: دراسة عن الحوكمة المالية، علي حسن، ص4. <<luar|W6000001.pdf|4>>]\n"
                    "**حسن**، علي. __حوكمة التمويل الإسلامي (Islamic Finance Governance)__. 2021م (DOI: 10.5555/cr1).\n",
                    encoding="utf8",
                )
                kode, out_e, err = _cli("dirasat-cek", uji_dir.name)
                assert kode == 0 and "0 perlu dicek" in out_e and "0 fatal" in out_e, out_e + err
            finally:
                import shutil
                shutil.rmtree(uji_dir, ignore_errors=True)

    print("lolos uji dirasat (tanggal, bahasa, urut kolam, biblio, dedup judul, info W/DOI, fallback OA PDF, dirasat-cek, keamanan)")


if __name__ == "__main__":
    utama()
