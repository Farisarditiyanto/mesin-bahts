# Pemakai baru

Lanjutan `AGENTS.md` bagian «Pemakai baru». Baca penuh saat pemakai baru pertama kali memakai agent atau belum menyelesaikan pemasangan awal (`periksa`, connector `shamela`, kunci OpenAlex).

Anggap pemakai baru pertama kali memakai agent, tidak membaca README, dan hanya memberi tautan repo plus permintaan bahts. Kerjakan semuanya sendiri; pemakai cukup menjawab pertanyaan. Pakai bahasa awam.

1. Repo belum ada di komputer → cek dulu folder `mesin-bahts` di dalam folder Dokumen pemakai. Belum ada → unduh ke sana: `git clone`, atau kalau `git` tidak ada, unduh `https://github.com/Farisarditiyanto/mesin-bahts/archive/refs/heads/main.zip` lalu ekstrak dan namai foldernya `mesin-bahts` (zip itu terekstrak sebagai `mesin-bahts-main`). Folder Dokumen = folder dokumen akun pemakai (di Windows bisa berada di dalam OneDrive). Jangan mengunduh ke folder sistem, folder program, atau folder kerja orang lain. Semua bahts pemakai tinggal di dalam folder itu.
2. Jalankan `python mesin/bahts.py periksa` (di Linux/macOS biasanya `python3`). Bereskan sendiri tiap baris `BELUM` dengan perintah yang disebutnya, lalu ulangi sampai tidak ada lagi yang bisa kamu bereskan. Baris huruf bertulisan «(hanya untuk @format …)» dilewati, kecuali naskah memakai profil itu: baris itu tidak menahan `rakit`, dan perintahnya memunculkan jendela izin admin. `python` tidak dikenal → pasang Python 3.12 dulu (Windows: `winget install Python.Python.3.12`); kalau sesudah itu `python` masih tidak dikenal di terminalmu, pakai `py`. Beri tahu pemakai bahwa `siapkan` memasang satu font (font mushaf) untuk akunnya.
3. `periksa` bilang `rakit` BELUM karena Windows atau Microsoft Word → beri tahu pemakai sekarang, sebelum menulis apa pun: hasilnya berhenti di naskah yang sudah dicek, tanpa Word dan PDF. Tanya: lanjut, atau pasang Word dulu. Jangan memasang Word sendiri dan jangan memakai pengganti Word. Yang BELUM «huruf Traditional Arabic» → jalankan perintah PowerShell admin yang disebut `periksa`, dan beri tahu pemakai dulu bahwa Windows akan menampilkan satu jendela izin: cukup klik Yes. Perintah itu selesai sesudah jendelanya menutup; ulangi `periksa`. Masih BELUM → minta pemakai menambah papan ketik Arab seperti yang disebut `periksa`.
4. Connector `shamela` wajib: jangan mengumpulkan bahan sebelum alat `shamela_*` tersedia.
   - Cari dulu dengan pencari alat agentmu (Claude Code: ToolSearch «shamela»): di banyak agent alat connector disembunyikan sampai dicari, dan lewat gateway MCP namanya berawalan lain (mis. `toolport__shamela__shamela_search_phrase`), barangnya sama.
   - Tanda `shamela` tersambung = ada `shamela_search_phrase`; yang hanya punya `shamela_search` dan `shamela_find` itu connector `qurangallery` (langkah 5), bukan `shamela`.
   - Kalau alat `shamela_*` belum tersedia, beri tahu pemakai kegunaannya (mencari kitab yang membahas suatu masalah, termasuk yang belum diunduh) dan cara menyambungkannya dengan akun shamela.link sendiri (mengubah pengaturan agent di luar repo = tanya pemakai dulu):
     - **Claude Code**: baca daftar connector dari `.mcp.json`; masuk akun lewat `/mcp`.
     - **OpenCode**: baca daftar connector dari `opencode.json`; masuk akun lewat `opencode mcp auth shamela`.
     - **Command Code**: baca daftar connector dari `.mcp.json`, tetapi pendaftaran login otomatisnya ditolak shamela.link sehingga entri `shamela` perlu ditimpa entri lokal di `~/.commandcode` dengan `clientId` repo (beri tahu pemakai browser akan terbuka untuk login). Jalankan dari folder repo lewat bash atau PowerShell 7 (`pwsh`; PowerShell 5.1 membuang tanda kutip di dalam JSON; di Git Bash gunakan `commandcode`):
       ```bash
       commandcode mcp add-json --scope local shamela '{"type":"http","url":"https://shamela.link/mcp","oauth":{"clientId":"XibdiamYnAOtrCxycxRltQsDFisFhAWc","authorizationUrl":"https://shamela.link/api/auth/oauth2/authorize","tokenUrl":"https://shamela.link/api/auth/oauth2/token","scopes":["openid","offline_access"],"resource":"https://shamela.link/mcp","callbackPort":8085}}'
       ```
       Lalu cek `commandcode mcp list` sampai tertulis `shamela … local ✔` (belum ✔ → `commandcode mcp auth shamela`), lalu mulai sesi baru.
     - **Codex**: daftarkan alamat dari `.mcp.json` lalu masuk akun:
       ```bash
       codex mcp add shamela --url https://shamela.link/mcp
       codex mcp login shamela
       ```
     - **Hermes Agent**: daftarkan alamat dari `.mcp.json` (tautan masuk muncul saat pertama tersambung):
       ```bash
       hermes mcp add shamela --url https://shamela.link/mcp --auth oauth
       ```
     - **Agent lain**: daftarkan alamat dari `.mcp.json` lewat pengaturan MCP agent tersebut; connector tanpa akun didaftarkan dengan cara yang sama tanpa langkah masuk.
   - Pemakai menolak atau belum bisa masuk → jangan mulai mengumpulkan bahan; jelaskan sebabnya dan tunggu sampai `shamela` tersambung.
5. Connector tanpa akun di `.mcp.json` ikut dipasang bersama `shamela`, supaya semuanya siap walau tidak semua dipakai: `qurangallery` (seluruh Shamela dengan nomor kitab yang sama: frasa persis, pencari sumber kutipan, juz/halaman cetak → `page_id`; cadangan pertama `shamela`), `turath` (isi semua kitab), `hadithunlocked` (hadits, derajat, syarah, sejarah), `tafsir` (tafsir per ayat, sebab turun, qiraat, i'rab), `quran` (teks ayat, morfologi, sebaran kata). Semuanya penunjuk jalan. Minta izinnya sekali untuk semua connector, jangan satu per satu. Bedanya dengan `shamela`: yang ini tidak menahan pekerjaan. Layanannya mati atau gagal tersambung → lanjut, lalu sebut di laporan akhir. Pemakai menolak → lewati.
6. Kunci OpenAlex wajib hanya untuk bahts yang memuat الدراسات السابقة; bahts lain tidak memerlukannya, jadi jangan dimintakan di awal. Dosen minta الدراسات السابقة, `kunci_openalex.txt` belum ada, dan variabel lingkungan `OPENALEX_API_KEY` kosong → minta kunci gratis (openalex.org > Settings > API key) sebelum menulis `#S`: tanpa kunci `dirasat-pdf` hanya bisa memakai tautan PDF akses terbuka, jadi isi banyak penelitian tidak bisa dibaca. Pemakai memberi kuncinya → simpan sebagai satu baris di berkas itu. Jangan menulis kunci itu di tempat lain.
