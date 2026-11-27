# SPDX-License-Identifier: AGPL-3.0-or-later
# Kepala dan kaki halaman isi (@kepala) dan garis pemisah catatan kaki; di-dot-source rakit.ps1 dan memakai $word,
# $doc, $TA, dan $FMT miliknya. Nilai @kepala sudah diputuskan olah.rencana_cetak ($RENCANA.kepala); bentuk tiap nilai
# ditulis di Pasang-Kepala saja (kotak dan @templat: kepala dari berkas Word, disalin rakit.ps1). Ukuran dari profil
# @format: ukuran_kepala (teks), ukuran_nomor_kepala (nomor tebal klasik), garis_catatan (cm).
#
# Di paragraf kanan-ke-kiri Word membaca perataan dan posisi tab dari kanan: Alignment 0 = rata kanan, tab 2 (rata
# «kanan») di posisi selebar bidang teks = ujung kirinya tepat di tepi kiri. LeftIndent = sisi kanan.

# gaya paragraf judul #K/#F dan judul فهرس (rakit.ps1 `Judul`): sumber STYLEREF judul bagian berjalan. Berbasis Normal
# tanpa ubahan, jadi tampilan judul tetap dari format langsungnya
$GAYA_BERJALAN = 'Judul Bahts Berjalan'

function Gaya-Berjalan {
    $g = try { $doc.Styles.Item($GAYA_BERJALAN) } catch { $null }
    if (-not $g) {
        $g = $doc.Styles.Add($GAYA_BERJALAN, 1)          # 1 = wdStyleTypeParagraph
        $g.BaseStyle = -1; $g.NextParagraphStyle = -1    # -1 = wdStyleNormal
    }
    return $g
}

# judul #F dua baris (@judul_fasl: dua_baris/kotak/pemisah): baris pertamanya saja yang bergaya $GAYA_BERJALAN, jadi
# STYLEREF hanya membaca «المبحث الأول». Sisanya («: تعريف …») ditulis juga di ujung baris pertama itu, 1 pt putih
# selebar 1% dan dirapatkan: tidak terlihat dan tidak menggeser baris, tetapi ikut dibaca STYLEREF, jadi kepala berjalan memuat judul
# utuh. Teks tersembunyi (Font.Hidden) tidak dibaca STYLEREF (dicoba di Word). Dipanggil di kursor rakit.ps1 ($sel, Tulis)
function Ekor-Berjalan($ekor) {
    if (-not $ekor) { return }
    $awal = $sel.Start
    Tulis (': ' + $ekor) $TA 1 0 0 16777215              # 16777215 = putih
    $f = $doc.Range($awal, $sel.Start).Font; $f.Scaling = 1; $f.Spacing = -2   # skala 1% saja masih ±36 pt (diukur di PDF)
    $sel.Font.Scaling = 100; $sel.Font.Spacing = 0
}

# paragraf kepala/kaki yang kosong: kanan-ke-kiri, rata $rata (0 kanan, 1 tengah), huruf profil, tanpa tab dan garis
function HF-Baru($hf, $rata = 0) {
    $hf.LinkToPrevious = $false
    $hf.Range.Text = ''
    foreach ($sp in @($hf.Range.ShapeRange)) { try { $sp.Delete() } catch {} }
    $pf = $hf.Range.ParagraphFormat
    $pf.ReadingOrder = 0; $pf.Alignment = $rata
    $pf.LeftIndent = 0; $pf.RightIndent = 0; $pf.FirstLineIndent = 0; $pf.SpaceBefore = 0; $pf.SpaceAfter = 0
    $pf.LineSpacingRule = 0; $pf.TabStops.ClearAll(); $pf.Borders.Enable = 0
    Huruf $hf.Range.Font $TA ([single]$FMT.ukuran_kepala) 0
}

# rentang kosong tepat sebelum tanda paragraf akhir kepala/kaki: tempat teks berikutnya
function HF-Ujung($hf) { $r = $hf.Range; $r.Collapse(0); return $r }   # Word menaruhnya sebelum tanda paragraf akhir

