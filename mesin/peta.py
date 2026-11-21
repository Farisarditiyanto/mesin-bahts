# SPDX-License-Identifier: AGPL-3.0-or-later
"""`peta <folder>`: ringkasan terstruktur offline (tidak mengubah berkas, tidak membebani `cek`) untuk penulis dan
pemeriksa langkah 5:
1) Struktur & Cakupan (pohon judul, jumlah kata/catatan kaki/paragraf polos per bagian, bagian isi tanpa catatan kaki);
2) Sijil Sumber & Cakupan Mazhab (tiap kitab berbukti urut dari pengarang tertua, tanda [معتمد]/[معاصر], matriks mazhab);
3) Busur Argumen (المقدمة ↔ الترجيح/الخلاف/الإجماع ↔ الخاتمة berdampingan untuk mendeteksi kontradiksi & qaws maftuh);
4) Daftar Hadits {H:…} beserta ringkasan takhrij-nya;
5) Daftar `terima` di `riset.txt` beserta perhatian asli yang ditutupnya."""
import re

import norma
import shamela
import waqfeya
from cek_sumber import MAZHAB, MODERN, mutamad
from dasar import LUAR, WAQFEYA_BUKTI
from kitab_lokal import kitab_meta
from olah import periksa

_KLAIM_KHUTTAH = re.compile(r"(?:خطة البحث|قسمت|جعلته|مقدمة|فصل|مبحث|مطلب|أهداف|أسئلة|مشكلة البحث|منهج البحث)")
_KLAIM_TARJIH = re.compile(
    r"(?<![ء-ي])(?:والراجح|الراجح|الترجيح|ويترجح|والأقرب|والصواب|يتبين|ويظهر للباحث|"
    r"القول الأول|القول الثاني|القول الثالث|المذهب الأول|المذهب الثاني|"
    r"واتفق العلماء|اتفق العلماء|اتفق الفقهاء|أجمع العلماء|أجمع الفقهاء|الإجماع على|بالإجماع)(?![ء-ي])"
)
_KLAIM_NATAIJ = re.compile(r"(?:النتائج|نتيج[ةه]|توصل|تبين|الراجح|خلاص[ةه]|أهم ما|التوصيات)")
_RINGKAS_WAJAR = re.compile(
    r"^(?:(?:الفصل|المبحث|المطلب)\s+(?:التمهيدي|الختامي)(?![ء-ي])"
    r"|(?:(?:الفصل|المبحث|المطلب)\s+[^:：]+[:：]\s*)?"
    r"(?:ال)?(?:تمهيد|مدخل|مقدم[ةه]|خاتم[ةه]|ترجيح|صور[ةه]\s+المسأل[ةه]|تحرير\s+محل\s+النزاع)(?![ء-ي]))"
)
_MAZHAB_NAMA = {"حنفي": "الحنفية", "مالكي": "المالكية", "شافعي": "الشافعية", "حنبلي": "الحنابلة"}


def _ringkas_teks(teks, maks=150):
    t = " ".join((teks or "").split())
    return t if len(t) <= maks else t[:maks - 1] + "…"


def _kumpul_struktur(blok):
    """Pohon bagian (#K/#F/#B/#M/#S) dengan jumlah kata, catatan kaki, dan paragraf polos tanpa catatan kaki."""
    bagian, kini = [], None
    for b in blok:
        k = b["k"]
        if k == "R":
            break
        if k in ("K", "F", "B", "M", "S"):
            kini = {"n": b["n"], "k": k, "judul": b.get("judul", ""), "kata": 0, "fn": 0, "polos": 0}
            bagian.append(kini)
        elif kini is not None and b.get("runs"):
            wc = len("".join(r.get("t", "") for r in b["runs"]).split())
            fns = sum(1 for r in b["runs"] if "fn" in r)
            kini["kata"] += wc
            kini["fn"] += fns
            if k == "P" and fns == 0 and wc >= 8:
                kini["polos"] += 1
    return bagian


