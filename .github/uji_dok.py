# SPDX-License-Identifier: AGPL-3.0-or-later
"""Penjaga struktural dokumentasi dan konfigurasi:
1. `dok/mutamad.md` terurai lengkap oleh `cek_sumber.mutamad()` untuk keempat mazhab, dan cocok dengan tabel bagiannya;
2. Seluruh tautan markdown dan path repo ber-backtick (`dok/…`, `.github/…`, `mesin/…`, `contoh/…`) di `AGENTS.md`,
   `dok/*.md`, dan `README*.md` menunjuk berkas/folder yang benar-benar ada;
3. Seluruh profil di `mesin/format.json` hanya memakai kunci yang dikenal `olah.py` (`BAWAAN_FORMAT`, `IKUT_FORMAT`,
   `_sumber`) dengan tipe dan nilai yang sah.
"""
import json, re, sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "mesin"))
import cek_sumber, olah

MAZHAB = ("حنفي", "مالكي", "شافعي", "حنبلي")
WAJIB_FORMAT = {"huruf", "matan", "catatan", "judul", "catatan_ulang_tiap_halaman"}
SAH_FORMAT = WAJIB_FORMAT | {"_sumber"} | set(olah.BAWAAN_FORMAT) | set(olah.IKUT_FORMAT)
TEKS_FORMAT = {"_sumber", "huruf", "huruf_judul"}
BOOL_FORMAT = {"catatan_ulang_tiap_halaman", "mulakhas_berjarak"}
NON_NEGATIF = {"jarak_paragraf", "jarak_judul", "jarak_sebelum_sub"}
BERKAS_DOK = lambda: [AKAR / "AGENTS.md", *sorted((AKAR / "dok").glob("*.md")),
                      AKAR / "README.md", AKAR / "README.id.md", AKAR / "README.ar.md"]
JANGAN_ADA_DI_DOK = {"mesin/_tmp", "mesin/UthmanicHafs_V22.ttf"}
JALUR_BACKTICK = re.compile(r"(?<![A-Za-z0-9_./-])((?:dok|\.github|mesin|contoh)/[^\s,;:)'\"<>`]+)")
TAUTAN_MD = re.compile(r"\]\(([^)\s]+)\)|src=\"([^\"]+)\"")


def cek_mutamad():
    hasil = cek_sumber.mutamad()
    assert set(hasil) == set(MAZHAB), f"mazhab mutamad.md tidak lengkap: {sorted(hasil)}"
    teks = (AKAR / "dok" / "mutamad.md").read_text(encoding="utf8")
    for mz in MAZHAB:
        ids = hasil[mz]
        assert ids and all(isinstance(x, int) and x > 0 for x in ids), f"ID mazhab {mz} tidak sah: {ids}"
        m = re.search(rf"^## {mz}\n(.*?)(?=^## |\Z)", teks, re.M | re.S)
        assert m, f"bagian «## {mz}» hilang di dok/mutamad.md"
        tabel_ids = {int(x) for x in re.findall(r"^\| (\d+) \|", m.group(1), re.M)}
        assert tabel_ids == ids, f"dok/mutamad.md {mz}: tabel ringkas {sorted(ids)} != bagian {sorted(tabel_ids)}"


def _resolusi(berkas, jalur):
    jalur = jalur.split("#", 1)[0]
    if not jalur:
        return True
    if berkas.parent == AKAR:
        return (AKAR / jalur).exists()
    return (berkas.parent / jalur).exists() or (AKAR / jalur).exists()


def cek_tautan_dan_path():
    salah = []
    for berkas in BERKAS_DOK():
        teks = berkas.read_text(encoding="utf8")
        rel = berkas.relative_to(AKAR).as_posix()
        for t1, t2 in TAUTAN_MD.findall(teks):
            tujuan = t1 or t2
            if tujuan.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if not _resolusi(berkas, tujuan):
                salah.append(f"{rel}: tautan rusak «{tujuan}»")
        for isi in re.findall(r"`([^`\n]+)`", teks):
            for tok in JALUR_BACKTICK.findall(isi):
                if any(c in tok for c in "<>{}…") or tok.rstrip("/") in JANGAN_ADA_DI_DOK:
                    continue
                if "*" in tok:
                    if not any(AKAR.glob(tok)):
                        salah.append(f"{rel}: pola path `{tok}` tidak cocok berkas mana pun")
                elif not (AKAR / tok).exists():
                    salah.append(f"{rel}: path repo `{tok}` tidak ditemukan")
    assert not salah, "\n".join(salah)


def cek_format_json():
    profil_semua = json.loads((AKAR / "mesin" / "format.json").read_text(encoding="utf8"))
    assert isinstance(profil_semua, dict) and profil_semua, "format.json kosong"
    for nama, p in profil_semua.items():
        assert isinstance(p, dict), f"profil {nama} bukan objek"
        asing = set(p) - SAH_FORMAT
        assert not asing, f"format.json[{nama}] memakai kunci tak dikenal: {sorted(asing)}"
        kurang = WAJIB_FORMAT - set(p)
        assert not kurang, f"format.json[{nama}] kurang kunci wajib: {sorted(kurang)}"
        for k, v in p.items():
            if k in TEKS_FORMAT:
                assert isinstance(v, str) and v.strip(), f"format.json[{nama}].{k} harus teks tak kosong: {v!r}"
            elif k in BOOL_FORMAT:
                assert isinstance(v, bool), f"format.json[{nama}].{k} harus boolean: {v!r}"
            else:
                assert not isinstance(v, bool) and isinstance(v, (int, float)), f"format.json[{nama}].{k} harus angka: {v!r}"
                assert (v >= 0 if k in NON_NEGATIF else v > 0), f"format.json[{nama}].{k} di luar batas: {v!r}"
        cetak = olah.format_cetak(p)
        assert set(cetak) - {"_sumber"} == SAH_FORMAT - {"_sumber"}, f"format_cetak({nama}) tidak lengkap: {sorted(cetak)}"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cek_mutamad()
    cek_tautan_dan_path()
    cek_format_json()
    n_profil = len(json.loads((AKAR / "mesin" / "format.json").read_text(encoding="utf8")))
    print(f"lolos uji dok & konfigurasi: 4 mazhab mutamad, {len(BERKAS_DOK())} berkas dok/README, {n_profil} profil format.json")


if __name__ == "__main__":
    main()
