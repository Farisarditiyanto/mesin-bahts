# SPDX-License-Identifier: AGPL-3.0-or-later
"""Penunjuk takhrij: cari hadits di «المنصة الحديثية» (alminasa.ai) -> kitab, كتاب/باب, nomor, juz/halaman cetak,
dan hukum ulama beserta kitab hukumnya. Gratis, tanpa kunci, butuh internet. Dipanggil lewat bahts.py.

Hanya penunjuk jalan: layanan orang lain, tanpa janji tetap ada, dan datanya bisa salah. Yang ditulis di bahts tetap
yang terbaca di kitab lokal (`ambil`, `halaman`) dan lolos `cek`. Isinya 12 kitab: الكتب التسعة, المستدرك,
صحيح ابن حبان, صحيح ابن خزيمة; hadits di luar itu dicari dengan `temukan`.
"""
import json

import jaringan, norma, shamela
from cocok import kunci_frasa
from dasar import perintah
from norma import HARAKAT
from kitab_lokal import kepala_hadits
from layanan import MIRIP_MIN, SIRAP

ALMINASA = "https://alminasa.ai/api/reactivesearchproxy/es-prod-euw1-hadith-12-read/_search"
KOLOM = ["book_name", "number", "editions", "chapter", "sub_chapter", "matn", "rulings"]


SHAHIHAIN = ("صحيح البخاري", "صحيح مسلم")
MIRIP_MAKS = 5  # riwayat «lafaznya berbeda» yang dicetak kalau Shahihain tidak muncul
MATAN_MAKS = 110  # huruf matan yang dicetak tiap riwayat
LOKAL = "    SUDAH DIUNDUH:"  # awal baris riwayat yang kitabnya sudah di-`ambil`


def _tanya(query, maks):
    """Hits alminasa untuk satu query Elasticsearch (urut dari kitab yang paling sahih)."""
    badan = {"query": query, "size": maks, "sort": [{"authenticity_order": "asc"}], "_source": KOLOM}
    # layanannya hanya menjawab JSON rapat berhuruf Arab asli; bentuk lain dibiarkannya sampai waktu habis
    isi = json.dumps(badan, separators=(",", ":"), ensure_ascii=False).encode("utf8")
    with jaringan.buka_berjatah("Jatah pencarian alminasa.ai untuk komputer ini habis untuk sekarang. Sementara itu pakai "
                                "`temukan`, connector turath/shamela, atau `katalog` lalu `cari`.",
                                ALMINASA, isi, {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}) as r:
        jawab = r.read()
    try:
        return json.loads(jawab)["hits"]
    except (ValueError, KeyError, TypeError) as e:  # bukan JSON (perawatan, wifi minta masuk) atau bentuknya berubah
        raise SystemExit(f"hadits: jawaban alminasa.ai {jaringan.JAWABAN_ASING} ({type(e).__name__} {e}). "
                         f"{jaringan.SEBAB_ASING.capitalize()}. Sementara itu pakai "
                         "`temukan`, connector turath/shamela, atau `katalog` lalu `cari`.")


def _nomor(s):
    """Nomor hadits riwayat layanan s (angka saja)."""
    return [int(n) for n in s.get("number") or [] if str(n).isdigit()]


def _kata(teks):
    """Kata-kata teks dalam bentuk `padat`: bahan pencocok matan layanan dengan hadits di kitab lokal."""
    return [k for k in map(norma.padat, norma.norm(teks).split()) if k]


def _hadits_lokal(sid):
    """[(nomor, «juz/halaman» kepalanya, « kata kata … » teksnya (`_kata`))] tiap hadits kitab lokal sid. Teks satu hadits = dari kepalanya
    sampai kepala pemisah berikutnya (batas `kepala_hadits`), juga lanjutannya di halaman/rekaman berikutnya. Kepala
    bernomor ganda («134 - (2951)» di مسلم) = satu hadits untuk tiap nomornya."""
    hadits, terbuka = [], []  # terbuka: nomor, letak, dan potongan teks hadits yang belum ditutup kepala berikutnya
    for p in shamela.rekaman_di(sid, range(len(shamela.indeks(sid)))):
        juz = shamela.nama_juz(p.get("part"))
        for hal, b in norma.per_halaman(p):
            teks, kepala, batas = kepala_hadits(b)
            ruas = sorted({pos for pos, _ in batas}) + [len(teks)]
            for _, _, potongan in terbuka:
                potongan.append(teks[:ruas[0]])
            for awal, ujung in zip(ruas, ruas[1:]):
                hadits += [(n, letak, _ruas(potongan)) for n, letak, potongan in terbuka]
                # nomor kepala di ruas ini selain kepala pemisah (nomor urut riwayat di مسلم) ikut kepala pemisahnya
                terbuka = [(n, f"{juz}/{hal}", [teks[awal:ujung]]) for q, n in kepala if awal <= q < ujung]
    hadits += [(n, letak, _ruas(potongan)) for n, letak, potongan in terbuka]
    shamela.lepas()
    return hadits


