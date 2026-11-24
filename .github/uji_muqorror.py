# SPDX-License-Identifier: AGPL-3.0-or-later
"""Perintah muqorror mempertahankan scan, catatan sambung, tautan, dan PDF lama."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf

from bantu import REPO, bahts


def utama(folder):
    kitab = folder / "kitab asli.pdf"
    with pymupdf.open() as pdf:
        for i in range(5):
            p = pdf.new_page()
            p.insert_text((72, 86), f"Kitab {i + 1}")
            if i == 2:
                p.set_rotation(90)
        pdf.save(kitab)
    asli = kitab.read_bytes()
    baris = [f"Baris {i:02d}. Uraian dalam lembar catatan." for i in range(45)]
    data = {
        "judul": "Muqorror uji",
        "kitab": kitab.name,
        "sumber": [{"id": "P01", "judul": "Rekaman satu", "tautan": "https://example.org/rekaman"}],
        "bagian": [
            {"judul": "Bab satu", "halaman": [[1, 1], [3, 4]], "catatan": [
                {"judul": "شَرْحُ الإِعْرَابِ", "sumber": ["P01"], "butir": ["مَا قَامَ إِلَّا زَيْدٌ.", *baris]},
            ]},
            {"judul": "Bab dua", "halaman": [[5, 5]], "catatan": []},
        ],
    }
    rencana = folder / "rencana.json"
    hasil = folder / "hasil.pdf"
    rencana.write_text(json.dumps(data, ensure_ascii=False), encoding="utf8")
    r = bahts(REPO, "muqorror", rencana, hasil)
    assert r.returncode == 0 and "PDF=" in r.stdout, r
    assert kitab.read_bytes() == asli
    with pymupdf.open(kitab) as asal, pymupdf.open(hasil) as jadi:
        daftar = {judul: halaman for _, judul, halaman in jadi.get_toc()}
        p_awal = daftar["Bab satu"] - 1
        p_akhir = daftar["Bab dua"] - 1
        for p_asal, p_jadi in zip((0, 2, 3, 4), (p_awal, p_awal + 1, p_awal + 2, p_akhir)):
            assert asal[p_asal].get_pixmap().digest == jadi[p_jadi].get_pixmap().digest
        assert p_akhir > p_awal + 4
        catatan = "".join(jadi[i].get_text() for i in range(p_awal + 3, p_akhir))
        for i in range(len(baris)):
            assert f"Baris {i:02d}." in catatan, i
        assert any("Aref Ruqaa" in f[3] for f in jadi[p_awal + 3].get_fonts())
        tujuan = {tautan["page"] for tautan in jadi[0].get_links() if tautan["kind"] == pymupdf.LINK_GOTO}
        assert {p_awal, p_awal + 3, p_akhir, daftar["Daftar sumber kelas"] - 1} <= tujuan, tujuan
        assert any(link.get("uri") == "https://example.org/rekaman" for link in jadi[-1].get_links())

    lama = hasil.read_bytes()
    data["bagian"][0]["catatan"][0]["sumber"] = ["P02"]
    rencana.write_text(json.dumps(data, ensure_ascii=False), encoding="utf8")
    r = bahts(REPO, "muqorror", rencana, hasil)
    assert r.returncode and "belum didaftar: P02" in r.stderr, r
    assert hasil.read_bytes() == lama

    data["bagian"][0]["catatan"][0]["sumber"] = ["P01"]
    rencana.write_text(json.dumps(data, ensure_ascii=False), encoding="utf8")
    r = bahts(REPO, "muqorror", rencana, kitab)
    assert r.returncode and "tidak boleh menimpa kitab" in r.stderr, r
    assert kitab.read_bytes() == asli


if __name__ == "__main__":
    with TemporaryDirectory(prefix="uji-muqorror-") as d:
        utama(Path(d))
    print("muqorror: halaman asli, catatan, tautan, dan perlindungan berkas lolos")