def _timpang_catatan(blok):
    """Daftar ringkas bagian setingkat (#F, atau #B di bawah satu #F) yang panjangnya timpang >=5x (maks >=500 kata)."""
    daftar_f, cur_f, cur_b = [], None, None
    for b in blok:
        k = b["k"]
        if k == "R":
            break
        if k == "K":
            cur_f = cur_b = None
        elif k == "F":
            cur_f = {"n": b["n"], "judul": b.get("judul", ""), "kata": 0, "anak": []}
            daftar_f.append(cur_f)
            cur_b = None
        elif k == "B":
            cur_b = {"n": b["n"], "judul": b.get("judul", ""), "kata": 0}
            if cur_f is not None:
                cur_f["anak"].append(cur_b)
        elif b.get("runs"):
            wc = len("".join(r.get("t", "") for r in b["runs"]).split())
            if cur_f is not None:
                cur_f["kata"] += wc
            if cur_b is not None:
                cur_b["kata"] += wc
    kelompok = [daftar_f] + [f["anak"] for f in daftar_f if len(f["anak"]) >= 2]
    out = []
    for d in kelompok:
        sah = [x for x in d if x["kata"] > 0 and not _RINGKAS_WAJAR.match(norma.HARAKAT.sub("", x["judul"]).strip())]
        if len(sah) < 2:
            continue
        hi = max(sah, key=lambda x: x["kata"])
        lo = min(sah, key=lambda x: x["kata"])
        if hi["kata"] >= 500 and hi["kata"] / lo["kata"] >= 5.0:
            out.append(f"L{lo['n']} «{lo['judul'][:35]}» ({lo['kata']} kata) vs L{hi['n']} «{hi['judul'][:35]}» "
                       f"({hi['kata']} kata; {hi['kata'] / lo['kata']:.1f}×)")
    return out


def _sijil_sumber(ctx):
    """Rekap kitab Shamela/Waqfeya/PDF/<<luar>> yang benar-benar berbukti di catatan kaki + cakupan mazhab."""
    sids, wids, pdfs = {}, {}, {}
    n_luar = 0
    for p in ctx.penunjuk:
        for b in p.get("bukti", ()):
            if mw := WAQFEYA_BUKTI.fullmatch(b):
                wids[mw.group(1)] = wids.get(mw.group(1), 0) + 1
            elif b.startswith(LUAR + "|"):
                nama = b.split("|", 2)[1].strip()
                pdfs[nama] = pdfs.get(nama, 0) + 1
            elif b == LUAR:
                n_luar += 1
            else:
                p0 = b.split("|", 1)[0].strip()
                if p0.isdigit():
                    sids[int(p0)] = sids.get(int(p0), 0) + 1
    mt = mutamad()
    semua_mt = set().union(*mt.values()) if mt else set()
    baris_sh = []
    bukti_mazhab = {mz: 0 for mz in MAZHAB}
    for sid, cnt in sids.items():
        vm = kitab_meta(sid)
        try:
            m = shamela.info(sid)
            judul = (m.get("title_ar") or "?").split(" - ")[0]
            pengarang = m.get("main_author_name_ar") or "?"
            kat = m.get("category_name_ar") or "?"
        except (LookupError, OSError, ValueError, SystemExit):
            judul, pengarang, kat = "?", "?", "?"
        wafat = vm["wafat"] if vm and vm["wafat"] < 2000 else None
        for mz, (kat_id, _) in MAZHAB.items():
            if sid in mt.get(mz, ()) or (vm and vm["kategori"] == kat_id and vm["wafat"] < MODERN):
                bukti_mazhab[mz] += cnt
        tanda = []
        if sid in semua_mt:
            tanda.append("معتمد")
        if wafat is None or wafat >= MODERN:
            tanda.append("معاصر")
        baris_sh.append((wafat is None, wafat or 9999, sid, cnt, judul, pengarang, kat, tanda))
    baris_sh.sort()
    # Mazhab yang disebut di paragraf matan (di luar #R)
    teks_matan = " ".join(
        "".join(r.get("t", "") for r in b.get("runs", ()))
        for b in ctx.blok if b["k"] == "P"
    )
    polos_matan = norma.HARAKAT.sub("", teks_matan)
    mazhab_disebut = {mz for mz, (_, pola) in MAZHAB.items() if re.search(pola, polos_matan)}
    return {
        "shamela": baris_sh, "waqfeya": wids, "pdf": pdfs, "luar": n_luar,
        "mazhab_disebut": mazhab_disebut, "bukti_mazhab": bukti_mazhab,
    }


