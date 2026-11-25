# SPDX-License-Identifier: AGPL-3.0-or-later
"""`edisi <kueri|sid|w…> [pengarang]`: rekonsiliasi kitab dan edisi lintas-katalog offline antara katalog Shamela
(8.589 kitab, termasuk `group_id` multi-edisi) dan katalog Waqfeya (±10.000 kitab).

Aturan normalisasi judul, pemisahan judul alternatif (`=` / `المسمى` / kurung), ekor edisi (`- ت …` / `- ط …`),
pembedaan karya sama vs karya terkait (`مختصر`/`شرح`/`حاشية`/`تخريج`/`نظم`) vs konflik ukuran (`الكبرى`/`الصغرى`),
serta pencocokan nama pengarang Arab (anti jebakan kerabat `سبط ابن الجوزي` ≠ `ابن الجوزي`, anti konflik nisbah
`ابن حجر العسقلاني` ≠ `ابن حجر الهيتمي`, dan toleransi tahun wafat) diadaptasi dari prinsip `turath-match` &
`arabic-bib` tanpa dependensi tambahan."""
import functools, re

import norma
import shamela

# Bagian nama yang dipakai banyak ulama (ism, kunyah, laqab umum): tidak membedakan pengarang
NAMA_UMUM = frozenset(norma.norm(x) for x in """محمد أحمد عبد الله الدين بن ابن أبو أبي أبا أم آل ذي ذو علي عمر الرحمن
إبراهيم الحسن الحسين حسن حسين سعيد يوسف عثمان إسماعيل يحيى موسى سليمان عيسى صالح خالد جعفر طاهر العباس القاسم الفضل
بكر زيد مصطفى عمرو يعقوب داود إسحاق منصور محمود الشيخ الإمام الحافظ العلامة القاضي شهاب جمال كمال زين تقي شمس بدر
عماد نجم سراج فخر العزيز العالم الفقيه المحدث الدكتور الأستاذ رحمه تعالى في من عن على إلى و أو""".split())
NOMOR_WAQFEYA = re.compile(r"w[0-9a-f]{8}")
# Variasi ejaan klasik nama/nisbah Arab («الأصفهاني» = «الأصبهاني», «إسحق» = «إسحاق», «عبد الرحمان» = «عبد الرحمن»)
_EJA_NAMA = (("اصفهان", "اصبهان"), ("اسحق", "اسحاق"), ("الرحمان", "الرحمن"), ("طاووس", "طاوس"), ("داوود", "داود"))


def _lipat_nama(teks):
    s = norma.norm(teks or "")
    for a, b in _EJA_NAMA:
        if a in s:
            s = s.replace(a, b)
    return s


def kata_nama(nama):
    """Kata nama yang membedakan orang, tanpa «ال» («العثيمين» = «عثيمين»), termasuk syuhrah pendek yang khas
    («ابن حزم», «ابن باز», «ابن وهب», «ابن أبي العز», «ابن عبد البر»)."""
    out = set()
    for w in _lipat_nama(nama).split():
        if len(w) < 2 or w in NAMA_UMUM or "ال" + w in NAMA_UMUM:
            continue
        w2 = w[2:] if w.startswith("ال") and len(w) >= 4 else w
        if len(w2) >= 2 and w2 not in NAMA_UMUM and "ال" + w2 not in NAMA_UMUM:
            out.add(w2)
    return out

