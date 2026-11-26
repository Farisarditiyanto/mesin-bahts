# SPDX-License-Identifier: AGPL-3.0-or-later
"""`bukti <folder>`: untuk pemeriksa, tiap catatan kaki berbukti dicetak bersama teks kitab di sekitar letak
kutipannya, tiap {Q:} dengan teks ayatnya, dan tiap paragraf isi tanpa catatan kaki."""
import re
from pathlib import Path

import cocok
import norma
import shamela
import sumber_pdf
import waqfeya
from cek_kutipan import bagian_kutipan
from dasar import ELIPSIS, JUDUL_BAB, KUTIPAN_MIN, LUAR, WAQFEYA_BUKTI, perintah
from kitab_lokal import Bukti, akhir_rekaman, rekaman_urut
from olah import periksa

SEKITAR = 300  # huruf teks kitab yang dicetak `bukti` sebelum dan sesudah letak kutipan


def _ringkas(t, maks=200):
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= maks else f"{t[:maks // 2]} … {t[-maks // 2:]}"


def _teks_halaman(sid, juz, p1, p2, bagian):
    """Teks asli (tanpa tag dan harakat) bagian rekaman halaman p1..p2 saja, tiap halaman diawali ⦗n⦘.
    حاشية tanpa penanda halaman di rekaman banyak halaman: seluruhnya, ditandai ⦗awal-akhir⦘ (seperti `halaman`)."""
    out = []
    for r in rekaman_urut(sid, juz, p1, p2):
        pp = norma.per_halaman(r, bagian)
        if len(pp) == 1:
            a, z = r.get("page_num"), akhir_rekaman(r)
            pp = [(f"{a}-{z}" if z != a else a, pp[0][1])]
        else:
            pp = [(h, b) for h, b in pp if h is not None and p1 <= h <= p2]
        for h, b in pp:
            b = re.sub(r"\s+", " ", norma.HARAKAT.sub("", norma.TAGS.sub("", b))).strip()
            if b:
                out.append(f"⦗{h}⦘ {b}")
    return " ".join(out)


def _penunjuk_pdf(folder, berkas, hal, kutipan):
    """Baris `bukti` untuk <<luar|berkas.pdf|hal>>: cuplikan teks halaman PDF di folder bahts untuk pemeriksa."""
    folder = Path(folder).resolve()
    p = (folder / berkas.strip()).resolve()
    if not p.is_relative_to(folder):
        return f"PDF «{berkas}» di luar folder bahts (lihat `cek`)"
    if not p.is_file():
        return f"PDF «{berkas}» tidak ada di folder bahts (lihat `cek`)"
    try:
        status, teks = sumber_pdf.cuplikan(p, hal, kutipan, SEKITAR)
    except Exception as e:  # noqa: BLE001 — PDF rusak/bersandi dilaporkan sebagai catatan diagnostik untuk pemeriksa
        return f"PDF «{berkas}» hal {hal} tidak terbaca ({type(e).__name__}: {e})"
    if status == "scan":
        return f"{berkas} [PDF hal {hal}; halaman gambar/scan tanpa teks terbaca: buka PDF-nya langsung]"
    letak = ("sekitar kutipan" if status == "terbaca" else
             "kutipan TIDAK ditemukan di teks PDF, awal halaman" if kutipan else "awal halaman")
    return f"{berkas} [PDF hal {hal}; teks PDF, {letak}; cocokkan sendiri lafaz dan angkanya]: {teks}"


def _penunjuk_waqfeya(w, n, hal, kutipan):
    """Baris `bukti` untuk <<w…|berkas|hal>>: judul kitab Waqfeya, teks OCR di sekitar kutipan, dan scan yang harus
    dibaca pemeriksa (OCR bukan bukti)."""
    if not waqfeya.ada(w):
        return f"kitab Waqfeya belum diunduh: {perintah('ambil ' + w)}"
    try:
        teks = waqfeya.cuplikan(w, int(n), hal, kutipan, SEKITAR)
        bagian = bagian_kutipan(kutipan)
        keadaan, rinci = waqfeya.periksa_kutipan(w, int(n), hal, bagian) if bagian else ("makna", None)
    except (ValueError, IndexError, SystemExit) as e:
        return f"bentuk/letak bukti rusak (lihat `cek`): {e}"
    ocr = {"persis": "kutipan terbaca persis di OCR", "mirip": f"kutipan mirip {rinci}% di OCR",
           "tidak": "kutipan TIDAK terbaca di OCR (salah huruf OCR, atau lafaz/halaman salah)",
           "lain": "kutipan terbaca di halaman lain (lihat `cek`)", "makna": "nukilan makna"}.get(keadaan, keadaan)
    nc = waqfeya.nomor_cetak(w, int(n), waqfeya.rentang(hal)[0])
    ocr += f"; nomor cetak terbaca di OCR: {nc}" if nc is not None else "; nomor cetak tidak terbaca di OCR"
    return (f"{waqfeya.data(w)['judul']} [Waqfeya, OCR; {ocr}]: {_ringkas(teks, 2 * SEKITAR)} || scan: "
            f"{perintah(f'halaman {w} {n} {hal}')} (lafaz dan nomor halaman cetak dinilai dari scan)")


