"""Penunjuk takhrij: cari hadits di «المنصة الحديثية» (alminasa.ai) -> kitab, كتاب/باب, nomor, juz/halaman cetak,
dan hukum ulama beserta kitab hukumnya. Gratis, tanpa kunci, butuh internet. Dipanggil lewat bahts.py.

Hanya penunjuk jalan: layanan orang lain, tanpa janji tetap ada, dan datanya bisa salah. Yang ditulis di bahts tetap
yang terbaca di kitab lokal (`ambil`, `halaman`) dan lolos `cek`. Isinya 12 kitab: الكتب التسعة, المستدرك,
صحيح ابن حبان, صحيح ابن خزيمة; hadits di luar itu dicari dengan `temukan`.
"""
import json

from shamela import HARAKAT, _kunci, buka

ALMINASA = "https://alminasa.ai/api/reactivesearchproxy/es-prod-euw1-hadith-12-read/_search"
KOLOM = ["book_name", "number", "editions", "chapter", "sub_chapter", "matn", "rulings"]


SHAHIHAIN = ("صحيح البخاري", "صحيح مسلم")
MIRIP_MAKS = 5  # riwayat «lafaznya berbeda» yang dicetak kalau Shahihain tidak muncul


def _tanya(query, maks):
    """Hits alminasa untuk satu query Elasticsearch (urut dari kitab yang paling sahih)."""
    badan = {"query": query, "size": maks, "sort": [{"authenticity_order": "asc"}], "_source": KOLOM}
    # layanannya hanya menjawab JSON rapat berhuruf Arab asli; bentuk lain dibiarkannya sampai waktu habis
    isi = json.dumps(badan, separators=(",", ":"), ensure_ascii=False).encode("utf8")
    with buka(ALMINASA, isi, {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}) as r:
        jawab = r.read()
    try:
        return json.loads(jawab)["hits"]
    except (ValueError, KeyError, TypeError) as e:  # bukan JSON (perawatan, wifi minta masuk) atau bentuknya berubah
        raise SystemExit(f"hadits: jawaban alminasa.ai bukan data yang dikenal mesin ({type(e).__name__} {e}). Layanannya mungkin "
                         "sedang perawatan atau berubah, atau wifi minta masuk dulu lewat peramban. Sementara itu pakai "
                         "`temukan`, connector turath/shamela, atau `katalog` lalu `cari`.")


def _baris(hits, lebar):
    baris = []
    for h in hits:
        s = h["_source"]
        cetak = "؛ ".join(f"{e['volume']}/{e['page']} [{e.get('edition')}]" for e in s.get("editions") or [] if e.get("page"))
        nomor = "، ".join(map(str, s.get("number") or [])) or "-"
        baris += [f"\n{s['book_name']}، رقم {nomor}، {cetak or 'juz/halaman tidak tercatat'}",
                  f"    {s.get('chapter') or '-'}، {s.get('sub_chapter') or '-'}",
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
    else:  # pencariannya frasa persis: kosong di sini bukan bukti haditsnya tidak ada
        print("Coba طرف yang lebih pendek (3-5 kata berurutan dari matan), atau `temukan`.")
    return total or len(mirip)