# Kata yang mengubah suatu karya menjadi karya TERKAIT (syarah, ringkasan, hasyiah, takhrij), bukan edisi lain kitab sama
KATA_TERKAIT = frozenset(norma.padat(x) for x in """مختصر اختصار شرح بشرح حاشيه ذيل تكمله منتقي زوايد نظم رد تخريج
فهارس دراسه ترتيب تهذيب تلخيص مستدرك تعليق تعليقات تعليقه تقريرات حواشي فوايد تجريد تقريب مختارات""".split())
# Kata pembeda ukuran/versi kitab yang saling berkonflik bila berbeda («السنن الكبرى» ≠ «السنن الصغرى»)
KATA_UKURAN = frozenset(norma.padat(x) for x in "الكبري الصغري الوسطي الوسيط البسيط الوجيز الكبير الصغير الاوسط".split())
# Ekor keterangan edisi/cetak dan penanda salinan digital pada judul katalog
_SALINAN_DIGITAL = re.compile(
    r"\s*\((?:موافق للمطبوع|مشكول|نسخة أخرى|النسخة الشاملة|ط\s*[._:\s][^()]*|ت\s*[._:\s][^()]*|تحقيق[^()]*)\)"
)
_GABUNG_KITAB = re.compile(r"\s+(?:ويليه|ومعه|وبهامشه|ومعها|وبذيله|وعليه)\s+.*$")
_EKOR_EDISI = re.compile(r"\s*(?:-|—|–)\s*(?:ت[\s.:،_]|ط[\s.:،_]|تحقيق|طبعة|دار|مؤسسة|مكتبة|موافق للمطبوع|مشكول|نسخة أخرى|المطبعة).*$")
_EKOR_SEBARIS = re.compile(r"\s+(?:ت|ط)\s*[:._-]\s*.*$")
_RIWAYAT = re.compile(r"(?<![ء-ي])رواية\s+([^()\[\]،؛=–—-]+)")
_BUANG_DEPAN = re.compile(r"^(?:كتاب|رسالة في|جزء فيه)\s+")
_KERABAT = re.compile(r"(?<![ء-ي])(?:سبط|حفيد|والد|أخو|تلميذ)\s+")
_NISBAH_PEMBEDA = re.compile(r"(?<![ء-ي])(ال[ء-ي]{3,}[يى])(?![ء-ي])")
_NISBAH_UMUM = frozenset(norma.padat(x) for x in """الشافعي الحنبلي الحنفي المالكي الدمشقي البغدادي المصري المكي
المدني الكوفي البصري الأندلسي المغربي القرشي الأنصاري النيسابوري الرازي المروزي التميمي السلمي الأزدي""".split())
_KATA_FUNGSI = frozenset(norma.padat(x) for x in "في من على إلى عن مع بين حول عند لدى نحو تحت فوق أو و".split())
_WAFAT_MAKS = 2000
_KURUNG_EDISI = re.compile(r"\(((?:ط|ت)\s*[._:\s][^()]+|تحقيق[^()]+)\)")
_AWAL_ABU = re.compile(r"^اب[ايو](?= )")
_PISAH_JUDUL = re.compile(r"\s*=\s*|\s+المسمى\s+|\s+المسمّى\s+")
_KURUNG_JUDUL = re.compile(r"\(([^()]{4,})\)")
_AWAL_KURUNG_JUDUL = re.compile(r"^\s*(?:أو|تفسير|شرح|كتاب|مختصر|سنن|مسند|صحيح|جامع|مسائل)\s+")
_AWAL_AW = re.compile(r"^\s*أو\s+")
_HAPUS_KURUNG = re.compile(r"\([^()]*\)|\[[^\[\]]*\]")
_PISAH_DASH = re.compile(r"\s+-\s+")
_IBN_ABI = re.compile(r"(?<![ء-ي])ا?بن\s+أب[يو]")
_KURUNG_PENGARANG = re.compile(r"\(([^()]*)\)")
_KURUNG_CETAK = re.compile(r"\s*(?:ط|ت)\s*[._:]")
# Huruf yang bisa muncul di hasil `norma.padat` dari huruf lain (SAMA, EJAAN, ﷽, شئ/شي): sisanya wajib ada di teks mentah
_HURUF_BERUBAH = (
    frozenset(ke for _, ke in norma.SAMA)
    | frozenset("ءبسملرحني")
    | frozenset(c for a, b in norma.EJAAN for c in (set(b) - set(a)))
)


def _huruf_wajib(kata_list):
    return tuple(dict.fromkeys(c for k in kata_list for c in k if c not in _HURUF_BERUBAH))


