"""Bangun skill/bahts.zip (skill untuk Claude web) dari mesin/ dan skill/SKILL.md:  python skill/bangun.py

Tidak ada yang ditulis ulang di sini: aturan penulisan diambil dari AGENTS.md, daftar tanda dari olah.py,
kerangka naskah dari naskah_baru.txt dan profil dari format.json (data pribadi dibuang). Jalankan lagi tiap salah satunya berubah.
"""
import json, re, sys, zipfile
from pathlib import Path

SKILL = Path(__file__).parent
AKAR = SKILL.parent
MESIN = AKAR / "mesin"
sys.path.insert(0, str(MESIN))
import bahts, olah

# yang tidak ikut: perakit Word dan sampul dosen (hanya untuk Windows + Word)
ISI_MESIN = sorted(p for p in MESIN.iterdir() if p.is_file() and p.name not in ("rakit.ps1", "sampul.doc"))


def aturan():
    """Bagian «Aturan penulisan» dari AGENTS.md, tanpa judulnya."""
    teks = (AKAR / "AGENTS.md").read_text(encoding="utf8")
    return re.search(r"^## Aturan penulisan[^\n]*\n(.*?)(?=^## )", teks, re.S | re.M).group(1).strip()


def kerangka():
    """naskah_baru.txt tanpa data pribadi: tanda wajib selain judul dikosongkan supaya `cek` menagihnya."""
    kosong = "|".join(k for k in olah.WAJIB if k != "judul")
    return re.sub(rf"^@({kosong}):.*$", r"@\1:", (MESIN / "naskah_baru.txt").read_text(encoding="utf8"), flags=re.M)


def profil():
    """format.json tanpa catatan `_sumber` (catatan dalam untuk pemilik mesin; memuat nama orang)."""
    data = json.loads((MESIN / "format.json").read_text(encoding="utf8"))
    return json.dumps({k: {a: b for a, b in v.items() if a != "_sumber"} for k, v in data.items()}, ensure_ascii=False, indent=2)


def tulis(z, nama, isi):
    info = zipfile.ZipInfo("bahts/" + nama, (2026, 1, 1, 0, 0, 0))  # tanggal tetap: zip hanya berubah kalau isinya berubah
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, isi)


if __name__ == "__main__":
    skill = (SKILL / "SKILL.md").read_text(encoding="utf8").replace("{{ATURAN}}", aturan()).replace("{{TANDA}}", bahts.tanda())
    keluar = SKILL / "bahts.zip"
    with zipfile.ZipFile(keluar, "w") as z:
        tulis(z, "SKILL.md", skill)
        khusus = {"naskah_baru.txt": kerangka, "format.json": profil}
        for p in ISI_MESIN:
            tulis(z, "mesin/" + p.name, khusus[p.name]() if p.name in khusus else p.read_bytes())
    print(f"Jadi: skill/{keluar.name} ({keluar.stat().st_size / 1e6:.1f} MB, {len(ISI_MESIN) + 1} berkas)")
