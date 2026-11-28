// SPDX-License-Identifier: AGPL-3.0-or-later
// Kurung kurawal tiap .br, digambar sesudah tata letak selesai (potret.js memanggil window.GAMBAR): tingginya = tinggi
// anaknya (.ch), lebarnya = .bs. Gaya garisnya di tema.css (svg.tinta path).
window.GAMBAR = () => {
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