def ekstrak_ekor_edisi(judul):
    """Ambil keterangan cetak/edisi yang menempel di judul katalog (mis. `(ط. طيبة)`, `(ت_ الحويني)`, `- ت حلاق`)."""
    bag = []
    for m in _KURUNG_EDISI.finditer(judul or ""):
        bag.append(m.group(1).replace("_", ":").strip())
    if m := _EKOR_EDISI.search(judul or ""):
        bag.append(m.group(0).lstrip(" -–—").strip())
    return "؛ ".join(dict.fromkeys(bag))


def _riwayat(judul):
    bersih = _EKOR_SEBARIS.sub("", _EKOR_EDISI.sub("", _SALINAN_DIGITAL.sub("", judul)))
    if m := _RIWAYAT.search(norma.HARAKAT.sub("", bersih)):
        return norma.norm(m[1])
    return ""


def _beda_riwayat(judul_a, judul_b):
    a, b = _riwayat(judul_a), _riwayat(judul_b)
    # «رواية يحيى» dan «رواية يحيى بن يحيى الليثي» dapat merujuk ke riwayat yang sama.
    def kata(nama):
        return tuple(_AWAL_ABU.sub("ابو", nama).split())

    a, b = sorted((kata(a), kata(b)), key=len)
    return bool(a and a != b[:len(a)])


def _tanpa_ekor_pengarang(judul, pengarang, _kp=None):
    """Buang «لـ<pengarang>» di akhir judul («المحصول للرازي» -> «المحصول», «إعراب القرآن للنحاس» -> «إعراب القرآن»)
    hanya bila `pengarang` tersedia dan cocok dengan kata sesudah «لـ»."""
    kata = judul.split()
    if len(kata) < 2 or not pengarang:
        return judul
    akhir = kata[-1]
    if not akhir.startswith("ل"):
        return judul
    orang = "ال" + akhir[2:] if akhir.startswith("لل") else akhir[1:]
    kp = kata_nama(pengarang) if _kp is None else _kp
    if orang and (kata_nama(orang) & kp):
        sisa = " ".join(kata[:-1]).strip()
        if len(norma.padat(sisa)) >= 5:
            return sisa
    return judul


def pecah_judul(judul, pengarang=""):
    """Daftar judul pokok dan judul alternatif bersih dari satu baris judul katalog (memisahkan `=`, `المسمى`,
    kurung judul alternatif seperti `(تفسير ابن كثير)`, membuang ekor edisi dan kitab gabungan `ويليه`/`ومعه`)."""
    t = judul or ""
    if "(" in t:
        t = _SALINAN_DIGITAL.sub("", t)
    t = _GABUNG_KITAB.sub("", t)
    t = _EKOR_EDISI.sub("", t).strip()
    calon = []
    bagian = _PISAH_JUDUL.split(t) if ("=" in t or "المسم" in t) else (t,)
    for bag in bagian:
        # Judul masyhur di dalam kurung («تفسير القرآن العظيم (تفسير ابن كثير)») ikut diekstrak
        if "(" in bag:
            for km in _KURUNG_JUDUL.findall(bag):
                if _AWAL_KURUNG_JUDUL.match(km):
                    calon.append(_AWAL_AW.sub("", km).strip())
        # Potong ekor pengarang sesudah « - » («جمع القرآن - فهد الرومي») sebagai varian juga
        bersih = _HAPUS_KURUNG.sub(" ", bag).strip() if ("(" in bag or "[" in bag) else bag.strip()
        bersih = _EKOR_SEBARIS.sub("", bersih).strip()
        kepala = _PISAH_DASH.split(bersih, maxsplit=1)[0].strip() if "-" in bersih else bersih
        for k in (bersih, kepala):
            if k:
                calon.append(k)
    out = []
    kp = None
    for c in calon:
        c = _BUANG_DEPAN.sub("", c).strip(" -–—:،")
        if c and c not in out:
            out.append(c)
        if pengarang and c:
            if kp is None and " ل" in c:
                kp = kata_nama(pengarang)
            tanpa = _tanpa_ekor_pengarang(c, pengarang, kp)
            if tanpa and tanpa not in out:
                out.append(tanpa)
    return out


