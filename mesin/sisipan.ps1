# SPDX-License-Identifier: AGPL-3.0-or-later
# Sisipan bergaya kitab cetak lama (hitam putih, garis tipis atau ganda 0,75 pt, tanpa latar, rapat): kotak #T, butir
# daftar #-, tabel terjemah sejajar #P, pemisah #Z, tabel rumuz naskah #N, judul tepi {SJ:}, dan kode QR #U/{U:}.
# Di-dot-source rakit.ps1 dan memakai $word, $doc, $sel, $DATA, Para, Runs, Tulis, HalamanBaru, Pengantar, Menempel, dan
# ukuran huruf profil miliknya. Label, nomor, judul kotak, dan teks catatan kaki perbedaan naskah {F:} sudah diputuskan
# olah.py/naskah.py (_baris_kotak, _baris_daftar, _baris_paralel, _baris_nuskhah, Pengurai._farq).

# Kotak = paragraf berbingkai, bukan kotak teks: Word menolak catatan kaki di kotak teks, dan bingkai paragraf ikut
# terpotong pindah halaman. Sisi garis COM = sisi fisik halaman, juga di paragraf kanan-ke-kiri (-1 atas, -2 kiri,
# -3 bawah, -4 kanan). Paragraf bersebelahan yang garisnya sama digabung Word jadi satu bingkai (judul + teks kotak).
# jenis -> sisi bergaris, LineStyle (1 tunggal, 7 ganda)
$KOTAK = @{
    'فائدة' = @(-1, -2, -3, -4), 1
    'تنبيه' = @(-1, -3), 7
    'تعريف' = @(-1, -2, -3, -4), 7
    'خلاصة' = @(-1, -3), 1
    'متن' = @(-3), 7                                   # garis ganda di bawah lafaz matan, syarahnya di bawah garis
}
$JOROK_DAFTAR = 1.0                                    # cm tiap tingkat daftar, juga lebar jorok gantung «أ-»

# Garis dipasang sesudah teks kotak selesai ditulis, pada rentang paragrafnya: paragraf baru sesudah TypeParagraph
# mewarisi garis paragraf sebelumnya dan masuk bingkainya, lalu Borders.Enable = 0 di paragraf baru itu menghapus
# garis seluruh bingkai (diukur di Word)
function Bingkai($pf, $jenis) {
    $sisi, $gaya = $KOTAK[[string]$jenis]
    foreach ($s in $sisi) { $g = $pf.Borders.Item($s); $g.LineStyle = $gaya; $g.LineWidth = 6; $g.Color = 0 }   # 6 = 0,75 pt
    $pf.Borders.DistanceFromTop = 1; $pf.Borders.DistanceFromBottom = 1
    $pf.Borders.DistanceFromLeft = 4; $pf.Borders.DistanceFromRight = 4
    $pf.LeftIndent = 5; $pf.RightIndent = 5             # garis tegak di dalam bidang teks, bukan di tepi kertas
}

function Tulis-Kotak($i, $pb) {
    $blk = $DATA.blok[$i]
    if ($i -gt 0 -and $DATA.blok[$i - 1].kotak) {      # celah 4 pt: dua kotak berturut-turut tidak digabung Word
        Para 1 0 0; $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = 4; $sel.TypeParagraph()
    }
    $atas = 4; $awal = $sel.Start
    if ($blk.kotak.judul) {                             # judul tebal di tengah, menempel ke teks kotaknya
        Para 1 $atas 0; HalamanBaru $pb
        $sel.ParagraphFormat.KeepWithNext = -1
        Tulis ([string]$blk.kotak.judul) $TJ $uMatan 1 0
        $sel.TypeParagraph(); $atas = 0; $pb = $false
    }
    Para 3 $atas 0; HalamanBaru $pb
    $sel.ParagraphFormat.SpaceAfter = 4
    Runs $blk.runs $uMatan $false
    $sel.TypeParagraph()
    Bingkai $doc.Range($awal, $sel.Start - 1).ParagraphFormat $blk.kotak.jenis
}

# butir daftar: tingkat n menjorok (n-1) langkah dari kanan; label «أ-»/«١-» di jorok gantung selebar satu langkah
# (tab sesudah label = jorok gantung), «أولًا:» tebal mengawali teks tanpa jorok gantung. Sisi awal paragraf
# kanan-ke-kiri = LeftIndent COM: RightIndent tercetak di sisi kiri halaman (diukur di PDF)
function Tulis-Butir($i, $pb) {
    $blk = $DATA.blok[$i]; $d = $blk.daftar
    $w = $word.CentimetersToPoints($JOROK_DAFTAR)
    Para 3 0 0; HalamanBaru $pb
    $pf = $sel.ParagraphFormat
    if ($d.gantung) { $pf.LeftIndent = [single]($w * $d.tingkat); $pf.FirstLineIndent = [single](-$w) }
    else { $pf.LeftIndent = [single]($w * ($d.tingkat - 1)) }
    Runs $blk.runs $uMatan $false
    if ((Pengantar $blk) -and (Menempel $i)) { $sel.ParagraphFormat.KeepWithNext = -1 }
    $sel.TypeParagraph()
}