def _penunjuk_bukti(b, kutipan):
    """Baris `bukti` untuk satu bukti Shamela b: nama kitab, rantai judul, dan teks halaman itu di sekitar kutipan."""
    e = b.salah()
    if e:
        return [e]
    sid, juz, hal, p1, p2 = b.sid, b.juz, b.hal, b.p1, b.p2
    m = shamela.info(sid)
    hasil = [f"kitab: {m['title_ar']} — {m.get('main_author_name_ar') or '?'}"]
    bagian_q = [x for x in ELIPSIS.split(kutipan or "") if len(norma.padat(x)) >= KUTIPAN_MIN]
    q = norma.padat(bagian_q[0]) if bagian_q else ""
    rr = rekaman_urut(sid, juz, p1, p2)
    # rantai judul di letak kutipan; kutipan tidak ketemu (atau melintasi rekaman) -> judul di awal halaman p1
    letak_judul = None
    for r in rr if q else ():
        for bagian, _ in norma.BAGIAN:
            c, h = cocok.letak_pertama(r, q, bagian), cocok.tempat(r, q, bagian, dalam=(p1, p2))
            if c and h and p1 <= (h[0] or 0) and (h[1] or 0) <= p2:
                letak_judul = letak_judul or (r, c, h, bagian)
    if not letak_judul and rr:
        batas = norma.ruas_halaman(rr[0], "body")[1]
        letak_judul = (rr[0], (next((a for a, _, h1, _ in batas if h1 == p1), 0),) * 2, (p1, p1), "body")
    if letak_judul:
        judul = shamela.rantai_calon(sid, *letak_judul)
        hasil.append("bab: " + (judul[0] if len(judul) == 1 else "RAGU, salah satu dari: " + " | ".join(judul)))
    # kutipan yang lafaznya meleset di tengah: letak awalnya tetap ditunjuk (kata-kata awal terpanjang yang ada di halaman)
    kata_awal = bagian_q[0].split() if bagian_q else []
    teks = {bagian: _teks_halaman(sid, juz, p1, p2, bagian) for bagian, _ in norma.BAGIAN}
    padat_ = {bagian: norma.padat(raw) for bagian, raw in teks.items()}
    for k in range(len(kata_awal), 0, -1):
        qk = norma.padat(" ".join(kata_awal[:k]))
        if len(qk) < KUTIPAN_MIN:
            break
        for bagian, tanda in norma.BAGIAN:
            raw = teks[bagian]
            if qk not in padat_[bagian]:
                continue
            i = cocok.letak_asli(raw, qk)
            h = ([x[1] for x in re.finditer(r"⦗([\d-]+)⦘", raw[:i + 1])] or [hal])[-1]
            a, z = max(0, i - SEKITAR), i + len(kutipan) + SEKITAR
            sebagian = f" (hanya awal kutipan yang ada: «{' '.join(kata_awal[:k])}»)" if k < len(kata_awal) else ""
            hasil.append(f"{shamela.letak(juz, h)}{tanda}{sebagian}: {'…' * (a > 0)}{raw[a:z]}{'…' * (z < len(raw))}")
            return hasil
    raw = teks["body"]
    if not raw:
        return hasil + [f"{shamela.letak(juz, (p1, p2))}: halaman itu tidak ada di kitab {sid} juz {juz}"]
    sebab = "kutipan TIDAK ketemu di halaman itu" if q else "tanpa kutipan untuk dicari"
    return hasil + [f"{shamela.letak(juz, (p1, p2))}: {sebab}; awal halaman: {raw[:2 * SEKITAR]}{'…' * (len(raw) > 2 * SEKITAR)}"]


