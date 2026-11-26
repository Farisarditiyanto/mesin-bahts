# SPDX-License-Identifier: AGPL-3.0-or-later
"""Uji perintah `ubah <folder> [pembanding]` (diff revisi & konservasi token) lewat pintu CLI (`bahts.py`)."""
import hashlib, os, subprocess, sys, tempfile
from pathlib import Path
from bantu import bahts, salin_mesin

sys.stdout.reconfigure(encoding="utf8")
sys.stderr.reconfigure(encoding="utf8")


def utama():
    with tempfile.TemporaryDirectory(prefix="bahts-revisi-") as t:
        akar = Path(t)
        salin_mesin(akar, ("_meta", "11223"), huruf=False)
        f = akar / "uji"
        f.mkdir()

        lama = (
            "@judul: عنوان أول\n"
            "@nama: طالب\n"
            "#K المقدمة\n"
            "الحمد لله {Q:1:2}، وبلغت النسبة 25% في ٧ حالات.\n"
            "وهذه المسألة تجوز بشرط أن تكون خالية من الغرر، إلا إذا دعت الحاجة على الراجح[^انظر: رسالة، ص5. <<11223|-|5>>].\n"
            "#E x = y + 1\n"
            "والمعادلة {E:\\frac{a}{b}} ثابتة.\n"
            "#K الخاتمة\n"
            "تم البحث.\n"
        )
        # 1. Naskah identik (termasuk beda CRLF vs LF) -> "Tidak ada perubahan", kode 0
        (f / "lama.txt").write_bytes(lama.encode("utf8"))
        (f / "naskah.txt").write_bytes(lama.replace("\n", "\r\n").encode("utf8"))
        r = bahts(akar, "ubah", "uji", "lama.txt")
        assert r.returncode == 0 and "Tidak ada perubahan" in r.stdout, r.stdout + r.stderr

        # 2. Revisi mengubah metadata @, mengganti angka Arab-Indic ٧ -> 7 (harus netral),
        #    menghapus {Q:1:2}, bukti <<11223|-|5>>, rumus #E & {E:...}, angka 25%, dan syarat/qayd fikih,
        #    serta menambah bukti baru dan syarat «ما لم».
        baru = (
            "@judul: عنوان معدل بعد المراجعة\n"
            "@nama: طالب\n"
            "#K المقدمة\n"
            "الحمد لله، في 7 حالات فقط.\n"
            "وهذه المسألة تجوز ما لم تفض إلى ضرر[^انظر: رسالة، ص6. <<11223|-|6>>].\n"
            "والمعادلة ثابتة.\n"
            "#K الخاتمة\n"
            "تم البحث.\n"
        )
        (f / "naskah.txt").write_text(baru, encoding="utf8")
        r = bahts(akar, "ubah", "uji", "lama.txt")
        out = r.stdout
        assert r.returncode == 0, out + r.stderr
        assert "Baris berubah:" in out and 'bukti "uji"' in out, out
        assert "Token HILANG" in out, out
        assert "<<11223|-|5>>" in out, out
        assert "{Q:1:2}" in out, out
        assert "{E:\\frac{a}{b}}" in out, out
        assert "#E x = y + 1" in out, out
        assert "25%" in out, out
        # ٧ -> 7 tidak boleh dilaporkan hilang maupun tambah
        baris_angka = [b for b in out.splitlines() if "angka:" in b]
        assert baris_angka and all("7" not in b for b in baris_angka), out
        # Frasa panjang «إلا إذا» tidak terhitung ganda sebagai «إلا»
        baris_syarat_hilang = next(b for b in out.splitlines() if b.strip().startswith("- syarat/qayd fikih:"))
        assert "إلا إذا" in baris_syarat_hilang and "بشرط أن" in baris_syarat_hilang and "على الراجح" in baris_syarat_hilang, out
        tanpa_frasa = baris_syarat_hilang.replace("إلا إذا", "").replace("بشرط أن", "")
        assert "إلا" not in tanpa_frasa and "بشرط" not in tanpa_frasa, baris_syarat_hilang
        # Token TAMBAH tercatat
        assert "Token TAMBAH:" in out and "<<11223|-|6>>" in out and "ما لم" in out, out

        # 3. Pembanding otomatis dari laporan.txt (NASKAH_SHA256) + mesin/_tmp/revisi/<sha>.txt tanpa argumen ke-2
        sha = hashlib.sha256(lama.encode("utf8")).hexdigest()
        rev_dir = akar / "mesin" / "_tmp" / "revisi"
        rev_dir.mkdir(parents=True, exist_ok=True)
        (rev_dir / f"{sha}.txt").write_text(lama, encoding="utf8")
        (f / "laporan.txt").write_text(f"NASKAH_SHA256={sha}\nHALAMAN=25\n", encoding="utf8")
        r_auto = bahts(akar, "ubah", "uji")
        assert r_auto.returncode == 0, r_auto.stdout + r_auto.stderr
        assert f"rakit terakhir (laporan.txt, {sha[:10]})" in r_auto.stdout, r_auto.stdout
        assert "<<11223|-|5>>" in r_auto.stdout, r_auto.stdout

        # 4. Pembanding tidak ada -> keluar non-nol dengan pesan rapi tanpa Traceback
        (f / "laporan.txt").unlink()
        r_kosong = bahts(akar, "ubah", "uji")
        assert r_kosong.returncode != 0 and "Traceback" not in r_kosong.stderr, r_kosong.stdout + r_kosong.stderr
        assert "Belum ada salinan pembanding" in r_kosong.stderr, r_kosong.stderr

        r_hilang = bahts(akar, "ubah", "uji", "tidak-ada.txt")
        assert r_hilang.returncode != 0 and "Traceback" not in r_hilang.stderr, r_hilang.stdout + r_hilang.stderr
        assert "tidak ditemukan" in r_hilang.stderr, r_hilang.stderr

        # 5. Regresi: {E: tidak tertutup di satu baris tidak boleh menelan atau memotong baris sesudahnya,
        #    dan angka desimal Arab «٣٫٥٪» setara dengan «3.5%».
        lama_e = (
            "@judul: تجربة\n@nama: طالب\n#K المقدمة\n"
            "المعادلة {E:x + 1}.\n"
            "والآية {Q:1:2} بنسبة ٣٫٥٪ على الراجح.\n"
            "نهاية } هنا.\n"
        )
        baru_e = (
            "@judul: تجربة\n@nama: طالب\n#K المقدمة\n"
            "المعادلة {E:x + 1.\n"
            "والآية {Q:1:2} بنسبة 3.5% على الراجح.\n"
            "نهاية } هنا.\n"
        )
        (f / "lama_e.txt").write_text(lama_e, encoding="utf8")
        (f / "naskah.txt").write_text(baru_e, encoding="utf8")
        r_e = bahts(akar, "ubah", "uji", "lama_e.txt")
        assert r_e.returncode == 0, r_e.stdout + r_e.stderr
        assert "{Q:1:2}" not in r_e.stdout and "على الراجح" not in r_e.stdout and "3.5%" not in r_e.stdout, r_e.stdout

        # 6. Regresi: git HEAD fallback pada naskah UTF-8 ber-BOM tidak boleh melaporkan diff palsu
        git_env = {**os.environ, "GIT_AUTHOR_NAME": "u", "GIT_AUTHOR_EMAIL": "u@e",
                   "GIT_COMMITTER_NAME": "u", "GIT_COMMITTER_EMAIL": "u@e"}
        bom_teks = "@judul: دراسة عام 2025 على الراجح\n@nama: طالب\n#K المقدمة\nنص.\n"
        (f / "naskah.txt").write_text(bom_teks, encoding="utf-8-sig")
        subprocess.run(["git", "-C", str(akar), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(akar), "add", "uji/naskah.txt"], check=True)
        subprocess.run(["git", "-C", str(akar), "commit", "-q", "-m", "init"], check=True, env=git_env)
        r_git = bahts(akar, "ubah", "uji")
        assert r_git.returncode == 0 and "Tidak ada perubahan sejak git HEAD" in r_git.stdout, r_git.stdout + r_git.stderr

    print("lolos uji revisi (diff baris, konservasi token, salinan rakit otomatis, dan galat pembanding)")


if __name__ == "__main__":
    utama()
