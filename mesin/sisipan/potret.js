// SPDX-License-Identifier: AGPL-3.0-or-later
// Potret tiap halaman sisipan (#fig) jadi PNG, satu browser untuk semua: node potret.js tugas.json
// tugas.json = {chrome, skala, tugas: [{html: file-URL, png: jalur}]}. Dijalankan lewat «npx -p puppeteer-core@…»:
// npx tidak mengisi NODE_PATH, jadi puppeteer-core dicari di folder node_modules yang npx taruh di PATH.
const fs = require('fs');
const path = require('path');
const cari = process.env.PATH.split(path.delimiter)
  .filter(p => p.endsWith(path.join('node_modules', '.bin'))).map(p => path.dirname(p));
const puppeteer = require(require.resolve('puppeteer-core', { paths: cari }));

(async () => {
  const kerja = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  // --no-sandbox: Ubuntu 23.10+ menolak sandbox Chrome tanpa profil AppArmor; yang dibuka hanya HTML buatan mesin
  const browser = await puppeteer.launch({ executablePath: kerja.chrome, headless: true, args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1600, height: 1200, deviceScaleFactor: kerja.skala });
    for (const t of kerja.tugas) {
      await page.goto(t.html, { waitUntil: 'load' });
      await page.evaluate(() => document.fonts.ready);
      await page.evaluate(() => window.GAMBAR && window.GAMBAR());
      const fig = await page.$('#fig');
      await fig.screenshot({ path: t.png });
    }
  } finally {
    await browser.close();
  }
})().catch(e => { console.error('Error: ' + (e && e.message || e)); process.exit(1); });
