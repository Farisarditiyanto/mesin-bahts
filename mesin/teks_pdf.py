# SPDX-License-Identifier: AGPL-3.0-or-later
"""Teks PDF buatan Word supaya bisa disalin dan dicari (Ctrl+F) dengan benar. Dipanggil `rakit` sesudah Word menyimpan PDF.

Word menulis huruf Arab di PDF dalam urutan tampak (kiri ke kanan); pembaca PDF (Chrome/Edge, Firefox, SumatraPDF)
membaliknya per huruf. Glyph sambungan (mis. «لا», «في», «لله») dipetakan Word ke beberapa huruf dalam urutan baca,
sehingga ikut terbalik: «الله» tersalin «هللا», «المقدمة» «املقدمة». Word juga kadang memetakan glyph harakat ke huruf
lain (syaddah jadi «ن»). Yang diubah hanya peta glyph -> huruf (ToUnicode); tampilan halaman tidak berubah.
"""
import os, re, unicodedata
from pathlib import Path

from berkas import sementara
from norma import norm, padat

ARAB = re.compile(r"[\u0600-\u06ff\ufb50-\ufdff\ufe70-\ufeff]")
HARAKAT = re.compile(r"[\u064b-\u065f\u0670]")


def _berkas_huruf():
    """{nama huruf tanpa spasi: berkas} dari daftar huruf Windows (semua akun, lalu akun ini)."""
    import winreg
    hasil = {}
    for akar, folder in ((winreg.HKEY_LOCAL_MACHINE, Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"),
                         (winreg.HKEY_CURRENT_USER, Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts")))):
        try:
            k = winreg.OpenKey(akar, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts")
        except OSError:
            continue
        with k:
            for i in range(winreg.QueryInfoKey(k)[1]):
                nama, nilai, _ = winreg.EnumValue(k, i)
                nama = re.sub(r"\s*\(.*\)$", "", nama).replace(" ", "")
                hasil.setdefault(nama, Path(nilai) if os.path.isabs(nilai) else folder / nilai)
    return hasil


def _isi_glyph(basefont, daftar):
    """{nomor glyph: (teks, kode)} dari berkas huruf yang dipakai Word; {} kalau berkasnya tidak ketemu.
    teks = huruf yang digambar glyph itu: dari cmap, lalu lewat GSUB ke bentuk awal/tengah/akhir (ganti tunggal) dan
    ligatur (gabungan bagian-bagiannya); None kalau tidak tunggal. kode = huruf Unicode glyph itu sendiri di cmap."""
    from fontTools.ttLib import TTFont
    ps = basefont.split("+", 1)[-1]            # «BCDLEE+TraditionalArabic-Bold»; nama panjang dipotong Word
    keluarga = ps.split("-")[0]
    for nama, berkas in daftar.items():
        if not nama.startswith(keluarga) or not berkas.exists():
            continue
        try:
            t = TTFont(str(berkas), lazy=True, fontNumber=0)
            nama_ps = (t["name"].getDebugName(6) or "").replace(" ", "")
            if not (nama_ps.startswith(ps) or ps.startswith(nama_ps)):
                continue
            kode, teks = {}, {}
            for k, g in sorted(t.getBestCmap().items()):
                kode.setdefault(g, chr(k))
                teks.setdefault(g, set()).add(_baca(chr(k)))
            sub = []
            if "GSUB" in t:
                for lk in t["GSUB"].table.LookupList.Lookup:
                    for st in lk.SubTable:
                        jenis = lk.LookupType
                        if jenis == 7:
                            jenis, st = st.ExtSubTable.LookupType, st.ExtSubTable
                        sub.append((jenis, st))
            for _ in range(3):                       # ligatur dari bentuk hasil ganti tunggal, dan sebaliknya
                for jenis, st in sub:
                    if jenis == 1:
                        for dari, jadi in st.mapping.items():
                            if dari in teks and jadi not in kode:   # glyph yang punya kode sendiri: kodenya yang benar
                                teks.setdefault(jadi, set()).update(teks[dari])
                    elif jenis == 4:
                        for awal, daftar_lig in st.ligatures.items():
                            for lig in daftar_lig:
                                bagian = [awal] + list(lig.Component)
                                if lig.LigGlyph not in kode and all(len(teks.get(b, ())) == 1 for b in bagian):
                                    teks.setdefault(lig.LigGlyph, set()).add("".join(next(iter(teks[b])) for b in bagian))
            urut = {g: i for i, g in enumerate(t.getGlyphOrder())}
            return {urut[g]: (next(iter(teks.get(g, ()))) if len(teks.get(g, ())) == 1 else None, kode.get(g))
                    for g in set(teks) | set(kode) if g in urut}
        except Exception:
            continue
    return {}


def _baca(s):
    """Bentuk sajian (mis. U+FC60 « َّ» atau U+FEFB «لا») -> huruf biasa, tanpa spasi pengantar harakat lepas."""
    return unicodedata.normalize("NFKC", s).strip()


def _dasar(s):
    return HARAKAT.sub("", s).replace(" ", "")


def _peta(teks):
    """ToUnicode -> {glyph: teks}, bfchar dan bfrange."""
    peta = {}
    hx = lambda h: bytes.fromhex(h).decode("utf-16-be")
    for blok in re.findall(r"beginbfchar(.*?)endbfchar", teks, re.S):
        for a, b in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", blok):
            peta[int(a, 16)] = hx(b)
    for blok in re.findall(r"beginbfrange(.*?)endbfrange", teks, re.S):
        for a, b, d in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[[^\]]*\]|<[0-9A-Fa-f]*>)", blok):
            a, b = int(a, 16), int(b, 16)
            if d.startswith("["):
                for i, x in enumerate(re.findall(r"<([0-9A-Fa-f]*)>", d)):
                    peta[a + i] = hx(x)
            else:
                s = hx(d[1:-1])
                for i in range(b - a + 1):
                    peta[a + i] = s[:-1] + chr(ord(s[-1]) + i) if s else s
    return peta


def _cmap(peta):
    baris = [f"<{g:04X}> <{s.encode('utf-16-be').hex().upper()}>" for g, s in sorted(peta.items())]
    blok = "".join(f"{len(baris[i:i + 100])} beginbfchar\n" + "\n".join(baris[i:i + 100]) + "\nendbfchar\n"
                   for i in range(0, len(baris), 100))
    return ("/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
            "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
            "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n" + blok +
            "endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n").encode("latin1")


def _gid(f):
    """Nomor glyph di PDF (CID) -> nomor glyph di berkas huruf. Word kadang menulis peta CIDToGIDMap sendiri, bukan
    Identity (nomor halaman: CID 49 = glyph ١ nomor 206); tanpa peta itu glyph ١ dibaca sebagai huruf lain."""
    peta = f["/DescendantFonts"][0].get_object().get("/CIDToGIDMap")
    if peta is None or not hasattr(peta.get_object(), "get_data"):   # /Identity
        return lambda c: c
    data = peta.get_object().get_data()
    return lambda c: int.from_bytes(data[2 * c:2 * c + 2], "big") if 2 * c + 2 <= len(data) else c


def _baris(hal):
    """[(y, x, ukuran, teks)] tiap potongan teks halaman (y dari bawah halaman, satuan pt)."""
    out = []
    def lihat(t, cm, tm, fd, fs):
        if t.strip():
            out.append((tm[5] * cm[3] + cm[5], tm[4] * cm[0] + cm[4], abs(fs * tm[3] * cm[3]), t))
    hal.extract_text(visitor_text=lihat)
    return out


TEPI = 65  # pt dari tepi atas/bawah: nomor halaman (1,25 cm) ada di sini, matan dan catatan kaki (tepi 2,5 cm) tidak
ANGKA = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _ada(kata, teks):
    """`kata` (padat) ada di `teks`, boleh dengan urutan huruf yang tertukar: teks PDF Word membalik huruf glyph
    sambungan («بين» tersalin «بني», «الإسلام» «اإلسالم») dan kadang memindah ujung baris ke awalnya («…عند الفقهاء»
    tersalin «ءاحكم … عند الفقه»), jadi tiap baris juga dicoba diputar. Huruf yang kurang atau lebih tetap tidak ada
    («بيع» bukan «البيع»)."""
    calon = [padat(teks)] + [p[i:] + p[:i] for p in map(padat, teks.splitlines()) for i in range(1, len(p))]
    urut, n = sorted(kata), len(kata)
    return any(kata in c or any(sorted(c[i:i + n]) == urut for i in range(len(c) - n + 1)) for c in calon)


def periksa(pdf, bahan):
    """Peringatan sesudah rakit (tidak menggagalkan): titik-titik isian di sampul, @judul yang tidak ada di sampul, jenis
    angka nomor halaman yang tidak sesuai @angka, dan baris terakhir matan halaman yang berakhir «:». Teks PDF buatan Word
    tidak tersalin persis (huruf sambung, angka ٠-٩), jadi pencocokannya longgar: yang diperingatkan hanya yang jelas."""
    import pypdf
    meta, fmt = bahan["meta"], bahan["format"]
    halaman = pypdf.PdfReader(pdf).pages
    pesan = []
    awal = 0 if meta.get("bentuk") == "kitab" or meta.get("tanpa_sampul") else 1  # halaman 1 = sampul (bukan potongan --fasl)
    if awal and halaman:
        sampul = halaman[0].extract_text() or ""
        polos = re.sub(r"\s+", "", sampul.replace("…", "...")).translate(ANGKA)
        nim = str(meta.get("nim") or "").translate(ANGKA)
        for n in {nim, nim[::-1]} - {""}:                # nomor mahasiswa contoh «000000000» bukan isian kosong
            polos = polos.replace(n, "")
        if re.search(r"\.{4,}|0{4,}", polos):
            pesan.append("titik-titik isian («....» atau «٠٠٠٠») masih tercetak di sampul: isi atau hapus di "
                         + ("templat Word (@templat)." if meta.get("templat") else "naskah."))
        hilang = [k for k in norm(str(meta.get("judul", ""))).split() if padat(k) and not _ada(padat(k), sampul)]
        if hilang:
            pesan.append(f"sampul tidak memuat @judul persis (tidak terbaca: {' '.join(hilang)}): samakan judul di "
                         + ("sampul templat Word dengan @judul." if meta.get("templat") else "sampul dengan @judul."))
    hindi = meta.get("angka", "hindi") == "hindi"
    nomor, ujung = {}, []
    batas = (float(fmt["matan"]) + float(fmt["catatan"])) / 2   # matan dan judul; catatan kaki lebih kecil
    for i, hal in enumerate(halaman[awal:], awal + 1):
        tinggi = float(hal.mediabox.height)
        potong = sorted(_baris(hal), key=lambda p: -p[1])   # kanan ke kiri
        # kaki halaman = nomor halaman saja (@templat yang nomornya di kepala halaman: tidak diperiksa)
        kaki = re.sub(r"[\s\u200c\u200e\u200f]", "", "".join(t for y, x, u, t in potong if y < TEPI))
        if kaki:
            nomor[i] = kaki.isascii() and kaki.isdigit()   # ٠-٩ terbaca benar sesudah betulkan (_gid)
        matan = [p for p in potong if TEPI < p[0] < tinggi - TEPI and p[2] >= batas]
        if matan:
            y0 = min(p[0] for p in matan)
            akhir = "".join(t for y, x, u, t in matan if abs(y - y0) < 2).strip()
            while re.search(r"\([^()]{1,4}\)$", akhir):   # nomor catatan kaki «(١)» sesudah «:»
                akhir = re.sub(r"\s*\([^()]{1,4}\)$", "", akhir)
            if akhir.endswith(":"):
                ujung.append(i)
    if hindi:
        salah = [i for i, latin in nomor.items() if latin]
    else:   # @nomor abjad: halaman sebelum nomor 1 bernomor huruf, bukan angka
        pertama = min((i for i, latin in nomor.items() if latin), default=None)
        abjad = meta.get("nomor") in ("abjad", "mukadimah")
        salah = [i for i, latin in nomor.items() if not latin and not (abjad and (pertama is None or i < pertama))]
    if salah:
        jenis, lawan = ("0123", "٠١٢٣ (bawaan)") if hindi else ("bukan 0123", "0123 (@angka: latin)")
        pesan.append(f"nomor halaman tercetak {jenis} padahal @angka {lawan} di {len(salah)} halaman "
                     f"(halaman PDF ke-{', '.join(map(str, salah[:5]))}{' …' if len(salah) > 5 else ''}): rakit lagi.")
    if ujung:
        pesan.append(f"baris terakhir matan berakhir «:» (pengantar terpisah dari isinya di halaman berikutnya) di halaman "
                     f"PDF ke-{', '.join(map(str, ujung))}: lihat halamannya; perlu → pendekkan/panjangkan paragraf sebelumnya.")
    return pesan


def betulkan(pdf):
    """Tulis ulang peta glyph -> huruf tiap huruf Word (Type0) di `pdf`. Hasil: jumlah glyph yang petanya diubah."""
    import pypdf
    daftar = _berkas_huruf() if os.name == "nt" else {}
    w = pypdf.PdfWriter(clone_from=pypdf.PdfReader(pdf))
    sudah, ubah = set(), 0
    for hal in w.pages:
        for f in (hal["/Resources"].get("/Font") or {}).values():
            f = f.get_object()
            tu = f.raw_get("/ToUnicode") if f.get("/Subtype") == "/Type0" else None
            if tu is None or tu.idnum in sudah:
                continue
            sudah.add(tu.idnum)
            lama = _peta(tu.get_object().get_data().decode("latin1"))
            asli = _isi_glyph(str(f["/BaseFont"])[1:], daftar) if any(ARAB.search(s) for s in lama.values()) else {}
            gid = _gid(f)
            baru = {}
            for g, s in lama.items():
                teks, kode = asli.get(gid(g), (None, None))
                # Word memetakan glyph menurut kemunculan pertamanya: ligatur «نا» bisa jadi «نًّ», syaddah jadi «ن».
                # Huruf yang digambar glyph itu (dari font) menang kalau hurufnya (tanpa harakat) berbeda
                if teks and ARAB.search(teks) and _dasar(teks) != _dasar(s):
                    s = teks
                # glyph sambungan berisi beberapa huruf Arab (juga ﷺ = «صلى الله عليه وسلم»): dibalik, supaya kembali
                # urut sesudah dibalik pembaca PDF
                if len(s) > 1 and ARAB.search(s):
                    s = s[::-1]
                ubah += s != lama[g]
                baru[g] = s
            tu.get_object().set_data(_cmap(baru))
    with sementara(pdf) as part:
        with open(part, "wb") as h:
            w.write(h)
    return ubah
