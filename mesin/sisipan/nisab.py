# SPDX-License-Identifier: AGPL-3.0-or-later
"""#D نسب: النسب الأربع بين الكليين (التساوي، العموم والخصوص المطلق، العموم والخصوص الوجهي، التباين) sebagai lingkaran
bertanda huruf (أ، ب) bergaya buku mantiq lama; daerah bersama diarsir. Kalimat حكم tiap nisbah disusun mesin."""
import norma
from sisipan import E, Salah, pisah

NAMA = "نسب"
URAIAN = ("pasangan كلي dan nisbahnya, satu baris tiap pasangan (paling banyak empat): «نسبة: أ | ب | nisbah»; nisbah = "
          "تساو، عموم مطلق (أ lebih umum), عموم وجهي, atau تباين")
KUNCI = {"نسبة": "أ | ب | تساو/عموم مطلق/عموم وجهي/تباين"}
CONTOH = """#D نسب | الشكل (11): النسب الأربع بين الكليين
#D نسبة: الإنسان | الناطق | تساو
#D نسبة: الحيوان | الإنسان | عموم مطلق
#D نسبة: الحيوان | الأبيض | عموم وجهي
#D نسبة: الإنسان | الحجر | تباين"""

# kata kunci -> (nama nisbah, kalimat حكمها: {a}/{b} = nama كلي, {a_}/{b_} = tanpa «ال»)
NISAB = {
    "تساو": ("التساوي", "كل {a_} {b_}، وكل {b_} {a_}"),
    "مطلق": ("العموم والخصوص المطلق", "كل {b_} {a_}، وبعض {a} ليس ب{b_}"),
    "وجه": ("العموم والخصوص الوجهي", "بعض {a} {b_}، وبعض {a} ليس ب{b_}، وبعض {b} ليس ب{a_}"),
    "تباين": ("التباين", "لا شيء من {a} ب{b_}، ولا شيء من {b} ب{a_}"),
}


def urai(n_kepala, baris):
    pasangan = []
    for n, _, v in baris:
        bagian = pisah(v)
        jenis = next((k for k in NISAB if k in norma.norm(bagian[2])), None) if len(bagian) == 3 else None
        if len(bagian) != 3 or not all(bagian) or not jenis:
            raise Salah(n, f"«نسبة:» harus berbentuk «{KUNCI['نسبة']}»")
        pasangan.append((bagian[0], bagian[1], jenis))
    if not 1 <= len(pasangan) <= 4:
        raise Salah(n_kepala, "نسب butuh satu sampai empat baris «#D نسبة: …»")
    return pasangan


ARSIR = ('<pattern id="arsir" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         '<line x1="0" y1="0" x2="0" y2="4"/></pattern>')


def _venn(jenis):
    """SVG 120×72: lingkaran أ di kanan, ب di kiri (bacaan RTL); daerah أ∩ب diarsir; huruf di daerah masing-masing."""
    huruf = lambda x, y, t: f'<text x="{x}" y="{y}">{t}</text>'
    if jenis == "تساو":
        bentuk = '<circle cx="60" cy="36" r="30" class="isi"/>'
        teks = huruf(60, 42, "أ = ب")
    elif jenis == "مطلق":
        bentuk = '<circle cx="60" cy="36" r="33"/><circle cx="48" cy="40" r="17" class="isi"/>'
        teks = huruf(78, 30, "أ") + huruf(48, 46, "ب")
    elif jenis == "وجه":
        bentuk = ('<clipPath id="kiri"><circle cx="46" cy="36" r="28"/></clipPath><circle cx="74" cy="36" r="28"/>'
                  '<circle cx="46" cy="36" r="28"/><circle cx="74" cy="36" r="28" class="isi" clip-path="url(#kiri)"/>')
        teks = huruf(88, 42, "أ") + huruf(32, 42, "ب")
    else:
        bentuk = '<circle cx="88" cy="36" r="24"/><circle cx="32" cy="36" r="24"/>'
        teks = huruf(88, 42, "أ") + huruf(32, 42, "ب")
    return f'<svg class="venn" viewBox="0 0 120 72" width="120" height="72"><defs>{ARSIR}</defs>{bentuk}{teks}</svg>'


def html(d, angka):
    """Satu tabel bergaris ganda (seperti syarah mantiq cetakan lama): kepala = nama nisbah, lalu lingkaran, lalu
    keterangan huruf dan kalimat حكمها."""
    kepala, gambar, ket = "", "", ""
    for a, b, jenis in d:
        nama, hukm = NISAB[jenis]
        tanpa = lambda s: s[2:] if s.startswith("ال") and len(s.split()[0]) > 3 else s
        kalimat = hukm.format(a=a, b=b, a_=tanpa(a), b_=tanpa(b))
        kepala += f"<th>{nama}</th>"
        gambar += f'<td class="tengah">{_venn(jenis)}</td>'
        ket += f'<td class="tengah hukm"><span class="n">أ: {E(a)}، ب: {E(b)}</span><br>{E(kalimat)}</td>'
    return f'<table class="tbl arbaa"><tr>{kepala}</tr><tr>{gambar}</tr><tr>{ket}</tr></table>'