def _kata_judul(judul):
    return [p for k in judul.split() if len(p := norma.padat(k)) >= 2 and p not in _KATA_FUNGSI]


def hubungan_judul(j1, j2):
    """Hubungan dua judul bersih: `sama` (tepat/awal), `terkait` (syarah/mukhtashar/hasyiah), atau `beda`."""
    k1, k2 = _kata_judul(j1), _kata_judul(j2)
    if not k1 or not k2:
        return "beda"
    p1, p2 = "".join(k1), "".join(k2)
    # Konflik ukuran («السنن الكبرى» ≠ «السنن الصغرى»)
    u1, u2 = set(k1) & KATA_UKURAN, set(k2) & KATA_UKURAN
    if u1 and u2 and u1 != u2:
        return "beda"
    if p1 == p2:
        return "sama"
    # Salah satu memuat penanda karya turunan (مختصر/شرح/حاشية…) yang tidak ada di sisi lain
    t1, t2 = set(k1) & KATA_TERKAIT, set(k2) & KATA_TERKAIT
    pendek, panjang = (k1, k2) if len(k1) <= len(k2) else (k2, k1)
    awal_sama = (
        (len(pendek) >= 2 and (panjang[:len(pendek)] == pendek
                               or (len(pendek) >= 3 and set(pendek) <= set(panjang) and pendek[0] == panjang[0])))
        or (len(pendek) == 1 and len(pendek[0]) >= 6 and panjang[0] == pendek[0])
    )
    if awal_sama:
        # Subjudul penjelas di ekor sesudah judul pendek («فيض القدير شرح الجامع الصغير» ↔ «فيض القدير»)
        # tetap karya sama (termasuk kata ukuran milik kitab yang disyarah di dalam subjudul itu),
        # sedangkan kata turunan di awal judul («شرح …», «مختصر …») adalah karya terkait.
        ekor_panjang = panjang[len(pendek):]
        subjudul_turunan = (
            panjang[:len(pendek)] == pendek
            and bool(ekor_panjang)
            and ekor_panjang[0] in KATA_TERKAIT
            and ekor_panjang[0] != "بشرح"
            and not (set(pendek) & KATA_TERKAIT)
        )
        if u1 != u2 and not subjudul_turunan:
            return "beda"
        if t1 != t2 and not subjudul_turunan:
            return "terkait"
        return "sama"
    # Karya terkait: judul pendek muncul utuh sesudah kata turunan («شرح <judul pendek>», «مختصر <judul pendek>»)
    if len(pendek) >= 2 and t1 != t2 and "".join(pendek) in "".join(panjang):
        return "terkait"
    return "beda"


def _nisbah_khas(nama):
    out = set()
    for m in _NISBAH_PEMBEDA.finditer(_lipat_nama(nama)):
        p = norma.padat(m.group(1))
        if p not in _NISBAH_UMUM and len(p) >= 5:
            out.add(p)
    return out


def _tahun_wafat_sah(w):
    return w if isinstance(w, int) and 0 < w < _WAFAT_MAKS else None