def _ruas(potongan):
    return " " + " ".join(_kata(" ".join(potongan))) + " "


def _cocok(matan, ruas):
    """Matan layanan terbaca di teks hadits itu (`_ruas`): sebagian besar deret SIRAP katanya (matan yang lebih pendek:
    seluruhnya) ada di sana, dengan batas MIRIP_MIN pencocok edisi `takhrij`."""
    kata = _kata(matan)
    deret = [" " + " ".join(kata[i:i + SIRAP]) + " " for i in range(max(len(kata) - SIRAP + 1, 1))] if kata else []
    return bool(deret) and sum(d in ruas for d in deret) / len(deret) >= MIRIP_MIN


def _lokal(hits):
    """(kitab lokal: {nama kitab layanan (`padat`): [sid]}, hadits: {sid: `_hadits_lokal`}) untuk riwayat yang kitabnya
    sudah di-`ambil`. Kitab lokal = judulnya tanpa keterangan edisi («سنن ابن ماجه - ت عبد الباقي» → «سنن ابن ماجه») sama
    dengan nama kitab layanan; «صحيح سنن أبي داود» dan sejenisnya tidak. Tiap kitab dibaca sekali, hanya kalau ada riwayatnya."""
    judul = {}
    for sid in shamela.punya():
        judul.setdefault(norma.padat(shamela.info(sid)["title_ar"].split(" - ")[0]), []).append(sid)
    perlu = {sid for h in hits for sid in judul.get(norma.padat(h["_source"]["book_name"]), ())}
    return judul, {sid: _hadits_lokal(sid) for sid in sorted(perlu)}


def _letak_lokal(sid, hadits, n, matan):
    """Baris «SUDAH DIUNDUH» riwayat bernomor layanan n di kitab lokal sid. Juz/halaman lokal hanya dicetak kalau matan
    layanan terbaca di hadits itu: penomoran layanan (mis. المكنز) bisa beda dengan edisi lokal, jadi «606 -» di edisi lokal
    bisa hadits lain. Kalau tidak cocok, matannya dicari di hadits lain kitab itu."""
    cari = perintah(f'cari {sid} "<lafaz matan>"')
    if not _kata(matan):
        return f"{LOKAL} kitab {sid}, tetapi matan riwayat ini kosong di layanan, jadi «{n} -» tidak bisa dicocokkan: {cari}"
    letak = next((letak for k, letak, ruas in hadits if k == n and _cocok(matan, ruas)), None)
    if letak:
        return f"{LOKAL} edisi lokal {sid}: {letak} (kepala hadits «{n} -»)"
    beda = (f"«{n} -» di sana hadits lain (LAFAZ TIDAK COCOK: penomoran edisinya beda)" if any(k == n for k, _, _ in hadits)
            else f"«{n} -» tidak ketemu sebagai kepala hadits di sana (penomoran edisinya bisa berbeda)")
    lain = next(((k, letak) for k, letak, ruas in hadits if k != n and _cocok(matan, ruas)), None)
    if lain:
        return f"{LOKAL} edisi lokal {sid}: {lain[1]} (kepala hadits «{lain[0]} -», lafaz matannya cocok; {beda})"
    return f"{LOKAL} kitab {sid}, tetapi {beda}, dan matannya tidak ketemu di kitab itu: {cari}"