# baris #P berturut-turut = satu tabel dua kolom: Arab di kanan (kolom pertama tabel kanan-ke-kiri), terjemah Latin
# kiri-ke-kanan di kiri (Times New Roman seperti #L). Garis tipis di atas, di bawah, dan tegak di tengah saja.
# Dikembalikan: indeks blok #P terakhir
function Tulis-Paralel($i, $pb) {
    $baris = @($DATA.blok[$i])
    while ($i + 1 -lt $DATA.blok.Count -and $null -ne $DATA.blok[$i + 1].paralel) { $i++; $baris += $DATA.blok[$i] }
    Para 1 4 0; HalamanBaru $pb
    $tbl = $doc.Tables.Add($sel.Range, [int]$baris.Count, 2)
    $tbl.TableDirection = 0; $tbl.Borders.Enable = 0; $tbl.Rows.Alignment = 1
    $tbl.PreferredWidthType = 2; $tbl.PreferredWidth = 100; $tbl.Rows.AllowBreakAcrossPages = -1
    foreach ($s in -1, -3, -6) { $g = $tbl.Borders.Item($s); $g.LineStyle = 1; $g.LineWidth = 6; $g.Color = 0 }   # -6 = garis tegak dalam
    $tbl.TopPadding = 2; $tbl.BottomPadding = 2; $tbl.LeftPadding = 5; $tbl.RightPadding = 5
    $rf = $tbl.Range.ParagraphFormat
    $rf.ReadingOrder = 0; $rf.FirstLineIndent = 0; $rf.LeftIndent = 0; $rf.RightIndent = 0; $rf.Alignment = 0
    $rf.SpaceBefore = 0; $rf.SpaceAfter = 0; $rf.LineSpacingRule = 0; $rf.KeepWithNext = 0; $rf.PageBreakBefore = 0
    for ($r = 0; $r -lt $baris.Count; $r++) {
        $x = $tbl.Cell($r + 1, 1).Range; $x.Collapse(1); $x.Select()
        Runs $baris[$r].runs $uTabel $false
        $y = $tbl.Cell($r + 1, 2).Range; $y.ParagraphFormat.ReadingOrder = 1; $y.Collapse(1); $y.Select()
        $awal = $sel.Start
        Tulis ([string]$baris[$r].paralel) 'Times New Roman' $uLatin 0 0
        $doc.Range($awal, $sel.Start).Select(); $word.Selection.LtrRun()
    }
    $doc.Range($tbl.Range.End, $tbl.Range.End).Select()
    if ($i + 1 -lt $DATA.blok.Count -and $DATA.blok[$i + 1].k -eq 'J') {   # tabel #J tepat sesudahnya tidak digabung Word
        Para 1 0 0; $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = 2; $sel.TypeParagraph()
    }
    return $i
}

# #Z: tiga bintang Arab «٭» (U+066D) di tengah, rapat; «*» Latin tercetak kecil dan naik di huruf Arab
function Tulis-Pemisah($pb) {
    Para 1 3 0; HalamanBaru $pb
    Tulis '٭     ٭     ٭' $TA $uMatan 0 0
    $sel.ParagraphFormat.SpaceAfter = 3
    $sel.TypeParagraph()
}

# #N: tabel الرمز | النسخة dari @nuskhah, bergaris seperti #P (atas, bawah kepala, bawah; tegak di tengah), tanpa latar
function Tulis-Nuskhah($blk, $pb) {
    $baris = @($blk.nuskhah)
    Para 1 4 0; HalamanBaru $pb
    $tbl = $doc.Tables.Add($sel.Range, [int]$baris.Count + 1, 2)
    $tbl.TableDirection = 0; $tbl.Borders.Enable = 0; $tbl.Rows.Alignment = 1
    $tbl.PreferredWidthType = 2; $tbl.PreferredWidth = 100; $tbl.Rows.AllowBreakAcrossPages = -1
    foreach ($s in -1, -3, -6) { $g = $tbl.Borders.Item($s); $g.LineStyle = 1; $g.LineWidth = 6; $g.Color = 0 }
    $g = $tbl.Rows(1).Borders.Item(-3); $g.LineStyle = 1; $g.LineWidth = 6; $g.Color = 0
    $tbl.TopPadding = 2; $tbl.BottomPadding = 2; $tbl.LeftPadding = 5; $tbl.RightPadding = 5
    $rf = $tbl.Range.ParagraphFormat
    $rf.ReadingOrder = 0; $rf.FirstLineIndent = 0; $rf.LeftIndent = 0; $rf.RightIndent = 0; $rf.Alignment = 3
    $rf.SpaceBefore = 0; $rf.SpaceAfter = 0; $rf.LineSpacingRule = 0; $rf.KeepWithNext = 0; $rf.PageBreakBefore = 0
    $tbl.Columns(1).PreferredWidthType = 2; $tbl.Columns(1).PreferredWidth = 15
    $tbl.Columns(2).PreferredWidthType = 2; $tbl.Columns(2).PreferredWidth = 85
    $tbl.Rows(1).HeadingFormat = -1
    $isi = @(, @(@(@{ t = 'الرمز'; b = $true }), @(@{ t = 'النسخة'; b = $true }))) + $baris
    for ($r = 0; $r -lt $isi.Count; $r++) {
        for ($c = 0; $c -lt 2; $c++) {
            $x = $tbl.Cell($r + 1, $c + 1).Range
            if ($r -eq 0 -or $c -eq 0) { $x.ParagraphFormat.Alignment = 1 }
            $x.Collapse(1); $x.Select()
            Runs $isi[$r][$c] $uTabel $false
        }
    }
    $doc.Range($tbl.Range.End, $tbl.Range.End).Select()
}

