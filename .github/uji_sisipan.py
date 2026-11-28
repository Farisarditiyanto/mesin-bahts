# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sisipan #D lewat pintu pemakai (`bahts.py cek`): data yang salah = GAGAL di barisnya; contoh tiap jenis di `tanda`
tergambar jadi PNG ber-DPI di <folder>/.sisipan (kalau Node.js + Chrome/Edge ada); PNG yang sudah ada cukup untuk `cek`
tanpa Node.js; tanpa Node.js dan tanpa PNG = GAGAL yang menyebut syaratnya."""
import os, re, sys, tempfile, unittest
from pathlib import Path

from bantu import REPO, SAMPUL_UJI, bahts, salin_mesin

sys.path.insert(0, str(REPO / "mesin"))
import diagram
import pymupdf

KEPALA = "@judul: تجربة الأشكال\n" + SAMPUL_UJI + "@tanpa: pustaka\n#K المقدمة\nفقرة تمهيدية.\n"
DPI = 300


def tanpa_node():
    """PATH tanpa folder yang berisi node/npx: `cek` tidak bisa menggambar."""
    return os.pathsep.join(p for p in os.environ["PATH"].split(os.pathsep)
                           if not (Path(p) / ("npx.cmd" if os.name == "nt" else "npx")).exists())


def galat(keluar):
    """{nomor baris: pesan GAGAL} dari laporan `cek`."""
    return {int(m[1]): m[2] for m in re.finditer(r"^  ✗ baris (\d+): (.*)$", keluar, re.M)}


class Sisipan(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="bahts-uji-sisipan-")
        self.addCleanup(tmp.cleanup)
        self.akar = Path(tmp.name)
        salin_mesin(self.akar, huruf=False)
        self.folder = self.akar / "bahts" / "uji"
        self.folder.mkdir(parents=True)

    def cek(self, isi, env=None):
        (self.folder / "naskah.txt").write_text(KEPALA + isi, encoding="utf8")
        if env:
            lama = os.environ["PATH"]
            os.environ["PATH"] = env
            self.addCleanup(os.environ.__setitem__, "PATH", lama)
        try:
            r = bahts(self.akar, "cek", "bahts/uji", batas=900)
        finally:
            if env:
                os.environ["PATH"] = lama
        self.assertNotIn("Traceback", r.stderr)
        self.assertNotIn("GALAT MESIN", r.stdout)
        return r.stdout

    def test_data_salah_gagal_di_barisnya(self):
        n0 = KEPALA.count("\n")
        isi = ["#D خلاف | ش", "#D قول: أ | الحنفية", "فقرة.",
               "#D قياس | ق", "#D أصل: الخمر | نص | زائد", "#D فرع: النبيذ", "#D علة: الإسكار", "#D حكم: التحريم", "فقرة.",
               "#D شجرة | ش", "#D فرع: أ | ب، ج", "#D فرع: د | هـ", "فقرة.",
               "#D مراتب | م", "#D مرتبة: أ | ب", "#D مرتبة: ج", "#D حكم: 2-3 | x", "فقرة.",
               "#D تعارض | ت", "#D منهج: الجمهور | الجمع", "فقرة.",
               "#D مقاصد | م", "#D ضروريات: أ", "#D لون: أحمر", "فقرة.",
               "#D خلاف | ش", "#D قول: أ | ب", "#D قول: ج | د", "#D راجح: ٣"]
        harus = {1: "paling sedikit dua", 5: "«أصل:» harus berbentuk", 12: "induk «د» belum tertulis",
                 17: "di luar martabat 1-2", 20: "paling sedikit dua langkah", 24: "kunci «لون» tidak dikenal",
                 22: "«#D تحسينيات: …» belum ada", 29: "tidak menunjuk qaul"}
        dapat = galat(self.cek("\n".join(isi) + "\n", env=tanpa_node()))
        self.assertEqual(sorted(dapat), sorted(n0 + n for n in harus), dapat)
        for n, kata in harus.items():
            self.assertIn(kata, dapat[n0 + n])

    def test_contoh_tanda_tergambar_lalu_cukup_tanpa_node(self):
        if not (diagram.npx() and diagram.browser()):
            self.skipTest("perlu Node.js (npx) + Chrome/Edge")
        tanda = bahts(self.akar, "tanda").stdout
        bagian = tanda[tanda.index("\nSisipan #D") + 1:].split("\n\n")[0]  # contoh tiap jenis; paragraf di antaranya
        contoh = "\n".join(b.strip() if b.strip().startswith("#D ") else "فقرة." for b in bagian.splitlines()[1:])
        jumlah = len(re.findall(r"^#D [^:|]+\|", contoh, re.M))
        keluar = self.cek(contoh + "\n")
        self.assertIn("GAGAL: 0", keluar)
        png = sorted((self.folder / ".sisipan").glob("*.png"))
        self.assertEqual(len(png), jumlah)
        self.assertGreaterEqual(jumlah, 6)
        for p in png:  # cetak: ber-DPI, paling lebar = lebar teks, dipotong ke tinta + 3pt, hitam-putih tanpa latar abu-abu
            g = pymupdf.Pixmap(pymupdf.csGRAY, pymupdf.Pixmap(str(p)))
            self.assertEqual(round(pymupdf.Pixmap(str(p)).xres), DPI, p.name)
            self.assertLessEqual(g.width / DPI * 2.54, 15, p.name)
            px = g.samples
            self.assertLess(sum(60 < v < 200 for v in px) / len(px), 0.06, p.name)
            gelap = [i for i, v in enumerate(px) if v < 128]
            kolom = [i % g.width for i in gelap]
            tepi = max(min(kolom), g.width - 1 - max(kolom), gelap[0] // g.width, g.height - 1 - gelap[-1] // g.width)
            self.assertLessEqual(tepi / DPI * 2.54, 0.3, p.name)
        waktu = {p: p.stat().st_mtime_ns for p in png}
        # PNG sudah ada: tanpa Node.js tetap lolos dan tidak digambar ulang
        self.assertIn("GAGAL: 0", self.cek(contoh + "\n", env=tanpa_node()))
        self.assertEqual({p: p.stat().st_mtime_ns for p in png}, waktu)
        # data berubah tanpa Node.js = GAGAL yang menyebut syaratnya, di baris kepala sisipannya
        ubah = contoh.replace("الإسكار", "الإسكار والتغطية")
        dapat = galat(self.cek(ubah + "\n", env=tanpa_node()))
        self.assertEqual(len(dapat), 1, dapat)
        self.assertIn("belum tergambar: Node.js", next(iter(dapat.values())))


if __name__ == "__main__":
    unittest.main(verbosity=2)
