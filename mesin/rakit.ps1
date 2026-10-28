# Rakit <Folder>\<berkas>.docx + .pdf dari build.json (hasil olah.py), memakai Word asli (COM).
# Dipanggil oleh bahts.py; jangan dijalankan langsung.
param([Parameter(Mandatory)][string]$Build, [Parameter(Mandatory)][string]$Folder)
$ErrorActionPreference = 'Stop'
$dir = $PSScriptRoot
$DATA = Get-Content -LiteralPath $Build -Raw -Encoding UTF8 | ConvertFrom-Json
$M = $DATA.meta
$Out = Join-Path $Folder $M.berkas; $Laporan = Join-Path $Folder 'laporan.txt'
$FMT = $DATA.format                                      # profil dari format.json (dipilih @format)
$TA = [string]$FMT.huruf; $QF = 'KFGQPC HAFS Uthmanic Script'
$uMatan = [single]$FMT.matan; $uCatatan = [single]$FMT.catatan; $uJudul = [single]$FMT.judul   # ukuran huruf (Word minta angka pecahan)
$uAyat = if ($FMT.ayat) { [single]$FMT.ayat } else { $uMatan }   # ukuran ayat di matan dan فهرس الآيات; profil tanpa "ayat" = sama dengan matan
$ULANG = if ($FMT.catatan_ulang_tiap_halaman) { 2 } else { 0 }   # nomor catatan kaki: 2 = mulai ulang tiap halaman, 0 = bersambung
# @angka hindi: teks naskah sudah diubah olah.py; nomor yang dihitung di sini (فهرس, المصادر, {P:}) diubah Angka;
# nomor halaman dicetak Word menurut Options.ArabicNumeral (gaya nomor Word «Hindi» = angka India २, bukan ٢)
$HINDI = $M.angka -eq 'hindi'
function Angka($s) {
    $s = [string]$s
    if (-not $HINDI) { return $s }
    return -join ($s.ToCharArray() | ForEach-Object { if ($_ -ge [char]'0' -and $_ -le [char]'9') { [char](0x0660 + [int]$_ - 48) } else { $_ } })
}
$JUDUL = $M.judul; $NAMA = $M.nama; $NIM = $M.nim
# judul sampul «… - دراسة …»: bagian sesudah « - » jadi baris kedua yang lebih kecil (kepala halaman tetap judul utuh)
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
$MERAH = 176; $COKLAT = 2772843           # warna Word (BGR): lafaz matn RGB(176,0,0); rumuz RGB(107,79,42)