def cocok_pengarang(nama_a, nama_b, wafat_a=None, wafat_b=None):
    """Bandingkan dua nama pengarang Arab: `sama`, `beda`, atau `ragu` (arabic-bib rules: tolak nama umum semata,
    tolak jebakan kerabat `سبط ابن الجوزي` ≠ `ابن الجوزي`, tolak konflik nisbah khas `العسقلاني` ≠ `الهيتمي`)."""
    wa, wb = _tahun_wafat_sah(wafat_a), _tahun_wafat_sah(wafat_b)
    if wa and wb and abs(wa - wb) > 12:
        return "beda"
    ka_a, ka_b = bool(_KERABAT.search(nama_a or "")), bool(_KERABAT.search(nama_b or ""))
    if ka_a != ka_b:
        return "beda"
    # «ابن/بن أبي حاتم» bukan ayahnya «أبو حاتم»; mendukung «بن» maupun «ابن» («أبو بكر بن أبي شيبة» = «ابن أبي شيبة»)
    ibn_abi_a = bool(_IBN_ABI.search(norma.HARAKAT.sub("", nama_a or "")))
    ibn_abi_b = bool(_IBN_ABI.search(norma.HARAKAT.sub("", nama_b or "")))
    if ibn_abi_a != ibn_abi_b and ("أبو" in (nama_a or "") or "أبي" in (nama_a or "")) and ("أبو" in (nama_b or "") or "أبي" in (nama_b or "")):
        return "beda"
    kata_a, kata_b = kata_nama(nama_a), kata_nama(nama_b)
    if not kata_a or not kata_b:
        return "sama" if (wa and wb and abs(wa - wb) <= 2) else "ragu"
    # Dua tokoh ber-syuhrah sama dengan nisbah khas berlawanan (mis. «ابن حجر العسقلاني» vs «ابن حجر الهيتمي»)
    na, nb = _nisbah_khas(nama_a), _nisbah_khas(nama_b)
    if na and nb and not (na & nb):
        return "beda"
    if kata_a & kata_b:
        return "sama"
    return "beda"


def _pengarang_terima(nama_a, nama_b, wafat_a=None, wafat_b=None):
    """True bila dua pengarang sah dipasangkan: jika keduanya terisi wajib `sama` (tidak meloloskan `ragu`)."""
    hasil = cocok_pengarang(nama_a, nama_b, wafat_a, wafat_b)
    if hasil == "sama":
        return True
    if hasil == "ragu" and (not (nama_a or "").strip() or not (nama_b or "").strip()):
        return True
    return False


@functools.cache
def _shamela_dasar():
    """Indeks ringan katalog Shamela: (by_id, by_group) tanpa memecah semua judul."""
    try:
        daftar = shamela.isi_katalog()
    except SystemExit:
        return {}, {}
    by_id, by_group = {}, {}
    for r in daftar:
        sid = int(r["shamela_id"])
        by_id[sid] = r
        gid = r.get("group_id")
        if gid:
            by_group.setdefault(gid, []).append(sid)
    return by_id, by_group


@functools.cache
def _indeks_shamela():
    """Indeks katalog Shamela: (by_id, by_padat, by_group)."""
    by_id, by_group = _shamela_dasar()
    if not by_id:
        return {}, {}, {}
    by_padat = {}
    for sid, r in by_id.items():
        for j in pecah_judul(r.get("title_ar") or "", r.get("main_author_name_ar") or ""):
            p = norma.padat(j)
            if len(p) >= 4:
                by_padat.setdefault(p, set()).add(sid)
    return by_id, by_padat, by_group


