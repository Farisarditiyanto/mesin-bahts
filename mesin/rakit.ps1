# SPDX-License-Identifier: AGPL-3.0-or-later
# Rakit <Hasil>\<berkas>.docx + .pdf dari bahan JSON -Build (hasil olah.py), memakai Word asli (COM).
# Dipanggil oleh bahts.py; jangan dijalankan langsung.
param([Parameter(Mandatory)][string]$Build, [Parameter(Mandatory)][string]$Folder, [string]$Hasil = $Folder,
      [Parameter(Mandatory)][string]$Kunci, [string]$Galat)
$ErrorActionPreference = 'Stop'
# Galat yang menghentikan skrip ini ditulis juga ke -Galat (UTF-8): bahts.py mengutipnya di pesan GAGAL, karena layar
# bisa dipotong pemanggil (tail/grep) dan huruf Arabnya rusak lewat pipa. Tanpa berkas itu = PowerShell dimatikan dari luar.
trap {
    if ($Galat) { [IO.File]::WriteAllText($Galat, "$($_.Exception.Message) (rakit.ps1 baris $($_.InvocationInfo.ScriptLineNumber))", (New-Object Text.UTF8Encoding $false)) }
    break
}
$dir = $PSScriptRoot
$DATA = Get-Content -LiteralPath $Build -Raw -Encoding UTF8 | ConvertFrom-Json
$M = $DATA.meta
$Out = Join-Path $Hasil $M.berkas; $Laporan = Join-Path $Hasil 'laporan.txt'
$FMT = $DATA.format                                      # profil dari format.json (dipilih @format; @catatan_kaki/@spasi sudah ditimpakan olah.py)
$TA = [string]$FMT.huruf; $QF = 'KFGQPC HAFS Uthmanic Script'
$uMatan = [single]$FMT.matan; $uCatatan = [single]$FMT.catatan; $uJudul = [single]$FMT.judul   # ukuran huruf (Word minta angka pecahan)
$uAyat = if ($FMT.ayat) { [single]$FMT.ayat } else { $uMatan }   # ukuran ayat di matan dan فهرس الآيات; profil tanpa "ayat" = sama dengan matan
$ULANG = if ($FMT.catatan_ulang_tiap_halaman) { 2 } else { 0 }   # nomor catatan kaki: 2 = mulai ulang tiap halaman, 0 = bersambung
$SPASI = if ($FMT.spasi) { [single]$FMT.spasi } else { 1 }   # jarak baris matan dan judul (kali satu baris); catatan kaki dan فهرس tetap satu spasi
$MULAKHAS_JARAK = [bool]$FMT.mulakhas_berjarak   # paragraf di bawah #K الملخص/ملخص البحث: berjarak 6 pt, tanpa awal alinea menjorok
$SPASI_MULAKHAS = if ($FMT.spasi_mulakhas) { [single]$FMT.spasi_mulakhas } else { $SPASI }   # jarak baris bagian #K الملخص… (termasuk الملخص باللغة الأجنبية)
$spasiAktif = $SPASI
# @angka hindi: teks naskah sudah diubah olah.py; nomor yang dihitung di sini (فهرس, المصادر, {P:}) diubah Angka;
# nomor halaman dicetak Word menurut Options.ArabicNumeral (gaya nomor Word «Hindi» = angka India २, bukan ٢)
$HINDI = $M.angka -eq 'hindi'
function Angka($s) {
    $s = [string]$s
    if (-not $HINDI) { return $s }
    return -join ($s.ToCharArray() | ForEach-Object { if ($_ -ge [char]'0' -and $_ -le [char]'9') { [char](0x0660 + [int]$_ - 48) } else { $_ } })
}
$JUDUL = $M.judul; $NAMA = $M.nama; $NIM = $M.nim
# judul sampul «… - …» (sub-judul hanya kalau @judul memuatnya): bagian sesudah « - » jadi baris kedua yang lebih kecil (kepala halaman tetap judul utuh)
$JUDUL1 = $JUDUL; $JUDUL2 = ''
if ($JUDUL -match '^(.+?)\s+[-–—]\s*(.+)$') { $JUDUL1 = $Matches[1].Trim(); $JUDUL2 = $Matches[2].Trim() }
$MUSYRIF = if ($M.musyrif -and $M.musyrif -ne '-') { [string]$M.musyrif } else { '' }
$JABATAN = if ($MUSYRIF -and $M.jabatan -and $M.jabatan -ne '-') { [string]$M.jabatan } else { '' }
# فهرس dicetak kalau ada isinya dan tidak disebut di @tanpa (ayat, hadits, maudhuat)
$TANPA = @(([string]$M.tanpa -split '[,، ]+') | Where-Object { $_ })
$adaAy = [bool]@($DATA.ayat).Count -and $TANPA -notcontains 'ayat'
$adaHd = [bool]@($DATA.hadits).Count -and $TANPA -notcontains 'hadits'
$adaTo = $TANPA -notcontains 'maudhuat'
$KITAB = $M.bentuk -eq 'kitab'           # @bentuk: kitab = tanpa sampul bahts, judul di kepala halaman, hanya #K (dan @halaman_baru) halaman baru
$adaPu = $TANPA -notcontains 'pustaka' -and (-not $KITAB -or @($DATA.pustaka).Count)   # @tanpa: pustaka = sumber cukup di catatan kaki
$ABJAD = $M.nomor -in 'abjad', 'mukadimah'             # @nomor: abjad = sebelum #F pertama nomor halaman huruf, mulai #F pertama ١، ٢، ٣
$NOMOR_MUQ = $M.nomor -eq 'mukadimah'      # @nomor: mukadimah = sama, tetapi ١ mulai #K المقدمة
$PUSTAKA_AKHIR = $M.pustaka -eq 'akhir'   # @pustaka: akhir = sumber sesudah فهرس الأحاديث, berjudul فهرس المصادر والمراجع
# tata letak yang bisa dicampur (olah.GAYA, @model): tiap bagian memilih bentuknya sendiri
$KEPALA_KOTAK = $M.kepala -eq 'kotak'      # kepala halaman: judul kanan, nomor halaman berbingkai kiri, garis di bawahnya
$JUDUL_KEPALA = if ($M.kepala_judul) { [string]$M.kepala_judul } else { $JUDUL }
$AYAT_SURAH = $M.fihris_ayat -eq 'surah'   # فهرس الآيات: السورة (digabung per surat) | الآية «… الآية n» | الصفحة
$HADITS_RINGKAS = $M.fihris_hadits -eq 'ringkas'   # فهرس الأحاديث: الأحاديث | الصفحة
$TO_TITIK = $M.maudhuat -eq 'titik'        # فهرس الموضوعات bertitik-titik tanpa tabel
$PUSTAKA_MUALLIF = $M.pustaka_gaya -eq 'muallif'   # القرآن الكريم bernomor; **…** tebal, __…__ miring
$KANAN = @(([string]$M.judul_kanan -split '[,، ]+') | Where-Object { $_ -in 'B', 'M' })   # judul #B/#M rata kanan
$TJ = if ($FMT.huruf_judul) { [string]$FMT.huruf_judul } else { $TA }   # huruf judul (#K/#F/#B/#M/#S dan judul فهرس)
$JARAK_P = if ($FMT.jarak_paragraf) { [single]$FMT.jarak_paragraf } else { 0 }   # pt sesudah paragraf matan
$U_PUSTAKA = if ($FMT.ukuran_pustaka) { [single]$FMT.ukuran_pustaka } else { $null }   # ukuran huruf المصادر (bawaan = matan)
$FIHRIS_SAMBUNG = $M.fihris -eq 'sambung'  # فهرس sesudah yang pertama menyambung di halaman yang sama
$TEPI_KANAN = if ($FMT.tepi_kanan) { [single]$FMT.tepi_kanan } else { 3.5 }   # cm
$MERAH = 176; $COKLAT = 2772843           # warna Word (BGR): lafaz matn RGB(176,0,0); rumuz RGB(107,79,42)

