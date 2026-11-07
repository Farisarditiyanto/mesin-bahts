# SPDX-License-Identifier: AGPL-3.0-or-later
"""Penunjuk takhrij: cari hadits di «المنصة الحديثية» (alminasa.ai) -> kitab, كتاب/باب, nomor, juz/halaman cetak,
dan hukum ulama beserta kitab hukumnya. Gratis, tanpa kunci, butuh internet. Dipanggil lewat bahts.py.

Hanya penunjuk jalan: layanan orang lain, tanpa janji tetap ada, dan datanya bisa salah. Yang ditulis di bahts tetap
yang terbaca di kitab lokal (`ambil`, `halaman`) dan lolos `cek`. Isinya 12 kitab: الكتب التسعة, المستدرك,
صحيح ابن حبان, صحيح ابن خزيمة; hadits di luar itu dicari dengan `temukan`.
"""
import json, time, urllib.error

import norma, shamela
from norma import HARAKAT
from shamela import _kunci, buka

ALMINASA = "https://alminasa.ai/api/reactivesearchproxy/es-prod-euw1-hadith-12-read/_search"
KOLOM = ["book_name", "number", "editions", "chapter", "sub_chapter", "matn", "rulings"]


SHAHIHAIN = ("صحيح البخاري", "صحيح مسلم")
MIRIP_MAKS = 5  # riwayat «lafaznya berbeda» yang dicetak kalau Shahihain tidak muncul
LOKAL = "    SUDAH DIUNDUH:"  # awal baris riwayat yang kitabnya sudah di-`ambil`


def _tanya(query, maks):
    """Hits alminasa untuk satu query Elasticsearch (urut dari kitab yang paling sahih)."""
    badan = {"query": query, "size": maks, "sort": [{"authenticity_order": "asc"}], "_source": KOLOM}
    # layanannya hanya menjawab JSON rapat berhuruf Arab asli; bentuk lain dibiarkannya sampai waktu habis
    isi = json.dumps(badan, separators=(",", ":"), ensure_ascii=False).encode("utf8")
    # 429 = jatah permintaan alminasa sementara habis: tunggu sekali sesuai retry-after, jangan berjatah dua kali
    for ulang in (True, False):
        try:
            with buka(ALMINASA, isi, {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}) as r:
                jawab = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            tunggu = e.headers.get("retry-after") or ""
            tunggu = int(tunggu) if tunggu.isdigit() else 11
            if tunggu > 30 or not ulang:
                raise SystemExit("Jatah pencarian alminasa.ai untuk komputer ini habis untuk sekarang. Sementara itu pakai "
                                 "`temukan`, connector turath/shamela, atau `katalog` lalu `cari`.")
            time.sleep(tunggu + 1)
    try:
        return json.loads(jawab)["hits"]
    except (ValueError, KeyError, TypeError) as e:  # bukan JSON (perawatan, wifi minta masuk) atau bentuknya berubah
        raise SystemExit(f"hadits: jawaban alminasa.ai bukan data yang dikenal mesin ({type(e).__name__} {e}). Layanannya mungkin "
                         "sedang perawatan atau berubah, atau wifi minta masuk dulu lewat peramban. Sementara itu pakai "
                         "`temukan`, connector turath/shamela, atau `katalog` lalu `cari`.")


def _nomor(s):
    """Nomor hadits riwayat layanan s (angka saja)."""
    return [int(n) for n in s.get("number") or [] if str(n).isdigit()]


