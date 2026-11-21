# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pemeriksaan bahasa akademik Arab dan keseimbangan panjang bagian untuk `cek`:
- pronomina orang pertama yang dilarang («أقول»، «قلت:»، «قلنا»، «أرجح»، «نرجح»، «في رأيي»؛ أبو سليمان، ص193);
- tanda baca Latin nyasar di tengah kalimat Arab (`,`/`;`/`?`) dan «و » kata sambung yang terpisah spasi;
- jejak obrolan/klise AI berat di luar kutipan;
- ketimpangan mencolok panjang antarbagian setingkat (أبو سليمان، ص194-195).

Semuanya perhatian (tidak pernah GAGAL), hanya pada paragraf matan penulis sendiri (#P) di luar tanda petik, ayat,
hadits, rumus, dan tautan; tidak dijalankan untuk `@bentuk: kitab`."""
import re

import norma
from dasar import JUDUL_BAB, JUDUL_ISI, TAKHRIJ_AWAL, ekor
from petik import seragam

URL_POLA = re.compile(r"https?://\S+|www\.\S+|10\.\d{4,}/\S+", re.I)
# Pengungkapan diri AI (tidak pernah sah di naskah bahts)
AI_TERUNGKAP = re.compile(
    r"بصفتي نموذج ذكاء اصطناعي|كنموذج لغوي|كنموذج ذكاء اصطناعي|كمساعد ذكاء اصطناعي"
    r"|لا أستطيع تصفح الإنترنت|بيانات تدريبي|as an ai language model|as a large language model",
    re.I,
)
# Pronomina orang pertama yang dilarang أبو سليمان، كتابة البحث العلمي، ص193:
# «أرجح» tanpa awalan «أنا/إني» sering berupa isim tafdhil fiqih («أرجح القولين»، «أرجح ما قيل») sehingga hanya ditandai
# bila diawali «أنا/إني»; «قلت» dibatasi ke «قلت:» agar tidak salah menangkap fi'il «قلّت غلتها».
PRONOMINA_PERTAMA = re.compile(
    r"(?<![ء-ي])(?:[وف]?(?:أقول|اقول|قلنا|نرجح|في رأيي|في رايي)"
    r"|[وف]?(?:أنا|انا|إني|اني)\s+(?:أرجح|ارجح))(?![ء-ي])"
)
QULTU_AWAL = re.compile(r"(?<![ء-ي])[وف]?قلت\s*:")
RIWAYAT_PENGANTAR = re.compile(r"(?:عن\s+\S+[^.]{0,60}قال|أتيت رسول الله|حدثنا|أخبرنا)")
# Tanda baca Latin nyasar di tengah teks Arab (seharusnya «،»/«؛»/«؟») dan «و » terpisah spasi dari kata sesudahnya
TANDA_LATIN_ARAB = re.compile(r"(?<=[ء-ي])\s*([,;])(?=\s*[ء-ي])|(?<=[ء-ي])\s*(\?)")
WAW_PISAH = re.compile(r"(?<![ء-ي])و[ \t]+(?=[ء-ي]{2,})")
# Klise/calque AI berat (daftar ketat agar tidak salah menangkap ungkapan ilmiah Arab baku)
KLISE_AI = re.compile(
    r"(?<![ء-ي])(?:في عالم اليوم|في عالمنا المعاصر|يلعب دورا محوريا|تلعب دورا محوريا"
    r"|يمثل نقلة نوعية|تمثل نقلة نوعية|يغير قواعد اللعبة|تغير قواعد اللعبة"
    r"|إطلاق العنان|اطلاق العنان|تجربة مستخدم سلسة)(?![ء-ي])"
)
# Bagian yang secara wajar lebih ringkas sehingga tidak dinilai timpang terhadap bagian setingkatnya
RINGKAS_WAJAR = re.compile(
    r"^(?:(?:الفصل|المبحث|المطلب)\s+(?:التمهيدي|الختامي)(?![ء-ي])"
    r"|(?:(?:الفصل|المبحث|المطلب)\s+[^:：]+[:：]\s*)?"
    r"(?:ال)?(?:تمهيد|مدخل|مقدم[ةه]|خاتم[ةه]|ترجيح|صور[ةه]\s+المسأل[ةه]|تحرير\s+محل\s+النزاع)(?![ء-ي]))"
)
KATA_TIMPANG_MIN = 500  # bagian terpanjang minimal sebanyak ini agar bahts pendek tidak berisik
RASIO_TIMPANG = 5.0  # terpanjang / terpendek >= 5x dianggap timpang mencolok


def _tanpa_kutipan(teks):
    """Ganti pasangan kutipan «…» dan "…" dengan penanda non-spasi (\x00) agar «و«…»» tidak berubah jadi «و »."""
    teks, lama = seragam(teks), None
    while teks != lama:
        teks, lama = re.sub(r'«[^«»]*»|"[^"«»]*"', "\x00", teks), teks
    return teks


def _teks_penulis(runs, catatan):
    """Teks paragraf #P milik penulis sendiri; ayat {Q:}, hadits {H:}/takhrij, rumus, URL, dan kutipan diganti
    penanda non-spasi (\x00) agar jarak asli di sekitar «و» dan tanda baca tidak berubah."""
    bagian, buf, hadits = [], [], False
    for r in runs:
        if "fn" in r:
            isi = "".join(x.get("t", "") for x in catatan[r["fn"]]["runs"]).strip()
            if hadits or TAKHRIJ_AWAL.match(isi) or isi.startswith("متفق عليه"):
                bagian.append("\x00")
            else:
                bagian.append("".join(buf))
            buf, hadits = [], False
        elif str(r.get("bm", "")).startswith("h_"):
            hadits = True
        elif r.get("q") or r.get("omml"):
            buf.append("\x00")
        elif "t" in r:
            buf.append(r["t"])
    if hadits:
        bagian.append("\x00")
    elif buf:
        bagian.append("".join(buf))
    teks = URL_POLA.sub("\x00", "".join(bagian))
    return _tanpa_kutipan(teks)


def periksa_gaya(blok, catatan):
    """Perhatian bahasa akademik Arab dan jejak AI pada paragraf matan (#P) di luar tanda petik."""
    hasil = []
    for b in blok:
        if b["k"] == "R":
            break
        if b["k"] != "P" or "n" not in b:
            continue
        teks = _teks_penulis(b["runs"], catatan)
        if not teks.replace("\x00", "").strip():
            continue
        tampil = teks.replace("\x00", "…")
        polos = norma.HARAKAT.sub("", teks)
        n = b["n"]
        if m := AI_TERUNGKAP.search(polos):
            hasil.append(f"baris {n}: teks memuat ungkapan sistem AI «{m.group(0)}»: hapus seluruh kalimat obrolan AI{ekor(tampil)}")
            continue
        if m := PRONOMINA_PERTAMA.search(polos):
            hasil.append(f"baris {n}: kata ganti orang pertama «{m.group(0)}» di luar kutipan: tulis pendapat penulis "
                         f"secara tak langsung («والرأي»، «والراجح»، «ويظهر للباحث») (أبو سليمان، كتابة البحث العلمي، ص193){ekor(tampil)}")
        elif (m := QULTU_AWAL.search(polos)) and not RIWAYAT_PENGANTAR.search(polos):
            hasil.append(f"baris {n}: kata ganti orang pertama «{m.group(0)}» di luar kutipan: tulis pendapat penulis "
                         f"secara tak langsung («والرأي»، «والراجح») (أبو سليمان، كتابة البحث العلمي، ص193){ekor(tampil)}")
        if m := TANDA_LATIN_ARAB.search(polos):
            tanda = m.group(1) or m.group(2)
            ganti = {",": "،", ";": "؛", "?": "؟"}[tanda]
            hasil.append(f"baris {n}: tanda baca Latin «{tanda}» di tengah kalimat Arab: ganti dengan «{ganti}»{ekor(tampil)}")
        if m := WAW_PISAH.search(polos):
            hasil.append(f"baris {n}: huruf sambung «و» terpisah spasi dari kata sesudahnya: tempelkan tanpa spasi "
                         f"(«وال…», bukan «و ال…»){ekor(tampil)}")
        # Samakan alif/tanwin untuk klise AI («دورًا» -> «دورا»)
        lipat = re.sub("[أإآ]", "ا", polos)
        if m := KLISE_AI.search(lipat):
            hasil.append(f"baris {n}: ungkapan klise/terjemahan harfiah «{m.group(0)}»: ganti dengan gaya ilmiah Arab yang "
                         f"langsung dan konkret{ekor(tampil)}")
    return hasil


def _kata_blok(b):
    return len("".join(r.get("t", "") for r in b.get("runs", ())).split())


def keseimbangan_bagian(blok):
    """Perhatian bila antarbagian setingkat (#F, atau #B di bawah satu #F, selain bagian pengantar/ringkas) sangat
    timpang (terpanjang >= KATA_TIMPANG_MIN dan rasio >= RASIO_TIMPANG) (أبو سليمان، ص194-195).
    `#B` di luar `#F` (di bawah `#K المقدمة`) sengaja tidak dibandingkan: bagian tingkat atas selalu `#F` (`tanda`)."""
    kelompok = []
    daftar_f, cur_f, cur_b = [], None, None
    for b in blok:
        k = b["k"]
        if k == "R":
            break
        if k == "K":
            cur_f = cur_b = None
        elif k == "F":
            cur_f = {"n": b["n"], "judul": b["judul"], "kata": 0, "anak": []}
            daftar_f.append(cur_f)
            cur_b = None
        elif k == "B":
            cur_b = {"n": b["n"], "judul": b["judul"], "kata": 0}
            if cur_f is not None:
                cur_f["anak"].append(cur_b)
        elif k not in (*JUDUL_ISI, *JUDUL_BAB, "H", "G", "E"):
            wc = _kata_blok(b)
            if cur_f is not None:
                cur_f["kata"] += wc
            if cur_b is not None:
                cur_b["kata"] += wc
    kelompok.append(daftar_f)
    for f in daftar_f:
        if len(f["anak"]) >= 2:
            kelompok.append(f["anak"])
    hasil = []
    for daftar in kelompok:
        sah = [x for x in daftar if x["kata"] > 0 and not RINGKAS_WAJAR.match(norma.HARAKAT.sub("", x["judul"]).strip())]
        if len(sah) < 2:
            continue
        terpanjang = max(sah, key=lambda x: x["kata"])
        terpendek = min(sah, key=lambda x: x["kata"])
        rasio = terpanjang["kata"] / terpendek["kata"]
        if terpanjang["kata"] >= KATA_TIMPANG_MIN and rasio >= RASIO_TIMPANG:
            hasil.append(
                f"baris {terpendek['n']}: bagian «{terpendek['judul'][:40]}» ({terpendek['kata']} kata) sangat timpang "
                f"dibanding «{terpanjang['judul'][:40]}» ({terpanjang['kata']} kata; rasio {rasio:.1f}×): tinjau "
                f"keseimbangan panjang antarbagian (أبو سليمان، كتابة البحث العلمي، ص194-195)"
            )
    return hasil