# satu rakit dalam satu waktu: rakit kedua berhenti di sini, sebelum mematikan Word milik rakit pertama (kunci lepas sendiri saat proses ini selesai).
# bahts.py menunggu kunci ini lepas sebelum rakit berikutnya (rakit.ps1 yang Python-nya dimatikan masih memegangnya).
try { $pegangKunci = [IO.File]::Open($Kunci, 'OpenOrCreate', 'ReadWrite', 'None') }
catch { throw "Rakit lain sedang jalan (memakai Word yang sama): tunggu sampai selesai, lalu ulangi." }
# Proses /Automation bisa milik aplikasi lain. Hanya Word yang dibuat di sini yang dibersihkan di finally.
# Rakit yang dimatikan paksa (terminal ditutup) tidak sempat ke finally, dan Word-nya tetap hidup: rakit berikutnya
# mematikan Word yang dicatat rakit itu, asal masih proses yang sama (nomor proses bisa dipakai ulang proses lain)
$CATATAN_WORD = "$dir\_tmp\rakit.word"
if (Test-Path -LiteralPath $CATATAN_WORD) {
    foreach ($baris in Get-Content -LiteralPath $CATATAN_WORD) {
        $id, $mulai = $baris -split '\|'
        $id = $id -as [int]                             # baris rusak dilewati: Get-Process -Id 'abc' menghentikan skrip
        $p = if ($id) { Get-Process -Id $id -ErrorAction SilentlyContinue }
        if ($p -and $p.ProcessName -eq 'WINWORD' -and [string]$p.StartTime.Ticks -eq $mulai) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    }
    Remove-Item -LiteralPath $CATATAN_WORD -Force
}
$wordLain = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$tmp = "$Hasil\word\kerja.docx"
try {
    [IO.Directory]::CreateDirectory((Split-Path -Parent $tmp)) | Out-Null
    $word = New-Object -ComObject Word.Application
    $wordIni = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $_.Id -notin $wordLain } | ForEach-Object { $_.Id })
    if ($wordIni) { Set-Content -LiteralPath $CATATAN_WORD -Encoding ASCII -Value @(Get-Process -Id $wordIni -ErrorAction SilentlyContinue | ForEach-Object { "$($_.Id)|$($_.StartTime.Ticks)" }) }
    $word.Visible = $false; $word.ScreenUpdating = $false; $word.DisplayAlerts = 0
    # pengaturan Word pemakai (berlaku untuk semua dokumennya): dipinjam selama rakit, dikembalikan di finally.
    # 2 = angka di teks Arab dicetak ٠-٩, di teks Latin 0-9; 0 = selalu 0-9
    $numeralLama = $word.Options.ArabicNumeral
    $NUMERAL = if ($HINDI) { 2 } else { 0 }; $word.Options.ArabicNumeral = $NUMERAL
    # Alamat kerja Word berupa string biasa untuk COM.
    # huruf profil yang tidak terpasang diganti Word diam-diam: berhenti di sini saja
    if (@($word.FontNames) -notcontains $TA) { throw "Huruf [$TA] belum terpasang di Windows. Jalankan: python mesin/bahts.py periksa" }
    if (@($word.FontNames) -notcontains $TJ) { Write-Output "PERINGATAN: huruf judul $TJ belum terpasang di Windows: judul dicetak $TA."; $TJ = $TA }
    # ---------- 1. Sampul: berangkat dari template sampul (bentuk kitab: dokumen kosong) ----------
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force }
    # Tampilan Draft selama menyusun: di Print Layout (bawaan kebanyakan pemakai) tiap Select menyusun ulang halaman sampai
    # titik itu (bahts 63 catatan kaki: rakit ±110 detik, Draft ±40). Sebelum .docx disimpan dan sebelum dokumen ditutup
    # kembali ke Print Layout (3): .docx menyimpan tampilannya dan dibuka pemakai dalam tampilan itu, dan Word mengingat
    # tampilan dokumen terakhir sebagai bawaannya. Tampilan awal Word tanpa jendela (Web Layout) bukan tampilan pemakai
    function Draft { $script:draft = $true; $doc.ActiveWindow.View.Type = 1 }
    $TPL = $null; $kepalaTpl = $null
    # FormattedText ke dokumen lain hanya membawa format langsung; yang datang dari gaya templat (arah, rata, garis,
    # huruf judul) disalin per paragraf. Huruf disalin per sifat, hanya yang seragam dalam paragrafnya (bukan 9999999):
    # menyalin objek Font utuh ikut membawa sifat yang tak tentu. Miring hanya disalin kalau templatnya miring: Word
    # melaporkan Italic kop sampul pemakai terbalik menurut arah bagian (0 padahal XML-nya miring, -1 padahal tidak),
    # jadi menyalin Italic=0 malah menulis <w:i/>. Nama huruf per jenis aksara: Name pada teks Arab = huruf Arabnya,
    # dan menulisnya ke Name mengganti huruf Latin paragraf itu
    function SalinGaya($asal, $tujuan) {
        $n = [Math]::Min($asal.Paragraphs.Count, $tujuan.Paragraphs.Count)
        for ($i = 1; $i -le $n; $i++) {
            $pa = $asal.Paragraphs($i); $pt = $tujuan.Paragraphs($i)
            $pt.Format = $pa.Format
            $fa = $pa.Range.Font; $ft2 = $pt.Range.Font
            # sifat ditulis satu-satu: $font.$nama = … pada objek COM diam-diam tidak berpengaruh
            $T = 9999999
            if ($fa.Size -ne $T) { $ft2.Size = $fa.Size }; if ($fa.SizeBi -ne $T) { $ft2.SizeBi = $fa.SizeBi }
            if ($fa.Bold -ne $T) { $ft2.Bold = $fa.Bold }; if ($fa.BoldBi -ne $T) { $ft2.BoldBi = $fa.BoldBi }
            if ($fa.Italic -eq -1) { $ft2.Italic = -1 }; if ($fa.ItalicBi -eq -1) { $ft2.ItalicBi = -1 }
            if ($fa.NameAscii) { $ft2.NameAscii = $fa.NameAscii }; if ($fa.NameOther) { $ft2.NameOther = $fa.NameOther }; if ($fa.NameBi) { $ft2.NameBi = $fa.NameBi }
        }
    }
    function Ganti($p, $teks) { $r = $p.Range; [void]$r.MoveEnd(1, -1); $r.Text = $teks }
    # judul dikecilkan sampai muat satu baris (mis. utama 36 -> 26, baris kedua 26 -> 22); yang tetap terlalu panjang diratakan:
    # tepi kiri-kanan paragrafnya dilebarkan 6 pt demi 6 pt selama jumlah barisnya tetap, jadi tiap baris kira-kira sama
    # panjang dan baris terakhir tidak tinggal satu kata («… وأوضح / المسالك»)
    function Seimbang($p, $uk, $kecil) {
        while ($uk -gt $kecil -and $p.Range.ComputeStatistics(1) -gt 1) { $uk -= 2; $p.Range.Font.Size = [single]$uk; $p.Range.Font.SizeBi = [single]$uk }
        $n = $p.Range.ComputeStatistics(1); if ($n -le 1) { return }
        $pf = $p.Range.ParagraphFormat
        for ($tepi = 6; $tepi -le 180; $tepi += 6) {
            $pf.LeftIndent = [single]$tepi; $pf.RightIndent = [single]$tepi
            if ($p.Range.ComputeStatistics(1) -gt $n) { $pf.LeftIndent = [single]($tepi - 6); $pf.RightIndent = [single]($tepi - 6); break }
        }
    }
    if ($KITAB) { $doc = $word.Documents.Add(); $doc.SaveAs2($tmp, 16); Draft }
    elseif ($M.sampul -in 'qism', 'jakarta' -and -not $M.templat) {   # @sampul bawaan selalu terisi: @templat didahulukan
    # @sampul: qism = model قسم الشريعة (logo, judul dalam kurung, العام الجامعي): teks penanda diganti, bentuknya dari templat
    # jakarta = sama, dari sampul_jakarta.docx: «قسم الشريعة بجاكرتا», logo berwarna, baris @sifat, nomor tanpa «الرقم الجامعي:»
    $JAKARTA = $M.sampul -eq 'jakarta'
    $doc = $word.Documents.Open($(if ($JAKARTA) { "$dir\sampul_jakarta.docx" } else { "$dir\sampul_qism.docx" }), $false, $true)
    $doc.SaveAs2($tmp, 16)
    Draft
    # العام الجامعي bawaan = tahun hijriah saat tahun ajaran mulai (1 Agustus): satu tahun ajaran tetap satu tahun
    # walau 1 Muharram lewat di tengahnya (Juni 2027 = 1449, tahun ajarannya masih 1448)
    $awal = [datetime]::new((Get-Date).Year, 8, 1); if ((Get-Date) -lt $awal) { $awal = $awal.AddYears(-1) }
    $TAHUN = if ($M.tahun) { [string]$M.tahun } else { Angka ([Globalization.UmAlQuraCalendar]::new().GetYear($awal)) }
    $pJudul = $null; $pSub = $null; $buang = @()
    foreach ($p in @($doc.Paragraphs)) {
        $t = $p.Range.Text.Trim()
        if ($t -eq 'عنوان البحث') { Ganti $p $JUDUL1; $pJudul = $p }
        # sub-judul (bagian judul sesudah « - ») dalam kurung; tanpa sub-judul barisnya kosong
        elseif ($t -eq '( موضوع البحث )') { Ganti $p $(if ($JUDUL2) { "( $JUDUL2 )" } else { '' }); $pSub = $p }
        # @jenis dan @nim tercetak kalau diisi; kosong (atau "-") = barisnya dibuang
        elseif ($t -eq 'نوع البحث') { if ($M.jenis -and $M.jenis -ne '-') { Ganti $p ([string]$M.jenis) } else { $buang += $p } }
        elseif ($t -eq 'الرقم الجامعي') { if ($NIM -and $NIM -ne '-') { Ganti $p $(if ($JAKARTA) { Angka $NIM } else { "الرقم الجامعي: $(Angka $NIM)" }) } else { $buang += $p } }
        elseif ($t -eq 'صفة الطالب') { if ($M.sifat -and $M.sifat -ne '-') { Ganti $p ([string]$M.sifat) } else { $buang += $p } }
        # pembimbing: tanpa @musyrif (atau "-") ketiga barisnya kosong; tanpa @jabatan (atau "-") baris jabatannya kosong
        elseif ($t -eq 'المشرف') { if (-not $MUSYRIF) { Ganti $p '' } }
        elseif ($t -eq 'اسم المشرف') { Ganti $p $MUSYRIF }
        elseif ($t -eq 'الدرجة العلمية للمشرف') { Ganti $p $JABATAN }
        elseif ($t -eq 'إعداد الطالب:') { if ($M.thalibah -eq 'ya') { Ganti $p 'إعداد الطالبة:' } }
        elseif ($t -eq 'اسم الطالب') { Ganti $p $NAMA }
        elseif ($t -eq 'السنة الهجرية') { Ganti $p "$TAHUN هـ" }
    }
    if ($JAKARTA) {
        $SM = if (@($word.FontNames) -contains 'Sakkal Majalla') { 'Sakkal Majalla' } else { $TA }
        foreach ($p in @($doc.Paragraphs)) {
            $t = $p.Range.Text.Trim(); $f = $p.Range.Font
            $u = switch ($t) {
                'المشرف' { 18, 1, $SM } { $_ -eq $MUSYRIF -and $MUSYRIF } { 18, 1, $SM } { $_ -eq $JABATAN -and $JABATAN } { 18, 0, $SM }
                { $_ -in 'إعداد الطالب:', 'إعداد الطالبة:' } { 16, 1, $SM } $NAMA { 16, 1, $SM }
                { $M.sifat -and $_ -eq [string]$M.sifat } { 16, 0, $SM } { $NIM -and $_ -eq (Angka $NIM) } { 18, 0, $TA }
                'العام الجامعي' { 18, 0, $TA } "$TAHUN هـ" { 18, 0, $TA } 'قسم الشريعة بجاكرتا' { 16, 0, $TA }
            }
            if ($u) { $f.Size = [single]$u[0]; $f.SizeBi = [single]$u[0]; $f.Bold = $u[1]; $f.BoldBi = $u[1]; $f.Name = $u[2]; $f.NameBi = $u[2]; $p.LineSpacingRule = 0 }
        }
    }
    foreach ($p in $buang) { [void]$p.Range.Delete() }
    # huruf judul model (dari templat: PT Bold Heading) belum terpasang = Word diam-diam memakai huruf lain: pakai huruf profil tebal
    $hJudul = $pJudul.Range.Font.NameBi
    if (@($word.FontNames) -notcontains $hJudul) {
        Write-Output "PERINGATAN: huruf $hJudul (judul sampul qism) belum terpasang di Windows: judul dicetak $TA tebal. Pasang hurufnya, lalu rakit lagi."
        $f = $pJudul.Range.Font; $f.Name = $TA; $f.NameBi = $TA; $f.Bold = 1; $f.BoldBi = 1
    }
    Seimbang $pJudul $(if ($JAKARTA) { 22 } else { 24 }) 18   # judul 24 seperti model (jakarta 22), dikecilkan sampai 18 supaya muat satu baris
    if ($JUDUL2) { Seimbang $pSub 18 16 }
    else { $pSub.Range.Font.Size = 2; $pSub.Range.Font.SizeBi = 2; $pSub.SpaceBefore = 0 }   # tanpa sub-judul: tanpa celah
    # judul sangat panjang: sampul tetap satu halaman, judul dan sub-judul dikecilkan sampai 14.
    # Jumlah halaman dihitung di Print Layout, dengan satu paragraf sementara untuk baris pemisah bagian sesudah sampul
    $doc.ActiveWindow.View.Type = 3
    $doc.Content.InsertParagraphAfter()
    $uk = $pJudul.Range.Font.SizeBi; $kecil = $false
    while ($uk -gt 14 -and $doc.ComputeStatistics(2) -gt 1) {
        $uk--; $kecil = $true
        foreach ($q in @($pJudul, $pSub)) {
            if ($q.Range.Font.SizeBi -gt $uk) { $q.Range.Font.Size = [single]$uk; $q.Range.Font.SizeBi = [single]$uk }
        }
    }
    if ($kecil) {                                        # baris berubah sesudah dikecilkan: ratakan lagi
        foreach ($q in @($pJudul, $pSub)) { $q.LeftIndent = 0; $q.RightIndent = 0; $u = $q.Range.Font.SizeBi; Seimbang $q $u $u }
    }
    # masih dua halaman: jarak di atas «العام الجامعي» dipendekkan, lalu jarak antarbagian lain
    $pTahun = @($doc.Paragraphs) | Where-Object { $_.Range.Text.Trim() -eq 'العام الجامعي' } | Select-Object -First 1
    while ($doc.ComputeStatistics(2) -gt 1 -and $pTahun.SpaceBefore -gt 0) { $pTahun.SpaceBefore = [Math]::Max(0, $pTahun.SpaceBefore - 10) }
    foreach ($q in @($doc.Paragraphs)) {
        if ($doc.ComputeStatistics(2) -le 1) { break }
        if ($q.SpaceBefore -gt 0) { $q.SpaceBefore = 0 }
    }
    if ($doc.ComputeStatistics(2) -gt 1) {
        Write-Output "PERINGATAN: judul terlalu panjang untuk sampul qism: sampulnya jadi dua halaman. Pendekkan @judul."
    }
    [void]$doc.Paragraphs.Last.Range.Delete()
    Draft
    }
    elseif ($M.templat) {
    # @templat: Word mahasiswa sendiri; halaman pertamanya jadi sampul apa adanya, kepala halamannya dipakai di bagian isi
    $doc = $word.Documents.Add(); $doc.SaveAs2($tmp, 16); Draft
    $TPL = $word.Documents.Open($M.templat, $false, $true)
    $akhir = if ($TPL.ComputeStatistics(2) -gt 1) { $TPL.GoTo(1, 1, 2).Start - 1 } else { $TPL.Content.End - 1 }
    $doc.Content.FormattedText = $TPL.Range(0, $akhir).FormattedText
    $doc.Activate()                                      # Selection di bawah milik dokumen aktif; Open membuat templat aktif
    $pt = $TPL.Sections(1).PageSetup; $p1 = $doc.Sections(1).PageSetup
    $p1.SectionDirection = $pt.SectionDirection         # arah bagian dulu: di bagian kanan-ke-kiri tepi kiri dan kanan bertukar
    $p1.PageWidth = $pt.PageWidth; $p1.PageHeight = $pt.PageHeight
    $p1.TopMargin = $pt.TopMargin; $p1.BottomMargin = $pt.BottomMargin; $p1.LeftMargin = $pt.LeftMargin; $p1.RightMargin = $pt.RightMargin
    foreach ($h in 1..3) { try { $doc.Sections(1).Headers($h).Range.Text = '' } catch {} ; try { $doc.Sections(1).Footers($h).Range.Text = '' } catch {} }
    # gaya sesudah tata halaman: mengganti arah bagian menyetel ulang huruf paragrafnya
    SalinGaya $TPL.Range(0, $akhir) $doc.Content
    # kotak teks sampul (mis. kop) ikut disalin gayanya, berpasangan menurut urutan
    $ka = @($TPL.Shapes | Where-Object { $_.TextFrame.HasText }); $kt = @($doc.Shapes | Where-Object { $_.TextFrame.HasText })
    for ($i = 0; $i -lt [Math]::Min($ka.Count, $kt.Count); $i++) { SalinGaya $ka[$i].TextFrame.TextRange $kt[$i].TextFrame.TextRange }
    } else {
    $doc = $word.Documents.Open("$dir\sampul.doc", $false, $true)
    $doc.SaveAs2($tmp, 16)
    $doc.Convert()
    Draft
    foreach ($h in 1..3) { try { $doc.Sections(1).Headers($h).Range.Text = '' } catch {} ; try { $doc.Sections(1).Footers($h).Range.Text = '' } catch {} }
    foreach ($s in $doc.Shapes) {
        if ($s.Type -eq 17) {
            $tr = $s.TextFrame.TextRange
            $f = $tr.Find; $f.ClearFormatting(); $f.Replacement.ClearFormatting()
            [void]$f.Execute('الملكة العربية', $true, $false, $false, $false, $false, $true, 0, $false, 'المملكة العربية', 2)
            $tr.Font.Name = $TA; $tr.Font.NameBi = $TA; $tr.Font.Size = 15; $tr.Font.SizeBi = 15; $tr.Font.Bold = 1; $tr.Font.BoldBi = 1
            $tr.ParagraphFormat.SpaceAfter = 0; $tr.ParagraphFormat.SpaceBefore = 0; $tr.ParagraphFormat.LineSpacingRule = 0
            $s.Height = $s.Height + 45
        }
    }
    $pNama = $null; $pJudul = $null
    foreach ($p in $doc.Paragraphs) {
        $t = $p.Range.Text.Trim()
        if ($t -eq 'عنوان البحث') { Ganti $p $JUDUL1; $pJudul = $p }
        elseif ($t -like 'بحث صفي للمستوى*') { Ganti $p $(if ($M.jenis -eq '-') { '' } else { $M.jenis }) }
        elseif ($t -like 'اسم*الطالبة*') { Ganti $p $(if ($M.thalibah -eq 'ya') { 'اسم الطالبة :' } else { 'اسم الطالب :' }); $pNama = $p }
        elseif ($t -eq '4300000') { Ganti $p $NIM }
        elseif ($t -like 'الفصل الدراسي*') { Ganti $p $M.fasl }
        # pembimbing: tanpa @musyrif (atau "-") ketiga barisnya kosong; tanpa @jabatan (atau "-") baris jabatannya kosong
        elseif ($t -like 'المشرف على البحث*') { if (-not $MUSYRIF) { Ganti $p '' } }
        elseif ($t -eq 'اسم المشرف') { Ganti $p $MUSYRIF }
        elseif ($t -eq 'الدرجة العلمية للمشرف') { Ganti $p $JABATAN }
    }
    $pNama.Range.InsertParagraphAfter()
    $pBaru = $pNama.Next(1); Ganti $pBaru $NAMA
    if ($JUDUL2) { $pJudul.Range.InsertParagraphAfter(); Ganti $pJudul.Next(1) $JUDUL2 }
    foreach ($p in $doc.Paragraphs) {
        $r = $p.Range; $t = $r.Text.Trim()
        if ($t.Length -gt 0) {
            $sz = $r.Font.SizeBi; if ($sz -gt 100) { $sz = 19 }
            $r.Font.Name = $TA; $r.Font.NameBi = $TA; $r.Font.Bold = 1; $r.Font.BoldBi = 1
            if ($t -eq $JUDUL1) { $r.Font.Size = 36; $r.Font.SizeBi = 36 }
            elseif ($JUDUL2 -and $t -eq $JUDUL2) { $r.Font.Size = 26; $r.Font.SizeBi = 26 }
            else { $r.Font.Size = [Math]::Max($sz, 20); $r.Font.SizeBi = [Math]::Max($sz, 20) }
        }
    }
    Seimbang $pJudul 36 26
    if ($JUDUL2) { Seimbang $pJudul.Next(1) 26 22 }
    # buang paragraf kosong di ekor sampul supaya sampul tetap 1 halaman
    while ($doc.Paragraphs.Count -gt 3 -and $doc.Paragraphs.Last.Range.Text.Trim().Length -eq 0 -and $doc.Paragraphs.Last.Previous(1).Range.Text.Trim().Length -eq 0) {
        $doc.Paragraphs.Last.Previous(1).Range.Delete() | Out-Null
    }
    }

    # ---------- 2. Bagian isi ----------
    $sel = $word.Selection
    [void]$sel.EndKey(6)
    if (-not $KITAB) { $sel.InsertBreak(2) }             # section break (halaman baru) sesudah sampul
    # potongan `rakit --fasl` selain yang pertama: sampul (bagian Word pertama, berikut pemisahnya) dibuang; tata halaman isi
    # disetel sesudah ini, jadi isinya sama dengan potongan bersampul
    if ($M.tanpa_sampul -and -not $KITAB) { [void]$doc.Sections(1).Range.Delete(); [void]$sel.EndKey(6) }
    $sec = $doc.Sections($doc.Sections.Count)
    $ps = $sec.PageSetup
    $ps.PaperSize = 7
    $ps.TopMargin = $word.CentimetersToPoints(2.5); $ps.BottomMargin = $word.CentimetersToPoints(2.5)
    $ps.LeftMargin = $word.CentimetersToPoints(2.5); $ps.RightMargin = $word.CentimetersToPoints($TEPI_KANAN)
    $ps.HeaderDistance = $word.CentimetersToPoints($(if ($FMT.jarak_kepala) { [single]$FMT.jarak_kepala } else { 1.25 })); $ps.FooterDistance = $word.CentimetersToPoints(1.25)
    $ft = $sec.Footers(1); $ft.LinkToPrevious = $false; $sec.Headers(1).LinkToPrevious = $false
    $ft.Range.Text = ''
    [void]$ft.Range.Fields.Add($ft.Range, 33)
    $ft.Range.ParagraphFormat.Alignment = 1
    # pedoman: nomor halaman di tengah bawah, huruf dan ukuran sama dengan matan, dihitung mulai dari المقدمة
    $ft.Range.Font.Name = $TA; $ft.Range.Font.NameBi = $TA; $ft.Range.Font.Size = $uMatan; $ft.Range.Font.SizeBi = $uMatan
    $ft.PageNumbers.RestartNumberingAtSection = $true; $ft.PageNumbers.StartingNumber = 1
    if ($ABJAD) { $ft.PageNumbers.NumberStyle = 46 }     # wdPageNumberStyleArabicLetter1: أ ب ت
    $ftIsi = $null; $bagianDepan = $sec.Index
    if ($KEPALA_KOTAK -and -not $TPL) { $TPL = $word.Documents.Open("$dir\kepala_kotak.docx", $false, $true); $doc.Activate() }
    if ($TPL) {                                          # kepala halaman @templat (nomor halamannya di situ): kaki halaman dikosongkan
        $hd = $sec.Headers(1); $sh0 = $TPL.Sections(1).Headers(1); $hd.Range.FormattedText = $sh0.Range.FormattedText
        # FormattedText membawa format langsung saja; arah, rata, dan garis dari gaya «Header» templat disalin per paragraf
        while ($hd.Range.Paragraphs.Count -gt $sh0.Range.Paragraphs.Count) {
            [void]$hd.Range.Paragraphs.Last.Previous(1).Range.Characters.Last.Delete()   # tanda paragraf (bukan $doc.Range: kepala halaman cerita lain)
        }
        SalinGaya $sh0.Range $hd.Range
        # nomor halaman: kalau kepala templat tidak memuat PAGE, nomor di kaki halaman bawaan mesin tetap dicetak
        $adaPage = @($sh0.Range.Fields | Where-Object { $_.Code.Text -match 'PAGE' }).Count -gt 0
        foreach ($sp in $sh0.Shapes) { if ($sp.TextFrame.HasText -and @($sp.TextFrame.TextRange.Fields | Where-Object { $_.Code.Text -match 'PAGE' }).Count) { $adaPage = $true } }
        if ($adaPage) { $ft.Range.Text = '' }
        if ($KEPALA_KOTAK) {                             # penanda judul di kepala_kotak.docx = judul (pendek) bahts ini
            $f = $hd.Range.Find; $f.ClearFormatting(); $f.Replacement.ClearFormatting()
            [void]$f.Execute('عنوان البحث', $true, $false, $false, $false, $false, $true, 0, $false, $JUDUL_KEPALA, 2)
        }
        $TPL.Close(0); $TPL = $null; $doc.Activate(); $script:kepalaTpl = $hd
    }
    # kepala halaman berjalan gaya cetakan kitab, bergaris bawah: halaman genap = judul kitab, halaman ganjil = judul bab
    # (#K / فهرس; tiap judul itu mulai bagian Word baru, lihat Judul). Nomor halaman bersambung di kaki semua halaman
    function KepalaHalaman($h, $teks) {
        $r = $h.Range; $r.Text = $teks
        $r.Font.Name = $TA; $r.Font.NameBi = $TA; $r.Font.Size = $uCatatan; $r.Font.SizeBi = $uCatatan; $r.Font.Bold = 1; $r.Font.BoldBi = 1
        $r.ParagraphFormat.ReadingOrder = 0; $r.ParagraphFormat.Alignment = 1
        $b = $r.Paragraphs(1).Borders.Item(-3); $b.LineStyle = 1; $b.LineWidth = 12
    }
    if ($KITAB) {
        $doc.PageSetup.OddAndEvenPagesHeaderFooter = -1
        KepalaHalaman $sec.Headers(1) $JUDUL; KepalaHalaman $sec.Headers(3) $JUDUL
        $fg = $sec.Footers(3); $fg.Range.Text = ''; [void]$fg.Range.Fields.Add($fg.Range, 33); $fg.Range.ParagraphFormat.Alignment = 1
        $fg.Range.Font.Name = $TA; $fg.Range.Font.NameBi = $TA; $fg.Range.Font.Size = $uMatan; $fg.Range.Font.SizeBi = $uMatan
    }

    $st = $doc.Styles.Item(-30)                          # Footnote Text
    $st.Font.Name = $TA; $st.Font.NameBi = $TA; $st.Font.Size = $uCatatan; $st.Font.SizeBi = $uCatatan
    $st.ParagraphFormat.ReadingOrder = 0; $st.ParagraphFormat.Alignment = 3
    $st.ParagraphFormat.SpaceAfter = 0; $st.ParagraphFormat.SpaceBefore = 0; $st.ParagraphFormat.LineSpacingRule = 0
    $doc.Footnotes.NumberingRule = $ULANG
    $doc.Footnotes.NumberStyle = 0

    function Para($align, $before, $indent) {
        $pf = $sel.ParagraphFormat
        $pf.Reset()
        $pf.ReadingOrder = 0; $pf.Alignment = [int]$align
        $pf.SpaceBefore = [single]$before; $pf.SpaceAfter = 0; $pf.LineSpacingRule = 0
        if ($spasiAktif -ne 1) { $pf.LineSpacingRule = 5; $pf.LineSpacing = $word.LinesToPoints($spasiAktif) }   # 5 = wdLineSpaceMultiple
        $pf.LeftIndent = 0; $pf.RightIndent = 0; $pf.FirstLineIndent = [single]$indent
        $pf.KeepWithNext = 0; $pf.PageBreakBefore = 0; $pf.WidowControl = -1
    }
    function Tulis($t, $font, $size, $bold, $sup, $warna = -16777216) {
        if (-not $t) { return }
        $sel.InsertAfter($t)
        $f = $sel.Font
        $f.Name = [string]$font; $f.NameBi = [string]$font; $f.Size = [single]$size; $f.SizeBi = [single]$size
        $f.Bold = [int]$bold; $f.BoldBi = [int]$bold; $f.Italic = 0; $f.ItalicBi = 0; $f.Superscript = [int]$sup; $f.Color = [int]$warna
        $sel.Collapse(0)
    }
    # Halaman fisik sebuah posisi (seperti Information(3)) dari awal tiap halaman: GoTo sekali per halaman. Information per
    # catatan kaki menyusun halaman dari awal dokumen tiap dipanggil, makin belakang makin lambat (bahts 63 catatan kaki:
    # ±10 detik per putaran NomorCatatan; dengan GoTo ±0,2 detik). Untuk penanda فهرس (Hal) Information(1) tetap lebih
    # cepat: bentuk kitab 187 halaman 7 detik, peta GoTo 9,5
    function AwalHalaman { $n = $doc.ComputeStatistics(2); return , @(for ($k = 1; $k -le $n; $k++) { $doc.GoTo(1, 1, $k).Start }) }
    function HalamanDi($awal, $pos) {
        $lo = 0; $hi = $awal.Count - 1
        while ($lo -lt $hi) { $mid = [int][Math]::Floor(($lo + $hi + 1) / 2); if ($awal[$mid] -le $pos) { $lo = $mid } else { $hi = $mid - 1 } }
        return $lo + 1
    }
    # tautan/DOI (pola olah.TAUTAN) = run kiri-ke-kanan, dicetak apa adanya: di teks kanan-ke-kiri Word (angka konteks)
    # mencetak «doi.org/10.21608/jasis.2021» sebagai «doi.org/١٠,٢١٦٠٨/jasis.٢٠٢١». $teks mulai di posisi $awal cerita $rg
    function Tautan($rg, $awal, $teks) {
        if (-not $teks) { return }
        foreach ($a in [regex]::Matches($teks, $DATA.tautan)) {
            $l = $rg.Duplicate; $l.SetRange($awal + $a.Index, $awal + $a.Index + $a.Length); $l.Select(); $word.Selection.LtrRun()
        }
    }
    function TeksRuns($runs) { $s = ''; foreach ($r in $runs) { if ($null -ne $r.t) { $s += $r.t } elseif ($r.pg) { $s += '⟦' + $r.pg + '⟧' } }; return $s }
    # nomor catatan kaki = tanda buatan sendiri, bukan nomor otomatis Word: nomor otomatis Word selalu 0-9
    # (Options.ArabicNumeral tidak berlaku untuknya). Nomornya dibetulkan NomorCatatan sesudah halaman tersusun.
    $asalCatatan = New-Object System.Collections.ArrayList   # nomor urut Word -> indeks bahan (bukti diam/potongan bisa melompat)
    function Catatan($idx) {
        [void]$asalCatatan.Add($idx)
        $awal = $sel.Start
        Tulis '(' $TA $uMatan 0 1
        $fn = @(BuatCatatan $sel.Range $idx (Angka ($doc.Footnotes.Count + 1)))[-1]
        $doc.Range($fn.Reference.End, $fn.Reference.End).Select()
        Tulis ')' $TA $uMatan 0 1
        # «(١)» kanan-ke-kiri: tanpa itu kurungnya terbalik di sekitar angka ٠-٩
        $doc.Range($awal, $sel.Start).Select(); $word.Selection.RtlRun(); $sel.Collapse(0)
    }
    function BuatCatatan($rg, $idx, $nomor) {
        $c = $DATA.catatan[$idx]
        $fn = $doc.Footnotes.Add($rg, $nomor, (' ' + (TeksRuns $c.runs)))
        $fr = $fn.Range                                  # mulai dari spasi di depan teks; tanda + spasi Word di depannya
        $fr.Font.Name = $TA; $fr.Font.NameBi = $TA; $fr.Font.Size = $uCatatan; $fr.Font.SizeBi = $uCatatan; $fr.Font.Bold = 0; $fr.Font.BoldBi = 0; $fr.Font.Superscript = 0
        $fp = $fr.Paragraphs(1); $fp.ReadingOrder = 0; $fp.Alignment = 3
        $fr.Select(); $word.Selection.RtlRun()
        if ($c.al) {   # @angka_ayat: latin: angka di run kiri-ke-kanan dicetak Word 0-9 walau angka konteks
            foreach ($a in [regex]::Matches((TeksRuns $c.runs), '[0-9]+(?:[-–][0-9]+)*')) {
                $l = $fn.Range; $l.SetRange($fr.Start + 1 + $a.Index, $fr.Start + 1 + $a.Index + $a.Length); $l.Select(); $word.Selection.LtrRun()
            }
        }
        Tautan $fn.Range ($fr.Start + 1) (TeksRuns $c.runs)
        $fr.ParagraphFormat.SpaceBefore = 0; $fr.ParagraphFormat.SpaceAfter = 0; $fr.ParagraphFormat.LineSpacingRule = 0
        $off = 1
        foreach ($r in $c.runs) {
            $len = 0
            if ($null -ne $r.t) { $len = $r.t.Length } elseif ($r.pg) { $len = $r.pg.Length + 2 }
            if ($r.q) { $q = $fn.Range; $q.SetRange($fr.Start + $off, $fr.Start + $off + $len); $q.Font.Name = $QF; $q.Font.NameBi = $QF }
            $off += $len
        }
        # nomor di catatan kaki: (1) ukuran normal, bukan superskrip
        $pr = $fr.Paragraphs(1).Range
        $m = $fn.Range; $m.SetRange($pr.Start, $pr.Start + $nomor.Length)
        $m.Font.Superscript = 0; $m.Font.Size = $uCatatan; $m.Font.SizeBi = $uCatatan; $m.Font.Name = $TA; $m.Font.NameBi = $TA
        $m.InsertBefore('('); $m.InsertAfter(')')
        $m.Font.Superscript = 0
        # nomor di matan: (1) superskrip; kurungnya ditulis Catatan
        $ref = $fn.Reference
        $ref.Font.Superscript = 1; $ref.Font.Size = $uMatan; $ref.Font.SizeBi = $uMatan; $ref.Font.Name = $TA; $ref.Font.NameBi = $TA
        $ref.Select(); $word.Selection.RtlRun()
        return $fn
    }
    # nomor tercetak: mulai 1 lagi tiap halaman (ULANG 2) atau bersambung. Catatan kaki yang nomornya salah dibuat ulang
    # di tempat yang sama (tanda buatan sendiri tidak bisa diganti); itu bisa menggeser halaman, jadi diulang sampai tetap.
    function NomorCatatan {
        for ($putaran = 1; $putaran -le 5; $putaran++) {
            $doc.Repaginate()
            # halaman hanya dibaca untuk nomor yang mulai ulang tiap halaman, dan hanya kalau ada catatan kaki: AwalHalaman
            # membaca awal tiap halaman (bentuk kitab 187 halaman tanpa catatan kaki: ±6 detik untuk apa-apa)
            $ulangHal = $ULANG -eq 2 -and $doc.Footnotes.Count -gt 0
            if ($ulangHal) { $awal = AwalHalaman }
            $salah = @(); $hal = -1; $n = 0; $i = 0
            foreach ($fn in $doc.Footnotes) {
                $i++
                if ($ulangHal) { $p = HalamanDi $awal $fn.Reference.Start; if ($p -ne $hal) { $n = 0; $hal = $p } }
                $n++
                if ($fn.Reference.Text -ne (Angka $n)) { $salah += , @($i, (Angka $n)) }
            }
            if (-not $salah.Count) { return }
            [array]::Reverse($salah)
            foreach ($s in $salah) {
                # objek catatan kaki Word menunjuk nomor urut: hapus dulu, baru buat di tempatnya
                $lama = $doc.Footnotes.Item($s[0]); $pos = $lama.Reference.Start; $lama.Delete()
                [void](BuatCatatan $doc.Range($pos, $pos) $asalCatatan[$s[0] - 1] $s[1])
            }
        }
        throw "Nomor catatan kaki belum tetap sesudah 5 putaran penyusunan halaman."
    }
    # baris terakhir paragraf yang cuma 1-2 kata ("runt"): jarak huruf paragraf itu dirapatkan 0,1 s.d. 0,3 pt sampai kata
    # itu naik ke baris sebelumnya; tidak berhasil sampai 0,3 = dibiarkan. Hanya paragraf rata kanan-kiri di luar tabel,
    # bukan sub-judul #S (tebal seluruhnya). Nomor baris (Information 10) hanya ada di Print Layout (di Draft -1).
    # Sesudah NomorCatatan (nomor final menentukan lebar baris), lalu NomorCatatan lagi (halaman bisa bergeser).
    # Qulub 27 halaman: runt 22 -> 8, rakit +±30 detik; bentuk kitab 162 halaman: 140 -> 50, +±2 menit
    function BarisPendek {
        $doc.ActiveWindow.View.Type = 3; $doc.Repaginate()
        # runt = kata ketiga dari belakang (huruf saja, bukan angka catatan kaki/tanda baca) ada di baris lain daripada akhir paragraf
        function Runt($r) {
            $akhir = $r.Characters.Last; $pg = $akhir.Information(3); $ln = $akhir.Information(10)
            $ws = $r.Words; $i = $ws.Count; $n = 0
            while ($i -ge 1) {
                $wd = $ws.Item($i); $i--
                if ($wd.Text -notmatch '\p{L}') { continue }
                $n++; if ($n -eq 3) { return ($wd.Information(10) -ne $ln -or $wd.Information(3) -ne $pg) }
            }
            return $false
        }
        $calon = @(foreach ($p in $doc.Paragraphs) {
            $r = $p.Range
            if ($p.Alignment -ne 3 -or $r.Information(12) -or $r.Font.Bold -eq -1 -or $r.ComputeStatistics(1) -lt 2) { continue }
            if (Runt $r) { $p }
        })
        foreach ($p in $calon) {
            $r = $p.Range; $ok = $false
            foreach ($sp in -0.1, -0.2, -0.3) { $r.Font.Spacing = $sp; if (-not (Runt $r)) { $ok = $true; break } }
            if (-not $ok) { $r.Font.Spacing = 0 }
        }
        if ($draft) { $doc.ActiveWindow.View.Type = 1 }
    }
    function Runs($runs, $size, $paksaTebal, $paksaMerah) {
        foreach ($r in $runs) {
            if ($null -ne $r.fn) { Catatan $r.fn }
            elseif ($r.z) {                               # rumuz sumber: huruf kecil cokelat terangkat tanpa kurung, menempel sebelum nomor catatan kaki
                $awal = $sel.Start; Tulis (' ' + $r.z) $TA $size 1 1 $COKLAT
                $doc.Range($awal, $sel.Start).Select(); $word.Selection.RtlRun(); $sel.Collapse(0)
            }
            elseif ($r.bm) { [void]$doc.Bookmarks.Add($r.bm, $sel.Range) }
            elseif ($r.q) { $u = $size; if ($size -eq $uMatan) { $u = $uAyat }; $w = -16777216; if ($r.w) { $w = $r.w }; Tulis $r.t $QF $u 0 0 $w }
            elseif ($null -ne $r.t) {
                $tb = 0; if ($r.b -or $r.m -or $paksaTebal) { $tb = 1 }   # lafaz matn di syarah: tebal + merah (cetakan Saudi: tebal dalam kurung)
                $w = -16777216; if ($r.m -or $paksaMerah) { $w = $MERAH } elseif ($r.w) { $w = $r.w }   # w = @warna sumber paragraf
                $awal = $sel.Start; Tulis $r.t $TA $size $tb 0 $w
                if ($r.t -match $DATA.tautan) { $akhir = $sel.Start; Tautan $doc.Content $awal $r.t; $doc.Range($akhir, $akhir).Select() }
            }
        }
    }
    function Judul($teks, $bm, $pb, $k = '') {
        if ($pb -and $KITAB) {                           # bentuk kitab: judul halaman baru = bagian Word baru, judulnya jadi kepala halaman ganjil
            $sel.InsertBreak(2)
            $s = $doc.Sections($doc.Sections.Count)
            $h = $s.Headers(1); $h.LinkToPrevious = $false; KepalaHalaman $h $teks
            $s.Footers(1).PageNumbers.RestartNumberingAtSection = $false
            $pb = $false
        }
        Para $(if ($k -in $KANAN) { 3 } else { 1 }) 6 0  # @judul_kanan: #B/#M rata kanan seperti #S
        $sel.ParagraphFormat.KeepWithNext = -1
        if ($pb) { $sel.ParagraphFormat.PageBreakBefore = -1; $sel.ParagraphFormat.SpaceBefore = 0 }
        if ($bm) { [void]$doc.Bookmarks.Add($bm, $sel.Range) }
        Tulis $teks $TJ $uJudul 1 0
        $sel.TypeParagraph()
    }

    $toc = New-Object System.Collections.ArrayList
    $nKotak = 0
    $garis = New-Object System.Collections.ArrayList   # paragraf @warna: garis tegak di sisi awal (tetap terlihat di fotokopi hitam putih)
    $diMulakhas = $false; $nT = 0; $pertama = $true; $iR = -1; $pbBerikut = $false; $berjarakL = $false
    function HalamanBaru { if ($script:pbBerikut) { $sel.ParagraphFormat.PageBreakBefore = -1; $sel.ParagraphFormat.SpaceBefore = 0; $script:pbBerikut = $false } }
    # paragraf pengantar = berakhir «:» (spasi dan nomor catatan kaki di ujung tidak dihitung, mis. «…وفيها قولان:»), atau
    # seluruhnya tebal (**أدلة القول الأول:**): tidak boleh tertinggal sendirian di dasar halaman, daftar/dalilnya di
    # halaman berikutnya. Seperti judul (#S): menempel ke paragraf sesudahnya (KeepWithNext), dan Word memecah paragraf
    # panjangnya sendiri, jadi yang ikut pindah hanya baris terakhirnya. Rangkaian paragraf pengantar berturut-turut
    # hanya dua yang terakhir yang menempel: rantai panjang bisa memindah hampir satu halaman dan menyisakan halaman kosong
    function Pengantar($b) {
        if (-not $b -or $b.k -ne 'P') { return $false }
        $tk = @($b.runs | Where-Object { $null -ne $_.t -and $_.t.Trim() })
        if (-not $tk.Count) { return $false }
        return ($tk[-1].t.TrimEnd() -match ':$') -or (@($tk | Where-Object { -not $_.b }).Count -eq 0)
    }
    function Menempel($j) {
        $nx = $DATA.blok[$j + 1]
        if (-not $nx -or $nx.k -in 'K', 'F', 'B', 'M', 'H', 'R') { return $false }   # sesudahnya halaman/judul baru atau akhir isi
        return -not ((Pengantar $nx) -and (Pengantar $DATA.blok[$j + 2]))
    }
    for ($i = 0; $i -lt $DATA.blok.Count; $i++) {
        $blk = $DATA.blok[$i]
        if ($blk.k -eq 'R') { $iR = $i; break }
        if ($blk.k -eq 'H') { $pbBerikut = -not $pertama; continue }   # #H: blok sesudahnya mulai halaman baru
        if ($blk.k -in 'K', 'F', 'B', 'M') {
            $pb = ((($blk.k -in 'K', 'F' -and -not ($KITAB -and $blk.k -eq 'F')) -or $blk.k -in $M.halaman_baru) -and -not $pertama) -or $pbBerikut   # @halaman_baru: B/M juga halaman baru
            $pbBerikut = $false
            $awalIsi = if ($NOMOR_MUQ) { $blk.k -eq 'K' -and $blk.judul -eq 'المقدمة' } else { $blk.k -eq 'F' }
            if ($ABJAD -and $awalIsi -and -not $ftIsi) {   # #F pertama (@nomor: mukadimah: المقدمة): bagian Word baru, nomor kembali ١
                $sel.InsertBreak(2)
                $ftIsi = $doc.Sections($doc.Sections.Count).Footers(1); $ftIsi.LinkToPrevious = $false
                $ftIsi.PageNumbers.NumberStyle = 0; $ftIsi.PageNumbers.RestartNumberingAtSection = $true; $ftIsi.PageNumbers.StartingNumber = 1
                $pb = $false
            }
            $pertama = $false
            $diMulakhas = $MULAKHAS_JARAK -and $blk.k -eq 'K' -and $blk.judul -match '^(ال)?ملخص' -and $blk.judul -notmatch 'الأجنبية|الإنجليزية'
            $spasiAktif = if ($blk.k -eq 'K' -and $blk.judul -match '^(ال)?ملخص') { $SPASI_MULAKHAS } else { $SPASI }
            $nT++; $bm = "t_$nT"
            Judul $blk.judul $bm $pb $blk.k
            $lvl = @{ K = 0; F = 0; B = 1; M = 2 }[$blk.k]
            [void]$toc.Add(@{ t = $blk.judul; bm = $bm; lvl = $lvl })
        }
        elseif ($blk.k -eq 'T') {                         # kotak matn: bingkai merah tipis, teks merah, rata kanan-kiri
            Para 3 6 0
            HalamanBaru
            $awal = $sel.Start
            Runs $blk.runs $uMatan $false $true
            $nKotak++; [void]$doc.Bookmarks.Add("kotak_$nKotak", $doc.Range($awal, $sel.Start))   # bingkainya dipasang sesudah isi selesai
            $sel.TypeParagraph()
        }
        elseif ($blk.k -eq 'V') {                         # bait syair: di tengah, tanpa awal alinea
            Para 1 2 0
            HalamanBaru
            Runs $blk.runs $uMatan $false
            $sel.TypeParagraph()
        }
        elseif ($blk.k -eq 'L') {                         # paragraf Latin: kiri ke kanan, rata kanan-kiri
            $judulL = [bool]$blk.tengah                    # «#L **Abstract**»: judul tebal di tengah, paragraf #L sesudahnya berjarak
            $jarakL = if ($judulL) { 6 } elseif ($i -gt 0 -and $DATA.blok[$i - 1].k -eq 'L' -and $script:berjarakL) { 6 } else { 0 }
            $script:berjarakL = $judulL -or ($jarakL -gt 0)
            Para 3 $jarakL 0
            HalamanBaru
            $sel.ParagraphFormat.ReadingOrder = 1
            $sel.ParagraphFormat.Alignment = if ($judulL) { 1 } else { 3 }
            if ($judulL) { $sel.ParagraphFormat.KeepWithNext = -1 }
            $awal = $sel.Start
            Tulis $blk.runs[0].t 'Times New Roman' $(if ($judulL) { $uJudul } else { $uMatan }) ([int]$judulL) 0
            $doc.Range($awal, $sel.Start).Select(); $word.Selection.LtrRun(); $sel.Collapse(0)
            $sel.TypeParagraph()
        }
        elseif ($blk.k -eq 'S') {
            Para 3 6 0
            HalamanBaru
            $sel.ParagraphFormat.KeepWithNext = -1
            if ($TO_TITIK -and $blk.judul.StartsWith('❖')) {   # فهرس الموضوعات titik: sub-judul «❖ …» ikut, di bawah judul sebelumnya
                $nT++; [void]$doc.Bookmarks.Add("t_$nT", $sel.Range); [void]$toc.Add(@{ t = $blk.judul; bm = "t_$nT"; lvl = 1 })
            }
            Tulis $blk.judul $TJ $uJudul 1 0
            $sel.TypeParagraph()
        }
        else {
            if ($diMulakhas) { Para 3 $(if ($DATA.blok[$i - 1].k -eq 'K') { 0 } else { 6 }) 0 } else { Para 3 0 ($word.CentimetersToPoints(0.8)); $sel.ParagraphFormat.SpaceAfter = $JARAK_P }
            HalamanBaru
            $awal = $sel.Start
            Runs $blk.runs $uMatan $false
            $teks = @($blk.runs | Where-Object { $_.t -and $_.t.Trim() })
            $biasa = @($teks | Where-Object { -not $_.m })    # lafaz matn ((…)) tetap merah: tidak dihitung
            $w = @($biasa | Where-Object { $_.w } | ForEach-Object { $_.w } | Select-Object -Unique)
            if ($biasa.Count -and $w.Count -eq 1 -and @($biasa | Where-Object { -not $_.w }).Count -eq 0) {
                [void]$doc.Bookmarks.Add("garis_$($garis.Count + 1)", $doc.Range($awal, $sel.Start)); [void]$garis.Add($w[0])
            }
            if ((Pengantar $blk) -and (Menempel $i)) { $sel.ParagraphFormat.KeepWithNext = -1 }
            $sel.TypeParagraph()
        }
    }

    function Sel-Akhir { [void]$sel.EndKey(6) }
    # judul المصادر/فهرس: yang pertama sesudah الخاتمة selalu halaman baru; @fihris: sambung = sisanya menyambung
    $script:fihrisPertama = $true
    function JudulFihris($teks, $bm) {
        $pb = $script:fihrisPertama -or -not $FIHRIS_SAMBUNG; $script:fihrisPertama = $false
        Judul $teks $bm $pb
        if (-not $pb) { $p = $sel.Paragraphs(1).Previous(1); if ($p) { $p.SpaceBefore = 24 } }
    }
    function Tabel($rows, $widthsCm, $garis) {
        Para 3 0 0
        $tbl = $doc.Tables.Add($sel.Range, [int]$rows, [int]$widthsCm.Count)
        $tbl.TableDirection = 0
        $tbl.Borders.Enable = $garis
        $tbl.AllowAutoFit = $false
        for ($c = 1; $c -le $widthsCm.Count; $c++) { $tbl.Columns($c).Width = $word.CentimetersToPoints($widthsCm[$c - 1]) }
        $tbl.Rows.Alignment = 1
        $tbl.Range.ParagraphFormat.ReadingOrder = 0; $tbl.Range.ParagraphFormat.SpaceAfter = 0; $tbl.Range.ParagraphFormat.SpaceBefore = 0
        $tbl.Range.ParagraphFormat.LineSpacingRule = 0; $tbl.Range.ParagraphFormat.FirstLineIndent = 0
        $tbl.Range.Font.Name = $TA; $tbl.Range.Font.NameBi = $TA; $tbl.Range.Font.Size = $uMatan; $tbl.Range.Font.SizeBi = $uMatan
        $tbl.Range.Font.Bold = 0; $tbl.Range.Font.BoldBi = 0
        return $tbl
    }
    function Sel($tbl, $r, $c, $teks, $align, $bold) {
        $rg = $tbl.Cell($r, $c).Range
        $rg.Text = $teks
        $rg.Font.Name = $TA; $rg.Font.NameBi = $TA; $rg.Font.Size = $uMatan; $rg.Font.SizeBi = $uMatan
        $rg.ParagraphFormat.Alignment = $align
        $rg.Font.Bold = $bold; $rg.Font.BoldBi = $bold
        Tautan $rg $rg.Start $teks
    }

    # sel berisi **tebal** dan __miring__ (@pustaka_gaya: muallif): teks ditulis tanpa tandanya, lalu tiap ruas diberi gayanya
    function SelGaya($tbl, $r, $c, $teks) {
        $polos = $teks -replace '\*\*|__', ''
        Sel $tbl $r $c $polos 3 0
        $rg0 = $tbl.Cell($r, $c).Range.Start; $pos = 0; $b = $false; $it = $false
        foreach ($m in [regex]::Split($teks, '(\*\*|__)')) {
            if ($m -eq '**') { $b = -not $b; continue }; if ($m -eq '__') { $it = -not $it; continue }
            if ($m.Length -and ($b -or $it)) {
                $x = $tbl.Cell($r, $c).Range; $x.SetRange($rg0 + $pos, $rg0 + $pos + $m.Length)
                if ($b) { $x.Font.Bold = 1; $x.Font.BoldBi = 1 }; if ($it) { $x.Font.Italic = 1; $x.Font.ItalicBi = 1 }
            }
            $pos += $m.Length
        }
    }
    # ---------- 3. المصادر والمراجع (tabel tanpa garis, urut abjad) ----------
    $bmSesudahIsi = "t_$($nT + 1)"   # judul pertama sesudah الخاتمة (المصادر, atau فهرس pertama): HALAMAN_ISI = halamannya - 1
    function Tulis-Pustaka($judul) {
    $script:nT++; JudulFihris $judul "t_$script:nT"; [void]$toc.Add(@{ t = $judul; bm = "t_$script:nT"; lvl = 0 })
    $n = $DATA.pustaka.Count
    # baris القرآن الكريم (selalu paling atas kalau ada) bertanda «-», kitab lain bernomor 1, 2, ...; penandanya dari olah.py
    $adaQuran = [bool]$DATA.quran
    $geser = if ($adaQuran) { 1 } else { 0 }
    if ($PUSTAKA_MUALLIF) { $geser = 0 }                 # @pustaka_gaya: muallif = القرآن الكريم ikut bernomor (١.)
    $tb = Tabel $n @(1.3, 13.7) 0
    for ($r = 1; $r -le $n; $r++) {
        $no = if ($adaQuran -and $r -eq 1 -and -not $PUSTAKA_MUALLIF) { '-' } else { (Angka ($r - $geser)) + '.' }
        Sel $tb $r 1 $no 1 0
        if ($PUSTAKA_MUALLIF) { SelGaya $tb $r 2 $DATA.pustaka[$r - 1] } else { Sel $tb $r 2 $DATA.pustaka[$r - 1] 3 0 }
    }
    if ($U_PUSTAKA) { $tb.Range.Font.Size = $U_PUSTAKA; $tb.Range.Font.SizeBi = $U_PUSTAKA }
    Sel-Akhir
    }
    if ($adaPu -and -not $PUSTAKA_AKHIR) { Tulis-Pustaka 'المصادر والمراجع' }

    # ---------- 4. الفهارس ----------
    if ($adaAy) {
    $jAy = if ($AYAT_SURAH) { 'فهرس الآيات الكريمة' } else { 'فهرس الآيات القرآنية' }
    $nT++; JudulFihris $jAy "t_$nT"; [void]$toc.Add(@{ t = $jAy; bm = "t_$nT"; lvl = 0 })
    # gabung ayat yang sama, urut mushaf
    $ay = @{}; $urut = New-Object System.Collections.ArrayList
    foreach ($a in $DATA.ayat) {
        $key = '{0:D3}:{1}' -f [int]$a.s, $a.a
        if (-not $ay.ContainsKey($key)) { $ay[$key] = @{ t = $a.t; surah = $a.surah; a = $a.a; bm = @($a.k); s = [int]$a.s; n = [int](($a.a -split '-')[0]) }; [void]$urut.Add($key) }
        else { $ay[$key].bm += $a.k; if ($a.t.Length -gt $ay[$key].t.Length) { $ay[$key].t = $a.t } }
    }
    $urut = $urut | Sort-Object { $ay[$_].s }, { $ay[$_].n }
    # @fihris_ayat: surah = السورة | الآية | الصفحة; sel السورة digabung per surat, ayat diakhiri «الآية n»
    $cA = if ($AYAT_SURAH) { 2 } else { 1 }; $cP = if ($AYAT_SURAH) { 3 } else { 4 }
    if ($AYAT_SURAH) { $tAy = Tabel ($urut.Count + 1) @(2.6, 10.4, 2.0) 1; Sel $tAy 1 1 'السورة' 1 1; Sel $tAy 1 2 'الآية' 1 1; Sel $tAy 1 3 'الصفحة' 1 1 }
    else { $tAy = Tabel ($urut.Count + 1) @(7.9, 2.6, 2.5, 2.0) 1; Sel $tAy 1 1 'الآية' 1 1; Sel $tAy 1 2 'السورة' 1 1; Sel $tAy 1 3 'رقمها' 1 1; Sel $tAy 1 4 'الصفحة' 1 1 }
    $r = 1
    foreach ($key in $urut) {
        $r++; $a = $ay[$key]
        $kata = $a.t -split ' '
        $nk = 4; if ($kata.Count -gt 5 -and $kata[3].Length -le 3) { $nk = 5 }; $pot = if ($kata.Count -gt $nk) { ($kata[0..($nk - 1)] -join ' ') + ' ...' } else { $a.t }
        $ekor = if ($AYAT_SURAH) { ' الآية ' + (Angka $a.a) } else { '' }
        $rg = $tAy.Cell($r, $cA).Range; $rg.Text = '﴿' + $pot + '﴾' + $ekor; $rg.ParagraphFormat.Alignment = 3
        # huruf mushaf hanya untuk kata-kata ayat; titik-titik « ...» tetap huruf matan (huruf mushaf tidak punya titik)
        $nq = if ($pot.EndsWith(' ...')) { $pot.Length - 4 } else { $pot.Length }
        $q = $tAy.Cell($r, $cA).Range; $q.SetRange($rg.Start + 1, $rg.Start + 1 + $nq); $q.Font.Name = $QF; $q.Font.NameBi = $QF; $q.Font.Size = $uAyat; $q.Font.SizeBi = $uAyat
        if ($AYAT_SURAH) { $ra = $tAy.Cell($r, $cA).Range; $ra.Font.Size = $uCatatan; $ra.Font.SizeBi = $uCatatan }   # contoh: sel ayat kecil (14)
        if ($AYAT_SURAH) { Sel $tAy $r 1 $a.surah 1 0 } else { Sel $tAy $r 2 $a.surah 1 0; Sel $tAy $r 3 (Angka $a.a) 1 0 }
        Sel $tAy $r $cP (Angka '00') 1 0
    }
    if ($AYAT_SURAH) { $h1 = $tAy.Rows(1).Range.Font; $h1.Name = $TJ; $h1.NameBi = $TJ }
    if ($AYAT_SURAH) {                                   # gabung sel السورة yang sama, dari bawah supaya nomor baris tetap
        $akhirS = $urut.Count + 1
        for ($r = $urut.Count + 1; $r -ge 2; $r--) {
            $atas = if ($r -gt 2) { $ay[$urut[$r - 3]].s } else { -1 }
            if ($atas -ne $ay[$urut[$r - 2]].s) {
                if ($akhirS -gt $r) {
                    $tAy.Cell($r, 1).Merge($tAy.Cell($akhirS, 1))
                    Sel $tAy $r 1 $ay[$urut[$r - 2]].surah 1 0
                }
                $tAy.Cell($r, 1).VerticalAlignment = 1; $akhirS = $r - 1
            }
        }
    }
    Sel-Akhir
    }
    if ($adaHd) {
    $jHd = if ($HADITS_RINGKAS) { 'فهرس الأحاديث الشريفة' } else { 'فهرس الأحاديث والآثار' }
    $nT++; JudulFihris $jHd "t_$nT"; [void]$toc.Add(@{ t = $jHd; bm = "t_$nT"; lvl = 0 })
    $cH = if ($HADITS_RINGKAS) { 2 } else { 3 }          # @fihris_hadits: ringkas = الأحاديث | الصفحة, طرف dalam kurung
    if ($HADITS_RINGKAS) { $tHd = Tabel ($DATA.hadits.Count + 1) @(7.5, 7.5) 1; Sel $tHd 1 1 'الأحاديث' 1 1; Sel $tHd 1 2 'الصفحة' 1 1; $h1 = $tHd.Rows(1).Range.Font; $h1.Name = $TJ; $h1.NameBi = $TJ }
    else { $tHd = Tabel ($DATA.hadits.Count + 1) @(8.6, 4.4, 2.0) 1; Sel $tHd 1 1 'طرف الحديث أو الأثر' 1 1; Sel $tHd 1 2 'الراوي' 1 1; Sel $tHd 1 3 'الصفحة' 1 1 }
    $r = 1
    foreach ($h in $DATA.hadits) {
        $r++
        if ($HADITS_RINGKAS) { Sel $tHd $r 1 ('(' + $h.t + ')') 3 0; $rh = $tHd.Cell($r, 1).Range; $rh.Font.Size = 12; $rh.Font.SizeBi = 12 } else { Sel $tHd $r 1 ('«' + $h.t + '»') 3 0; Sel $tHd $r 2 $h.r 1 0 }
        Sel $tHd $r $cH (Angka '00') 1 0
    }
    Sel-Akhir
    }
    if ($adaPu -and $PUSTAKA_AKHIR) { Tulis-Pustaka 'فهرس المصادر والمراجع' }
    if ($adaTo) {
    $nT++; JudulFihris 'فهرس الموضوعات' "t_$nT"
    if (-not $TO_TITIK) { [void]$toc.Add(@{ t = 'فهرس الموضوعات'; bm = "t_$nT"; lvl = 0 }) }   # titik: tanpa barisnya sendiri (seperti contoh)
    if ($TO_TITIK) {                                     # @maudhuat: titik = «الموضوع ...... ص» per baris, nomor di tepi kiri
        $lebar = $sec.PageSetup.PageWidth - $sec.PageSetup.LeftMargin - $sec.PageSetup.RightMargin
        $r = 0
        foreach ($e in $toc) {
            $r++
            Para 3 0 0
            $pf = $sel.ParagraphFormat; $pf.Alignment = 0; $pf.SpaceAfter = 6
            if ($e.lvl -gt 0) { $pf.LeftIndent = $word.CentimetersToPoints(0.6 * $e.lvl) }
            $pf.TabStops.ClearAll(); [void]$pf.TabStops.Add($lebar, 2, 1)   # 2 = rata ujung (kiri di teks kanan-ke-kiri), 1 = titik-titik
            Tulis ($e.t + "`t") $TA $uMatan 0 0
            $awalNo = $sel.Start; Tulis (Angka '00') $TA $uMatan 0 0
            [void]$doc.Bookmarks.Add("tn_$r", $doc.Range($awalNo, $sel.Start))
            $sel.TypeParagraph()
        }
    } else {
    $tTo = Tabel ($toc.Count + 1) @(13.0, 2.0) 1
    Sel $tTo 1 1 'الموضوع' 1 1; Sel $tTo 1 2 'الصفحة' 1 1
    $r = 1
    foreach ($e in $toc) { $r++; Sel $tTo $r 1 $e.t 3 ([int]($e.lvl -eq 0)); $tTo.Cell($r, 1).Range.ParagraphFormat.RightIndent = 0; $tTo.Cell($r, 1).Range.ParagraphFormat.LeftIndent = 0; if ($e.lvl -gt 0) { $tTo.Cell($r, 1).Range.ParagraphFormat.RightIndent = $word.CentimetersToPoints(0.7 * $e.lvl) }; Sel $tTo $r 2 (Angka '00') 1 0 }
    Sel-Akhir
    }
    }

    # naskah tanpa catatan kaki tidak punya story catatan kaki
    if ($doc.Footnotes.Count) { foreach ($fpp in $doc.StoryRanges.Item(2).Paragraphs) { $fpp.ReadingOrder = 0; $fpp.Alignment = 3 } }
    foreach ($sc in $doc.Sections) { $sc.Range.FootnoteOptions.NumberingRule = $ULANG; $sc.Range.FootnoteOptions.StartingNumber = 1 }
    $doc.Range().FootnoteOptions.NumberingRule = $ULANG

    # bingkai kotak matn (#T): dipasang di akhir; dipasang saat menulis, Enter sesudahnya menyeret bingkai ke paragraf baru
    for ($k = 1; $k -le $nKotak; $k++) {
        $pf = $doc.Bookmarks.Item("kotak_$k").Range.ParagraphFormat
        foreach ($sisi in -1, -2, -3, -4) { $b = $pf.Borders.Item($sisi); $b.LineStyle = 1; $b.LineWidth = 4; $b.Color = $MERAH }
        $pf.Borders.DistanceFromLeft = 4; $pf.Borders.DistanceFromRight = 4; $pf.Borders.DistanceFromTop = 2; $pf.Borders.DistanceFromBottom = 2
        $pf.SpaceAfter = 6
    }
    for ($k = 1; $k -le $garis.Count; $k++) {
        $pf = $doc.Bookmarks.Item("garis_$k").Range.ParagraphFormat
        $b = $pf.Borders.Item(-4); $b.LineStyle = 1; $b.LineWidth = 12; $b.Color = $garis[$k - 1]
        $pf.Borders.DistanceFromRight = 4
    }
    NomorCatatan
    BarisPendek
    NomorCatatan

    # ---------- 5. Isi nomor halaman ----------
    $doc.Repaginate()
    $HURUF_NOMOR = 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي'    # urutan nomor Word gaya 46; Information(1) tetap memberi angka
    function Hal($bm) {                                  # 1 = nomor halaman seperti yang tercetak
        $r = $doc.Bookmarks.Item($bm).Range; $n = $r.Information(1)
        if ($ABJAD -and $r.Sections(1).Index -eq $bagianDepan) { return [string]$HURUF_NOMOR[$n - 1] }
        return $n
    }
    # {P:kunci} di catatan kaki: tiap ⟦h_…⟧ diganti nomor halaman hadits itu (satu catatan kaki bisa memuat beberapa)
    foreach ($fn in $doc.Footnotes) {
        foreach ($k in @([regex]::Matches($fn.Range.Text, '⟦(h_[^⟧]+)⟧') | ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique)) {
            $rg = $fn.Range; $f = $rg.Find; $f.ClearFormatting(); $f.Replacement.ClearFormatting()
            [void]$f.Execute(('⟦' + $k + '⟧'), $true, $false, $false, $false, $false, $true, 0, $false, (Angka (Hal $k)), 2)
        }
    }
    foreach ($fn in $doc.Footnotes) { if ($fn.Range.Text.Contains('⟦')) { throw "Nomor halaman {P:...} gagal diisi di catatan kaki: $($fn.Range.Text.Trim())" } }
    $doc.Repaginate()
    # tabel فهرس: angka asli («٢٤، ٣٠») bisa lebih lebar daripada '00', barisnya melipat, dan judul sesudahnya pindah halaman
    # (فهرس الموضوعات pernah mencetak 41 padahal judulnya di halaman 42): isi, Repaginate, ulangi sampai tidak ada yang berubah
    $isiLama = @{}
    for ($putaran = 1; $putaran -le 5; $putaran++) {
        $ubah = 0
        if ($adaAy) { $r = 1; foreach ($key in $urut) { $r++; $pg = Angka (($ay[$key].bm | ForEach-Object { Hal $_ } | Select-Object -Unique) -join '، '); if ($isiLama["a$r"] -ne $pg) { $isiLama["a$r"] = $pg; $ubah++; Sel $tAy $r $cP $pg 1 ([int]$AYAT_SURAH) } } }
        if ($adaHd) { $r = 1; foreach ($h in $DATA.hadits) { $r++; $ks = @($h.k); if ($h.lagi) { $ks += $h.lagi }; $pg = Angka (($ks | ForEach-Object { Hal $_ } | Select-Object -Unique) -join '، '); if ($isiLama["h$r"] -ne $pg) { $isiLama["h$r"] = $pg; $ubah++; Sel $tHd $r $cH $pg 1 ([int]$HADITS_RINGKAS) } } }
        if ($adaTo -and $TO_TITIK) {
            $r = 0
            foreach ($e in $toc) {
                $r++; $pg = Angka (Hal $e.bm)
                if ($isiLama["t$r"] -ne $pg) { $isiLama["t$r"] = $pg; $ubah++; $x = $doc.Bookmarks.Item("tn_$r").Range; $x.Text = $pg; [void]$doc.Bookmarks.Add("tn_$r", $x) }
            }
        }
        elseif ($adaTo) { $r = 1; foreach ($e in $toc) { $r++; $pg = Angka (Hal $e.bm); if ($isiLama["t$r"] -ne $pg) { $isiLama["t$r"] = $pg; $ubah++; Sel $tTo $r 2 $pg 1 0 } } }
        $doc.Repaginate()
        if (-not $ubah) { break }
    }
    if ($ubah) { Write-Output "PERINGATAN: nomor halaman فهرس belum tetap sesudah 5 putaran" }

    # ---------- 6. Simpan ----------
    # nomor halaman = teks kanan-ke-kiri, supaya ArabicNumeral 2 mencetaknya ٠-٩ (di akhir: memindah Selection ke kaki
    # halaman). RtlRun hanya ada di Selection, dan bisa diam-diam tidak berpengaruh: satu PDF pernah tercetak 0123 di
    # semua kaki halamannya, <w:rtl/> tidak ada di kaki halaman .docx-nya, dan rakit ulang naskah yang sama benar
    # (penyebabnya belum tahu). Jadi dikerjakan di Print Layout, lalu dibaca lagi dari XML-nya dan diulang sekali
    $doc.ActiveWindow.View.Type = 3
    function NomorRtl($hf) {
        if (-not $hf -or -not $hf.Range.Fields.Count) { return }   # kaki halaman tanpa PAGE (@templat: nomor di kepala halaman)
        for ($k = 1; $k -le 2; $k++) {
            $doc.Activate(); $hf.Range.Select(); $word.Selection.RtlRun()
            if ($hf.Range.WordOpenXML -match '<w:rtl/>') { return }
        }
        # nomor huruf (@nomor: abjad) tidak berangka
        if ($HINDI -and $hf.PageNumbers.NumberStyle -ne 46) { Write-Output "PERINGATAN: Word tidak mau membuat nomor halaman kanan-ke-kiri: nomor halaman bisa tercetak 0123. Rakit lagi." }
    }
    NomorRtl $ft
    if ($KITAB) { NomorRtl $fg }
    if ($ftIsi) { NomorRtl $ftIsi }
    # garis pemisah catatan kaki di kanan: ceritanya baru ada sesudah catatan kaki pertama; dokumen @templat berangkat dari
    # dokumen kosong yang gaya Normal-nya kiri-ke-kanan, jadi garisnya ikut ke kiri kalau tidak disetel di sini
    foreach ($g in @($doc.Footnotes.Separator, $doc.Footnotes.ContinuationSeparator)) {
        try { $g.ParagraphFormat.ReadingOrder = 0; $g.ParagraphFormat.Alignment = 0 } catch {}
    }
    $pages = $doc.ComputeStatistics(2)
    # halaman isi = المقدمة s.d. الخاتمة; tanpa المصادر dan فهرس = halaman terakhir. Ada المقدمة atau nomor tercetak dua
    # jenis (@nomor): dihitung dari halaman fisik, supaya #K sebelum المقدمة (الإهداء، الملخص) tidak ikut terhitung
    $bmMuqaddimah = ($toc | Where-Object { $_.t -eq 'المقدمة' } | Select-Object -First 1).bm
    if ($ABJAD -or $bmMuqaddimah) {
        $hAwal = if ($bmMuqaddimah) { $doc.Bookmarks.Item($bmMuqaddimah).Range.Information(3) } else { 1 }
        $hAkhir = if ($doc.Bookmarks.Exists($bmSesudahIsi)) { $doc.Bookmarks.Item($bmSesudahIsi).Range.Information(3) } else { $pages + 1 }
        $isi = $hAkhir - $hAwal
    }
    elseif ($doc.Bookmarks.Exists($bmSesudahIsi)) { $isi = (Hal $bmSesudahIsi) - 1 }
    else { $akhir = $doc.Content.End - 1; $isi = $doc.Range($akhir, $akhir).Information(1) }
    $lap = @("HALAMAN=$pages", "HALAMAN_ISI=$isi","CATATAN_KAKI=$($doc.Footnotes.Count)", "KATA(termasuk catatan kaki)=$($doc.ComputeStatistics(0, $true))")
    foreach ($e in $toc) { $lap += ("hal {0}: {1}" -f (Hal $e.bm), $e.t) }
    [IO.File]::AppendAllLines($Laporan, [string[]]$lap)
    $doc.EmbedTrueTypeFonts = $true; $doc.SaveSubsetFonts = $false; $doc.DoNotEmbedSystemFonts = $false
    $doc.ActiveWindow.View.Type = 3
    # nomor halaman di kotak teks kepala @templat ikut angka Arab (@angka): Word memilih angka menurut arah teks di
    # sekitarnya, dan teks hasil PAGE di kotak itu kiri-ke-kanan. RtlRun hanya ada di Selection, dan hanya di Print Layout
    if ($kepalaTpl) { foreach ($sh in $kepalaTpl.Shapes) { if ($sh.TextFrame.HasText) { $sh.TextFrame.TextRange.Select(); $word.Selection.RtlRun() } } }
    $doc.SaveAs2("$Out.docx", 16)
    $word.ScreenUpdating = $true                         # tanpa ini garis bingkai/kepala halaman tidak ikut ke PDF
    $word.Options.ArabicNumeral = $NUMERAL               # pengaturan milik seluruh Word pemakai: dipastikan lagi tepat sebelum PDF
    $doc.ExportAsFixedFormat("$Out.pdf", 17)
    $doc.Close($false)
}
finally {
    try { if ($draft) { $doc.ActiveWindow.View.Type = 3 } } catch {}
    try { foreach ($d in @($word.Documents)) { $d.Close($false) } } catch {}
    try { $word.Options.ArabicNumeral = $numeralLama } catch {}
    try { $word.Quit([ref]0) } catch {}                   # Quit menerima argumen ref; Quit(0) selalu gagal
    try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) } catch {}
    # cadangan: Word buatan skrip ini yang belum mati sesudah Quit dimatikan (yang itu saja)
    Start-Sleep -Milliseconds 500
    foreach ($id in $wordIni) { try { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue } catch {} }
    try { Remove-Item -LiteralPath $tmp, $CATATAN_WORD -Force -ErrorAction SilentlyContinue } catch {}
    try { $pegangKunci.Close() } catch {}
}