def shamela_untuk_waqfeya(b):
    """Nomor kitab Shamela yang setara dengan entri Waqfeya `b` (judul pokok/alternatif + kecocokan pengarang
    anti-kerabat/nisbah). Dipakai `waqfeya._di_shamela` dan `edisi`."""
    by_id, by_padat, _ = _indeks_shamela()
    if not by_id:
        return []
    judul_w = pecah_judul(b["judul"], b.get("pengarang") or "")
    calon = set()
    for j in judul_w:
        p = norma.padat(j)
        calon |= by_padat.get(p, set())
    peng_w = b.get("pengarang") or ""
    # Nama di dalam kurung judul Waqfeya hanya dipakai sebagai cadangan bila kolom pengarang tidak memuat kata khas
    # (mis. «محمد بن إسماعيل» pada «تفسير القرآن العظيم (تفسير ابن كثير)»), agar nama pengarang matan di dalam
    # judul syarah («صحيح مسلم بشرح النووي») tidak mencemari pencocokan pengarang syarahnya («النووي»).
    kurung_p = " ".join(x for x in _KURUNG_PENGARANG.findall(b["judul"]) if not _KURUNG_CETAK.match(x))
    peng_w_gab = peng_w if kata_nama(peng_w) else f"{peng_w} {kurung_p}".strip()
    hasil = []
    for sid in sorted(calon):
        r = by_id[sid]
        peng_s = r.get("main_author_name_ar") or ""
        if _beda_riwayat(b["judul"], r["title_ar"]) or not _pengarang_terima(peng_w_gab, peng_s):
            continue
        # Pastikan hubungan judul tidak konflik ukuran/turunan
        hub = [hubungan_judul(jw, js) for jw in judul_w for js in pecah_judul(r.get("title_ar") or "", peng_s)]
        if "sama" in hub:
            hasil.append(sid)
    if hasil:
        return hasil
    # Cadangan: awalan judul Shamela ≥6 huruf (untuk subjudul panjang seperti «المحصول» ↔ «المحصول في علم أصول الفقه»)
    if kata_nama(peng_w_gab):
        for j in judul_w:
            q = norma.padat(j)
            if len(q) < 6:
                continue
            for p_sh, sids in by_padat.items():
                if len(p_sh) >= 6 and (q.startswith(p_sh) or p_sh.startswith(q)):
                    for sid in sorted(sids):
                        r = by_id[sid]
                        peng_s = r.get("main_author_name_ar") or ""
                        if _beda_riwayat(b["judul"], r["title_ar"]) or cocok_pengarang(peng_w_gab, peng_s) != "sama":
                            continue
                        hub = [hubungan_judul(j, js) for js in pecah_judul(r.get("title_ar") or "", peng_s)]
                        if "sama" in hub and sid not in hasil:
                            hasil.append(sid)
    return sorted(hasil)


def _waqfeya_untuk_karya(judul_list, pengarang, wq, wafat=None):
    """(edisi_sama, karya_terkait) dari katalog Waqfeya (jika sudah terunduh) untuk satu karya."""
    if wq is None or not wq.KATALOG.exists():
        return [], []
    wkat = wq.katalog_ringkas()
    kata_kunci = {k for j in judul_list for k in _kata_judul(j) if len(k) >= 3}
    sama, terkait = [], []
    for w, b in wkat.items():
        peng_w = b.get("pengarang") or ""
        jw_list = pecah_judul(b["judul"], peng_w)
        if not any(k in kata_kunci for jw in jw_list for k in _kata_judul(jw)):
            continue
        hubs = {hubungan_judul(ja, jb) for ja in judul_list for jb in jw_list}
        if "sama" in hubs and not any(_beda_riwayat(j, b["judul"]) for j in judul_list):
            if _pengarang_terima(pengarang, peng_w, wafat_a=wafat):
                sama.append((w, b))
        elif "terkait" in hubs:
            terkait.append((w, b))
    return sama, terkait


def _baris_shamela(sid, r, lokal):
    ada = "ADA" if sid in lokal else "-"
    w = _tahun_wafat_sah(r.get("main_author_death_hijri"))
    era = f"ت {w}هـ" if w else "-"
    ekor = ekstrak_ekor_edisi(r.get("title_ar") or "")
    cat = f" | {ekor}" if ekor else ""
    return f"  [{ada:3s}] Shamela {sid:<6d} | {r.get('title_ar', '?')} — {r.get('main_author_name_ar') or '?'} ({era}) | {r.get('category_name_ar') or '?'}{cat}"


def _baris_waqfeya(w, b, wq):
    ada = "ADA" if (wq is not None and wq.ada(w)) else "-"
    ekor = ekstrak_ekor_edisi(b["judul"])
    cat = f" | {ekor}" if ekor else ""
    return f"  [{ada:3s}] Waqfeya {w} | {b['judul']} — {b['pengarang'] or '?'} ({b['halaman']} hal, {b['jumlah_berkas']} berkas){cat}"