def _lokal(hits):
    """(kitab lokal: {nama kitab layanan (`padat`): [sid]}, tempat: {(sid, nomor): «juz/halaman»}) untuk riwayat yang
    kitabnya sudah di-`ambil`. Kitab lokal = judulnya tanpa keterangan edisi («سنن ابن ماجه - ت عبد الباقي» → «سنن ابن
    ماجه») sama dengan nama kitab layanan; «صحيح سنن أبي داود» dan sejenisnya tidak. tempat = halaman cetak edisi lokal
    tempat nomor itu berdiri sebagai kepala hadits («2192 - حدثنا»). Tiap kitab dibaca sekali, hanya kalau ada riwayatnya."""
    judul = {}
    for sid in shamela.punya():
        judul.setdefault(norma.padat(shamela.info(sid)["title_ar"].split(" - ")[0]), []).append(sid)
    perlu = {}  # sid -> nomor yang dicari
    for h in hits:
        for sid in judul.get(norma.padat(h["_source"]["book_name"]), ()):
            perlu.setdefault(sid, set()).update(_nomor(h["_source"]))
    tempat = {}
    if perlu:
        import olah  # kepala hadits dibaca dengan aturan yang sama dengan `cek` (#nomor, takhrij)
    for sid, nomor in perlu.items():
        for p in shamela._rekaman_di(sid, range(len(shamela.indeks(sid)))):
            for hal, b in norma.per_halaman(p):
                for n in {n for _, n in olah.kepala_hadits(b)[1]} & nomor:
                    tempat.setdefault((sid, n), f"{shamela._juz(p)}/{hal}")
        shamela.lepas()
    return judul, tempat


def _baris(hits, lebar):
    baris, (judul, tempat) = [], _lokal(hits)
    for h in hits:
        s = h["_source"]
        cetak = "؛ ".join(f"{e['volume']}/{e['page']} [{e.get('edition')}]" for e in s.get("editions") or [] if e.get("page"))
        nomor = "، ".join(map(str, s.get("number") or [])) or "-"
        baris += [f"\n{s['book_name']}، رقم {nomor}، {cetak or 'juz/halaman tidak tercatat'}"]
        for n in _nomor(s):
            for sid in judul.get(norma.padat(s["book_name"]), ()):
                letak = tempat.get((sid, n))
                baris.append(f"{LOKAL} edisi lokal {sid}: {letak} (kepala hadits «{n} -»)" if letak else
                             f"{LOKAL} kitab {sid}, tetapi «{n} -» tidak ketemu sebagai kepala hadits di sana "
                             "(penomoran edisinya bisa berbeda): " + shamela.perintah(f'cari {sid} "<lafaz matan>"'))
        baris += [f"    {s.get('chapter') or '-'}، {s.get('sub_chapter') or '-'}",
                  f"    المتن: {(s.get('matn') or '')[:lebar]}"]
        baris += [f"    حكم: {k.get('ruler')}: {k.get('ruling')} — {k.get('book_name')}، {k.get('volume')}/{k.get('page')}"
                  for k in s.get("rulings") or []]
    return baris


def cari(taraf, maks=10, lebar=110):
    """Tiap riwayat yang memuat طرف itu: tempatnya di kitab, lalu hukum ulama atasnya. Kalau ada riwayat tetapi
    البخاري/مسلم tidak di antaranya: beberapa riwayat yang lafaznya mirip (sebagian besar kata sama), diberi tanda sendiri."""
    t = HARAKAT.sub("", taraf).strip()
    if not t or maks < 1:
        raise ValueError('bentuknya: hadits "<طرف>" [maks, angka 1 ke atas]')
    _kunci(t)  # طرف tanpa huruf Arab ditolak di sini, tanpa memakai jatah layanan
    # frasa persis, tetapi «من غشنا» juga menemukan «ومن غشنا»/«فمن غشنا» (Elasticsearch membedakannya), dan sebaliknya
    varian = {t, "و" + t, "ف" + t} | ({t[1:]} if t[0] in "وف" and len(t.split()[0]) > 2 else set())
    d = _tanya({"bool": {"should": [{"match_phrase": {"hadith": v}} for v in sorted(varian)], "minimum_should_match": 1}}, maks)
    # disusun dulu, baru dicetak: jawaban yang rusak di tengah tidak meninggalkan daftar setengah
    try:
        total, baris = d["total"]["value"], _baris(d["hits"], lebar)
        mirip = []
        # hanya kalau haditsnya ketemu di kitab lain: tanpa itu, «75% kata sama» menangkap kalimat apa saja yang berkata umum
        if total and not any(h["_source"]["book_name"] in SHAHIHAIN for h in d["hits"]):
            sudah = {h["_id"] for h in d["hits"]}
            m = _tanya({"match": {"hadith": {"query": t, "minimum_should_match": "75%"}}}, MIRIP_MAKS + len(sudah))
            mirip = _baris([h for h in m["hits"] if h["_id"] not in sudah][:MIRIP_MAKS], lebar)
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