def _busur_argumen(blok):
    """Ekstrak baris rencana/pertanyaan di المقدمة, baris قول/إجماع/ترجيح di isi, dan baris hasil di الخاتمة."""
    muq, isi, kha = [], [], []
    bagian = ""
    for b in blok:
        k = b["k"]
        if k == "R":
            break
        if k == "K":
            j = norma.HARAKAT.sub("", b.get("judul", "")).strip()
            bagian = "muq" if "مقدم" in j else "kha" if "خاتم" in j else ""
            continue
        if k == "F":
            bagian = "isi"
            continue
        if k != "P" or not b.get("runs"):
            continue
        teks = "".join(r.get("t", "") for r in b["runs"]).strip()
        if not teks:
            continue
        polos = norma.HARAKAT.sub("", teks)
        n_fn = sum(1 for r in b["runs"] if "fn" in r)
        if bagian == "muq" and _KLAIM_KHUTTAH.search(polos):
            muq.append((b["n"], n_fn, _ringkas_teks(teks, 150)))
        elif bagian == "isi" and _KLAIM_TARJIH.search(polos):
            isi.append((b["n"], n_fn, _ringkas_teks(teks, 150)))
        elif bagian == "kha" and (_KLAIM_NATAIJ.search(polos) or len(teks) >= 20):
            kha.append((b["n"], n_fn, _ringkas_teks(teks, 150)))
    return muq, isi, kha


def _daftar_hadits(ctx):
    """Ringkasan tiap hadits {H:…} di naskah (kunci `t` = taraf, `r` = rawi, baris dari bookmark `bm` di blok)
    beserta catatan kaki takhrij terdekat pada baris yang sama."""
    bm_baris = {r["bm"]: b["n"] for b in ctx.blok if "n" in b for r in b.get("runs", ()) if "bm" in r}
    fn_baris = {}
    for p in ctx.penunjuk:
        if "catatan" in p:
            fn_baris.setdefault(p["n"], []).append(p["catatan"])
    out = []
    for h in ctx.hadits_idx:
        baris_n = bm_baris.get(h.get("k"))
        fn = " | ".join(fn_baris.get(baris_n, ())[:2])
        out.append((baris_n, h.get("t", ""), h.get("r", ""), _ringkas_teks(fn, 110)))
    out.sort(key=lambda x: (x[0] is None, x[0] or 0))
    return out