# satu rakit dalam satu waktu: rakit kedua berhenti di sini, sebelum mematikan Word milik rakit pertama (kunci lepas sendiri saat proses ini selesai)
try { $kunci = [IO.File]::Open("$dir\_tmp\rakit.kunci", 'OpenOrCreate', 'ReadWrite', 'None') }
catch { throw "Rakit lain sedang jalan (memakai Word yang sama): tunggu sampai selesai, lalu ulangi." }
# bersihkan instance Word otomatis yang tertinggal dari percobaan sebelumnya (hanya yang /Automation)
Get-CimInstance Win32_Process -Filter "Name='WINWORD.EXE'" | Where-Object { $_.CommandLine -match '/Automation' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 800
$wordLain = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$word = New-Object -ComObject Word.Application
$wordIni = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $_.Id -notin $wordLain } | ForEach-Object { $_.Id })
$word.Visible = $false; $word.ScreenUpdating = $false; $word.DisplayAlerts = 0
# pengaturan Word pemakai (berlaku untuk semua dokumennya): dipinjam selama rakit, dikembalikan di finally.
# 2 = angka di teks Arab dicetak ٠-٩, di teks Latin 0-9; 0 = selalu 0-9
$numeralLama = $word.Options.ArabicNumeral
$word.Options.ArabicNumeral = if ($HINDI) { 2 } else { 0 }
$tmp = "$dir\_tmp\_kerja.docx"
try {
    # huruf profil yang tidak terpasang diganti Word diam-diam: berhenti di sini saja
    if (@($word.FontNames) -notcontains $TA) { throw "Huruf [$TA] belum terpasang di Windows. Jalankan: python mesin/bahts.py periksa" }
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
    # melaporkan Italic kop sampul Satria terbalik menurut arah bagian (0 padahal XML-nya miring, -1 padahal tidak),
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
    if ($KITAB) { $doc = $word.Documents.Add(); $doc.SaveAs2($tmp, 16); Draft }
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
    function Ganti($p, $teks) { $r = $p.Range; [void]$r.MoveEnd(1, -1); $r.Text = $teks }
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
    # judul dikecilkan sampai muat satu baris (utama 36 -> 26, baris kedua 26 -> 22); yang tetap terlalu panjang diratakan:
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
    $sec = $doc.Sections($doc.Sections.Count)
    $ps = $sec.PageSetup
    $ps.PaperSize = 7
    $ps.TopMargin = $word.CentimetersToPoints(2.5); $ps.BottomMargin = $word.CentimetersToPoints(2.5)
    $ps.LeftMargin = $word.CentimetersToPoints(2.5); $ps.RightMargin = $word.CentimetersToPoints(3.5)
    $ps.HeaderDistance = $word.CentimetersToPoints(1.25); $ps.FooterDistance = $word.CentimetersToPoints(1.25)
    $ft = $sec.Footers(1); $ft.LinkToPrevious = $false; $sec.Headers(1).LinkToPrevious = $false
    $ft.Range.Text = ''
    [void]$ft.Range.Fields.Add($ft.Range, 33)
    $ft.Range.ParagraphFormat.Alignment = 1
    # pedoman: nomor halaman di tengah bawah, huruf dan ukuran sama dengan matan, dihitung mulai dari المقدمة
    $ft.Range.Font.Name = $TA; $ft.Range.Font.NameBi = $TA; $ft.Range.Font.Size = $uMatan; $ft.Range.Font.SizeBi = $uMatan
    $ft.PageNumbers.RestartNumberingAtSection = $true; $ft.PageNumbers.StartingNumber = 1
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
    function TeksRuns($runs) { $s = ''; foreach ($r in $runs) { if ($null -ne $r.t) { $s += $r.t } elseif ($r.pg) { $s += '⟦' + $r.pg + '⟧' } }; return $s }
    # nomor catatan kaki = tanda buatan sendiri, bukan nomor otomatis Word: nomor otomatis Word selalu 0-9
    # (Options.ArabicNumeral tidak berlaku untuknya). Nomornya dibetulkan NomorCatatan sesudah halaman tersusun.
    function Catatan($idx) {
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
                [void](BuatCatatan $doc.Range($pos, $pos) ($s[0] - 1) $s[1])
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
                Tulis $r.t $TA $size $tb 0 $w
            }
        }
    }
    function Judul($teks, $bm, $pb) {
        if ($pb -and $KITAB) {                           # bentuk kitab: judul halaman baru = bagian Word baru, judulnya jadi kepala halaman ganjil
            $sel.InsertBreak(2)
            $s = $doc.Sections($doc.Sections.Count)
            $h = $s.Headers(1); $h.LinkToPrevious = $false; KepalaHalaman $h $teks
            $s.Footers(1).PageNumbers.RestartNumberingAtSection = $false
            $pb = $false
        }
        Para 1 6 0
        $sel.ParagraphFormat.KeepWithNext = -1
        if ($pb) { $sel.ParagraphFormat.PageBreakBefore = -1; $sel.ParagraphFormat.SpaceBefore = 0 }
        if ($bm) { [void]$doc.Bookmarks.Add($bm, $sel.Range) }
        Tulis $teks $TA $uJudul 1 0
        $sel.TypeParagraph()
    }

    $toc = New-Object System.Collections.ArrayList
    $nKotak = 0
    $garis = New-Object System.Collections.ArrayList   # paragraf @warna: garis tegak di sisi awal (tetap terlihat di fotokopi hitam putih)
    $nT = 0; $pertama = $true; $iR = -1
    for ($i = 0; $i -lt $DATA.blok.Count; $i++) {
        $blk = $DATA.blok[$i]
        if ($blk.k -eq 'R') { $iR = $i; break }
        if ($blk.k -in 'K', 'F', 'B', 'M') {
            $pb = (($blk.k -in 'K', 'F' -and -not ($KITAB -and $blk.k -eq 'F')) -or $blk.k -in $M.halaman_baru) -and -not $pertama   # @halaman_baru: B/M juga halaman baru
            $pertama = $false
            $nT++; $bm = "t_$nT"
            Judul $blk.judul $bm $pb
            $lvl = @{ K = 0; F = 0; B = 1; M = 2 }[$blk.k]
            [void]$toc.Add(@{ t = $blk.judul; bm = $bm; lvl = $lvl })
        }
        elseif ($blk.k -eq 'T') {                         # kotak matn: bingkai merah tipis, teks merah, rata kanan-kiri
            Para 3 6 0
            $awal = $sel.Start
            Runs $blk.runs $uMatan $false $true
            $nKotak++; [void]$doc.Bookmarks.Add("kotak_$nKotak", $doc.Range($awal, $sel.Start))   # bingkainya dipasang sesudah isi selesai
            $sel.TypeParagraph()
        }
        elseif ($blk.k -eq 'S') {
            Para 3 6 0
            $sel.ParagraphFormat.KeepWithNext = -1
            Tulis $blk.judul $TA $uJudul 1 0
            $sel.TypeParagraph()
        }
        else {
            Para 3 0 ($word.CentimetersToPoints(0.8))
            $awal = $sel.Start
            Runs $blk.runs $uMatan $false
            $teks = @($blk.runs | Where-Object { $_.t -and $_.t.Trim() })
            $biasa = @($teks | Where-Object { -not $_.m })    # lafaz matn ((…)) tetap merah: tidak dihitung
            $w = @($biasa | Where-Object { $_.w } | ForEach-Object { $_.w } | Select-Object -Unique)
            if ($biasa.Count -and $w.Count -eq 1 -and @($biasa | Where-Object { -not $_.w }).Count -eq 0) {
                [void]$doc.Bookmarks.Add("garis_$($garis.Count + 1)", $doc.Range($awal, $sel.Start)); [void]$garis.Add($w[0])
            }
            $sel.TypeParagraph()
        }
    }

    function Sel-Akhir { [void]$sel.EndKey(6) }
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
    }

    # ---------- 3. المصادر والمراجع (tabel tanpa garis, urut abjad) ----------
    $bmSesudahIsi = "t_$($nT + 1)"   # judul pertama sesudah الخاتمة (المصادر, atau فهرس pertama): HALAMAN_ISI = halamannya - 1
    if ($adaPu) {
    $nT++; Judul 'المصادر والمراجع' "t_$nT" $true; [void]$toc.Add(@{ t = 'المصادر والمراجع'; bm = "t_$nT"; lvl = 0 })
    $n = $DATA.pustaka.Count
    # baris القرآن الكريم (selalu paling atas kalau ada) bertanda «-», kitab lain bernomor 1, 2, ...; penandanya dari olah.py
    $adaQuran = [bool]$DATA.quran
    $geser = if ($adaQuran) { 1 } else { 0 }
    $tb = Tabel $n @(1.3, 13.7) 0
    for ($r = 1; $r -le $n; $r++) {
        $no = if ($adaQuran -and $r -eq 1) { '-' } else { (Angka ($r - $geser)) + '.' }
        Sel $tb $r 1 $no 1 0
        Sel $tb $r 2 $DATA.pustaka[$r - 1] 3 0
    }
    Sel-Akhir
    }

    # ---------- 4. الفهارس ----------
    if ($adaAy) {
    $nT++; Judul 'فهرس الآيات القرآنية' "t_$nT" $true; [void]$toc.Add(@{ t = 'فهرس الآيات القرآنية'; bm = "t_$nT"; lvl = 0 })
    # gabung ayat yang sama, urut mushaf
    $ay = @{}; $urut = New-Object System.Collections.ArrayList
    foreach ($a in $DATA.ayat) {
        $key = '{0:D3}:{1}' -f [int]$a.s, $a.a
        if (-not $ay.ContainsKey($key)) { $ay[$key] = @{ t = $a.t; surah = $a.surah; a = $a.a; bm = @($a.k); s = [int]$a.s; n = [int](($a.a -split '-')[0]) }; [void]$urut.Add($key) }
        else { $ay[$key].bm += $a.k; if ($a.t.Length -gt $ay[$key].t.Length) { $ay[$key].t = $a.t } }
    }
    $urut = $urut | Sort-Object { $ay[$_].s }, { $ay[$_].n }
    $tAy = Tabel ($urut.Count + 1) @(7.9, 2.6, 2.5, 2.0) 1
    Sel $tAy 1 1 'الآية' 1 1; Sel $tAy 1 2 'السورة' 1 1; Sel $tAy 1 3 'رقمها' 1 1; Sel $tAy 1 4 'الصفحة' 1 1
    $r = 1
    foreach ($key in $urut) {
        $r++; $a = $ay[$key]
        $kata = $a.t -split ' '
        $nk = 4; if ($kata.Count -gt 5 -and $kata[3].Length -le 3) { $nk = 5 }; $pot = if ($kata.Count -gt $nk) { ($kata[0..($nk - 1)] -join ' ') + ' ...' } else { $a.t }
        $rg = $tAy.Cell($r, 1).Range; $rg.Text = '﴿' + $pot + '﴾'; $rg.ParagraphFormat.Alignment = 3
        # huruf mushaf hanya untuk kata-kata ayat; titik-titik « ...» tetap huruf matan (huruf mushaf tidak punya titik)
        $nq = if ($pot.EndsWith(' ...')) { $pot.Length - 4 } else { $pot.Length }
        $q = $tAy.Cell($r, 1).Range; $q.SetRange($rg.Start + 1, $rg.Start + 1 + $nq); $q.Font.Name = $QF; $q.Font.NameBi = $QF; $q.Font.Size = $uAyat; $q.Font.SizeBi = $uAyat
        Sel $tAy $r 2 $a.surah 1 0; Sel $tAy $r 3 (Angka $a.a) 1 0; Sel $tAy $r 4 '00' 1 0
    }
    Sel-Akhir
    }
    if ($adaHd) {
    $nT++; Judul 'فهرس الأحاديث والآثار' "t_$nT" $true; [void]$toc.Add(@{ t = 'فهرس الأحاديث والآثار'; bm = "t_$nT"; lvl = 0 })
    $tHd = Tabel ($DATA.hadits.Count + 1) @(8.6, 4.4, 2.0) 1
    Sel $tHd 1 1 'طرف الحديث أو الأثر' 1 1; Sel $tHd 1 2 'الراوي' 1 1; Sel $tHd 1 3 'الصفحة' 1 1
    $r = 1
    foreach ($h in $DATA.hadits) { $r++; Sel $tHd $r 1 ('«' + $h.t + '»') 3 0; Sel $tHd $r 2 $h.r 1 0; Sel $tHd $r 3 '00' 1 0 }
    Sel-Akhir
    }
    if ($adaTo) {
    $nT++; Judul 'فهرس الموضوعات' "t_$nT" $true; [void]$toc.Add(@{ t = 'فهرس الموضوعات'; bm = "t_$nT"; lvl = 0 })
    $tTo = Tabel ($toc.Count + 1) @(13.0, 2.0) 1
    Sel $tTo 1 1 'الموضوع' 1 1; Sel $tTo 1 2 'الصفحة' 1 1
    $r = 1
    foreach ($e in $toc) { $r++; Sel $tTo $r 1 $e.t 3 ([int]($e.lvl -eq 0)); $tTo.Cell($r, 1).Range.ParagraphFormat.RightIndent = 0; $tTo.Cell($r, 1).Range.ParagraphFormat.LeftIndent = 0; if ($e.lvl -gt 0) { $tTo.Cell($r, 1).Range.ParagraphFormat.RightIndent = $word.CentimetersToPoints(0.7 * $e.lvl) }; Sel $tTo $r 2 '00' 1 0 }
    Sel-Akhir
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
    function Hal($bm) { return $doc.Bookmarks.Item($bm).Range.Information(1) }   # 1 = nomor halaman seperti yang tercetak
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
        if ($adaAy) { $r = 1; foreach ($key in $urut) { $r++; $pg = Angka (($ay[$key].bm | ForEach-Object { Hal $_ } | Select-Object -Unique) -join '، '); if ($isiLama["a$r"] -ne $pg) { $isiLama["a$r"] = $pg; $ubah++; Sel $tAy $r 4 $pg 1 0 } } }
        if ($adaHd) { $r = 1; foreach ($h in $DATA.hadits) { $r++; $ks = @($h.k); if ($h.lagi) { $ks += $h.lagi }; $pg = Angka (($ks | ForEach-Object { Hal $_ } | Select-Object -Unique) -join '، '); if ($isiLama["h$r"] -ne $pg) { $isiLama["h$r"] = $pg; $ubah++; Sel $tHd $r 3 $pg 1 0 } } }
        if ($adaTo) { $r = 1; foreach ($e in $toc) { $r++; $pg = Angka (Hal $e.bm); if ($isiLama["t$r"] -ne $pg) { $isiLama["t$r"] = $pg; $ubah++; Sel $tTo $r 2 $pg 1 0 } } }
        $doc.Repaginate()
        if (-not $ubah) { break }
    }

    # ---------- 6. Simpan ----------
    # nomor halaman = teks kanan-ke-kiri, supaya ArabicNumeral 2 mencetaknya ٠-٩ (di akhir: memindah Selection ke kaki halaman)
    $ft.Range.Select(); $word.Selection.RtlRun()
    if ($KITAB) { $fg.Range.Select(); $word.Selection.RtlRun() }
    # garis pemisah catatan kaki di kanan: ceritanya baru ada sesudah catatan kaki pertama; dokumen @templat berangkat dari
    # dokumen kosong yang gaya Normal-nya kiri-ke-kanan, jadi garisnya ikut ke kiri kalau tidak disetel di sini
    foreach ($g in @($doc.Footnotes.Separator, $doc.Footnotes.ContinuationSeparator)) {
        try { $g.ParagraphFormat.ReadingOrder = 0; $g.ParagraphFormat.Alignment = 0 } catch {}
    }
    $pages = $doc.ComputeStatistics(2)
    # halaman isi = المقدمة s.d. الخاتمة (nomor halaman dihitung mulai dari المقدمة); tanpa المصادر dan فهرس = halaman terakhir
    if ($doc.Bookmarks.Exists($bmSesudahIsi)) { $isi = (Hal $bmSesudahIsi) - 1 }
    else { $akhir = $doc.Content.End - 1; $isi = $doc.Range($akhir, $akhir).Information(1) }
    $lap = @("HALAMAN=$pages", "HALAMAN_ISI=$isi","CATATAN_KAKI=$($doc.Footnotes.Count)", "KATA(termasuk catatan kaki)=$($doc.ComputeStatistics(0, $true))")
    foreach ($e in $toc) { $lap += ("hal {0}: {1}" -f (Hal $e.bm), $e.t) }
    [IO.File]::AppendAllLines($Laporan, [string[]]$lap)
    if (Test-Path -LiteralPath "$Out.docx") { Remove-Item -LiteralPath "$Out.docx" -Force }
    $doc.EmbedTrueTypeFonts = $true; $doc.SaveSubsetFonts = $false; $doc.DoNotEmbedSystemFonts = $false
    $doc.ActiveWindow.View.Type = 3
    # nomor halaman di kotak teks kepala @templat ikut angka Arab (@angka): Word memilih angka menurut arah teks di
    # sekitarnya, dan teks hasil PAGE di kotak itu kiri-ke-kanan. RtlRun hanya ada di Selection, dan hanya di Print Layout
    if ($kepalaTpl) { foreach ($sh in $kepalaTpl.Shapes) { if ($sh.TextFrame.HasText) { $sh.TextFrame.TextRange.Select(); $word.Selection.RtlRun() } } }
    $doc.SaveAs2("$Out.docx", 16)
    $word.ScreenUpdating = $true                         # tanpa ini garis bingkai/kepala halaman tidak ikut ke PDF
    $doc.ExportAsFixedFormat("$Out.pdf", 17)
    $doc.Close($false)
}
finally {
    try { if ($draft) { $doc.ActiveWindow.View.Type = 3 } } catch {}
    try { foreach ($d in @($word.Documents)) { $d.Close($false) } } catch {}
    try { $word.Options.ArabicNumeral = $numeralLama } catch {}
    try { $word.Quit([ref]0) } catch {}                   # Quit menerima argumen ref; Quit(0) selalu gagal
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    # cadangan: Word buatan skrip ini yang belum mati sesudah Quit dimatikan (yang itu saja)
    Start-Sleep -Milliseconds 500
    foreach ($id in $wordIni) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    $kunci.Close()
}