def _baris(hits):
    baris, (judul, lokal) = [], _lokal(hits)
    for h in hits:
        s = h["_source"]
        cetak = "؛ ".join(f"{e['volume']}/{e['page']} [{e.get('edition')}]" for e in s.get("editions") or [] if e.get("page"))
        nomor = "، ".join(map(str, s.get("number") or [])) or "-"
        baris += [f"\n{s['book_name']}، رقم {nomor}، {cetak or 'juz/halaman tidak tercatat'}"]
        for n in _nomor(s):
            for sid in judul.get(norma.padat(s["book_name"]), ()):
                baris.append(_letak_lokal(sid, lokal[sid], n, s.get("matn") or ""))
        baris += [f"    {s.get('chapter') or '-'}، {s.get('sub_chapter') or '-'}",
                  f"    المتن: {(s.get('matn') or '')[:MATAN_MAKS]}"]
        baris += [f"    حكم: {k.get('ruler')}: {k.get('ruling')} — {k.get('book_name')}، {k.get('volume')}/{k.get('page')}"
                  for k in s.get("rulings") or []]
    return baris


def cari(taraf, maks=10):
    """Tiap riwayat yang memuat طرف itu: tempatnya di kitab, lalu hukum ulama atasnya. Kalau ada riwayat tetapi
    البخاري/مسلم tidak di antaranya: beberapa riwayat yang lafaznya mirip (sebagian besar kata sama), diberi tanda sendiri."""
    t = HARAKAT.sub("", taraf).strip()
    if not t or maks < 1:
        raise ValueError('bentuknya: hadits "<طرف>" [maks, angka 1 ke atas]')
    kunci_frasa(t)  # طرف tanpa huruf Arab ditolak di sini, tanpa memakai jatah layanan
    # frasa persis, tetapi «من غشنا» juga menemukan «ومن غشنا»/«فمن غشنا» (Elasticsearch membedakannya), dan sebaliknya
    varian = {t, "و" + t, "ف" + t} | ({t[1:]} if t[0] in "وف" and len(t.split()[0]) > 2 else set())
    d = _tanya({"bool": {"should": [{"match_phrase": {"hadith": v}} for v in sorted(varian)], "minimum_should_match": 1}}, maks)
    # disusun dulu, baru dicetak: jawaban yang rusak di tengah tidak meninggalkan daftar setengah
    try:
        total, baris = d["total"]["value"], _baris(d["hits"])
        mirip = []
        # hanya kalau haditsnya ketemu di kitab lain: tanpa itu, «75% kata sama» menangkap kalimat apa saja yang berkata umum
        if total and not any(h["_source"]["book_name"] in SHAHIHAIN for h in d["hits"]):
            sudah = {h["_id"] for h in d["hits"]}
            m = _tanya({"match": {"hadith": {"query": t, "minimum_should_match": "75%"}}}, MIRIP_MAKS + len(sudah))
            mirip = _baris([h for h in m["hits"] if h["_id"] not in sudah][:MIRIP_MAKS])
    except (KeyError, TypeError, AttributeError) as e:
        raise SystemExit(f"hadits: jawaban alminasa.ai berbentuk lain dari yang dikenal mesin ({type(e).__name__} {e}).")
    print(f"{total} riwayat cocok: {taraf}")
    if baris:
        print("\n".join(baris))
    if total > len(d["hits"]):
        print(f"\n(ditampilkan {len(d['hits'])}; tambah angka sesudah طرف untuk melihat lebih banyak)")
    if mirip:
        print("\n--- Riwayat mirip, LAFAZNYA BERBEDA (البخاري/مسلم tidak ada di atas): periksa lafaznya di kitabnya ---")
        print("\n".join(mirip))
    if total or mirip:
        print("\nPenunjuk saja, datanya bisa salah: baca di kitabnya sendiri (`ambil`, `halaman`) sebelum menulis.")
        if any(x.startswith(LOKAL) for x in baris + mirip):
            print("Juz/halaman layanan bisa dari edisi lain dari yang sudah diunduh: yang ditulis di naskah = juz/halaman "
                  "edisi lokal (baris «edisi lokal»), karena `cek` mencocokkannya dengan kitab lokal.")
        print("Daftar cocok memakai frasa persis: lafaz lain (mis. بالنية/بالنيات) bisa terlewat. Coba bentuk lain; daftar Riwayat mirip perlu diperiksa terpisah.")
    else:  # pencariannya frasa persis: kosong di sini bukan bukti haditsnya tidak ada
        print("Coba طرف yang lebih pendek (3-5 kata berurutan dari matan), atau `temukan`.")
    return total or len(mirip)