function HF-Teks($hf, $teks, $tebal = 0, $ukuran = $FMT.ukuran_kepala) {
    $r = HF-Ujung $hf; $r.InsertAfter($teks); Huruf $r.Font $TA ([single]$ukuran) $tebal
}

# $kode: 'PAGE' atau 'STYLEREF "…"'
function HF-Field($hf, $kode, $tebal = 0, $ukuran = $FMT.ukuran_kepala) {
    $f = $hf.Range.Fields.Add((HF-Ujung $hf), -1, $kode, $false)   # -1 = wdFieldEmpty: jenisnya dari kodenya
    $r = $hf.Range.Duplicate; $r.SetRange($f.Code.Start - 1, $f.Result.End + 1)
    Huruf $r.Font $TA ([single]$ukuran) $tebal
}

function HF-Berjalan($hf, $tebal) { HF-Field $hf "STYLEREF `"$GAYA_BERJALAN`"" $tebal }

# { IF { = { PAGE } - INT({ PAGE } / 2) * 2 } = 1 "{ STYLEREF judul bagian }" "$genap" }: halaman ganjil judul bagian
# berjalan, genap $genap. Bukan kepala ganjil/genap Word (OddAndEvenPagesHeaderFooter): dengannya Word menyisipkan
# halaman kosong di PDF supaya nomor ١ bagian isi jatuh di halaman fisik ganjil (sesudah sampul = halaman fisik 2).
# Tanpa MOD: pemisah argumennya mengikuti pengaturan daerah Windows («,» atau «;»). Field di dalam field dibuat dengan
# menimpa penandanya di kode field luar (Fields.Add pada rentang yang tidak kosong menggantinya)
function HF-GanjilGenap($hf, $genap) {
    $genap = $genap -replace '"', '\"'
    $luar = $hf.Range.Fields.Add((HF-Ujung $hf), -1, "IF @M = 1 `"@S`" `"$genap`"", $false)
    # penanda diganti dari yang paling belakang: letak penanda sebelumnya di kode tidak bergeser
    function Tanam($field, $penanda, $kode) {
        $c = $field.Code; $i = $c.Text.LastIndexOf($penanda)
        if ($i -lt 0) { throw "kepala bergantian: penanda $penanda tidak ada di field «$($c.Text)»" }
        $r = $c.Duplicate; $r.SetRange($c.Start + $i, $c.Start + $i + $penanda.Length)
        return $hf.Range.Fields.Add($r, -1, $kode, $false)
    }
    [void](Tanam $luar '@S' "STYLEREF `"$GAYA_BERJALAN`"")
    $sisa = Tanam $luar '@M' '= @P - INT(@P / 2) * 2'
    [void](Tanam $sisa '@P' 'PAGE'); [void](Tanam $sisa '@P' 'PAGE')
    $r = $hf.Range.Duplicate; $r.SetRange($luar.Code.Start - 1, $luar.Result.End + 1); Huruf $r.Font $TA ([single]$FMT.ukuran_kepala) 0
    [void]$luar.Update()
}

# garis di bawah paragraf kepala; $jenis = WdLineStyle (1 = tunggal), $tebal = WdLineWidth (4 = 0,5 pt)
function HF-Garis($hf, $jenis, $tebal) {
    $b = $hf.Range.ParagraphFormat.Borders(-3)           # -3 = wdBorderBottom
    $b.LineStyle = $jenis; $b.LineWidth = $tebal
    $hf.Range.ParagraphFormat.Borders.DistanceFromBottom = 2
}

# tab nomor halaman di ujung kiri bidang teks ($geser pt dari tepi kiri, rata $rata), dengan garis penghubung $isi
function HF-Tab($hf, $lebar, $rata, $isi = 0, $geser = 0) {
    [void]$hf.Range.ParagraphFormat.TabStops.Add([single]($lebar - $geser), $rata, $isi)
}

# tinggi baris paragraf kepala dipastikan (pt), supaya hiasan/bintang bisa diletakkan tepat terhadapnya
function HF-Tinggi($hf, $pt) { $pf = $hf.Range.ParagraphFormat; $pf.LineSpacingRule = 4; $pf.LineSpacing = [single]$pt }

# pedoman: nomor halaman di tengah bawah, huruf dan ukuran sama dengan matan; $kiri/$kanan mengapit nomornya («- ١٢ -»)
function KakiNomor($kaki, $apit = '') {
    HF-Baru $kaki 1
    Huruf $kaki.Range.Font $TA $uMatan 0
    if ($apit) { HF-Teks $kaki "$apit " 0 $uMatan }
    HF-Field $kaki 'PAGE' 0 $uMatan
    if ($apit) { HF-Teks $kaki " $apit" 0 $uMatan }
}

# hiasan kitab terbuka di bawah lengkung (mesin/hias_kitab.png, isinya putih menutup garis) di tengah garis kepala.
# Tepi bawah gambar bening dan piksel beningnya putih (bukan hitam): kalau tidak, tepi isi putih tampak sebagai garis
# tipis abu-abu di bawah lengkung saat gambar dikecilkan
function Hias-Kitab($hd, $tinggiBaris) {
    $g = $hd.Shapes.AddPicture("$dir\hias_kitab.png", $false, $true, 0, 0, $hd.Range)
    $g.LockAspectRatio = -1; $g.Width = $word.CentimetersToPoints(1.15)
    $g.WrapFormat.Type = 3                               # 3 = wdWrapNone (di depan teks): menutup garis di bawahnya
    $g.RelativeHorizontalPosition = 0; $g.Left = -999995   # tengah bidang teks (wdShapeCenter)
    $g.RelativeVerticalPosition = 2                      # dari atas paragraf kepala: kaki lengkung melewati garis sedikit
    $g.Top = [single]($tinggiBaris + 2 - $g.Height * 0.85)   # garis di 85% tinggi gambar: masih di dalam isi putih lengkung (sampai 90%); 10% bawah gambar bening
}

# bintang delapan (ربع الحزب) selebar $lebar pt: persegi + persegi miring (belah ketupat) bergaris tipis berisi putih, di
# belakang nomor halaman yang berpusat $pusat pt dari tepi kiri bidang teks dan $tengah pt di bawah atas paragraf kepala
function Bintang-Nomor($hd, $pusat, $tengah, $lebar) {
    $sisi = $lebar / 1.4142
    foreach ($b in @(@(4, $lebar), @(1, $sisi))) {     # 4 belah ketupat, 1 persegi
        $w = [single]$b[1]
        $sp = $hd.Shapes.AddShape($b[0], 0, 0, $w, $w, $hd.Range)
        $sp.Fill.Visible = -1; $sp.Fill.Solid(); $sp.Fill.ForeColor.RGB = 16777215
        $sp.Line.Visible = -1; $sp.Line.ForeColor.RGB = 0; $sp.Line.Weight = [single]0.6
        $sp.WrapFormat.Type = 5                          # 5 = wdWrapBehind: nomornya di atas
        $sp.RelativeHorizontalPosition = 0; $sp.Left = [single]($pusat - $w / 2)
        $sp.RelativeVerticalPosition = 2; $sp.Top = [single]($tengah - $w / 2)
    }
}

# kepala dan kaki halaman bagian isi $sec (bagian Word sesudahnya mewarisinya) menurut @kepala $jenis
function Pasang-Kepala($sec, $jenis, $judul) {
    $ps = $sec.PageSetup
    $lebar = $ps.PageWidth - $ps.LeftMargin - $ps.RightMargin
    $u = [single]$FMT.ukuran_kepala
    $hd = $sec.Headers(1); $ft = $sec.Footers(1)
    HF-Baru $hd; HF-Baru $ft
    switch ($jenis) {
        'klasik' {                                       # judul — garis memanjang — nomor tebal di pojok kiri
            HF-Tab $hd $lebar 2 3                        # 3 = wdTabLeaderLines
            HF-Teks $hd "$judul "
            # garis penghubung = garis bawah tab: tabnya dinaikkan supaya garis itu di tengah tinggi huruf, bukan di dasarnya
            $r = HF-Ujung $hd; $r.InsertAfter("`t"); Huruf $r.Font $TA $u 0; $r.Font.Position = [int][Math]::Round($u * 0.3)
            HF-Teks $hd ' ' 1 $FMT.ukuran_nomor_kepala
            HF-Field $hd 'PAGE' 1 $FMT.ukuran_nomor_kepala
        }
        { $_ -in 'bagian', 'bagian_hias' } {             # judul bagian berjalan tebal kanan, nomor kiri, garis penuh
            $t = [Math]::Round($u * 1.6)
            HF-Tinggi $hd $t; HF-Tab $hd $lebar 2
            HF-Berjalan $hd 1; HF-Teks $hd "`t"; HF-Field $hd 'PAGE'
            HF-Garis $hd 1 8                             # 8 = 1 pt
            if ($jenis -eq 'bagian_hias') { Hias-Kitab $hd $t }
        }
        'bintang' {                                      # judul kanan, nomor di dalam bintang di pojok kiri, garis tebal-tipis
            # bintang setinggi baris judul, nomornya sedikit lebih kecil daripada judul supaya tiga angka tetap di dalamnya
            $t = [Math]::Round($u * 1.6); $bintang = [single]($u * 1.5); $pusat = $bintang / 2 + 1; $uNo = $u - 2
            HF-Tinggi $hd $t; HF-Tab $hd $lebar 1 0 $pusat   # 1 = tab tengah: nomor berapa pun lebarnya tetap di pusat bintang
            HF-Teks $hd "$judul`t"; HF-Field $hd 'PAGE' 1 $uNo
            # pusat angka: garis dasar baris setinggi tepat $t ±0,82 $t di bawah atas paragraf, angka Arab ±0,7 ukurannya
            # (diukur di PDF); bintang dipusatkan ke situ, bukan ke tengah baris yang lebih tinggi daripada angkanya
            $tengah = $t * 0.82 - $uNo * 0.35
            # judul panjang pindah baris sebelum sampai bintang (tab nomor di luar batas kiri itu tetap dipakai Word);
            # garisnya di paragraf kedua yang selebar bidang teks, karena garis paragraf hanya sepanjang batasnya
            $hd.Range.ParagraphFormat.RightIndent = [single]($bintang + $word.CentimetersToPoints(0.4))
            $hd.Range.InsertParagraphAfter()
            $p = $hd.Range.Paragraphs(2)
            $p.RightIndent = [single]0; $p.TabStops.ClearAll(); $p.SpaceBefore = [single]8; $p.LineSpacingRule = 4; $p.LineSpacing = [single]2
            $b = $p.Borders(-1); $b.LineStyle = 11; $b.LineWidth = 18   # -1 atas; 11 = tebal di atas, tipis di bawah; 2,25 pt
            Bintang-Nomor $hd $pusat $tengah $bintang
        }
        'bergantian' {                                   # ganjil: judul bagian berjalan; genap: judul bahts; nomor di kaki
            HF-Baru $hd 1; HF-GanjilGenap $hd $judul; HF-Garis $hd 1 4
            KakiNomor $ft
        }
        'kaki' { KakiNomor $ft '-' }
        default { KakiNomor $ft }                        # '-' (dan kotak/@templat: kepala dari Word, nomor di kaki kalau kepala itu tanpa nomor)
    }
}

