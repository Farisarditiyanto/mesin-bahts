# SPDX-License-Identifier: AGPL-3.0-or-later
"""`ekspor`: satu kitab yang sudah diunduh (Shamela atau Waqfeya) jadi satu .txt (UTF-8) untuk dibaca.

Satu paragraf satu baris. Judul kitab = baris «# …»; judul bab dari daftar isi Shamela = «##» untuk tingkat teratas,
satu «#» lagi tiap tingkat di bawahnya;
penanda juz/halaman cetak «[ج١ ص ٥]» di baris sendiri di awal tiap halaman, حاشية sesudah halamannya di bawah garis
pemisah. Baris kosong hanya sebelum judul, sebelum penanda halaman, dan sesudah حاشية. Bukan bahan bahts: `cek` tetap membaca kitab lokal.
"""
import re
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape

import shamela, waqfeya
from berkas import sementara
from dasar import AD, HORMAT_CETAK
from norma import per_halaman

KONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")  # karakter kendali: bukan teks kitab
JUDUL = re.compile(shamela.JUDUL.pattern + r"(?P<teks>.*?)</span>", re.S | re.X)
PEMISAH_HTML = frozenset(("br", "p", "div", "li", "tr", "td", "th"))
BARIS = re.compile(r"\r\n?|\n")
NAMA_TERLARANG = re.compile(r'[\\/:*?"<>|\x00-\x1f]')  # tidak boleh di nama berkas Windows
TINGKAT_MAKS = 4  # judul yang lebih dalam tetap tingkat 4
PEMISAH_HASYIAH = "ـــــــــــــــ"
AKHIR_PARAGRAF = re.compile(r"[.:؟!*»)\]]\s*$")  # baris OCR yang menutup kalimat
# baris judul OCR (pendek, diawali kata judul): tidak disambung ke baris sebelum atau sesudahnya
JUDUL_OCR = re.compile(r"^(?:ال)?(?:باب|فصل|مبحث|مطلب|كتاب|مسألة|تمهيد|مقدمة|خاتمة|فهرس)\b")
KATA_JUDUL_MAKS = 8
KATA_JUDUL_PENDEK = 3  # baris sependek ini yang membuka paragraf baru («كلمة شكر», «الألف») = judul juga
AWAL_HASYIAH = re.compile(r"^\s*\([0-9٠-٩۰-۹]+\)")  # «(١) …»: catatan kaki selalu paragraf baru


class _TeksHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.teks = []

    def handle_data(self, data):
        self.teks.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in PEMISAH_HTML:
            self.teks.append("\n")

    def handle_endtag(self, tag):
        self.handle_starttag(tag, ())


def _html(s):
    p = _TeksHTML()
    p.feed(s)
    p.close()
    return "".join(p.teks)


def _rapi(s):
    return " ".join(KONTROL.sub("", s).translate(HORMAT_CETAK).replace("¬", "").split())


def bersih(s):
    """Teks satu baris kitab untuk dibaca: kalimat hormat untuk ligatur yang tidak ada di huruf, tanpa tag HTML,
    entitas HTML jadi hurufnya («&amp;» -> «&»), tanpa tanda «¬» Shamela di nomor حاشية («(¬١)» -> «(١)»)."""
    return _rapi(_html(s))


def tanpa_judul_ulang(paragraf):
    """Paragraf biasa yang isinya sama dengan judul tepat sebelum/sesudahnya dibuang: judul daftar isi yang disisipkan
    di awal rekaman bisa bersebelahan dengan baris judul yang sama di teks kitab."""
    judul = lambda i: 0 <= i < len(paragraf) and paragraf[i][0].startswith("Heading")
    return [(g, t) for i, (g, t) in enumerate(paragraf)
            if not (g == "Normal" and any(judul(j) and paragraf[j][1] == t for j in (i - 1, i + 1)))]


def isi_txt(paragraf):
    """[(gaya, teks)] -> isi berkas .txt. Gaya: Judul (kitab), Heading<n> (bab tingkat n), Pengarang, Halaman, Hasyiah,
    Normal."""
    out, lalu = [], ""
    for gaya, isi in tanpa_judul_ulang(paragraf):
        judul = gaya.startswith("Heading")
        # baris kosong sebelum penanda halaman, sebelum judul (yang tepat di bawah penanda halaman atau judul lain
        # menempel), dan sesudah حاشية: tanpa itu akhir حاشية tidak kelihatan
        if out and out[-1] and (gaya == "Halaman" or judul and not (lalu == "Halaman" or lalu.startswith("Heading"))
                                or lalu == "Hasyiah" != gaya):
            out.append("")
        out.append("# " + isi if gaya == "Judul" else "#" * (int(gaya[-1]) + 1) + " " + isi if judul else isi)
        lalu = gaya
    return "\n".join(out) + "\n"


def tulis(tujuan, paragraf):
    """Berkas .txt UTF-8 berakhiran baris LF (ditulis lewat nama sementara: yang ada = utuh)."""
    with sementara(tujuan) as tmp:
        tmp.write_bytes(isi_txt(paragraf).encode("utf8"))


def _judul(teks, tingkat):
    return f"Heading{min(tingkat, TINGKAT_MAKS)}", teks


def _baris_body(teks, tingkat):
    """Paragraf matan satu halaman: judul bertanda di body jadi judul, titik yang tertinggal sesudah judul
    («</span>.») dibuang."""
    out = []
    teks = JUDUL.sub(lambda m: f"\n\x01{m['nomor']}\x02{escape(bersih(m['teks']))}\n", teks)
    for b in BARIS.split(_html(teks)):
        if b.startswith("\x01"):
            n, t = b[1:].split("\x02", 1)
            if t := _rapi(t):
                out.append(_judul(t, tingkat.get(int(n), TINGKAT_MAKS)))
        elif (t := _rapi(b)) and not (not t.strip(".") and out and out[-1][0].startswith("Heading")):
            out.append(("Normal", t))
    return out