def cetak(folder):
    """Cetak peta struktur, sijil sumber, busur argumen, daftar hadits, dan `terima` satu bahts (offline)."""
    h = periksa(folder)
    ctx = h.ctx
    m = ctx.meta
    print(f"PETA BAHTS: {m.get('judul', '-')}")
    print(f"jenis={m.get('jenis', '-')} | format={m.get('format', '-')} | sampul={m.get('sampul', 'qism')} | "
          f"GAGAL={len(ctx.galat)} | perhatian={len(ctx.perhatian)} | diterima={len(ctx.diterima)}")

    bagian = _kumpul_struktur(ctx.blok)
    print(f"\n[1] Struktur & Cakupan ({len(bagian)} judul):")
    for s in bagian:
        jorok = {"K": "", "F": "", "B": "  ", "M": "    ", "S": "      "}[s["k"]]
        tanda = "  <-- 0 catatan kaki!" if s["k"] in ("F", "B", "M") and s["kata"] >= 80 and s["fn"] == 0 else ""
        print(f"  L{s['n']:4d} {jorok}#{s['k']} {s['judul'][:60]} ({s['kata']} kata, {s['fn']} fn, {s['polos']} P polos){tanda}")
    for tp in _timpang_catatan(ctx.blok):
        print(f"  ! ketimpangan panjang: {tp}")

    sijil = _sijil_sumber(ctx)
    tot_sh = sum(x[3] for x in sijil["shamela"])
    tot_wq = sum(sijil["waqfeya"].values())
    tot_pdf = sum(sijil["pdf"].values())
    print(f"\n[2] Sijil Sumber (Evidence Ledger): Shamela {len(sijil['shamela'])} kitab ({tot_sh} bukti), "
          f"Waqfeya {len(sijil['waqfeya'])} ({tot_wq}), PDF {len(sijil['pdf'])} ({tot_pdf}), <<luar>> {sijil['luar']}")
    for _, w, sid, cnt, judul, pengarang, kat, tanda in sijil["shamela"]:
        era = f"ت {w}هـ" if w < 9999 else "غير مؤرخ"
        tag = f" [{'، '.join(tanda)}]" if tanda else ""
        print(f"  [{sid:6d}] {cnt:2d}× | {era:10s} | {kat[:18]:18s} | {judul[:42]} — {pengarang[:24]}{tag}")
    for wid, cnt in sorted(sijil["waqfeya"].items()):
        j = waqfeya.data(wid)["judul"][:45] if waqfeya.ada(wid) else "(belum diunduh)"
        print(f"  [{wid}] {cnt:2d}× | Waqfeya (nilai dari scan) | {j}")
    for pdf, cnt in sorted(sijil["pdf"].items()):
        print(f"  [PDF]    {cnt:2d}× | {pdf}")
    if sijil["mazhab_disebut"]:
        ring_mz = []
        for mz in ("حنفي", "مالكي", "شافعي", "حنبلي"):
            if mz in sijil["mazhab_disebut"]:
                n_b = sijil["bukti_mazhab"][mz]
                ring_mz.append(f"{_MAZHAB_NAMA[mz]}: {n_b} bukti" + (" (KOSONG!)" if n_b == 0 else ""))
        print("  Cakupan kitab mazhab (disebut di matan): " + " | ".join(ring_mz))

    muq, isi, kha = _busur_argumen(ctx.blok)
    print(f"\n[3] Busur Argumen (المقدمة: {len(muq)}, الترجيح/الخلاف/الإجماع: {len(isi)}, الخاتمة: {len(kha)}):")
    for n, fn, t in muq[:8]:
        print(f"  [مقدمة L{n:4d} | {fn} fn] {t}")
    for n, fn, t in isi[:20]:
        print(f"  [متن   L{n:4d} | {fn} fn] {t}")
    if len(isi) > 20:
        print(f"  … (+{len(isi) - 20} baris tarjih/khilaf lainnya)")
    for n, fn, t in kha[:12]:
        print(f"  [خاتمة L{n:4d} | {fn} fn] {t}")

    hadits = _daftar_hadits(ctx)
    if hadits:
        print(f"\n[4] Hadits bertanda {{H:…}} ({len(hadits)}):")
        for n, taraf, rawi, fn in hadits:
            pos = f"L{n:4d}" if n else "L?   "
            print(f"  {pos} «{taraf[:55]}» (الراوي: {rawi or '-'})" + (f" | {fn}" if fn else ""))

    if ctx.diterima:
        print(f"\n[5] Perhatian Diterima (`terima` di riset.txt: {len(ctx.diterima)}, wajib dicek pemeriksa):")
        for kd, pesan, alasan in ctx.diterima:
            print(f"  {kd}: {_ringkas_teks(pesan, 95)} || alasan: {alasan}")
    return len(bagian)