# judul bahts di kepala (klasik, bintang, kotak) yang tidak muat satu baris mendorong nomor halaman keluar dari tempatnya
# (kotak: kepala_kotak.docx, judul rata kanan, sisi kirinya dicadangkan untuk kotak nomor) dan isi halaman ke bawah:
# diperingatkan sesudah tata halaman jadi (Print Layout), supaya ditulis @kepala_judul
function Periksa-Kepala($sec, $jenis) {
    if ($jenis -notin 'klasik', 'bintang', 'kotak') { return }
    $baris = $sec.Headers(1).Range.Paragraphs(1).Range.ComputeStatistics(1)   # 1 = wdStatisticLines
    if ($baris -gt 1) { Write-Output "PERINGATAN: judul di kepala halaman (@kepala: $jenis) tidak muat satu baris ($baris baris): tulis judul pendeknya di @kepala_judul, lalu rakit lagi." }
}

# judul bagian berjalan (bagian, bagian_hias, bergantian: judul #K/#F utuh $judul) yang tidak muat satu baris kepala
# halaman: diukur di dokumen Word sementara selebar bidang teks $lebar pt (bagian: dikurangi tempat nomor di kiri),
# huruf dan ukuran kepala, lalu diperingatkan. Judul bagian berjalan tidak punya padanan @kepala_judul: judulnya sendiri
# yang dipendekkan. bergantian juga memeriksa judul bahts di halaman genap ($bahts)
function Periksa-Berjalan($jenis, $judul, $bahts, $lebar) {
    if ($jenis -notin 'bagian', 'bagian_hias', 'bergantian') { return }
    $sisa = if ($jenis -eq 'bergantian') { $lebar } else { $lebar - $word.CentimetersToPoints(1.5) }
    $uji = $word.Documents.Add(); $doc.Activate()
    try {
        $p = $uji.Paragraphs(1)
        $p.ReadingOrder = 0; $p.Alignment = 0; $p.LeftIndent = 0; $p.RightIndent = 0; $p.FirstLineIndent = 0
        $ps = $uji.Sections(1).PageSetup; $ps.LeftMargin = 36; $ps.RightMargin = [single]($ps.PageWidth - 36 - $sisa)
        $daftar = @($judul | ForEach-Object { @{ t = $_; nama = "judul bagian «$_»" } })
        if ($jenis -eq 'bergantian') { $daftar += @{ t = $bahts; nama = 'judul bahts (halaman genap)' } }
        foreach ($j in $daftar) {
            $r = $uji.Range(0, $uji.Content.End - 1); $r.Text = [string]$j.t
            Huruf $r.Font $TA ([single]$FMT.ukuran_kepala) ([int]($jenis -ne 'bergantian'))
            $baris = $uji.Paragraphs(1).Range.ComputeStatistics(1)   # 1 = wdStatisticLines
            if ($baris -gt 1) {
                $jalan = if ($j.nama -like 'judul bahts*') { 'tulis judul pendeknya di @kepala_judul' } else { 'pendekkan judul itu di naskah, atau pilih @kepala lain' }
                Write-Output "PERINGATAN: $($j.nama) tidak muat satu baris di kepala halaman (@kepala: $jenis, $baris baris): $jalan, lalu rakit lagi."
            }
        }
    } finally { $uji.Close(0); $doc.Activate() }
}

