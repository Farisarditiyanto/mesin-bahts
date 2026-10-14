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
    if not taraf.strip() or maks < 1:
        raise ValueError('bentuknya: hadits "<طرف>" [maks, angka 1 ke atas]')
    badan = {"query": {"match_phrase": {"hadith": HARAKAT.sub("", taraf)}}, "size": maks,
             "sort": [{"authenticity_order": "asc"}], "_source": KOLOM}
    # layanannya hanya menjawab JSON rapat berhuruf Arab asli; bentuk lain dibiarkannya sampai waktu habis
    isi = json.dumps(badan, separators=(",", ":"), ensure_ascii=False).encode("utf8")
    minta = urllib.request.Request(ALMINASA, isi, {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(minta, timeout=60) as r:
        jawab = r.read()
    # disusun dulu, baru dicetak: jawaban yang rusak di tengah tidak meninggalkan daftar setengah
    try:
        d = json.loads(jawab)["hits"]
        total, baris = d["total"]["value"], []
        for h in d["hits"]:
            s = h["_source"]
            cetak = "؛ ".join(f"{e['volume']}/{e['page']} [{e.get('edition')}]" for e in s.get("editions") or [] if e.get("page"))
            nomor = "، ".join(map(str, s.get("number") or [])) or "-"
            baris += [f"\n{s['book_name']}، رقم {nomor}، {cetak or 'juz/halaman tidak tercatat'}",
                      f"    {s.get('chapter') or '-'}، {s.get('sub_chapter') or '-'}",
                      f"    المتن: {(s.get('matn') or '')[:lebar]}"]
            baris += [f"    حكم: {k.get('ruler')}: {k.get('ruling')} — {k.get('book_name')}، {k.get('volume')}/{k.get('page')}"
                      for k in s.get("rulings") or []]
    except (ValueError, KeyError, TypeError, AttributeError) as e:  # bukan JSON (perawatan, wifi minta masuk) atau bentuknya berubah
        raise SystemExit(f"hadits: jawaban alminasa.ai bukan data yang dikenal mesin ({type(e).__name__} {e}). Layanannya mungkin "
                         "sedang perawatan atau berubah, atau wifi minta masuk dulu lewat peramban. Sementara itu pakai "
                         "`temukan`, connector turath/shamela, atau `katalog` lalu `cari`.")
    print(f"{total} riwayat cocok: {taraf}")
    if baris:
        print("\n".join(baris))
    if total > len(d["hits"]):
        print(f"\n(ditampilkan {len(d['hits'])}; tambah angka sesudah طرف untuk melihat lebih banyak)")
    if total:
        print("\nPenunjuk saja, datanya bisa salah: baca di kitabnya sendiri (`ambil`, `halaman`) sebelum menulis.")
    else:  # pencariannya frasa persis: kosong di sini bukan bukti haditsnya tidak ada
        print("Coba طرف yang lebih pendek (3-5 kata berurutan dari matan), atau `temukan`.")
