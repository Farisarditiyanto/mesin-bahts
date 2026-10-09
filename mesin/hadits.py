"""Penunjuk takhrij: cari hadits di «المنصة الحديثية» (alminasa.ai) -> kitab, كتاب/باب, nomor, juz/halaman cetak,
dan hukum ulama beserta kitab hukumnya. Gratis, tanpa kunci, butuh internet. Dipanggil lewat bahts.py.

Hanya penunjuk jalan: layanan orang lain, tanpa janji tetap ada, dan datanya bisa salah. Yang ditulis di bahts tetap
yang terbaca di kitab lokal (`ambil`, `halaman`) dan lolos `cek`. Isinya 12 kitab: الكتب التسعة, المستدرك,
صحيح ابن حبان, صحيح ابن خزيمة; hadits di luar itu dicari dengan `temukan`.
"""
import json, urllib.request

from shamela import HARAKAT

ALMINASA = "https://alminasa.ai/api/reactivesearchproxy/es-prod-euw1-hadith-12-read/_search"
KOLOM = ["book_name", "number", "editions", "chapter", "sub_chapter", "matn", "rulings"]


def cari(taraf, maks=10, lebar=110):
    """Tiap riwayat yang memuat طرف itu: tempatnya di kitab, lalu hukum ulama atasnya."""
    badan = {"query": {"match_phrase": {"hadith": HARAKAT.sub("", taraf)}}, "size": maks,
             "sort": [{"authenticity_order": "asc"}], "_source": KOLOM}
    # layanannya hanya menjawab JSON rapat berhuruf Arab asli; bentuk lain dibiarkannya sampai waktu habis
    isi = json.dumps(badan, separators=(",", ":"), ensure_ascii=False).encode("utf8")
    minta = urllib.request.Request(ALMINASA, isi, {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(minta, timeout=60) as r:
        d = json.load(r)["hits"]
    print(f"{d['total']['value']} riwayat cocok: {taraf}")
    for h in d["hits"]:
        s = h["_source"]
        cetak = "؛ ".join(f"{e['volume']}/{e['page']} [{e.get('edition')}]" for e in s.get("editions") or [] if e.get("page"))
        nomor = "، ".join(map(str, s.get("number") or [])) or "-"
        print(f"\n{s['book_name']}، رقم {nomor}، {cetak or 'juz/halaman tidak tercatat'}")
        print(f"    {s.get('chapter') or '-'}، {s.get('sub_chapter') or '-'}")
        print(f"    المتن: {(s.get('matn') or '')[:lebar]}")
        for k in s.get("rulings") or []:
            print(f"    حكم: {k.get('ruler')}: {k.get('ruling')} — {k.get('book_name')}، {k.get('volume')}/{k.get('page')}")
    if d["total"]["value"] > len(d["hits"]):
        print(f"\n(ditampilkan {len(d['hits'])}; tambah angka sesudah طرف untuk melihat lebih banyak)")
    if d["hits"]:
        print("\nPenunjuk saja, datanya bisa salah: baca di kitabnya sendiri (`ambil`, `halaman`) sebelum menulis.")
    else:  # pencariannya frasa persis: kosong di sini bukan bukti haditsnya tidak ada
        print("Coba طرف yang lebih pendek (3-5 kata berurutan dari matan), atau `temukan`.")
