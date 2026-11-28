// SPDX-License-Identifier: AGPL-3.0-or-later
// Kurung kurawal tiap .br, digambar sesudah tata letak selesai (potret.js memanggil window.GAMBAR): tingginya = tinggi
// anaknya (.ch), lebarnya = .bs. Gaya garisnya di tema.css (svg.tinta path).
window.GAMBAR = () => {
  // .susut dan baris .lebar: teks yang dipatahkan lebar halaman selebar baris terpanjangnya (kotak tidak menyisakan ruang kosong di tepi)
  const lebar = [];
  document.querySelectorAll('.susut, .lebar .lf').forEach(e => {
    // kotak tiap huruf bukan spasi (spasi di patahan baris berkotak di tepi kotak lama, bukan di tinta), dikumpulkan per
    // baris: yang bertumpang tegak = satu baris (tebal dan biasa beda tinggi)
    const r = document.createRange(), baris = [], jalan = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
    for (let t = jalan.nextNode(); t; t = jalan.nextNode()) {
      for (let i = 0; i < t.length; i++) {
        if (/\s/.test(t.data[i])) continue;
        r.setStart(t, i);
        r.setEnd(t, i + 1);
        const x = r.getBoundingClientRect(), m = (x.top + x.bottom) / 2, b = baris.find(b => m > b.t && m < b.b);
        if (b) { b.l = Math.min(b.l, x.left); b.r = Math.max(b.r, x.right); }
        else baris.push({ l: x.left, r: x.right, t: x.top, b: x.bottom });
      }
    }
    const ukuran = baris.map(b => b.r - b.l);
    lebar.push([e, ukuran.length > 1 ? Math.ceil(Math.max(...ukuran)) + 1 + 'px' : '']);
  });
  // diukur semua dulu (ukuran satu tidak menggeser yang lain); teks sebaris cukup tidak dipatahkan: lebar berangka bisa
  // mematahkannya lagi karena pembulatan pada skala potret
  lebar.forEach(([e, w]) => { if (w) e.style.width = w; else e.style.whiteSpace = 'nowrap'; });
  const fig = document.getElementById('fig'), f = fig.getBoundingClientRect();
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'tinta');
  fig.prepend(svg);
  const kotak = e => { const r = e.getBoundingClientRect(); return { l: r.left - f.left, r: r.right - f.left, t: r.top - f.top, b: r.bottom - f.top }; };
  document.querySelectorAll('.br').forEach(br => {
    const s = kotak(br.querySelector(':scope>.bs')), c = kotak(br.querySelector(':scope>.ch'));
    // ujung kurung ke induk: kanan (biasa) atau kiri (.balik)
    const ujung = br.classList.contains('balik') ? s.l + 1 : s.r - 1, buka = br.classList.contains('balik') ? s.r - 1 : s.l + 1;
    const y1 = c.t + 1, y2 = c.b - 1, m = (y1 + y2) / 2, x = (ujung + buka) / 2, q = Math.min(Math.abs(ujung - buka) / 2, (y2 - y1) / 4);
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', `M${buka},${y1} Q${x},${y1} ${x},${y1 + q} L${x},${m - q} Q${x},${m} ${ujung},${m} ` +
      `Q${x},${m} ${x},${m + q} L${x},${y2 - q} Q${x},${y2} ${buka},${y2}`);
    svg.appendChild(p);
  });
};

