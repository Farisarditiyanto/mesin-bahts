# Rakit <Folder>\<berkas>.docx + .pdf dari build.json (hasil olah.py), memakai Word asli (COM).
# Dipanggil oleh bahts.py; jangan dijalankan langsung.
param([Parameter(Mandatory)][string]$Build, [Parameter(Mandatory)][string]$Folder)
$ErrorActionPreference = 'Stop'
$dir = $PSScriptRoot
$DATA = Get-Content $Build -Raw -Encoding UTF8 | ConvertFrom-Json
$M = $DATA.meta
$Out = Join-Path $Folder $M.berkas; $Laporan = Join-Path $Folder 'laporan.txt'
$FMT = $DATA.format                                      # profil dari format.json (dipilih @format)
$TA = [string]$FMT.huruf; $QF = 'KFGQPC HAFS Uthmanic Script'
$uMatan = [single]$FMT.matan; $uCatatan = [single]$FMT.catatan; $uJudul = [single]$FMT.judul   # ukuran huruf (Word minta angka pecahan)
$uAyat = if ($FMT.ayat) { [single]$FMT.ayat } else { $uMatan }   # ukuran ayat di matan dan فهرس الآيات; profil tanpa "ayat" = sama dengan matan
$ULANG = if ($FMT.catatan_ulang_tiap_halaman) { 2 } else { 0 }   # nomor catatan kaki: 2 = mulai ulang tiap halaman, 0 = bersambung
$JUDUL = $M.judul; $NAMA = $M.nama; $NIM = $M.nim
$MUSYRIF = if ($M.musyrif -and $M.musyrif -ne '-') { [string]$M.musyrif } else { '' }
$JABATAN = if ($MUSYRIF -and $M.jabatan -and $M.jabatan -ne '-') { [string]$M.jabatan } else { '' }

