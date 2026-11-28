# SPDX-License-Identifier: AGPL-3.0-or-later
"""Penghitung faraid `#D مواريث` (mesin/sisipan/mawarith.hitung) terhadap masalah yang jawabannya baku di kitab faraid:
bagian tiap waris dari harta, أصل المسألة، العول/الرد، التصحيح, dan masalah khilaf yang harus ditolak (bukan ditebak).
Penghitungnya fungsi murni yang menentukan angka di tabel yang dicetak, jadi diuji langsung per kasus; jalur `cek`
(GAGAL di baris kepala) diuji `uji_sisipan`."""
import sys, unittest
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mesin"))
from sisipan.mawarith import BelumDidukung, hitung

# (waris, {waris: bagian dari harta}, (أصل المسألة, sesudah عول/رد, hal, pengali تصحيح) atau None)
KASUS = [
    ({"زوجة": 1, "بنت": 1, "أم": 1, "عم شقيق": 1}, {"زوجة": "1/8", "بنت": "1/2", "أم": "1/6", "عم شقيق": "5/24"}, (24, 24, "", 1)),
    ({"بنت": 2, "بنت ابن": 1}, {"بنت": "1", "بنت ابن": "0"}, (3, 2, "رد", 1)),
    ({"بنت": 1, "أخ لأم": 1}, {"بنت": "1", "أخ لأم": "0"}, None),
    ({"زوج": 1, "أخت شقيقة": 2, "أم": 1}, {"زوج": "3/8", "أخت شقيقة": "1/2", "أم": "1/8"}, (6, 8, "عول", 1)),
    ({"زوجة": 1, "بنت": 2, "أب": 1, "أم": 1}, {"زوجة": "3/27", "بنت": "16/27", "أب": "4/27", "أم": "4/27"}, (24, 27, "عول", 1)),
    ({"زوج": 1, "أم": 1, "أب": 1}, {"زوج": "1/2", "أم": "1/6", "أب": "1/3"}, (6, 6, "", 1)),
    ({"زوجة": 1, "أم": 1, "أب": 1}, {"زوجة": "1/4", "أم": "1/4", "أب": "1/2"}, (4, 4, "", 1)),
    ({"بنت": 1, "أم": 1}, {"بنت": "3/4", "أم": "1/4"}, (6, 4, "رد", 1)),
    ({"زوجة": 1, "بنت": 1, "أم": 1}, {"زوجة": "1/8", "بنت": "21/32", "أم": "7/32"}, (24, 32, "رد", 1)),
    ({"ابن": 1, "بنت": 1}, {"ابن": "2/3", "بنت": "1/3"}, None),
    ({"بنت": 3, "عم شقيق": 1}, {"بنت": "2/3", "عم شقيق": "1/3"}, (3, 3, "", 3)),
    ({"زوجة": 1, "ابن": 2, "بنت": 3, "أب": 1}, {"زوجة": "1/8", "أب": "1/6", "ابن": "17/42", "بنت": "17/56"}, (24, 24, "", 7)),
    ({"بنت": 1, "بنت ابن": 1, "عم شقيق": 1}, {"بنت": "1/2", "بنت ابن": "1/6", "عم شقيق": "1/3"}, (6, 6, "", 1)),
    ({"بنت": 2, "بنت ابن": 1, "ابن ابن": 1}, {"بنت": "2/3", "ابن ابن": "2/9", "بنت ابن": "1/9"}, None),
    ({"بنت": 1, "أخت شقيقة": 1, "أخ لأب": 1}, {"بنت": "1/2", "أخت شقيقة": "1/2", "أخ لأب": "0"}, None),
    ({"أخت شقيقة": 1, "أخت لأب": 1, "عم شقيق": 1}, {"أخت شقيقة": "1/2", "أخت لأب": "1/6", "عم شقيق": "1/3"}, None),
    ({"أخت شقيقة": 2, "أخت لأب": 1, "أخ لأب": 1}, {"أخت شقيقة": "2/3", "أخ لأب": "2/9", "أخت لأب": "1/9"}, None),
    ({"أخ لأم": 2, "أم": 1, "أخ شقيق": 1}, {"أم": "1/6", "أخ لأم": "1/3", "أخ شقيق": "1/2"}, None),
    ({"بنت": 1, "أب": 1}, {"بنت": "1/2", "أب": "1/2"}, None),
    ({"أب": 1, "ابن": 1, "أم": 1}, {"أب": "1/6", "أم": "1/6", "ابن": "2/3"}, None),
    ({"أب": 1, "جدة لأب": 1, "ابن": 1}, {"جدة لأب": "0", "أب": "1/6", "ابن": "5/6"}, None),
    ({"جدة لأب": 1, "جدة لأم": 1, "ابن": 1}, {"جدة لأب": "1/12", "جدة لأم": "1/12", "ابن": "5/6"}, None),
    ({"ابن": 1, "جد": 1, "أخ لأم": 1}, {"جد": "1/6", "ابن": "5/6", "أخ لأم": "0"}, None),
    ({"زوج": 1, "بنت": 1, "بنت ابن": 1, "أب": 1, "أم": 1},
     {"زوج": "3/15", "بنت": "6/15", "بنت ابن": "2/15", "أب": "2/15", "أم": "2/15"}, (12, 15, "عول", 1)),
]
KHILAF = [{"جد": 1, "أخ شقيق": 1}, {"جد": 1, "أخت لأب": 2, "زوجة": 1},
          {"زوج": 1, "أم": 1, "أخ لأم": 2, "أخ شقيق": 1}, {"زوج": 1}, {"زوجة": 2}]


class Mawarith(unittest.TestCase):
    def test_masalah_baku(self):
        for waris, harap, pokok in KASUS:
            with self.subTest(waris=waris):
                h = hitung(waris)
                bagian = {b.kunci: b.bagian for b in h.baris}
                self.assertEqual(bagian, {k: F(v) for k, v in harap.items()})
                self.assertEqual(sum(bagian.values()), 1)
                if pokok:
                    self.assertEqual((h.asl, h.akhir, h.hal, h.tashih), pokok)
                for b in h.baris:  # التصحيح: saham tiap orang utuh
                    self.assertEqual((h.saham(b) / b.jumlah).denominator, 1, b)

    def test_khilaf_ditolak(self):
        for waris in KHILAF:
            with self.subTest(waris=waris), self.assertRaises(BelumDidukung):
                hitung(waris)


if __name__ == "__main__":
    unittest.main(verbosity=2)
