# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regresi jaringan: kunci layanan tidak boleh ikut ke asal lain saat dialihkan."""
import contextlib, io, json, runpy, sys, threading, unittest, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mesin"))
import dirasat, jaringan

KUNCI = "KUNCI-PALSU-UJI"
BEARER = "Bearer " + KUNCI


class AlihJaringan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.permintaan = []

        class Jawaban(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                cls.permintaan.append((self.server.server_port, self.path, self.headers.get("Authorization")))
                tujuan = cls.alih.get(self.path.split("?", 1)[0])
                if tujuan:
                    self.send_response(302)
                    self.send_header("Location", tujuan)
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.end_headers()
                    if self.path == "/hasil":
                        self.wfile.write(json.dumps({"meta": {"count": 1}, "results": [{
                            "id": "https://openalex.org/W1", "title": "دراسة اختبار", "authorships": [],
                            "publication_year": 2026, "type": "article"}]}).encode("utf8"))
                    else:
                        self.wfile.write(b"ok")

        cls.utama = ThreadingHTTPServer(("127.0.0.1", 0), Jawaban)
        cls.lain = ThreadingHTTPServer(("127.0.0.1", 0), Jawaban)
        cls.url = f"http://127.0.0.1:{cls.utama.server_port}"
        cls.url_lain = f"http://127.0.0.1:{cls.lain.server_port}"
        cls.alih = {"/sama": cls.url + "/akhir", "/port": cls.url_lain + "/akhir",
                    "/host": f"http://localhost:{cls.utama.server_port}/akhir",
                    "/rantai": cls.url + "/port", "/cli": cls.url_lain + "/hasil"}
        cls.utas = [threading.Thread(target=s.serve_forever, daemon=True) for s in (cls.utama, cls.lain)]
        for t in cls.utas:
            t.start()

    @classmethod
    def tearDownClass(cls):
        for s in (cls.utama, cls.lain):
            s.shutdown()
            s.server_close()
        for t in cls.utas:
            t.join()

    def setUp(self):
        self.permintaan.clear()

    def buka(self, jalur):
        # Jalur asli dirasat -> jaringan.buka. Hanya alamat layanan dan kuncinya
        # yang ditiru; pengalihan benar-benar lewat dua peladen HTTP lokal.
        asli = dirasat.buka

        def lokal(url, **kw):
            return asli(url.replace("https://api.openalex.org", self.url), **kw)

        with patch.object(dirasat, "_kunci", return_value=KUNCI), \
                patch.object(dirasat, "buka", side_effect=lokal), \
                patch.dict("os.environ", {"no_proxy": "127.0.0.1,localhost"}):
            with dirasat._buka("https://api.openalex.org" + jalur) as r:
                self.assertEqual(r.read(), b"ok")
        self.assertEqual(self.permintaan[0][2], BEARER)

    def test_asal_sama_tetap_memakai_kunci(self):
        self.buka("/sama")
        self.assertEqual(self.permintaan[-1][2], BEARER)

    def test_port_lain_tanpa_kunci(self):
        self.buka("/port")
        self.assertIsNone(self.permintaan[-1][2])

    def test_host_lain_tanpa_kunci(self):
        self.buka("/host")
        self.assertIsNone(self.permintaan[-1][2])

    def test_rantai_pengalihan_tidak_membawa_kunci_ke_asal_lain(self):
        self.buka("/rantai")
        self.assertEqual(self.permintaan[1][2], BEARER)
        self.assertIsNone(self.permintaan[-1][2])

    def test_cli_dirasat_tetap_mencetak_hasil_tanpa_membocorkan_kunci(self):
        class Keluaran(io.StringIO):
            def reconfigure(self, **kw):
                pass

        asli = dirasat.buka

        def lokal(url, **kw):
            return asli(url.replace("https://api.openalex.org", self.url), **kw)

        skrip = Path(jaringan.__file__).with_name("bahts.py")
        keluar = Keluaran()
        with patch.object(sys, "argv", [str(skrip), "dirasat", "اختبار"]), \
                patch.object(dirasat, "OPENALEX", "https://api.openalex.org/cli"), \
                patch.object(dirasat, "SUMBER", (("OpenAlex, menurut kata", dirasat._kata, False),)), \
                patch.object(dirasat, "_kunci", return_value=KUNCI), \
                patch.object(dirasat, "buka", side_effect=lokal), \
                patch.dict("os.environ", {"no_proxy": "127.0.0.1,localhost"}), \
                contextlib.redirect_stdout(keluar):
            runpy.run_path(str(skrip), run_name="__main__")
        self.assertIn("1 penelitian cocok", keluar.getvalue())
        self.assertIn("دراسة اختبار", keluar.getvalue())
        self.assertNotIn(KUNCI, keluar.getvalue())
        self.assertEqual(self.permintaan[0][2], BEARER)
        self.assertIsNone(self.permintaan[-1][2])


class AlihProtokol(unittest.TestCase):
    def alih(self, awal, akhir):
        # Transport TLS tidak ditiru dengan sertifikat longgar. Jalankan pembuat
        # permintaan pengalihan asli yang juga dipakai peladen lokal di atas.
        req = urllib.request.Request(awal, headers={"Authorization": BEARER})
        return jaringan._AlihAman().redirect_request(req, None, 302, "Found", {}, akhir)

    def test_https_ke_http_tanpa_kunci(self):
        req = self.alih("https://api.openalex.org:443/a", "http://api.openalex.org:443/b")
        self.assertIsNone(req.get_header("Authorization"))

    def test_port_bawaan_dan_huruf_host_tetap_asal_sama(self):
        req = self.alih("https://API.OPENALEX.ORG/a", "https://api.openalex.org:443/b")
        self.assertEqual(req.get_header("Authorization"), BEARER)


class MaknaSaja(unittest.TestCase):
    """Pencarian makna selalu mengembalikan sesuatu, juga untuk kata sampah: tanpa hasil menurut kata, ada peringatan."""
    def cari(self, kata_cocok):
        w = {"judul": "xcvz", "peneliti": [], "tahun": 2026, "jenis": "report", "wadah": None, "doi": None,
             "tautan": None, "pdf": None, "ringkasan": ""}
        sumber = (("kata", lambda *a: (kata_cocok, [dict(w, judul="kata", doi="10.1/a")] * bool(kata_cocok), None), False),
                  ("makna", lambda *a: (45, [w], None), True), ("DOAJ", lambda *a: (0, [], None), False))
        keluar = io.StringIO()
        with patch.object(dirasat, "SUMBER", sumber), contextlib.redirect_stdout(keluar):
            dirasat.cari("qwxzvqwxzv")
        return keluar.getvalue()

    def test_tanpa_hasil_menurut_kata_ada_peringatan(self):
        out = self.cari(0)
        self.assertIn("PERINGATAN: hasil di bawah ini hanya MIRIP MAKNANYA", out)
        self.assertIn("PERINGATAN: semua hasil di atas hanya MIRIP MAKNANYA", out)
        self.assertLess(out.index("PERINGATAN"), out.index("xcvz"))

    def test_ada_hasil_menurut_kata_tanpa_peringatan(self):
        self.assertNotIn("PERINGATAN", self.cari(1))


if __name__ == "__main__":
    unittest.main()