# bersihkan instance Word otomatis yang tertinggal dari percobaan sebelumnya (hanya yang /Automation)
Get-CimInstance Win32_Process -Filter "Name='WINWORD.EXE'" | Where-Object { $_.CommandLine -match '/Automation' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 800
$wordLain = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$word = New-Object -ComObject Word.Application
$wordIni = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $_.Id -notin $wordLain } | ForEach-Object { $_.Id })
$word.Visible = $false; $word.ScreenUpdating = $false; $word.DisplayAlerts = 0
$tmp = "$dir\_tmp\_kerja.docx"
try {
    # ---------- 1. Sampul: berangkat dari template dosen ----------
    if (Test-Path $tmp) { Remove-Item $tmp -Force }
    $doc = $word.Documents.Open("$dir\sampul.doc", $false, $true)
    $doc.SaveAs2($tmp, 16)
    $doc.Convert()
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
    $pNama = $null
    foreach ($p in $doc.Paragraphs) {
        $t = $p.Range.Text.Trim()
        if ($t -eq 'عنوان البحث') { Ganti $p $JUDUL }
        elseif ($t -like 'بحث صفي للمستوى*') { Ganti $p $M.jenis }
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
    foreach ($p in $doc.Paragraphs) {
        $r = $p.Range
        if ($r.Text.Trim().Length -gt 0) {
            $sz = $r.Font.SizeBi; if ($sz -gt 100) { $sz = 19 }
            $r.Font.Name = $TA; $r.Font.NameBi = $TA; $r.Font.Bold = 1; $r.Font.BoldBi = 1
            if ($r.Text.Trim() -eq $JUDUL) { $r.Font.Size = 36; $r.Font.SizeBi = 36 } else { $r.Font.Size = [Math]::Max($sz, 20); $r.Font.SizeBi = [Math]::Max($sz, 20) }
        }
    }
    # buang paragraf kosong di ekor sampul supaya sampul tetap 1 halaman
    while ($doc.Paragraphs.Count -gt 3 -and $doc.Paragraphs.Last.Range.Text.Trim().Length -eq 0 -and $doc.Paragraphs.Last.Previous(1).Range.Text.Trim().Length -eq 0) {
        $doc.Paragraphs.Last.Previous(1).Range.Delete() | Out-Null
    }

    # ---------- 2. Bagian isi ----------
    $sel = $word.Selection
    [void]$sel.EndKey(6)
    $sel.InsertBreak(2)                                  # section break (halaman baru)
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

    $st = $doc.Styles.Item(-30)                          # Footnote Text
    $st.Font.Name = $TA; $st.Font.NameBi = $TA; $st.Font.Size = $uCatatan; $st.Font.SizeBi = $uCatatan
    $st.ParagraphFormat.ReadingOrder = 0; $st.ParagraphFormat.Alignment = 3
    $st.ParagraphFormat.SpaceAfter = 0; $st.ParagraphFormat.SpaceBefore = 0; $st.ParagraphFormat.LineSpacingRule = 0
    $doc.Footnotes.NumberingRule = $ULANG
    $doc.Footnotes.NumberStyle = 0
    try { $doc.Footnotes.Separator.ParagraphFormat.ReadingOrder = 0; $doc.Footnotes.Separator.ParagraphFormat.Alignment = 0 } catch {}

    function Para($align, $before, $indent) {
        $pf = $sel.ParagraphFormat
        $pf.Reset()
        $pf.ReadingOrder = 0; $pf.Alignment = [int]$align
        $pf.SpaceBefore = [single]$before; $pf.SpaceAfter = 0; $pf.LineSpacingRule = 0
        $pf.LeftIndent = 0; $pf.RightIndent = 0; $pf.FirstLineIndent = [single]$indent
        $pf.KeepWithNext = 0; $pf.PageBreakBefore = 0; $pf.WidowControl = -1
    }
    function Tulis($t, $font, $size, $bold, $sup) {
        if (-not $t) { return }
        $sel.InsertAfter($t)
        $f = $sel.Font
        $f.Name = [string]$font; $f.NameBi = [string]$font; $f.Size = [single]$size; $f.SizeBi = [single]$size
        $f.Bold = [int]$bold; $f.BoldBi = [int]$bold; $f.Italic = 0; $f.ItalicBi = 0; $f.Superscript = [int]$sup; $f.Color = -16777216
        $sel.Collapse(0)
    }
    function TeksRuns($runs) { $s = ''; foreach ($r in $runs) { if ($null -ne $r.t) { $s += $r.t } elseif ($r.pg) { $s += '⟦' + $r.pg + '⟧' } }; return $s }
    function Catatan($idx) {
        $c = $DATA.catatan[$idx]
        Tulis '(' $TA $uMatan 0 1
        $fn = $doc.Footnotes.Add($sel.Range, [Type]::Missing, (' ' + (TeksRuns $c.runs)))
        $fr = $fn.Range
        $fr.Font.Name = $TA; $fr.Font.NameBi = $TA; $fr.Font.Size = $uCatatan; $fr.Font.SizeBi = $uCatatan; $fr.Font.Bold = 0; $fr.Font.BoldBi = 0; $fr.Font.Superscript = 0
        $fp = $fr.Paragraphs(1); $fp.ReadingOrder = 0; $fp.Alignment = 3
        $fr.Select(); $word.Selection.RtlRun()
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
        $m = $fn.Range; $m.SetRange($pr.Start, $pr.Start + 1)
        $m.Font.Superscript = 0; $m.Font.Size = $uCatatan; $m.Font.SizeBi = $uCatatan; $m.Font.Name = $TA; $m.Font.NameBi = $TA
        $m.InsertBefore('('); $m.InsertAfter(')')
        $m.Font.Superscript = 0
        # nomor di matan: (1) superskrip
        $ref = $fn.Reference
        $ref.Font.Superscript = 1; $ref.Font.Size = $uMatan; $ref.Font.SizeBi = $uMatan; $ref.Font.Name = $TA; $ref.Font.NameBi = $TA
        $doc.Range($ref.End, $ref.End).Select()
        Tulis ')' $TA $uMatan 0 1
    }
    function Runs($runs, $size, $paksaTebal) {
        foreach ($r in $runs) {
            if ($null -ne $r.fn) { Catatan $r.fn }
            elseif ($r.bm) { [void]$doc.Bookmarks.Add($r.bm, $sel.Range) }
            elseif ($r.q) { $u = $size; if ($size -eq $uMatan) { $u = $uAyat }; Tulis $r.t $QF $u 0 0 }
            elseif ($null -ne $r.t) { $tb = 0; if ($r.b -or $paksaTebal) { $tb = 1 }; Tulis $r.t $TA $size $tb 0 }
        }
    }
    function Judul($teks, $bm, $pb) {
        Para 1 6 0
        $sel.ParagraphFormat.KeepWithNext = -1
        if ($pb) { $sel.ParagraphFormat.PageBreakBefore = -1; $sel.ParagraphFormat.SpaceBefore = 0 }
        if ($bm) { [void]$doc.Bookmarks.Add($bm, $sel.Range) }
        Tulis $teks $TA $uJudul 1 0
        $sel.TypeParagraph()
    }

    $toc = New-Object System.Collections.ArrayList
    $nT = 0; $pertama = $true; $iR = -1
    for ($i = 0; $i -lt $DATA.blok.Count; $i++) {
        $blk = $DATA.blok[$i]
        if ($blk.k -eq 'R') { $iR = $i; break }
        if ($blk.k -in 'K', 'F', 'B', 'M') {
            $pb = ($blk.k -in 'K', 'F' -and -not $pertama)
            $pertama = $false
            $nT++; $bm = "t_$nT"
            Judul $blk.judul $bm $pb
            $lvl = @{ K = 0; F = 0; B = 1; M = 2 }[$blk.k]
            [void]$toc.Add(@{ t = $blk.judul; bm = $bm; lvl = $lvl })
        }
        elseif ($blk.k -eq 'S') {
            Para 3 6 0
            $sel.ParagraphFormat.KeepWithNext = -1
            Tulis $blk.judul $TA $uJudul 1 0
            $sel.TypeParagraph()
        }
        else {
            Para 3 0 ($word.CentimetersToPoints(0.8))
            Runs $blk.runs $uMatan $false
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
    $nT++; Judul 'المصادر والمراجع' "t_$nT" $true; [void]$toc.Add(@{ t = 'المصادر والمراجع'; bm = "t_$nT"; lvl = 0 })
    $n = $DATA.pustaka.Count
    $tb = Tabel $n @(1.3, 13.7) 0
    for ($r = 1; $r -le $n; $r++) {
        $no = if ($r -eq 1) { '-' } else { ($r - 1).ToString() + '.' }
        Sel $tb $r 1 $no 1 0
        Sel $tb $r 2 $DATA.pustaka[$r - 1] 3 0
    }
    Sel-Akhir

    # ---------- 4. الفهارس ----------
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
        Sel $tAy $r 2 $a.surah 1 0; Sel $tAy $r 3 $a.a 1 0; Sel $tAy $r 4 '00' 1 0
    }
    Sel-Akhir
    $nT++; Judul 'فهرس الأحاديث والآثار' "t_$nT" $true; [void]$toc.Add(@{ t = 'فهرس الأحاديث والآثار'; bm = "t_$nT"; lvl = 0 })
    $tHd = Tabel ($DATA.hadits.Count + 1) @(8.6, 4.4, 2.0) 1
    Sel $tHd 1 1 'طرف الحديث أو الأثر' 1 1; Sel $tHd 1 2 'الراوي' 1 1; Sel $tHd 1 3 'الصفحة' 1 1
    $r = 1
    foreach ($h in $DATA.hadits) { $r++; Sel $tHd $r 1 ('«' + $h.t + '»') 3 0; Sel $tHd $r 2 $h.r 1 0; Sel $tHd $r 3 '00' 1 0 }
    Sel-Akhir
    $nT++; Judul 'فهرس الموضوعات' "t_$nT" $true; [void]$toc.Add(@{ t = 'فهرس الموضوعات'; bm = "t_$nT"; lvl = 0 })
    $tTo = Tabel ($toc.Count + 1) @(13.0, 2.0) 1
    Sel $tTo 1 1 'الموضوع' 1 1; Sel $tTo 1 2 'الصفحة' 1 1
    $r = 1
    foreach ($e in $toc) { $r++; Sel $tTo $r 1 $e.t 3 ([int]($e.lvl -eq 0)); $tTo.Cell($r, 1).Range.ParagraphFormat.RightIndent = 0; $tTo.Cell($r, 1).Range.ParagraphFormat.LeftIndent = 0; if ($e.lvl -gt 0) { $tTo.Cell($r, 1).Range.ParagraphFormat.RightIndent = $word.CentimetersToPoints(0.7 * $e.lvl) }; Sel $tTo $r 2 '00' 1 0 }
    Sel-Akhir

    # naskah tanpa catatan kaki tidak punya story catatan kaki
    if ($doc.Footnotes.Count) { foreach ($fpp in $doc.StoryRanges.Item(2).Paragraphs) { $fpp.ReadingOrder = 0; $fpp.Alignment = 3 } }
    foreach ($sc in $doc.Sections) { $sc.Range.FootnoteOptions.NumberingRule = $ULANG; $sc.Range.FootnoteOptions.StartingNumber = 1 }
    $doc.Range().FootnoteOptions.NumberingRule = $ULANG

    # ---------- 5. Isi nomor halaman ----------
    $doc.Repaginate()
    function Hal($bm) { return $doc.Bookmarks.Item($bm).Range.Information(1) }   # 1 = nomor halaman seperti yang tercetak
    $r = 1; foreach ($key in $urut) { $r++; $pg = ($ay[$key].bm | ForEach-Object { Hal $_ } | Select-Object -Unique) -join '، '; Sel $tAy $r 4 $pg 1 0 }
    $r = 1; foreach ($h in $DATA.hadits) { $r++; $ks = @($h.k); if ($h.lagi) { $ks += $h.lagi }; $pg = ($ks | ForEach-Object { Hal $_ } | Select-Object -Unique) -join '، '; Sel $tHd $r 3 $pg 1 0 }
    $r = 1; foreach ($e in $toc) { $r++; Sel $tTo $r 2 ([string](Hal $e.bm)) 1 0 }
    foreach ($fn in $doc.Footnotes) {
        $t = $fn.Range.Text
        if ($t -match '⟦(h_[a-z]+)⟧') {
            $rg = $fn.Range; $f = $rg.Find; $f.ClearFormatting(); $f.Replacement.ClearFormatting()
            [void]$f.Execute(('⟦' + $Matches[1] + '⟧'), $true, $false, $false, $false, $false, $true, 0, $false, ([string](Hal $Matches[1])), 1)
        }
    }
    $doc.Repaginate()

    # ---------- 6. Simpan ----------
    $pages = $doc.ComputeStatistics(2)
    $lap = @("HALAMAN=$pages", "CATATAN_KAKI=$($doc.Footnotes.Count)", "KATA(termasuk catatan kaki)=$($doc.ComputeStatistics(0, $true))")
    foreach ($e in $toc) { $lap += ("hal {0}: {1}" -f (Hal $e.bm), $e.t) }
    [IO.File]::AppendAllLines($Laporan, [string[]]$lap)
    if (Test-Path "$Out.docx") { Remove-Item "$Out.docx" -Force }
    $doc.EmbedTrueTypeFonts = $true; $doc.SaveSubsetFonts = $false; $doc.DoNotEmbedSystemFonts = $false
    $doc.SaveAs2("$Out.docx", 16)
    $doc.ExportAsFixedFormat("$Out.pdf", 17)
    $doc.Close($false)
}
finally {
    try { foreach ($d in @($word.Documents)) { $d.Close($false) } } catch {}
    try { $word.Quit(0) } catch {}
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    # Word buatan skrip ini kadang tidak ikut mati setelah Quit: matikan yang itu saja
    Start-Sleep -Milliseconds 500
    foreach ($id in $wordIni) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
}