def _tanpa_catatan(blok, dikecualikan=()):
    """(baris, teks) tiap paragraf isi tanpa satu pun catatan kaki. Isi = bab #F (bukan yang bernama مقدمة/خاتمة) dan
    #B/#M di bawahnya, atau #B/#M langsung sesudah #K المقدمة; #K dan المصادر (#R) bukan isi. `cek` tidak bisa
    menilai kalimat tanpa catatan kaki, jadi pemeriksa langkah 5 yang menilai apakah ada penisbatan atau fakta di
    dalamnya yang perlu sumber (mis. «وثمرة الخلاف أن الحنفية…» tanpa catatan kaki)."""
    di_isi, bab_luar = False, False  # bab_luar: #F terakhir bernama مقدمة/خاتمة
    for b in blok:
        if b["k"] == "R":
            return
        if b["k"] in JUDUL_BAB:
            bab_luar = b["k"] == "F" and bool(re.search(r"مقدم[ةه]|خاتم[ةه]", norma.HARAKAT.sub("", b.get("judul", ""))))
            di_isi = b["k"] == "F" and not bab_luar
        elif b["k"] in ("B", "M"):
            di_isi = not bab_luar
        elif di_isi and b["k"] == "P" and b["n"] not in dikecualikan and not any("fn" in r for r in b["runs"]):
            teks = "".join(r.get("t", "") for r in b["runs"]).strip()
            if teks:
                yield b["n"], teks


def bukti(folder, dari=None, sampai=None):
    """`bukti`: untuk tiap catatan kaki berbukti <<sid|juz|hal…>> dan ayat {Q:} di baris dari..sampai (None = semua):
    paragraf matan dan isi catatan kaki utuh, lalu nama kitab, rantai judul, dan teks halaman kitab di sekitar letak
    kutipan; juga tiap paragraf isi tanpa catatan kaki (_tanpa_catatan), di urutan barisnya. Naskahnya diurai
    `olah.periksa` (sama dengan `cek`), tetapi laporan dan putusannya tidak dicetak.
    Tiap baris keluaran diawali «baris n», supaya bisa disaring. Kembalikan jumlah yang dicetak."""
    ctx = periksa(folder).ctx
    dalam = lambda n: (dari is None or dari <= n) and (sampai is None or n <= sampai)
    polos = [{"n": n, "polos": t} for n, t in _tanpa_catatan(ctx.blok, ctx.ayat_matan) if dalam(n)]
    pilih = sorted([u for u in ctx.penunjuk if dalam(u["n"])] + polos, key=lambda u: u["n"])
    ke, tercetak = {}, None
    for u in pilih:
        if "polos" in u:
            print(f"baris {u['n']} tanpa catatan kaki: «{_ringkas(u['polos'], 600)}»")
            continue
        if "ayat" in u:
            print(f"baris {u['n']} ayat {{Q:{u['ayat']}}}: ﴿{u['t']}﴾")
            continue
        ke[u["n"]] = ke.get(u["n"], 0) + 1
        kepala = f"baris {u['n']} #{ke[u['n']]}"
        if u["runs"] is not tercetak:  # beberapa catatan kaki di satu paragraf: matannya dicetak sekali
            tercetak = u["runs"]
            print(f"{kepala} matan: {''.join(r.get('t', '') for r in u['runs']).strip()}")
        print(f"{kepala} kutipan: " + (f"«{_ringkas(u['kutipan'])}»" if u["kutipan"] else "(tanpa kutipan bertanda petik)"))
        print(f"{kepala} catatan: {u['catatan']}")
        for b in u["bukti"]:
            if b.startswith(LUAR + "|"):
                bag = b.split("|", 2)
                if len(bag) == 3:
                    print(f"{kepala} <<{b}>> {_penunjuk_pdf(folder, bag[1], bag[2], u['kutipan'])}")
                else:
                    print(f"{kepala} <<{_ringkas(b, 80)}>>: bentuk bukti PDF rusak (lihat `cek`)")
                continue
            if m := WAQFEYA_BUKTI.fullmatch(b):
                print(f"{kepala} <<{b}>> {_penunjuk_waqfeya(*m.groups(), u['kutipan'])}")
                continue
            try:
                bukti_ = Bukti.urai(b)
            except ValueError:
                print(f"{kepala} <<{_ringkas(b, 80)}>>: bentuk bukti rusak (lihat `cek`)"); continue
            pot = bukti_.potongan
            pot = re.sub(r"\{Q:[^}]*\}", " ﴿﴾ ", pot) if pot is not None and not pot.startswith("#") else None
            for x in _penunjuk_bukti(bukti_, pot or u["kutipan"]):
                print(f"{kepala} <<{_ringkas(b, 80)}>> {x}")
    if not pilih:
        print("Tidak ada catatan kaki berbukti <<sid|juz|hal>> atau ayat {Q:} di " + (
            "naskah ini." if dari is None else f"baris {dari}" + (f"-{sampai}" if sampai != dari else "") + "."))
    return len(pilih)