def _shamela(sid):
    m = shamela.info(sid)
    judul = shamela.judul_rekaman(sid)
    tingkat = {n: k for daftar in judul.values() for n, _, k in daftar}
    out = [("Judul", bersih(m["title_ar"])), ("Pengarang", bersih(m.get("main_author_name_ar") or ""))]
    tadi = (object(), -1)  # (juz, halaman) penanda terakhir
    # urut page_id = urut kitab; urutan berkas unduhan tidak selalu begitu (mis. صحيح البخاري: rekaman مقدمة dan
    # hadits berselang-seling), dan judul daftar isi menunjuk page_id
    for p in sorted(shamela.rekaman(sid), key=lambda p: p["page_id"]):
        juz = p.get("part")
        hasyiah = dict(per_halaman(p, "footnotes")) if p.get("footnotes") else {}
        potong = per_halaman(p)
        bertanda = {int(m["nomor"]) for m in JUDUL.finditer(p.get("body") or "")}
        for k, (hal, teks) in enumerate(potong):
            # satu penanda per halaman cetak (kitab hadits menyimpan tiap hadits sebagai rekaman sendiri); nomor yang
            # mundur ikut ditandai: sesudah مقدمة المحقق nomor kitab mulai ١ lagi
            if isinstance(hal, int) and (juz, hal) != tadi:  # rekaman tanpa nomor halaman: tanpa penanda
                tadi = juz, hal
                out.append(("Halaman", f"[{juz + ' ' if juz and not juz.isdigit() else 'ج' + juz + ' ' if juz else ''}ص {hal}]"
                            .translate(AD)))
            if k == 0:  # judul daftar isi yang tidak bertanda di body: di awal rekamannya
                out += [_judul(t, d) for n, j, d in judul.get(p["page_id"], ()) if n not in bertanda and (t := bersih(j))]
            out += _baris_body(teks, tingkat)
            # حاشية tanpa penanda halaman di rekaman banyak halaman: semuanya sesudah halaman terakhir rekaman itu
            isi = hasyiah.get(hal, "") if len(hasyiah) > 1 else ("".join(hasyiah.values()) if k == len(potong) - 1 else "")
            if baris := [t for b in BARIS.split(isi) if (t := bersih(b))]:
                out += [("Hasyiah", PEMISAH_HASYIAH), *(("Hasyiah", t) for t in baris)]
    return m["title_ar"], out


def _waqfeya(w):
    d = waqfeya.data(w)
    out = [("Judul", bersih(d["judul"])), ("Pengarang", bersih(d.get("pengarang") or ""))]
    for i, nama in enumerate(d["berkas"], 1):
        if len(d["berkas"]) > 1:
            out.append(("Heading1", bersih(nama)))
        for n, teks in enumerate(waqfeya.ocr(w, i), 1):
            out.append(("Halaman", f"[PDF ص {n}]".translate(AD)))
            out += [("Normal", t) for t in paragraf_ocr(teks)]
    return d["judul"], out


def paragraf_ocr(teks):
    """Baris OCR satu halaman -> paragraf: baris yang tidak menutup kalimat disambung baris berikutnya (sisa kalimat yang
    turun baris), kecuali baris berikutnya awal catatan kaki «(١)»; baris judul («الباب الثاني», atau baris pendek yang membuka paragraf) berdiri sendiri."""
    out, tutup = [], True  # tutup: paragraf terakhir tidak boleh disambung
    for b in teks.splitlines():
        if not (t := bersih(b)):
            tutup = True
            continue
        judul = t.isdecimal() or JUDUL_OCR.match(t) is not None and len(t.split()) <= KATA_JUDUL_MAKS
        if out and not tutup and not judul and not AWAL_HASYIAH.match(t):
            out[-1] += " " + t
        else:
            out.append(t)
            judul = judul or (len(t.split()) <= KATA_JUDUL_PENDEK and not AWAL_HASYIAH.match(t))
        tutup = judul or AKHIR_PARAGRAF.search(out[-1]) is not None
    return out


def ekspor(kitab, ke):
    """Tiap kitab (nomor Shamela atau w…) -> <ke>/<judul> (<nomor>).txt; yang belum diunduh diunduh dulu. Nomor di nama
    berkas: kitab lain yang judulnya sama tidak tertimpa. Kembalikan jalurnya."""
    kitab = list(dict.fromkeys(map(str, kitab)))
    ke = Path(ke).expanduser()
    ke.mkdir(parents=True, exist_ok=True)
    ww = [x for x in kitab if str(x).startswith("w")]
    gagal = (shamela.ambil(*[x for x in kitab if x not in ww]) if len(ww) < len(kitab) else []) + (waqfeya.ambil(*ww) if ww else [])
    if gagal:
        raise SystemExit(f"Belum terunduh: {', '.join(map(str, gagal))} (lihat pesan di atas).")
    hasil = []
    for x in kitab:
        judul, paragraf = _waqfeya(x) if x in ww else _shamela(x)
        tujuan = ke / f"{NAMA_TERLARANG.sub(' ', judul).strip()[:120]} ({x}).txt"
        try:
            tulis(tujuan, paragraf)
        except PermissionError:  # Windows: berkas yang sedang dikunci program lain tidak bisa diganti
            raise SystemExit(f"{tujuan} sedang dibuka program lain: tutup dulu, lalu ulangi.") from None
        print(f"{x}\t{tujuan}")
        hasil.append(tujuan)
    return hasil