# {SJ:judul}: paragraf berbingkai (framePr) di tepi kiri halaman, sejajar baris pertama paragraf sesudahnya. Posisi
# tegaknya relatif ke paragraf itu, jadi ikut pindah bersama paragrafnya (bentuk mengapung yang ditambat ke halaman
# bergeser ke halaman lain). Bingkai dipasang sesudah paragraf berikutnya dibuka: paragraf baru mewarisi framePr, dan
# dua paragraf berbingkai sama yang bersebelahan digabung Word jadi satu bingkai.
$TEPI_JAANIB = 0.5                                     # cm dari tepi kertas kiri; celah ke teks 0,3 cm
function Tulis-Jaanib($judul, $pb) {
    Para 1 0 0; HalamanBaru $pb
    $sel.ParagraphFormat.KeepWithNext = -1
    $awal = $sel.Start
    Tulis ([string]$judul) $TJ $uCatatan 1 0
    $sel.TypeParagraph()
    $kiri = $sel.Sections(1).PageSetup.LeftMargin
    # Frames.Add pada teks paragrafnya (tanpa tanda paragraf): Word memindah teks itu ke paragraf berbingkai dan menyisakan
    # paragraf kosong tanpa bingkai di bawahnya, yang memakan satu baris: dihapus di sini
    $fr = $doc.Frames.Add($doc.Range($awal, $sel.Start - 1))
    $kosong = $fr.Range.Paragraphs(1).Next(1)
    if ($kosong.Range.Text -eq "`r" -and $kosong.Range.End -le $sel.Start) { [void]$kosong.Range.Delete() }
    $fr.Borders.Enable = 0                                 # Frames.Add memberi garis keliling
    $fr.RelativeHorizontalPosition = 1; $fr.HorizontalPosition = $word.CentimetersToPoints($TEPI_JAANIB)   # 1 = halaman
    $fr.WidthRule = 2; $fr.Width = [single]($kiri - $word.CentimetersToPoints($TEPI_JAANIB + 0.3))   # 2 = tepat
    $fr.RelativeVerticalPosition = 2; $fr.VerticalPosition = 0                                     # 2 = paragraf
    $fr.HorizontalDistanceFromText = 0; $fr.VerticalDistanceFromText = 0; $fr.LockAnchor = $true
}

# Kode QR = bidang DISPLAYBARCODE Word (bukan gambar): Word menggambarnya sendiri, tetap bidang hidup di .docx.
# \s = skala (persen), \q 1 = koreksi galat M. Alamat 29 huruf: catatan kaki (50) = QR 1,5 cm, modul 0,42 mm; blok
# (80) = 2,3 cm (diukur di PDF). Skala 35 = modul 0,28 mm, terlalu halus untuk kamera ponsel dari kertas
$QR_CATATAN = 50; $QR_BLOK = 80
function Pasang-QR($rg, $url, $skala) {
    [void]$doc.Fields.Add($rg, -1, "DISPLAYBARCODE ""$url"" QR \s $skala \q 1", $false)
}

# #U: kode QR di tengah, lalu keterangan dan alamatnya (kecil, di tengah) di bawahnya
function Tulis-QR($blk, $pb) {
    Para 1 6 0; HalamanBaru $pb
    $sel.ParagraphFormat.KeepWithNext = -1
    $p = $sel.Start
    $sel.TypeParagraph()
    Pasang-QR $doc.Range($p, $p) ([string]$blk.qr) $QR_BLOK
    Para 1 2 0
    $sel.ParagraphFormat.SpaceAfter = 6
    Runs $blk.runs $uCatatan $false
    $sel.TypeText([string][char]11)
    Runs @(@{ t = [string]$blk.qr }) $uCatatan $false
    $sel.TypeParagraph()
}