def _cari_katalog(item_iter, ambil_judul, ambil_peng, wajib_q, wajib_p, kata_q, kata_p):
    """Filter entri katalog (Shamela atau Waqfeya) yang memuat seluruh kata judul dan pengarang."""
    pres, padat = norma.PRESENTASI.search, norma.padat
    hasil = []
    for key, val in item_iter:
        peng = ambil_peng(val)
        if wajib_p and not (all(c in peng for c in wajib_p) or pres(peng)):
            continue
        raw = ambil_judul(val) + " " + peng
        if wajib_q and not (all(c in raw for c in wajib_q) or pres(raw)):
            continue
        blob = padat(raw)
        if all(k in blob for k in kata_q) and (not kata_p or all(k in padat(peng) for k in kata_p)):
            hasil.append((key, val))
    return hasil


def cetak(kueri, pengarang="", maks=15, wq=None):
    """`edisi <kueri|sid|w…> [pengarang]`: cari kandidat satu karya lintas Shamela dan Waqfeya (offline)."""
    by_id, by_group = _shamela_dasar()
    lokal = set(shamela.punya())
    q = kueri.strip()

    # 1. Input nomor Shamela
    if q.isdigit():
        sid = int(q)
        r = by_id.get(sid)
        if not r:
            raise SystemExit(f"Kitab Shamela {sid} tidak ada di katalog.")
        peng = r.get("main_author_name_ar") or ""
        judul_l = pecah_judul(r.get("title_ar") or "", peng)
        wafat = _tahun_wafat_sah(r.get("main_author_death_hijri"))
        print(f"EDISI KITAB: {judul_l[0] if judul_l else r.get('title_ar')} — {peng or '?'}"
              + (f" (ت {wafat}هـ)" if wafat else ""))
        saudara, sh_terkait, riwayat_lain = {sid}, set(), set()
        satu_grup = set(by_group.get(r.get("group_id"), ()))
        for s2, r2 in by_id.items():
            if s2 == sid:
                continue
            peng2 = r2.get("main_author_name_ar") or ""
            hubs = {hubungan_judul(ja, jb) for ja in judul_l for jb in pecah_judul(r2.get("title_ar") or "", peng2)}
            if "terkait" in hubs and ("sama" not in hubs or s2 in satu_grup):
                sh_terkait.add(s2)
                continue
            if "sama" not in hubs or not _pengarang_terima(peng, peng2, wafat, r2.get("main_author_death_hijri")):
                continue
            if _beda_riwayat(r["title_ar"], r2["title_ar"]):
                riwayat_lain.add(s2)
            else:
                saudara.add(s2)
        print(f"\nKandidat cetakan di Shamela ({len(saudara)}):")
        for s2 in sorted(saudara):
            print(_baris_shamela(s2, by_id[s2], lokal))
        wq_sama, wq_terkait = _waqfeya_untuk_karya(judul_l, peng, wq, wafat)
        print(f"\nKandidat scan di Waqfeya ({len(wq_sama)}):")
        if wq is None or not wq.KATALOG.exists():
            print("  (katalog Waqfeya belum diunduh; jalankan `waqfeya \"<judul>\"` sekali untuk mengunduhnya)")
        elif not wq_sama:
            print("  (tidak ditemukan kandidat karya di katalog Waqfeya)")
        for w, b in wq_sama[:maks]:
            print(_baris_waqfeya(w, b, wq))
        if riwayat_lain:
            print(f"\nRiwayat lain di Shamela ({len(riwayat_lain)}):")
            for s2 in sorted(riwayat_lain):
                print(_baris_shamela(s2, by_id[s2], lokal))
        if sh_terkait or wq_terkait:
            print(f"\nKarya terkait (syarah/mukhtashar/hasyiah, bukan edisi sama — {len(sh_terkait)} Shamela, {len(wq_terkait)} Waqfeya):")
            for s2 in sorted(sh_terkait)[:5]:
                print(_baris_shamela(s2, by_id[s2], lokal))
            for w, b in wq_terkait[:5]:
                print(_baris_waqfeya(w, b, wq))
        print("\nCocokkan riwayat dan data cetak sebelum memakai nomor juz/halaman.")
        return len(saudara) + len(wq_sama)

    # 2. Input nomor Waqfeya (w…) — tetap 100% offline: tolak dengan pesan bersih bila katalog belum diunduh
    if NOMOR_WAQFEYA.fullmatch(q):
        if wq is None or not wq.KATALOG.exists():
            raise SystemExit('Katalog Waqfeya belum diunduh; jalankan `waqfeya "<judul>"` sekali untuk mengunduhnya.')
        b = wq.katalog_ringkas().get(q)
        if not b:
            raise SystemExit(f"Kitab Waqfeya {q} tidak ada di katalog.")
        judul_l = pecah_judul(b["judul"], b.get("pengarang") or "")
        print(f"EDISI KITAB: {judul_l[0] if judul_l else b['judul']} — {b['pengarang'] or '?'}")
        sh_cocok = shamela_untuk_waqfeya(b)
        print(f"\nKandidat cetakan di Shamela ({len(sh_cocok)}):")
        if not sh_cocok:
            print("  (tidak ditemukan di katalog Shamela; pakai Waqfeya ini dan baca dari scan)")
        for s2 in sh_cocok:
            print(_baris_shamela(s2, by_id[s2], lokal))
        wq_sama, _ = _waqfeya_untuk_karya(judul_l, b["pengarang"], wq)
        print(f"\nKandidat scan di Waqfeya ({len(wq_sama)}):")
        for w, bw in wq_sama[:maks]:
            print(_baris_waqfeya(w, bw, wq))
        print("\nCocokkan riwayat dan data cetak sebelum memakai nomor juz/halaman.")
        return len(sh_cocok) + len(wq_sama)

    # 3. Pencarian judul (+ pengarang opsional) lintas Shamela & Waqfeya sekaligus
    kata_q = [norma.padat(k) for k in q.split() if norma.padat(k)]
    kata_p = [p[2:] if p.startswith("ال") and len(p) >= 5 else p
              for k in pengarang.split() if (p := norma.padat(k))]
    if not kata_q:
        raise SystemExit('Tulis judul kitab, nomor Shamela, atau nomor Waqfeya (mis. `edisi "تفسير القرطبي"`).')
    wajib_q, wajib_p = _huruf_wajib(kata_q), _huruf_wajib(kata_p)
    padat = norma.padat
    sh_hits = _cari_katalog(by_id.items(), lambda r: r.get("title_ar") or "", lambda r: r.get("main_author_name_ar") or "",
                            wajib_q, wajib_p, kata_q, kata_p)
    q_gabung = "".join(kata_q)
    sh_hits.sort(key=lambda x: (not padat(x[1].get("title_ar") or "").startswith(q_gabung), len(x[1].get("title_ar") or ""), x[0]))
    wq_hits = []
    if wq is not None and wq.KATALOG.exists():
        wq_hits = _cari_katalog(wq.katalog_ringkas().items(), lambda b: b["judul"], lambda b: b["pengarang"],
                                wajib_q, wajib_p, kata_q, kata_p)
        wq_hits.sort(key=lambda x: (not padat(x[1]["judul"]).startswith(q_gabung), len(x[1]["judul"])))
    print(f"HASIL LINTAS-KATALOG «{q}»" + (f" ({pengarang})" if pengarang else "")
          + f": {len(sh_hits)} Shamela, {len(wq_hits)} Waqfeya")
    print("\nShamela (utamakan bila ada):")
    for sid, r in sh_hits[:maks]:
        print(_baris_shamela(sid, r, lokal))
    if not sh_hits:
        print("  (tidak ada)")
    print("\nWaqfeya (cadangan scan bila tidak ada di Shamela):")
    if wq is None or not wq.KATALOG.exists():
        print("  (katalog Waqfeya belum diunduh)")
    elif not wq_hits:
        print("  (tidak ada)")
    for w, b in wq_hits[:maks]:
        print(_baris_waqfeya(w, b, wq))
    return len(sh_hits) + len(wq_hits)