// Sesudah tata letak, sebelum kurung: label .tanda di tiap .lajur (garis waktu, batang bagian) diletakkan di x = data-x
// (0..1 dari kanan) di atas (data-sisi="a") atau bawah ("b") poros .lajur, bertingkat supaya tidak bertumpuk, dengan
// garis penunjuk ke poros. Sesudah kurung: garis .simpul[data-ke] ke simpul induknya (pohon isnad).
(() => {
  const kurung = window.GAMBAR, NS = 'http://www.w3.org/2000/svg';
  const garis = (svg, d) => { const p = document.createElementNS(NS, 'path'); p.setAttribute('d', d); svg.appendChild(p); };
  const lajur = () => document.querySelectorAll('.lajur').forEach(l => {
    const W = l.clientWidth, jarak = 3, label = [...l.querySelectorAll(':scope>.tanda')];
    if (!label.length) return;
    const h = Math.max(...label.map(t => t.offsetHeight)), sela = 6;
    // tingkat terendah yang tidak menumpuk label setingkat, tidak dilewati garis penunjuk label yang lebih jauh, dan
    // garis penunjuknya sendiri tidak melewati label yang lebih dekat ke poros. .bendera: label di kiri garis penunjuknya
    // (teks Arab mulai dari garis itu; Python menyisakan ruang di ujung kiri poros), diletakkan dari kiri; selain itu di
    // tengahnya
    const sudah = { a: [], b: [] }, tingkat = { a: [], b: [] };
    label.sort((p, q) => q.dataset.x - p.dataset.x).forEach(t => {
      const w = t.offsetWidth, x = W - t.dataset.x * W, sisi = t.dataset.sisi || 'b', ada = sudah[sisi];
      let pilih = null;
      for (const k of l.classList.contains('bendera') ? [x - w + 1] : [x - w / 2]) {
        const kiri = Math.min(Math.max(k, 0), W - w), kanan = kiri + w;
        const tabrak = i => ada.some(s => (s.i === i && s.kiri < kanan + sela && kiri < s.kanan + sela) ||
          (s.i < i && x >= s.kiri - sela && x <= s.kanan + sela) || (i < s.i && s.x >= kiri - sela && s.x <= kanan + sela));
        let i = 0;
        const jauh = Math.max(-1, ...ada.map(s => s.i)) + 1;
        while (i < jauh && tabrak(i)) i++;  // tanpa tingkat bebas tabrakan: tingkat baru paling jauh
        if (!pilih || i < pilih.i) pilih = { i, kiri, kanan };
      }
      ada.push({ x, ...pilih });
      tingkat[sisi] = Array(Math.max(tingkat[sisi].length, pilih.i + 1)).fill(1);
      Object.assign(t.dataset, { i: pilih.i, kiri: pilih.kiri, px: x });
    });
    const poros = l.querySelector(':scope>.poros, :scope>.batang'), ph = poros ? poros.offsetHeight : 0;
    const atas = tingkat.a.length ? tingkat.a.length * (h + jarak) - jarak + 8 : 0;
    l.style.height = `${atas + ph + (tingkat.b.length ? 8 + tingkat.b.length * (h + jarak) - jarak : 0)}px`;
    if (poros) poros.style.top = `${atas}px`;
    label.forEach(t => {
      const i = +t.dataset.i, y = t.dataset.sisi === 'a' ? atas - 8 - (i + 1) * (h + jarak) + jarak : atas + ph + 8 + i * (h + jarak);
      Object.assign(t.style, { left: `${t.dataset.kiri}px`, top: `${y}px` });
      t.dataset.y = y;
    });
  });
  window.GAMBAR = () => {
    lajur();
    kurung();
    const fig = document.getElementById('fig'), f = fig.getBoundingClientRect(), svg = fig.querySelector('svg.tinta');
    const kotak = e => { const r = e.getBoundingClientRect(); return { l: r.left - f.left, r: r.right - f.left, t: r.top - f.top, b: r.bottom - f.top }; };
    document.querySelectorAll('.lajur').forEach(l => {
      const poros = l.querySelector(':scope>.poros, :scope>.batang');
      if (!poros) return;
      const p = kotak(poros), k = kotak(l);
      l.querySelectorAll(':scope>.tanda').forEach(t => {
        const x = k.l + +t.dataset.px, c = kotak(t);
        garis(svg, t.dataset.sisi === 'a' ? `M${x},${p.t} L${x},${c.b}` : `M${x},${p.b} L${x},${c.t}`);
      });
    });
    const simpul = {};
    document.querySelectorAll('.simpul').forEach(s => { simpul[s.dataset.id] = kotak(s); });
    document.querySelectorAll('.simpul[data-ke]').forEach(s => {
      const a = simpul[s.dataset.id];
      s.dataset.ke.split(' ').forEach(id => {
        const b = simpul[id];
        garis(svg, `M${(a.l + a.r) / 2},${a.t + 1} L${(b.l + b.r) / 2},${b.b - 1}`);
      });
    });
  };
})();