# garis pemisah catatan kaki: $FMT.garis_catatan cm di kanan. Tanda pemisah bawaan Word (lebarnya tetap) diganti garis
# atas paragraf yang ujung kirinya dimundurkan. Ceritanya baru ada sesudah catatan kaki pertama. Garis sambungan
# (catatan yang berlanjut ke halaman berikutnya) tetap selebar bidang teks, rata kanan
function Garis-Catatan($lebar) {
    $g = $doc.Footnotes.Separator
    if (-not $g) { return }                              # bahts tanpa catatan kaki
    $g.Text = ''
    $pf = $g.ParagraphFormat
    $pf.ReadingOrder = 0; $pf.Alignment = 0; $pf.LeftIndent = 0; $pf.FirstLineIndent = 0
    $pf.RightIndent = [single]($lebar - $word.CentimetersToPoints([single]$FMT.garis_catatan))
    $pf.SpaceBefore = 6; $pf.SpaceAfter = 0; $pf.LineSpacingRule = 4; $pf.LineSpacing = 6
    $b = $pf.Borders(-1); $b.LineStyle = 1; $b.LineWidth = 4     # -1 = wdBorderTop, 4 = 0,5 pt
    $s = $doc.Footnotes.ContinuationSeparator
    try { $s.ParagraphFormat.ReadingOrder = 0; $s.ParagraphFormat.Alignment = 0 } catch {}
}
