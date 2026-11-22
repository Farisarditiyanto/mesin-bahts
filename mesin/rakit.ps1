# SPDX-License-Identifier: AGPL-3.0-or-later
# Rakit <Hasil>\<berkas>.docx + .pdf dari bahan JSON -Build (hasil olah.py), memakai Word asli (COM).
# Dipanggil oleh rakit.py, yang menentukan semua jalur di luar <Hasil>\<berkas>; jangan dijalankan langsung.
param([Parameter(Mandatory)][string]$Build, [Parameter(Mandatory)][string]$Hasil, [Parameter(Mandatory)][string]$Laporan,
      [Parameter(Mandatory)][string]$PdfKhulasah, [Parameter(Mandatory)][string]$Kunci, [Parameter(Mandatory)][string]$Galat)
$ErrorActionPreference = 'Stop'
# Galat yang menghentikan skrip ini ditulis juga ke -Galat (UTF-8): rakit.py mengutipnya di pesan GAGAL, karena layar
# bisa dipotong pemanggil (tail/grep) dan huruf Arabnya rusak lewat pipa. Tanpa berkas itu = PowerShell dimatikan dari luar.
trap {
    [IO.File]::WriteAllText($Galat, "$($_.Exception.Message) (rakit.ps1 baris $($_.InvocationInfo.ScriptLineNumber))", (New-Object Text.UTF8Encoding $false))
    break
}
$dir = $PSScriptRoot
. "$dir\word.ps1"
$DATA = Get-Content -LiteralPath $Build -Raw -Encoding UTF8 | ConvertFrom-Json
$M = $DATA.meta
# Rencana cetak (olah.rencana_cetak): apa yang dicetak dan di mana sudah diputuskan di sana, termasuk bawaan profil.
# Skrip ini tidak mengurai @data berdaftar dan tidak punya bawaan profil sendiri
$RENCANA = $DATA.cetak
$Out = Join-Path $Hasil $M.berkas
$FMT = $RENCANA.format                                   # profil dari format.json (dipilih @format; @catatan_kaki/@spasi sudah ditimpakan), tiap kunci terisi
$TA = [string]$FMT.huruf; $QF = 'KFGQPC HAFS Uthmanic Script'
$uMatan = [single]$FMT.matan; $uCatatan = [single]$FMT.catatan; $uJudul = [single]$FMT.judul   # ukuran huruf (Word minta angka pecahan)
$uJudulSub = [single]$FMT.judul_sub                      # ukuran #B/#M/#S
$uAyat = [single]$FMT.ayat                               # ukuran ayat di matan dan فهرس الآيات
$uLatin = [single]$FMT.latin                             # paragraf #L (Times New Roman); judul «#L **…**» 2 poin lebih besar. Times sebesar matan Arab tampak jauh lebih besar dan Abstract luber
$ULANG = if ($FMT.catatan_ulang_tiap_halaman) { 2 } else { 0 }   # nomor catatan kaki: 2 = mulai ulang tiap halaman, 0 = bersambung
$SPASI = [single]$FMT.spasi                              # jarak baris matan dan judul (kali satu baris); catatan kaki dan فهرس tetap satu spasi
$MULAKHAS_JARAK = [bool]$FMT.mulakhas_berjarak   # paragraf di bawah #K الملخص/ملخص البحث: berjarak 6 pt, tanpa awal alinea menjorok
$SPASI_MULAKHAS = [single]$FMT.spasi_mulakhas            # jarak baris bagian #K الملخص… (termasuk الملخص باللغة الأجنبية)
$spasiAktif = $SPASI
# @angka hindi: teks naskah sudah diubah olah.py; nomor yang dihitung di sini (فهرس, المصادر, {P:}) diubah Angka;
# nomor halaman dicetak Word menurut Options.ArabicNumeral (gaya nomor Word «Hindi» = angka India २, bukan ٢)
$HINDI = $M.angka -eq 'hindi'
function Angka($s) {
    $s = [string]$s
    if (-not $HINDI) { return $s }
    return -join ($s.ToCharArray() | ForEach-Object { if ($_ -ge [char]'0' -and $_ -le [char]'9') { [char](0x0660 + [int]$_ - 48) } else { $_ } })
}
# huruf (teks Latin dan Arab sekaligus), ukuran, dan tebal sebuah objek Font Word; yang $null tidak disentuh
function Huruf($font, $nama, $ukuran, $tebal) {
    if ($nama) { $font.Name = [string]$nama; $font.NameBi = [string]$nama }
    if ($null -ne $ukuran) { $font.Size = [single]$ukuran; $font.SizeBi = [single]$ukuran }
    if ($null -ne $tebal) { $font.Bold = [int]$tebal; $font.BoldBi = [int]$tebal }
}
$JUDUL = $M.judul; $NAMA = $M.nama; $NIM = $M.nim
# judul sampul «… - …» sudah dipecah olah.rencana_cetak: bagian sesudah « - » jadi baris kedua yang lebih kecil (kepala halaman tetap judul utuh)
$JUDUL1 = [string]$RENCANA.judul_sampul[0]; $JUDUL2 = [string]$RENCANA.judul_sampul[1]
$MUSYRIF = if ($M.musyrif -and $M.musyrif -ne '-') { [string]$M.musyrif } else { '' }
$JABATAN = if ($MUSYRIF -and $M.jabatan -and $M.jabatan -ne '-') { [string]$M.jabatan } else { '' }
# tahun sampul (qism, jakarta, tengah). Bawaan = tahun hijriah saat tahun ajaran mulai (1 Agustus): satu tahun ajaran
# tetap satu tahun walau 1 Muharram lewat di tengahnya (Juni 2027 = 1449, tahun ajarannya masih 1448)
$awalAjaran = [datetime]::new((Get-Date).Year, 8, 1); if ((Get-Date) -lt $awalAjaran) { $awalAjaran = $awalAjaran.AddYears(-1) }
$TAHUN = if ($M.tahun) { [string]$M.tahun } else { Angka ([Globalization.UmAlQuraCalendar]::new().GetYear($awalAjaran)) }
# @tahun «١٤٤٨ - ٢٠٢٦» (hijriah - masehi) = «١٤٤٨هـ – ٢٠٢٦م»; satu tahun = «١٤٤٨ هـ» seperti model
$TAHUN_CETAK = if ($TAHUN -match '^\s*(\S+?)\s*[-–]\s*(\S+?)\s*$') { "$($Matches[1])هـ – $($Matches[2])م" } else { "$TAHUN هـ" }
$JENIS_BAGIAN = @($RENCANA.bagian | ForEach-Object { $_.jenis })   # المصادر dan فهرس yang dicetak (olah.bagian_akhir)
$adaAy = $JENIS_BAGIAN -contains 'ayat'; $adaHd = $JENIS_BAGIAN -contains 'hadits'; $adaTo = $JENIS_BAGIAN -contains 'maudhuat'
$KITAB = [bool]$RENCANA.kitab            # @bentuk: kitab = tanpa sampul bahts, judul di kepala halaman
$ABJAD = [bool]$RENCANA.abjad            # @nomor: halaman sebelum judul $RENCANA.nomor_satu bernomor huruf, mulai judul itu ١، ٢، ٣
# tata letak yang bisa dicampur (olah.GAYA, @model): tiap bagian memilih bentuknya sendiri
$KEPALA_KOTAK = $M.kepala -eq 'kotak'      # kepala halaman: judul kanan, nomor halaman berbingkai kiri, garis di bawahnya
$JUDUL_KEPALA = if ($M.kepala_judul) { [string]$M.kepala_judul } else { $JUDUL }
$AYAT_SURAH = $M.fihris_ayat -eq 'surah'   # فهرس الآيات: السورة (digabung per surat) | الآية «… الآية n» | الصفحة
$HADITS_RINGKAS = $M.fihris_hadits -eq 'ringkas'   # فهرس الأحاديث: الأحاديث | الصفحة
$TO_TITIK = $M.maudhuat -eq 'titik'        # فهرس الموضوعات bertitik-titik tanpa tabel
$PUSTAKA_MUALLIF = $M.pustaka_gaya -eq 'muallif'   # القرآن الكريم bernomor; **…** tebal, __…__ miring
$KANAN = @($RENCANA.judul_kanan)         # judul #B/#M rata kanan
$TJ = [string]$FMT.huruf_judul           # huruf judul (#K/#F/#B/#M/#S dan judul فهرس)
$JARAK_P = [single]$FMT.jarak_paragraf   # pt sesudah paragraf matan
$JARAK_J = [single]$FMT.jarak_judul      # pt sesudah judul #K/#F (baris keduanya kalau dua baris)
$U_PUSTAKA = [single]$FMT.ukuran_pustaka   # ukuran huruf المصادر
$FIHRIS_SAMBUNG = $M.fihris -eq 'sambung'  # فهرس sesudah yang pertama menyambung di halaman yang sama
$TEPI_KANAN = [single]$FMT.tepi_kanan   # cm
$MERAH = 176; $COKLAT = 2772843           # warna Word (BGR): lafaz matn RGB(176,0,0); rumuz RGB(107,79,42)

# satu rakit dalam satu waktu: rakit kedua berhenti di sini, sebelum mematikan Word milik rakit pertama (kunci lepas sendiri saat proses ini selesai).
# rakit.py menunggu kunci ini lepas sebelum rakit berikutnya (rakit.ps1 yang Python-nya dimatikan masih memegangnya).
try { $pegangKunci = [IO.File]::Open($Kunci, 'OpenOrCreate', 'ReadWrite', 'None') }
catch { throw "Rakit lain sedang jalan (memakai Word yang sama): tunggu sampai selesai, lalu ulangi." }
# Proses /Automation bisa milik aplikasi lain. Hanya Word yang dibuat di sini yang dibersihkan di finally.
# Rakit yang dimatikan paksa (terminal ditutup) tidak sempat ke finally, dan Word-nya tetap hidup: rakit berikutnya
# mematikan Word yang dicatat rakit itu, asal masih proses yang sama (nomor proses bisa dipakai ulang proses lain)
$CATATAN_WORD = "$dir\_tmp\rakit.word"
try { Bersihkan-WordRakit $CATATAN_WORD } catch { Write-Output "PERINGATAN: Word rakit lama belum bisa dihentikan; catatannya disimpan untuk rakit berikutnya: $($_.Exception.Message)" }
$tmp = "$Hasil\word\kerja.docx"
try {
    [IO.Directory]::CreateDirectory((Split-Path -Parent $tmp)) | Out-Null
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false; $word.ScreenUpdating = $false; $word.DisplayAlerts = 0
    # tanpa catatan, Word rakit ini tidak bisa dibereskan kalau rakit dimatikan paksa; rakitnya sendiri tetap jalan
    try { [void](Catat-WordRakit $word $CATATAN_WORD) } catch { Write-Output "PERINGATAN: proses Word rakit ini tidak dikenali: $($_.Exception.Message)" }
    # pengaturan Word pemakai (berlaku untuk semua dokumennya): dipinjam selama rakit, dikembalikan di finally.
    # 2 = angka di teks Arab dicetak ٠-٩, di teks Latin 0-9; 0 = selalu 0-9
    $numeralLama = $word.Options.ArabicNumeral
    $NUMERAL = if ($HINDI) { 2 } else { 0 }; $word.Options.ArabicNumeral = $NUMERAL
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
    function KosongkanKepalaKaki { foreach ($h in 1..3) { try { $doc.Sections(1).Headers($h).Range.Text = '' } catch {} ; try { $doc.Sections(1).Footers($h).Range.Text = '' } catch {} } }
    # judul dikecilkan sampai muat satu baris (mis. utama 36 -> 26, baris kedua 26 -> 22); yang tetap terlalu panjang diratakan:
    # tepi kiri-kanan paragrafnya dilebarkan 6 pt demi 6 pt selama jumlah barisnya tetap, jadi tiap baris kira-kira sama
    # panjang dan baris terakhir tidak tinggal satu kata («… وأوضح / المسالك»)
    function Seimbang($p, $uk, $kecil) {
        while ($uk -gt $kecil -and $p.Range.ComputeStatistics(1) -gt 1) { $uk -= 2; Huruf $p.Range.Font $null $uk }
        $n = $p.Range.ComputeStatistics(1); if ($n -le 1) { return }
        $pf = $p.Range.ParagraphFormat
        for ($tepi = 6; $tepi -le 180; $tepi += 6) {
            $pf.LeftIndent = [single]$tepi; $pf.RightIndent = [single]$tepi
            if ($p.Range.ComputeStatistics(1) -gt $n) { $pf.LeftIndent = [single]($tepi - 6); $pf.RightIndent = [single]($tepi - 6); break }
        }
    }
    # logo جامعة الإمام berwarna = gambar word/media/image2.png sampul_jakarta.docx (bytes PNG), dipakai @logo: berwarna dan
    # @sampul: tengah (.github/uji_struktur.py menjaga gambarnya)
    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
    $LOGO = 'word/media/image2.png'
    function LogoBerwarna {
        $z = [IO.Compression.ZipFile]::OpenRead("$dir\sampul_jakarta.docx")
        try { $s = $z.GetEntry($LOGO).Open(); $ms = New-Object IO.MemoryStream; $s.CopyTo($ms); $s.Dispose(); return , $ms.ToArray() } finally { $z.Dispose() }
    }
    if ($KITAB) { $doc = $word.Documents.Add(); $doc.SaveAs2($tmp, 16); Draft }
    elseif ($RENCANA.sampul -in 'qism', 'jakarta') {
    # @sampul: qism = model قسم الشريعة (logo, judul dalam kurung, العام الجامعي): teks penanda diganti, bentuknya dari templat
    # jakarta = sama, dari sampul_jakarta.docx: «قسم الشريعة بجاكرتا», logo berwarna, baris @sifat, nomor tanpa «الرقم الجامعي:»
    $JAKARTA = $RENCANA.sampul -eq 'jakarta'
    $SAMPUL = if ($JAKARTA) { "$dir\sampul_jakarta.docx" } else { "$dir\sampul_qism.docx" }
    # @logo: berwarna = salinan sampul_qism.docx yang gambar logonya (word/media/image2.png) diganti logo berwarna
    # sampul_jakarta.docx; kop, data, dan tata letak sampul qism tetap (.github/uji_struktur.py menjaga kedua gambarnya)
    if ($RENCANA.logo_berwarna) {
        $warna = LogoBerwarna
        $SAMPUL = Join-Path (Split-Path -Parent $tmp) 'sampul_logo_berwarna.docx'
        Copy-Item -LiteralPath "$dir\sampul_qism.docx" -Destination $SAMPUL -Force
        $z = [IO.Compression.ZipFile]::Open($SAMPUL, 'Update')
        try { $z.GetEntry($LOGO).Delete(); $s = $z.CreateEntry($LOGO).Open(); $s.Write($warna, 0, $warna.Length); $s.Dispose() } finally { $z.Dispose() }
    }
    $doc = $word.Documents.Open($SAMPUL, $false, $true)
    $doc.SaveAs2($tmp, 16)
    Draft
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
        elseif ($t -eq 'السنة الهجرية') { Ganti $p $TAHUN_CETAK }
        # @qism: baris qism model; « // » = pindah baris di paragraf yang sama (bentuk dan hurufnya tetap dari templat); di jakarta barisnya di sel tabel (teksnya berakhir tanda sel char 7)
        elseif ($M.qism -and $t.Trim([char]7, [char]13, ' ') -in 'قسم الشريعة', 'قسم الشريعة بجاكرتا') { Ganti $p (([string]$M.qism -split '\s*//\s*') -join [char]11) }
    }
    if ($JAKARTA) {
        $SM = if (@($word.FontNames) -contains 'Sakkal Majalla') { 'Sakkal Majalla' } else { $TA }
        foreach ($p in @($doc.Paragraphs)) {
            $t = $p.Range.Text.Trim(); $f = $p.Range.Font
            $u = switch ($t) {
                'المشرف' { 18, 1, $SM } { $_ -eq $MUSYRIF -and $MUSYRIF } { 18, 1, $SM } { $_ -eq $JABATAN -and $JABATAN } { 18, 0, $SM }
                { $_ -in 'إعداد الطالب:', 'إعداد الطالبة:' } { 16, 1, $SM } $NAMA { 16, 1, $SM }
                { $M.sifat -and $_ -eq [string]$M.sifat } { 16, 0, $SM } { $NIM -and $_ -eq (Angka $NIM) } { 18, 0, $TA }
                'العام الجامعي' { 18, 0, $TA } $TAHUN_CETAK { 18, 0, $TA } 'قسم الشريعة بجاكرتا' { 16, 0, $TA }
            }
            if ($u) { Huruf $f ($u[2]) ($u[0]) ($u[1]); $p.LineSpacingRule = 0 }
        }
    }
    foreach ($p in $buang) { [void]$p.Range.Delete() }
    # huruf judul model (dari templat: PT Bold Heading) belum terpasang = Word diam-diam memakai huruf lain: pakai huruf profil tebal
    $hJudul = $pJudul.Range.Font.NameBi
    if (@($word.FontNames) -notcontains $hJudul) {
        Write-Output "PERINGATAN: huruf $hJudul (judul sampul qism) belum terpasang di Windows: judul dicetak $TA tebal. Pasang hurufnya, lalu rakit lagi."
        Huruf $pJudul.Range.Font $TA $null 1
    }
    Seimbang $pJudul $(if ($JAKARTA) { 22 } else { 24 }) 18   # judul 24 seperti model (jakarta 22), dikecilkan sampai 18 supaya muat satu baris
    if ($JUDUL2) { Seimbang $pSub 18 16 }
    else { Huruf $pSub.Range.Font $null 2; $pSub.SpaceBefore = 0 }   # tanpa sub-judul: tanpa celah
    # judul sangat panjang: sampul tetap satu halaman, judul dan sub-judul dikecilkan sampai 14.
    # Jumlah halaman dihitung di Print Layout, dengan satu paragraf sementara untuk baris pemisah bagian sesudah sampul
    $doc.ActiveWindow.View.Type = 3
    $doc.Content.InsertParagraphAfter()
    $uk = $pJudul.Range.Font.SizeBi; $kecil = $false
    while ($uk -gt 14 -and $doc.ComputeStatistics(2) -gt 1) {
        $uk--; $kecil = $true
        foreach ($q in @($pJudul, $pSub)) {
            if ($q.Range.Font.SizeBi -gt $uk) { Huruf $q.Range.Font $null $uk }
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
    elseif ($RENCANA.sampul -eq 'tengah') {
    # @sampul: tengah = model خطة dosen المعهد, disusun di sini tanpa templat: logo berwarna di tengah atas dengan rasio
    # gambarnya sendiri, lalu baris-baris olah._sampul_tengah rata tengah, Traditional Arabic tebal 18, jarak antarbaris
    # 6 pt; celah satu baris sesudah lembaga. Ukuran dan jarak diukur dari contoh PDF المعهد (A4)
    $doc = $word.Documents.Add(); $doc.SaveAs2($tmp, 16); Draft
    KosongkanKepalaKaki
    $p1 = $doc.Sections(1).PageSetup; $p1.PaperSize = 7
    $p1.TopMargin = $word.CentimetersToPoints(2.5); $p1.BottomMargin = $word.CentimetersToPoints(2.5)
    $p1.LeftMargin = $word.CentimetersToPoints(2.5); $p1.RightMargin = $word.CentimetersToPoints(2.5)
    $TG = $RENCANA.tengah
    $png = Join-Path (Split-Path -Parent $tmp) 'logo_berwarna.png'
    [IO.File]::WriteAllBytes($png, (LogoBerwarna))
    $selT = $word.Selection
    function BarisTengah($sebelum) {
        $pf = $selT.ParagraphFormat
        $pf.Reset(); $pf.ReadingOrder = 0; $pf.Alignment = 1; $pf.LineSpacingRule = 0
        $pf.SpaceBefore = [single]$sebelum; $pf.SpaceAfter = 0; $pf.LeftIndent = 0; $pf.RightIndent = 0; $pf.FirstLineIndent = 0
    }
    BarisTengah 6                                        # logo 6 pt di bawah tepi atas 2,5 cm, seperti contoh
    $logo = $selT.InlineShapes.AddPicture($png, $false, $true)
    $logo.LockAspectRatio = -1
    $logo.Width = [single]($logo.Width * 162 / $logo.Height)   # tinggi 162 pt (±5,7 cm) seperti contoh; lebar ikut rasio gambar
    [void]$selT.EndKey(6)
    # tiap baris: teks, jarak di atasnya (pt), jenis. Jarak baris ke baris di contoh 33,6 pt = tinggi baris TA 18 + 6 pt;
    # celah = satu baris kosong lagi: di atas lembaga (di bawah logo) dan di atas baris sesudahnya (qism, atau judul
    # kalau «@qism: -»); dua baris itu yang dipendekkan dulu kalau sampul meluap
    $SATU = 33.6
    $isi = @(, @($TG.lembaga, 39, ''))
    foreach ($q in $TG.qism) { $isi += , @($q, 6, '') }
    foreach ($j in $TG.judul) { $isi += , @($j, 6, 'judul') }
    $isi += , @($TG.nama, 6, '')
    if ($TG.musyrif) { $isi += , @($TG.musyrif, 6, '') }
    $isi += , @($TAHUN_CETAK, 6, '')
    $isi[1][1] = 6 + $SATU
    # paragraf dicatat lewat nomornya: $doc.Paragraphs.Last menunjuk paragraf terakhir saat dibaca, bukan saat dicatat
    $nJudul = @(); $nCelah = @()
    for ($k = 0; $k -lt $isi.Count; $k++) {
        $b = $isi[$k]
        $selT.TypeParagraph(); BarisTengah $b[1]
        Huruf $selT.Font $TA 18 1
        $selT.TypeText([string]$b[0])
        $n = $doc.Paragraphs.Count
        if ($b[2] -eq 'judul') { $nJudul += $n }
        if ($k -le 1) { $nCelah += $n }
    }
    # Paragraph Word lewat pipa PowerShell diurai seperti koleksi (macet): ambil satu-satu dengan Item
    $pJudulT = @(); foreach ($n in $nJudul) { $pJudulT += $doc.Paragraphs.Item($n) }
    $celah = @(); foreach ($n in $nCelah) { $celah += $doc.Paragraphs.Item($n) }
    foreach ($p in $pJudulT) { Seimbang $p 18 16 }        # judul yang tidak muat satu baris: dikecilkan sampai 16, lalu diratakan
    # sampul tetap satu halaman: judul dikecilkan sampai 14, lalu celah lembaga/qism dipendekkan
    $doc.ActiveWindow.View.Type = 3
    $doc.Content.InsertParagraphAfter()
    $uk = 18; $kecil = $false
    while ($uk -gt 14 -and $doc.ComputeStatistics(2) -gt 1) { $uk--; $kecil = $true; foreach ($p in $pJudulT) { if ($p.Range.Font.SizeBi -gt $uk) { Huruf $p.Range.Font $null $uk } } }
    if ($kecil) { foreach ($p in $pJudulT) { $p.LeftIndent = 0; $p.RightIndent = 0; $u = $p.Range.Font.SizeBi; Seimbang $p $u $u } }   # baris berubah: ratakan lagi
    foreach ($p in $celah) { if ($doc.ComputeStatistics(2) -gt 1) { $p.SpaceBefore = 6 } }
    if ($doc.ComputeStatistics(2) -gt 1) {
        Write-Output "PERINGATAN: judul terlalu panjang untuk sampul tengah: sampulnya jadi dua halaman. Pendekkan @judul."
    }
    [void]$doc.Paragraphs.Last.Range.Delete()
    Draft
    }
    elseif ($RENCANA.sampul -eq 'templat') {
    # @templat: Word mahasiswa sendiri; halaman pertamanya jadi sampul apa adanya, kepala halamannya dipakai di bagian isi
    $doc = $word.Documents.Add(); $doc.SaveAs2($tmp, 16); Draft
    $TPL = $word.Documents.Open($M.templat, $false, $true)
    # sampul = sampai pemisah halaman atau pemisah bagian pertama, bukan sampai halaman 2 tata letak: sampul yang sudah
    # diisi bisa meluap (judul dua baris), dan potongan di halaman 2 diam-diam membuang baris akhirnya («العام الجامعي»)
    $akhir = $TPL.Content.End - 1; $pisah = $false
    $cari = $TPL.Content; $f = $cari.Find; $f.ClearFormatting()
    if ($f.Execute('^m')) { $akhir = $cari.Start; $pisah = $true }
    if ($TPL.Sections.Count -gt 1) { $akhir = [Math]::Min($akhir, $TPL.Sections(2).Range.Start - 1); $pisah = $true }
    if (-not $pisah -and $TPL.ComputeStatistics(2) -gt 1) {
        $akhir = $TPL.GoTo(1, 1, 2).Start - 1
        Write-Output "PERINGATAN: Word @templat lebih dari satu halaman tanpa pemisah halaman sesudah sampulnya: sampul dipotong di akhir halaman pertama dan teks sesudahnya tidak dicetak. Buka Word itu: sampul yang meluap → pendekkan isinya; sesudah sampul → sisipkan pemisah halaman (Ctrl+Enter)."
    }
    $doc.Content.FormattedText = $TPL.Range(0, $akhir).FormattedText
    $doc.Activate()                                      # Selection di bawah milik dokumen aktif; Open membuat templat aktif
    $pt = $TPL.Sections(1).PageSetup; $p1 = $doc.Sections(1).PageSetup
    $p1.SectionDirection = $pt.SectionDirection         # arah bagian dulu: di bagian kanan-ke-kiri tepi kiri dan kanan bertukar
    # kertas sampul = kertas isi (A4, sama dengan bagian isi di bawah), walau Word mahasiswa memakai kertas lain (mis. Letter):
    # bidang teks templat dipertahankan: tepi atas tetap seperti templat (kop tidak turun), selisih tinggi kertas masuk ke
    # tepi bawah, selisih lebar dibagi rata ke kiri dan kanan, jadi letak isi sampul sama dengan Word mahasiswa
    $p1.PaperSize = 7
    $dW = ($p1.PageWidth - $pt.PageWidth) / 2; $tepiMin = $word.CentimetersToPoints(1)
    $p1.TopMargin = $pt.TopMargin; $p1.BottomMargin = [Math]::Max($tepiMin, $pt.BottomMargin + $p1.PageHeight - $pt.PageHeight)
    $p1.LeftMargin = [Math]::Max($tepiMin, $pt.LeftMargin + $dW); $p1.RightMargin = [Math]::Max($tepiMin, $pt.RightMargin + $dW)
    KosongkanKepalaKaki
    # gaya sesudah tata halaman: mengganti arah bagian menyetel ulang huruf paragrafnya
    SalinGaya $TPL.Range(0, $akhir) $doc.Content
    # kotak teks sampul (mis. kop) ikut disalin gayanya, berpasangan menurut urutan
    $ka = @($TPL.Shapes | Where-Object { $_.TextFrame.HasText }); $kt = @($doc.Shapes | Where-Object { $_.TextFrame.HasText })
    for ($i = 0; $i -lt [Math]::Min($ka.Count, $kt.Count); $i++) { SalinGaya $ka[$i].TextFrame.TextRange $kt[$i].TextFrame.TextRange }
    # gambar/kotak yang diletakkan mendatar menurut tepi kertas (bukan kolom, tepi, atau paragraf) digeser sebesar selisih
    # tepinya (tepi atas tidak berubah, jadi letak tegaknya tetap); nilai di bawah -999000 = rata kiri/tengah/kanan Word, tidak digeser
    foreach ($s in $doc.Shapes) {
        if ($s.RelativeHorizontalPosition -eq 1 -and $s.Left -gt -999000) { $s.Left = $s.Left + $dW }
    }
    # di kertas A4 dengan tepi di atas sampul bisa lebih dari satu halaman; dihitung di Print Layout, dengan satu paragraf
    # sementara untuk baris pemisah bagian sesudah sampul (seperti sampul qism)
    $doc.ActiveWindow.View.Type = 3
    $doc.Content.InsertParagraphAfter()
    $nSampul = $doc.ComputeStatistics(2)
    [void]$doc.Paragraphs.Last.Range.Delete()
    Draft
    if ($nSampul -gt 1) {
        Write-Output "PERINGATAN: sampul dari @templat jadi $nSampul halaman di kertas A4: baris akhirnya pindah ke halaman berikutnya. Pendekkan isi sampul di Word @templat (judul, nama kampus) atau kecilkan hurufnya sampai muat satu halaman, lalu rakit lagi."
    }
    } elseif ($RENCANA.sampul -eq 'mahad') {
    $doc = $word.Documents.Open("$dir\sampul.doc", $false, $true)
    $doc.SaveAs2($tmp, 16)
    $doc.Convert()
    Draft
    KosongkanKepalaKaki
    foreach ($s in $doc.Shapes) {
        if ($s.Type -eq 17) {
            $tr = $s.TextFrame.TextRange
            $f = $tr.Find; $f.ClearFormatting(); $f.Replacement.ClearFormatting()
            [void]$f.Execute('الملكة العربية', $true, $false, $false, $false, $false, $true, 0, $false, 'المملكة العربية', 2)
            Huruf $tr.Font $TA 15 1
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
            $u = if ($t -eq $JUDUL1) { 36 } elseif ($JUDUL2 -and $t -eq $JUDUL2) { 26 } else { [Math]::Max($sz, 20) }
            Huruf $r.Font $TA $u 1
        }
    }
    Seimbang $pJudul 36 26
    if ($JUDUL2) { Seimbang $pJudul.Next(1) 26 22 }
    # buang paragraf kosong di ekor sampul supaya sampul tetap 1 halaman
    while ($doc.Paragraphs.Count -gt 3 -and $doc.Paragraphs.Last.Range.Text.Trim().Length -eq 0 -and $doc.Paragraphs.Last.Previous(1).Range.Text.Trim().Length -eq 0) {
        $doc.Paragraphs.Last.Previous(1).Range.Delete() | Out-Null
    }
    }
    else { throw "Model sampul «$($RENCANA.sampul)» tidak dikenal perakit." }

    # ---------- 2. Bagian isi ----------
    $sel = $word.Selection
    [void]$sel.EndKey(6)
    if ($RENCANA.basmalah) {                             # halaman ﷽ sesudah sampul, masih di bagian sampul (tanpa nomor)
        $hB = 'Arabic Typesetting'                       # ﷽ huruf ini = satu kaligrafi utuh; Traditional Arabic hanya mencetak «بسم»
        if (@($word.FontNames) -notcontains $hB) { Write-Output "PERINGATAN: huruf $hB belum terpasang di Windows: halaman basmalah dicetak $TA."; $hB = $TA }
        $sel.InsertBreak(7)
        $sel.ClearFormatting()
        # Word membuang jarak atas paragraf sesudah pindah halaman: turun ke tengah lewat satu paragraf kosong bertinggi pas
        $psS = $doc.Sections(1).PageSetup                # ukuran 72: lebar ﷽ ±14 cm; -40 = ﷽ tepat di tengah bidang sampul qism (diukur di PDF)
        $sel.ParagraphFormat.SpaceBefore = 0; $sel.ParagraphFormat.SpaceAfter = 0
        $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = [single][Math]::Max(1, ($psS.PageHeight - $psS.TopMargin - $psS.BottomMargin) / 2 - 40)
        $sel.TypeParagraph()
        $sel.ParagraphFormat.Alignment = 1; $sel.ParagraphFormat.LineSpacingRule = 0
        Huruf $sel.Font $hB 72 0
        $sel.TypeText([string][char]0xFDFD)
    }
    if ($RENCANA.ayat_pembuka) {                         # @ayat_pembuka: satu halaman ayat sesudah sampul (dan basmalah), tanpa nomor
        $sel.InsertBreak(7)
        $sel.ClearFormatting()
        $psS = $doc.Sections(1).PageSetup                # turun ke sepertiga bidang teks lewat satu paragraf kosong bertinggi pas (lihat basmalah)
        $sel.ParagraphFormat.SpaceBefore = 0; $sel.ParagraphFormat.SpaceAfter = 0
        $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = [single][Math]::Max(1, ($psS.PageHeight - $psS.TopMargin - $psS.BottomMargin) / 3)
        $sel.TypeParagraph()
        $sel.ParagraphFormat.Alignment = 1; $sel.ParagraphFormat.LineSpacingRule = 0; $sel.ParagraphFormat.ReadingOrder = 0
        $sel.ParagraphFormat.LeftIndent = 0; $sel.ParagraphFormat.RightIndent = 0; $sel.ParagraphFormat.FirstLineIndent = 0
        Huruf $sel.Font $TA 28 0; $sel.TypeText('﴿')
        Huruf $sel.Font $QF 28 0; $sel.TypeText([string]$RENCANA.ayat_pembuka.t)
        Huruf $sel.Font $TA 28 0; $sel.TypeText('﴾')
        $sel.TypeParagraph()
        $sel.ParagraphFormat.SpaceBefore = 12
        Huruf $sel.Font $TA $uMatan 0; $sel.TypeText((Angka $RENCANA.ayat_pembuka.rujukan))
    }
    if (-not $KITAB) { $sel.InsertBreak(2) }             # section break (halaman baru) sesudah sampul
    # potongan `rakit --fasl` selain yang pertama: sampul (bagian Word pertama, berikut pemisahnya) dibuang; tata halaman isi
    # disetel sesudah ini, jadi isinya sama dengan potongan bersampul
    if ($RENCANA.buang_sampul) { [void]$doc.Sections(1).Range.Delete(); [void]$sel.EndKey(6) }
    $sec = $doc.Sections($doc.Sections.Count)
    $ps = $sec.PageSetup
    $ps.PaperSize = 7
    $ps.TopMargin = $word.CentimetersToPoints(2.5); $ps.BottomMargin = $word.CentimetersToPoints(2.5)
    $ps.LeftMargin = $word.CentimetersToPoints(2.5); $ps.RightMargin = $word.CentimetersToPoints($TEPI_KANAN)
    $ps.HeaderDistance = $word.CentimetersToPoints([single]$FMT.jarak_kepala); $ps.FooterDistance = $word.CentimetersToPoints(1.25)
    # pedoman: nomor halaman di tengah bawah, huruf dan ukuran sama dengan matan, dihitung mulai dari المقدمة
    function KakiNomor($kaki) {
        $kaki.Range.Text = ''
        [void]$kaki.Range.Fields.Add($kaki.Range, 33)
        $kaki.Range.ParagraphFormat.Alignment = 1
        Huruf $kaki.Range.Font $TA $uMatan
    }
    $ft = $sec.Footers(1); $ft.LinkToPrevious = $false; $sec.Headers(1).LinkToPrevious = $false
    KakiNomor $ft
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
        # penanda judul «عنوان البحث» (kepala_kotak.docx, atau Word @templat yang belum diisi, mis. «قالب إثراء المتون
        # للباحثين») = judul (pendek) bahts ini, di teks kepala halaman dan di kotak teksnya; kurung penandanya ikut diganti
        $tempat = { @($hd.Range) + @(try { @($hd.Range.ShapeRange) | Where-Object { $_.TextFrame.HasText } | ForEach-Object { $_.TextFrame.TextRange } } catch { }) }
        foreach ($penanda in '(عنوان البحث)', 'عنوان البحث') {
            foreach ($r in & $tempat) {
                $f = $r.Find; $f.ClearFormatting(); $f.Replacement.ClearFormatting()
                [void]$f.Execute($penanda, $true, $false, $false, $false, $false, $true, 0, $false, $JUDUL_KEPALA, 2)
            }
        }
        if ((@(& $tempat | ForEach-Object { $_.Text }) -join ' ') -match 'عنوان البحث' -and $JUDUL_KEPALA -notmatch 'عنوان البحث') {
            Write-Output "PERINGATAN: kepala halaman dari @templat masih mencetak «عنوان البحث» di halaman isi: tulis judul bahts di kepala halaman Word @templat, lalu rakit lagi."
        }
        $TPL.Close(0); $TPL = $null; $doc.Activate(); $script:kepalaTpl = $hd
    }
    # kepala halaman berjalan gaya cetakan kitab, bergaris bawah: halaman genap = judul kitab, halaman ganjil = judul bab
    # (#K / فهرس; tiap judul itu mulai bagian Word baru, lihat Judul). Nomor halaman bersambung di kaki semua halaman
    function KepalaHalaman($h, $teks) {
        $r = $h.Range; $r.Text = $teks
        Huruf $r.Font $TA $uCatatan 1
        $r.ParagraphFormat.ReadingOrder = 0; $r.ParagraphFormat.Alignment = 1
        $b = $r.Paragraphs(1).Borders.Item(-3); $b.LineStyle = 1; $b.LineWidth = 12
    }
    if ($KITAB) {
        $doc.PageSetup.OddAndEvenPagesHeaderFooter = -1
        KepalaHalaman $sec.Headers(1) $JUDUL; KepalaHalaman $sec.Headers(3) $JUDUL
        $fg = $sec.Footers(3); KakiNomor $fg
    }

    $st = $doc.Styles.Item(-30)                          # Footnote Text
    Huruf $st.Font $TA $uCatatan
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
    # huruf Latin di teks Arab (pola olah.LATIN di bahan): Times New Roman, ukurannya sebanding $FMT.latin terhadap matan.
    # Glyph Latin Traditional Arabic lebar dan, di ukuran yang sama, tampak jauh lebih besar daripada huruf Arabnya.
    # Huruf mengisi Name/Size dan NameBi/SizeBi sekaligus: di run kanan-ke-kiri (catatan kaki) huruf Latin memakai yang Bi
    $rasioLatin = $uLatin / $uMatan
    function Latin($rg, $awal, $teks, $ukuran) {
        if (-not $teks -or $teks -notmatch $DATA.latin) { return }
        $u = [Math]::Ceiling($ukuran * $rasioLatin)       # matan 18 -> 12, catatan kaki 14 -> 10, sel tabel 16 -> 11
        foreach ($a in [regex]::Matches($teks, $DATA.latin)) {
            $l = $rg.Duplicate; $l.SetRange($awal + $a.Index, $awal + $a.Index + $a.Length); Huruf $l.Font 'Times New Roman' $u $null
        }
    }
    function Tulis($t, $font, $size, $bold, $sup, $warna = -16777216) {
        if (-not $t) { return }
        $awal = $sel.Start
        $sel.InsertAfter($t)
        $f = $sel.Font
        Huruf $f $font $size $bold
        $f.Italic = 0; $f.ItalicBi = 0; $f.Superscript = [int]$sup; $f.Color = [int]$warna
        if ($font -eq $TA -or $font -eq $TJ) { Latin $sel.Range $awal $t $size }
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
    # Nomor sementara pendek: panjang kunci {P:} bukan isi cetak dan tidak boleh mengubah susunan halaman.
    $PENANDA_HALAMAN = '00'
    $rujukanHalaman = @{}; $script:nRujukanHalaman = 0
    # $pg = isi tempat {P:}: '00' untuk teks yang dimasukkan; '__' (bukan angka, sama panjang) untuk mencari angka di teks
    # catatan kaki, supaya nomor halaman sementara tidak ikut dijadikan run kiri-ke-kanan @angka_ayat: latin
    function TeksRuns($runs, $pg = $PENANDA_HALAMAN) { $s = ''; foreach ($r in $runs) { if ($null -ne $r.t) { $s += $r.t } elseif ($r.pg) { $s += $pg } elseif ($r.omml) { $s += 'E' } }; return $s }
    # Paket Flat OPC untuk menyisipkan fragmen OMML (<m:oMath> atau <m:oMathPara>) lewat Range.InsertXML
    function PaketOmml($omml) {
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><pkg:package xmlns:pkg="http://schemas.microsoft.com/office/2006/xmlPackage"><pkg:part pkg:name="/_rels/.rels" pkg:contentType="application/vnd.openxmlformats-package.relationships+xml"><pkg:xmlData><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships></pkg:xmlData></pkg:part><pkg:part pkg:name="/word/document.xml" pkg:contentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"><pkg:xmlData><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><w:body><w:p>' + $omml + '</w:p></w:body></w:document></pkg:xmlData></pkg:part></pkg:package>'
    }
    # Sisipkan OMML di posisi $sel. Penjaga U+200F (RLM) di belakang memastikan kursor keluar dari zona matematika
    # (sehingga teks/tabel sesudahnya tidak masuk ke dalam rumus) sekaligus memulihkan arah kanan-ke-kiri teks Arab.
    function TulisOmml($omml, [bool]$jaga = $true) {
        $pkg = PaketOmml $omml
        if ($jaga) {
            $pos = $sel.Start
            $sel.InsertAfter('X' + [string][char]0x200F)
            $sel.Collapse(0)
            $r = $doc.Range($pos, $pos + 1)
            $r.InsertXML($pkg)
            $akhir = $r.Paragraphs(1).Range.End - 1
            $doc.Range($akhir, $akhir).Select()
        } else {
            $r = $sel.Range.Duplicate
            $r.InsertXML($pkg)
        }
    }
    # Word membalik huruf Arab di dalam <m:f> (dan membalik urutan baris rumus kanan-ke-kiri) bila persamaan
    # baris sendiri (#E) turun ke baris kedua. Perkecil huruf rumus bertahap sampai muat satu baris.
    function MuatRumus($pRange, [string]$omml, [string]$tag = '') {
        if (-not $pRange -or $pRange.OMaths.Count -eq 0 -or $omml -match '<m:(?:eqArr|m)>') { return }
        $omR = $pRange.OMaths(1).Range
        if ($omR.End -le $omR.Start) { return }
        $ujung = $omR.End - 1
        $turun = {
            $a = $doc.Range($omR.Start, $omR.Start); $b = $doc.Range($ujung, $ujung)
            ($a.Information(10) -ne $b.Information(10)) -or ($a.Information(3) -ne $b.Information(3))
        }
        if (-not (& $turun)) { return }
        $ukuran = [int[]](($uMatan - 2)..11 | Where-Object { ($_ -eq 11) -or (([int]$uMatan - $_) % 2 -eq 0) })
        foreach ($sz in $ukuran) {
            $omR.Font.SizeBi = $sz
            $omR.Font.Size = [Math]::Max(9, $sz - 2)
            if (-not (& $turun)) { return }
        }
        if ($omml -match '<w:rtl/>') {
            $ket = if ($tag) { " $tag" } else { '' }
            Write-Output "PERINGATAN: persamaan Arab$ket tetap melebihi satu baris walau diperkecil: ringkas atau pecah rumus supaya hurufnya tidak terbalik di Word."
        }
    }
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
        Huruf $fr.Font $TA $uCatatan 0; $fr.Font.Superscript = 0
        $fp = $fr.Paragraphs(1); $fp.ReadingOrder = 0; $fp.Alignment = 3
        $fr.Select(); $word.Selection.RtlRun()
        if ($c.al) {   # @angka_ayat: latin: angka di run kiri-ke-kanan dicetak Word 0-9 walau angka konteks
            foreach ($a in [regex]::Matches((TeksRuns $c.runs '__'), '[0-9]+(?:[-–][0-9]+)*')) {
                $l = $fn.Range; $l.SetRange($fr.Start + 1 + $a.Index, $fr.Start + 1 + $a.Index + $a.Length); $l.Select(); $word.Selection.LtrRun()
            }
        }
        Tautan $fn.Range ($fr.Start + 1) (TeksRuns $c.runs)
        Latin $fn.Range ($fr.Start + 1) (TeksRuns $c.runs) $uCatatan
        $fr.ParagraphFormat.SpaceBefore = 0; $fr.ParagraphFormat.SpaceAfter = 0; $fr.ParagraphFormat.LineSpacingRule = 0
        $off = 1
        $fnOmml = New-Object System.Collections.ArrayList
        foreach ($r in $c.runs) {
            $len = 0
            if ($null -ne $r.t) { $len = $r.t.Length } elseif ($r.pg) { $len = $PENANDA_HALAMAN.Length } elseif ($r.omml) { $len = 1; [void]$fnOmml.Add(@{ pos = ($fr.Start + $off); omml = $r.omml }) }
            if ($r.q) { $q = $fn.Range; $q.SetRange($fr.Start + $off, $fr.Start + $off + $len); Huruf $q.Font $QF }
            if ($r.pg) {
                $q = $fn.Range.Duplicate; $q.SetRange($fr.Start + $off, $fr.Start + $off + $len)
                $script:nRujukanHalaman++; $nama = "pgn_$script:nRujukanHalaman"
                [void]$doc.Bookmarks.Add($nama, $q); $rujukanHalaman[$nama] = $r.pg
            }
            $off += $len
        }
        if ($fnOmml.Count) {
            $fnOmml.Reverse()
            foreach ($o in $fnOmml) {
                $q = $fn.Range.Duplicate; $q.SetRange($o.pos, $o.pos + 1)
                $q.InsertXML((PaketOmml $o.omml))
            }
        }
        # nomor di catatan kaki: (1) ukuran normal, bukan superskrip
        $pr = $fr.Paragraphs(1).Range
        $m = $fn.Range; $m.SetRange($pr.Start, $pr.Start + $nomor.Length)
        $m.Font.Superscript = 0; Huruf $m.Font $TA $uCatatan
        $m.InsertBefore('('); $m.InsertAfter(')')
        $m.Font.Superscript = 0
        # nomor di matan: (1) superskrip; kurungnya ditulis Catatan.
        # Di tampilan Draft, $fr.Select() membuka panel catatan kaki (Panes(2)); memindah seleksi balik ke sel tabel #J
        # saat panel itu masih terbuka menjatuhkan WINWORD.EXE (0x800706BE), jadi panel ditutup dulu.
        if ($doc.ActiveWindow.Panes.Count -gt 1) { $doc.ActiveWindow.Panes(2).Close() }
        $ref = $fn.Reference
        $ref.Font.Superscript = 1; Huruf $ref.Font $TA $uMatan
        $ref.Select(); $word.Selection.RtlRun()
        return $fn
    }
    # nomor tercetak: mulai 1 lagi tiap halaman (ULANG 2) atau bersambung. Catatan kaki yang nomornya salah dibuat ulang
    # di tempat yang sama (tanda buatan sendiri tidak bisa diganti); itu bisa menggeser halaman, jadi diulang sampai tetap.
    # Catatan kaki di batas halaman bisa bolak-balik tanpa ujung: nomor awal halaman (١) lebih sempit daripada nomor
    # sambungan halaman sebelumnya (١٢), barisnya naik ke halaman itu, nomornya salah lagi (bahts 143 catatan kaki: 3 rakit
    # gagal). Catatan kaki yang salah lagi pada putaran berikutnya: jarak huruf paragraf matannya digeser sedikit (seperti
    # BarisPendek), supaya batas halamannya pindah dari tempat itu.
    function SalahNomor {
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
        return , $salah
    }
    function NomorCatatan {
        $geser = @{}; $salahLalu = @{}                   # nomor urut Word -> langkah jarak huruf yang sudah dipakai
        for ($putaran = 1; $putaran -le 12; $putaran++) {
            $salah = SalahNomor
            if (-not $salah.Count) { return }
            [array]::Reverse($salah)
            foreach ($s in $salah) {
                # objek catatan kaki Word menunjuk nomor urut: hapus dulu, baru buat di tempatnya
                $lama = $doc.Footnotes.Item($s[0]); $pos = $lama.Reference.Start; $lama.Delete()
                [void](BuatCatatan $doc.Range($pos, $pos) $asalCatatan[$s[0] - 1] $s[1])
            }
            $kini = @{}
            foreach ($s in $salah) {
                $i = $s[0]; $kini[$i] = 1
                if (-not $salahLalu.ContainsKey($i)) { continue }
                $k = [int]$geser[$i]; if ($k -ge $GESER_CATATAN.Count) { continue }
                $geser[$i] = $k + 1
                $doc.Footnotes.Item($i).Reference.Paragraphs(1).Range.Font.Spacing = $GESER_CATATAN[$k]
            }
            $salahLalu = $kini
        }
        throw "Nomor catatan kaki belum tetap sesudah 12 putaran penyusunan halaman."
    }
    $GESER_CATATAN = -0.1, -0.2, -0.3, 0.1, 0.2       # pt; sama kecilnya dengan perapatan BarisPendek
    # baris terakhir paragraf yang cuma 1-2 kata ("runt"): jarak huruf paragraf itu dirapatkan 0,1 s.d. 0,3 pt sampai kata
    # itu naik ke baris sebelumnya; tidak berhasil sampai 0,3 = dibiarkan. Hanya paragraf rata kanan-kiri di luar tabel,
    # bukan sub-judul #S (tebal seluruhnya). Baris dihitung di Print Layout: di Draft barisnya bukan baris halaman cetak.
    # Sesudah NomorCatatan (nomor final menentukan lebar baris), lalu NomorCatatan lagi (halaman bisa bergeser).
    # Qulub 27 halaman: runt 22 -> 8, rakit +±30 detik; bentuk kitab 162 halaman: 140 -> 50, +±2 menit
    function BarisPendek {
        $doc.ActiveWindow.View.Type = 3; $doc.Repaginate()
        # runt = kata ketiga dari belakang (huruf saja, bukan angka catatan kaki/tanda baca) ada di baris lain daripada akhir paragraf
        # «baris lain» dibaca dari jumlah baris: awal paragraf s.d. kata itu lebih sedikit barisnya daripada seluruh paragraf.
        # Jangan Information(10)/(3) per kata: ±75 ms per panggilan, empat per paragraf (BarisPendek dua kali lebih
        # lama). Rentangnya harus mulai di awal paragraf: jumlah baris rentang yang
        # mulai di tengah paragraf tidak bisa dipakai (selalu 1)
        function Runt($r) {
            $ws = $r.Words; $i = $ws.Count; $n = 0
            while ($i -ge 1) {
                $wd = $ws.Item($i); $i--
                if ($wd.Text -notmatch '\p{L}') { continue }
                $n++; if ($n -eq 3) { return ($doc.Range($r.Start, $wd.End).ComputeStatistics(1) -lt $r.ComputeStatistics(1)) }
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
            elseif ($r.omml) { TulisOmml $r.omml $true }
            elseif ($r.q) { $u = $size; if ($size -eq $uMatan) { $u = $uAyat }; $w = -16777216; if ($r.w) { $w = $r.w }; Tulis $r.t $QF $u 0 0 $w }
            elseif ($null -ne $r.t) {
                $tb = 0; if ($r.b -or $r.m -or $paksaTebal) { $tb = 1 }   # lafaz matn di syarah: tebal + merah (cetakan Saudi: tebal dalam kurung)
                $w = -16777216; if ($r.m -or $paksaMerah) { $w = $MERAH } elseif ($r.w) { $w = $r.w }   # w = @warna sumber paragraf
                $awal = $sel.Start; Tulis $r.t $TA $size $tb 0 $w
                if ($r.t -match $DATA.tautan) { $akhir = $sel.Start; Tautan $doc.Content $awal $r.t; $doc.Range($akhir, $akhir).Select() }
            }
        }
    }
    # $kedua = baris kedua judul (@judul_fasl: dua_baris): paragraf sendiri, rata dan ukuran sama, menempel ke baris pertama
    function Judul($teks, $bm, $pb, $k = '', $kedua = '') {
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
        Tulis $teks $TJ $(if ($k -in 'B', 'M') { $uJudulSub } else { $uJudul }) 1 0
        $sel.TypeParagraph()
        if ($kedua) {
            Para $(if ($k -in $KANAN) { 3 } else { 1 }) 6 0
            $sel.ParagraphFormat.KeepWithNext = -1
            Tulis $kedua $TJ $(if ($k -in 'B', 'M') { $uJudulSub } else { $uJudul }) 1 0
            $sel.TypeParagraph()
        }
        if ($k -in 'K', 'F' -and $JARAK_J) { $sel.Paragraphs(1).Previous(1).SpaceAfter = $JARAK_J }
    }

    $toc = New-Object System.Collections.ArrayList
    $nKotak = 0
    $garis = New-Object System.Collections.ArrayList   # paragraf @warna: garis tegak di sisi awal (tetap terlihat di fotokopi hitam putih)
    $diMulakhas = $false; $nT = 0; $iR = -1; $berjarakL = $false; $bmMuqaddimah = $null
    function HalamanBaru($pb) { if ($pb) { $sel.ParagraphFormat.PageBreakBefore = -1; $sel.ParagraphFormat.SpaceBefore = 0 } }
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
        if (-not $nx -or $nx.k -in 'K', 'F', 'B', 'M', 'H', 'R') { return $false }
        return -not ((Pengantar $nx) -and (Pengantar $DATA.blok[$j + 2]))
    }
    # Blok isi ditulis lewat satu scriptblock yang di-dot-source (lingkup yang sama): sekali dari awal sampai #R, dan
    # (@malahiq: akhir) sekali lagi untuk blok sesudah #R, sesudah المصادر والمراجع ditulis
    $mulaiBlok = 0
    $tulisBlok = {
    for ($i = $mulaiBlok; $i -lt $DATA.blok.Count; $i++) {
        $blk = $DATA.blok[$i]
        if ($blk.k -eq 'R') { $iR = $i; break }
        if ($blk.k -eq 'H') { continue }                  # #H: blok sesudahnya mulai halaman baru (sudah masuk $RENCANA.halaman_baru)
        if ($i -eq $RENCANA.maudhuat_awal) {              # @maudhuat_letak: awal — tempat فهرس الموضوعات, diisi sesudah semua judul ditulis (bagian 3)
            Para 1 0 0; $sel.ParagraphFormat.PageBreakBefore = -1
            [void]$doc.Bookmarks.Add('fihris_awal', $sel.Range); $sel.TypeParagraph()
        }
        $pb = $i -in $RENCANA.halaman_baru                # blok ini diawali pindah halaman (olah.awal_halaman)
        if ($blk.k -in 'K', 'F', 'B', 'M') {
            if ($i -eq $RENCANA.nomor_satu) {             # @nomor: #F pertama (mukadimah: المقدمة) = bagian Word baru, nomor kembali ١
                $sel.InsertBreak(2)
                $ftIsi = $doc.Sections($doc.Sections.Count).Footers(1); $ftIsi.LinkToPrevious = $false
                $ftIsi.PageNumbers.NumberStyle = 0; $ftIsi.PageNumbers.RestartNumberingAtSection = $true; $ftIsi.PageNumbers.StartingNumber = 1
                $pb = $false
            }
            $diMulakhas = $MULAKHAS_JARAK -and $blk.k -eq 'K' -and $blk.judul -match '^(ال)?ملخص' -and $blk.judul -notmatch 'الأجنبية|الإنجليزية'
            $spasiAktif = if ($blk.k -eq 'K' -and $blk.judul -match '^(ال)?ملخص') { $SPASI_MULAKHAS } else { $SPASI }
            $nT++; $bm = "t_$nT"
            if ($i -eq $RENCANA.awal_isi) { $bmMuqaddimah = $bm }   # awal halaman isi (HALAMAN_ISI)
            $dua = $RENCANA.judul_dua_baris."$i"             # @judul_fasl: dua_baris (olah.judul_dua_baris); فهرس tetap $blk.judul
            if ($dua) { Judul $dua[0] $bm $pb $blk.k $dua[1] } else { Judul $blk.judul $bm $pb $blk.k }
            $lvl = @{ K = 0; F = 0; B = 1; M = 2 }[$blk.k]
            [void]$toc.Add(@{ t = $blk.judul; bm = $bm; lvl = $lvl })
        }
        elseif ($blk.k -eq 'T') {                         # kotak matn: bingkai merah tipis, teks merah, rata kanan-kiri
            Para 3 6 0
            HalamanBaru $pb
            $awal = $sel.Start
            Runs $blk.runs $uMatan $false $true
            $nKotak++; [void]$doc.Bookmarks.Add("kotak_$nKotak", $doc.Range($awal, $sel.Start))   # bingkainya dipasang sesudah isi selesai
            $sel.TypeParagraph()
        }
        elseif ($blk.k -eq 'J') {                         # tabel: baris #J berturut-turut; baris pertama = kepala
            $baris = @($blk)
            while ($i + 1 -lt $DATA.blok.Count -and $DATA.blok[$i + 1].k -eq 'J') { $i++; $baris += $DATA.blok[$i] }
            Para 1 6 0
            HalamanBaru $pb
            $nk = @($baris[0].sel).Count
            $tbl = $doc.Tables.Add($sel.Range, [int]$baris.Count, [int]$nk)
            $tbl.TableDirection = 0                       # kanan ke kiri: kolom pertama naskah di kanan
            $tbl.Borders.Enable = 1
            $tbl.Rows.Alignment = 1
            $tbl.PreferredWidthType = 2; $tbl.PreferredWidth = 100   # selebar halaman
            $tbl.Rows.AllowBreakAcrossPages = -1
            if ($nk -ge 3) {                              # kolom pertama (nama baris) lebih sempit, sisanya dibagi rata
                $tbl.Columns.PreferredWidthType = 2
                $tbl.Columns(1).PreferredWidth = [single]18
                for ($c = 2; $c -le $nk; $c++) { $tbl.Columns($c).PreferredWidth = [single](82 / ($nk - 1)) }   # 82/3 = 27.33 (double) ditolak Word: «Specified cast is not valid»
            }
            $tbl.Rows(1).HeadingFormat = -1                # kepala diulang di halaman berikutnya
            $tbl.Rows(1).Shading.BackgroundPatternColor = 14277081   # abu-abu muda (RGB 217,217,217)
            $rf = $tbl.Range.ParagraphFormat
            $rf.ReadingOrder = 0; $rf.FirstLineIndent = 0; $rf.LeftIndent = 0; $rf.RightIndent = 0
            $rf.SpaceBefore = 0; $rf.SpaceAfter = 0; $rf.LineSpacingRule = 0; $rf.KeepWithNext = 0; $rf.PageBreakBefore = 0
            $uTabel = [single][Math]::Ceiling(($uMatan + $uCatatan) / 2)   # sel sempit: di antara matan dan catatan kaki (teks_pdf.periksa membaca huruf ini sebagai matan)
            for ($r = 0; $r -lt $baris.Count; $r++) {
                $isi = @($baris[$r].sel)
                for ($c = 0; $c -lt $nk; $c++) {
                    $x = $tbl.Cell($r + 1, $c + 1).Range
                    # isi rata kanan (bukan rata kanan-kiri: jarak kata melebar di sel sempit). Paragrafnya RTL, jadi rata
                    # kanan = awal baris = 0; nilai 2 disimpan jc="right" = ujung akhir = rata KIRI di halaman.
                    $x.ParagraphFormat.Alignment = $(if ($r -eq 0) { 1 } else { 0 })
                    $x.Collapse(1); $x.Select()
                    Runs $isi[$c] $uTabel ($r -eq 0) $false
                }
            }
            $doc.Range($tbl.Range.End, $tbl.Range.End).Select()
            if ($i + 1 -lt $DATA.blok.Count -and $DATA.blok[$i + 1].k -eq 'E' -and $DATA.blok[$i + 1].tag) {
                Para 1 0 0; $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = 2; $sel.TypeParagraph()
            }
        }
        elseif ($blk.k -eq 'G') {                         # gambar: di tengah, paling lebar = lebar teks, paling tinggi 70% halaman
            Para 1 6 0
            HalamanBaru $pb
            $ps = $sec.PageSetup
            $lebarTeks = $ps.PageWidth - $ps.LeftMargin - $ps.RightMargin
            $tinggiMaks = 0.7 * ($ps.PageHeight - $ps.TopMargin - $ps.BottomMargin)
            $shp = $sel.InlineShapes.AddPicture($blk.berkas, $false, $true)
            $shp.LockAspectRatio = -1
            $s = [Math]::Min(1.0, [Math]::Min($lebarTeks / $shp.Width, $tinggiMaks / $shp.Height))
            $shp.Width = [single]($shp.Width * $s)          # tinggi ikut (rasio dikunci)
            $sel.ParagraphFormat.KeepWithNext = -1           # gambar tidak terpisah dari keterangannya
            $sel.TypeParagraph()
            if (@($blk.runs).Count) {
                Para 1 0 0
                Runs $blk.runs $uCatatan $true $false
                $sel.ParagraphFormat.SpaceAfter = 6
                $sel.TypeParagraph()
            }
        }
        elseif ($blk.k -eq 'E') {                         # persamaan matematika baris sendiri (OMML Word asli)
            if ($blk.tag) {                               # dengan \tag{…}: tabel 3 kolom tanpa garis (rumus tengah, nomor di tepi kiri)
                Para 1 6 0
                HalamanBaru $pb
                $tbl = $doc.Tables.Add($sel.Range, 1, 3)
                $tbl.TableDirection = 0; $tbl.Borders.Enable = 0; $tbl.Rows.Alignment = 1
                $tbl.PreferredWidthType = 2; $tbl.PreferredWidth = 100
                $tbl.Columns.PreferredWidthType = 2
                $tbl.Columns(1).PreferredWidth = [single]8; $tbl.Columns(2).PreferredWidth = [single]84; $tbl.Columns(3).PreferredWidth = [single]8
                foreach ($c in 1..3) { $tbl.Cell(1, $c).VerticalAlignment = 1 }
                $rf = $tbl.Range.ParagraphFormat
                $rf.FirstLineIndent = 0; $rf.LeftIndent = 0; $rf.RightIndent = 0
                $rf.SpaceBefore = 2; $rf.SpaceAfter = 2; $rf.LineSpacingRule = 0; $rf.KeepWithNext = 0; $rf.PageBreakBefore = $(if ($pb) { -1 } else { 0 })
                $mid = $tbl.Cell(1, 2).Range; $mid.ParagraphFormat.ReadingOrder = 1; $mid.ParagraphFormat.Alignment = 1
                $mid.Collapse(1); $mid.Select()
                TulisOmml $blk.omml $false
                $num = $tbl.Cell(1, 3).Range
                $num.ParagraphFormat.ReadingOrder = 0; $num.ParagraphFormat.Alignment = 2
                $tTag = [string]$blk.tag
                if (-not ($tTag.StartsWith('(') -and $tTag.EndsWith(')'))) { $tTag = "($tTag)" }
                $num.Text = $tTag
                Huruf $num.Font $TA $uCatatan 0
                MuatRumus $tbl.Cell(1, 2).Range.Paragraphs(1).Range $blk.omml $tTag
                $doc.Range($tbl.Range.End, $tbl.Range.End).Select()
                # pisahkan tabel nomor persamaan dari tabel #J atau #E bertag berikutnya supaya Word tidak menggabungkannya
                if ($i + 1 -lt $DATA.blok.Count -and ($DATA.blok[$i + 1].k -eq 'J' -or ($DATA.blok[$i + 1].k -eq 'E' -and $DATA.blok[$i + 1].tag))) {
                    Para 1 0 0; $sel.ParagraphFormat.LineSpacingRule = 4; $sel.ParagraphFormat.LineSpacing = 2; $sel.TypeParagraph()
                }
            } else {
                Para 1 6 0
                HalamanBaru $pb
                $sel.ParagraphFormat.ReadingOrder = 1
                $sel.ParagraphFormat.SpaceAfter = 6
                $pos = $sel.Start
                $sel.TypeParagraph()
                $r = $doc.Range($pos, $pos)
                $r.InsertXML((PaketOmml $blk.omml))
                MuatRumus $r.Paragraphs(1).Range $blk.omml
                $akhir = $r.Paragraphs(1).Range.End
                $doc.Range($akhir, $akhir).Select()
            }
        }
        elseif ($blk.k -eq 'V') {                         # bait syair: di tengah, tanpa awal alinea
            Para 1 2 0
            HalamanBaru $pb
            Runs $blk.runs $uMatan $false
            $sel.TypeParagraph()
        }
        elseif ($blk.k -eq 'L') {                         # paragraf Latin: kiri ke kanan, rata kanan-kiri
            $judulL = [bool]$blk.tengah                    # «#L **Abstract**»: judul tebal di tengah, paragraf #L sesudahnya berjarak
            $jarakL = if ($judulL) { 6 } elseif ($i -gt 0 -and $DATA.blok[$i - 1].k -eq 'L' -and $script:berjarakL) { 6 } else { 0 }
            $script:berjarakL = $judulL -or ($jarakL -gt 0)
            Para 3 $jarakL 0
            HalamanBaru $pb
            $sel.ParagraphFormat.ReadingOrder = 1
            $sel.ParagraphFormat.Alignment = if ($judulL) { 1 } else { 3 }
            if ($judulL) { $sel.ParagraphFormat.KeepWithNext = -1 }
            $awal = $sel.Start
            Tulis $blk.runs[0].t 'Times New Roman' $(if ($judulL) { $uLatin + 2 } else { $uLatin }) ([int]$judulL) 0
            $doc.Range($awal, $sel.Start).Select(); $word.Selection.LtrRun(); $sel.Collapse(0)
            $sel.TypeParagraph()
        }
        elseif ($blk.k -eq 'S') {
            Para 3 6 0
            HalamanBaru $pb
            $sel.ParagraphFormat.KeepWithNext = -1
            if ($TO_TITIK -and $blk.judul.StartsWith('❖')) {   # فهرس الموضوعات titik: sub-judul «❖ …» ikut, di bawah judul sebelumnya
                $nT++; [void]$doc.Bookmarks.Add("t_$nT", $sel.Range); [void]$toc.Add(@{ t = $blk.judul; bm = "t_$nT"; lvl = 1 })
            }
            Tulis $blk.judul $TJ $uJudulSub 1 0
            $sel.TypeParagraph()
        }
        elseif ($null -ne $RENCANA.ihda."$i") {           # @ihda: tengah = paragraf الإهداء rata tengah, tebal, berjarak, tanpa menjorok
            Para 1 $RENCANA.ihda."$i" 0
            HalamanBaru $pb
            Runs $blk.runs $uMatan $true
            $sel.TypeParagraph()
        }
        else {
            if ($diMulakhas) { Para 3 $(if ($DATA.blok[$i - 1].k -eq 'K') { 0 } else { 6 }) 0 } else { Para 3 $(if ($i -gt 0 -and $DATA.blok[$i - 1].k -eq 'J') { 6 } else { 0 }) ($word.CentimetersToPoints(0.8)); $sel.ParagraphFormat.SpaceAfter = $JARAK_P }   # sesudah tabel: berjarak
            HalamanBaru $pb
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
    }
    . $tulisBlok

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
        Huruf $tbl.Range.Font $TA $uMatan 0
        return $tbl
    }
    function Sel($tbl, $r, $c, $teks, $align, $bold) {
        $rg = $tbl.Cell($r, $c).Range
        $rg.Text = $teks
        Huruf $rg.Font $TA $uMatan $bold
        $rg.ParagraphFormat.Alignment = $align
        Tautan $rg $rg.Start $teks
        Latin $rg $rg.Start $teks $uMatan
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
    # المصادر والمراجع: tabel tanpa garis, urut abjad
    function Tulis-Pustaka {
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
    Huruf $tb.Range.Font $null $U_PUSTAKA
    for ($r = 1; $r -le $n; $r++) { $rg = $tb.Cell($r, 2).Range; Latin $rg $rg.Start $(if ($PUSTAKA_MUALLIF) { $DATA.pustaka[$r - 1] -replace '\*\*|__', '' } else { $DATA.pustaka[$r - 1] }) $U_PUSTAKA }
    }

    # ---------- 3. Sesudah isi: المصادر والمراجع, الملاحق, الفهارس (yang dicetak, urutan, dan judulnya: $RENCANA.bagian) ----------
    $bmSesudahIsi = "t_$($nT + 1)"   # judul pertama sesudah الخاتمة (المصادر, atau فهرس pertama): HALAMAN_ISI = halamannya - 1
    $fihrisNama = @()                # فهرس nama ({N:}, {M:}): tabel dan barisnya, untuk isian nomor halamannya
    foreach ($bg in $RENCANA.bagian) {
    if ($bg.jenis -eq 'malahiq') {                       # @malahiq: akhir — blok sesudah #R = الملاحق, sesudah المصادر, sebelum فهرس
        $mulaiBlok = $iR + 1
        . $tulisBlok
        $script:fihrisPertama = $true                    # فهرس pertama sesudah الملاحق mulai halaman baru
        continue
    }
    $titik = $bg.jenis -eq 'maudhuat' -and $TO_TITIK     # @maudhuat: titik = «الموضوع ...... ص» per baris tanpa tabel, dan tanpa barisnya sendiri (seperti contoh)
    $diAwal = $bg.awal -and $doc.Bookmarks.Exists('fihris_awal')   # @maudhuat_letak: awal: ditulis di tempat yang disiapkan sebelum المقدمة
    if ($diAwal) {
        $doc.Bookmarks.Item('fihris_awal').Range.Select(); $sel.Collapse(1)
        Judul $bg.judul 't_maudhuat' $true                # tidak masuk فهرس-nya sendiri, dan tidak dihitung sebagai bagian sesudah isi
    } else {
    $nT++; JudulFihris $bg.judul "t_$nT"
    if (-not $titik) { [void]$toc.Add(@{ t = $bg.judul; bm = "t_$nT"; lvl = 0 }) }
    }
    if ($bg.jenis -eq 'pustaka') { Tulis-Pustaka }
    elseif ($bg.jenis -eq 'ayat') {
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
        $q = $tAy.Cell($r, $cA).Range; $q.SetRange($rg.Start + 1, $rg.Start + 1 + $nq); Huruf $q.Font $QF $uAyat
        if ($AYAT_SURAH) { Huruf ($tAy.Cell($r, $cA).Range.Font) $null $uCatatan }   # contoh: sel ayat kecil (14)
        if ($AYAT_SURAH) { Sel $tAy $r 1 $a.surah 1 0 } else { Sel $tAy $r 2 $a.surah 1 0; Sel $tAy $r 3 (Angka $a.a) 1 0 }
        Sel $tAy $r $cP (Angka '00') 1 0
    }
    if ($AYAT_SURAH) { Huruf ($tAy.Rows(1).Range.Font) $TJ }
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
    }
    elseif ($bg.jenis -eq 'hadits') {
    $cH = if ($HADITS_RINGKAS) { 2 } else { 3 }          # @fihris_hadits: ringkas = الأحاديث | الصفحة, طرف dalam kurung
    if ($HADITS_RINGKAS) { $tHd = Tabel ($DATA.hadits.Count + 1) @(7.5, 7.5) 1; Sel $tHd 1 1 'الأحاديث' 1 1; Sel $tHd 1 2 'الصفحة' 1 1; Huruf ($tHd.Rows(1).Range.Font) $TJ }
    else { $tHd = Tabel ($DATA.hadits.Count + 1) @(8.6, 4.4, 2.0) 1; Sel $tHd 1 1 'طرف الحديث أو الأثر' 1 1; Sel $tHd 1 2 'الراوي' 1 1; Sel $tHd 1 3 'الصفحة' 1 1 }
    $r = 1
    foreach ($h in $DATA.hadits) {
        $r++
        if ($HADITS_RINGKAS) { Sel $tHd $r 1 ('(' + $h.t + ')') 3 0; Huruf ($tHd.Cell($r, 1).Range.Font) $null 12 } else { Sel $tHd $r 1 ('«' + $h.t + '»') 3 0; Sel $tHd $r 2 $h.r 1 0 }
        Sel $tHd $r $cH (Angka '00') 1 0
    }
    }
    elseif ($bg.jenis -eq 'maudhuat') {
    if ($titik) {                                        # nomor di tepi kiri
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
    }
    }
    else {                                               # فهرس nama: nama | halaman
        $nm = @($DATA.($bg.jenis))
        $tN = Tabel ($nm.Count + 1) @(10.0, 5.0) 1; Sel $tN 1 1 $bg.kolom 1 1; Sel $tN 1 2 'الصفحة' 1 1
        $r = 1
        foreach ($a in $nm) { $r++; Sel $tN $r 1 $a.t 3 0; Sel $tN $r 2 (Angka '00') 1 0 }
        $tN.Rows(1).HeadingFormat = -1                    # judul kolom diulang di halaman sambungan
        $fihrisNama += , @{ tbl = $tN; baris = $nm; jenis = $bg.jenis }
    }
    if ($diAwal) {   # sesudah فهرس depan hanya boleh ada judul sesudahnya, atau satu paragraf pemisah bagian Word (@nomor)
        $ujung = if ($titik) { $sel.Start } else { $tTo.Range.End }
        $p = $doc.Range($ujung, $ujung).Paragraphs(1); $kosong = @()
        while ($p -and $p.Range.Text.Trim([char]13, [char]12, [char]32) -eq '') { $kosong += $p; $p = $p.Next(1) }
        # paragraf kosong (sisa tempatnya) dibuang: yang tersisa tumpah ke halaman baru kalau فهرس pas satu halaman, dan judul
        # sesudahnya mulai halaman baru lagi = halaman kosong. Paragraf pemisah bagian (@nomor) tetap, setinggi 1 pt
        foreach ($k in $kosong) {
            if ($k.Range.Text.Contains([string][char]12)) { $script:pFihrisEkor = $k; continue }
            try { [void]$k.Range.Delete() } catch { $script:pFihrisEkor = $k }
        }
        if ($script:pFihrisEkor) {
            $pe = $script:pFihrisEkor; Huruf $pe.Range.Font $null 1
            $pe.SpaceBefore = 0; $pe.SpaceAfter = 0; $pe.LineSpacingRule = 4; $pe.LineSpacing = 1; $pe.PageBreakBefore = 0   # 4 = wdLineSpaceExactly
        }
        $script:fihrisAwal = @{ titik = $titik; tabel = $(if ($titik) { $null } else { $tTo }); ujung = $ujung; rapat = 1.0 }
    }
    if (-not $titik -or $diAwal) { [void]$sel.EndKey(6) }
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

    # ---------- 4. Isi nomor halaman ----------
    $doc.Repaginate()
    $HURUF_NOMOR = 'أبتثجحخدذرزسشصضطظعغفقكلمنهوي'    # urutan nomor Word gaya 46; Information(1) tetap memberi angka
    function Hal($bm) {                                  # 1 = nomor halaman seperti yang tercetak
        $r = $doc.Bookmarks.Item($bm).Range; $n = $r.Information(1)
        if ($ABJAD -and $r.Sections(1).Index -eq $bagianDepan) { return [string]$HURUF_NOMOR[$n - 1] }
        return $n
    }
    # {P:kunci}: tiap angka punya bookmark sejak BuatCatatan, termasuk catatan kaki yang dibuat ulang NomorCatatan.
    # Isian bisa memindahkan targetnya ke halaman lain: perbarui lagi sampai nomor halaman dan catatan kaki tetap.
    # Jangan mencari angka biasa: itu bisa mengubah angka isi naskah.
    # halaman فهرس الأعلام: angka berurutan jadi rentang («25-29»); nomor huruf (@nomor) apa adanya
    function Rentang($hal) {
        $angka = @($hal | Where-Object { $_ -is [int] } | Sort-Object -Unique); $lain = @($hal | Where-Object { $_ -isnot [int] })
        $out = @($lain)
        for ($i = 0; $i -lt $angka.Count; $i++) {
            $j = $i; while ($j + 1 -lt $angka.Count -and $angka[$j + 1] -eq $angka[$j] + 1) { $j++ }
            $out += if ($j - $i -ge 2) { "$($angka[$i])-$($angka[$j])" } elseif ($j -gt $i) { "$($angka[$i])"; "$($angka[$j])" } else { "$($angka[$i])" }
            $i = $j
        }
        return ($out -join '، ')
    }
    function IsiRujukanHalaman {
        $ubah = 0
        foreach ($nama in @($rujukanHalaman.Keys)) {
            if (-not $doc.Bookmarks.Exists($nama)) { $rujukanHalaman.Remove($nama); continue } # catatan dibuat ulang
            $rg = $doc.Bookmarks.Item($nama).Range; $pg = Angka (Hal $rujukanHalaman[$nama])
            if ($rg.Text -ne $pg) {
                $rg.Text = $pg; [void]$doc.Bookmarks.Add($nama, $rg); $ubah++
            }
        }
        return $ubah
    }
    # Nomor catatan kaki sudah tetap sejak NomorCatatan di akhir bagian 3, dan sejak itu dokumen tidak diubah: putaran
    # pertama langsung mengisi {P:}. Tidak ada isian yang berubah = dokumennya masih yang diperiksa NomorCatatan terakhir,
    # jadi selesai tanpa membaca semua nomor sekali lagi (bahts 41 halaman: panggilan SalahNomor 7 -> 5)
    for ($putaran = 1; $putaran -le 12; $putaran++) {
        if ($putaran -gt 1) { NomorCatatan }
        $ubah = IsiRujukanHalaman
        $doc.Repaginate()
        if (-not $ubah) { break }
    }
    if ($putaran -gt 12) { throw "Nomor halaman {P:...} atau nomor catatan kaki belum tetap sesudah 12 putaran." }
    # tabel فهرس: angka asli («٢٤، ٣٠») bisa lebih lebar daripada '00', barisnya melipat, dan judul sesudahnya pindah halaman
    # (فهرس الموضوعات pernah mencetak 41 padahal judulnya di halaman 42): isi, Repaginate, ulangi sampai tidak ada yang berubah
    $isiLama = @{}
    # فهرس depan yang baris terakhirnya hampir di dasar halaman: paragraf pemisah bagian (1 pt) sesudahnya tumpah ke halaman
    # baru, lalu المقدمة mulai halaman baru lagi = halaman kosong. Barisnya dirapatkan sedikit (5% tiap putaran, paling banyak
    # 20%) sampai paragraf itu muat di halaman terakhir فهرس
    function RapatFihrisAwal {
        $fa = $script:fihrisAwal; $pe = $script:pFihrisEkor
        if (-not $fa -or -not $pe -or $fa.rapat -le 0.8) { return 0 }
        $hAkhir = $doc.Range($pe.Range.Start - 1, $pe.Range.Start - 1).Information(3)
        if ($pe.Range.Information(3) -le $hAkhir) { return 0 }
        $fa.rapat -= 0.05
        if ($fa.tabel) { $rf = $fa.tabel.Range.ParagraphFormat; $rf.LineSpacingRule = 5; $rf.LineSpacing = $word.LinesToPoints($fa.rapat) }
        else { $doc.Range($doc.Bookmarks.Item('t_maudhuat').Range.End, $pe.Range.Start).ParagraphFormat.SpaceAfter = [single](6 * $fa.rapat - 2) }
        return 1
    }
    for ($putaran = 1; $putaran -le 5; $putaran++) {
        $ubah = RapatFihrisAwal
        if ($adaAy) { $r = 1; foreach ($key in $urut) { $r++; $pg = Angka (($ay[$key].bm | ForEach-Object { Hal $_ } | Select-Object -Unique) -join '، '); if ($isiLama["a$r"] -ne $pg) { $isiLama["a$r"] = $pg; $ubah++; Sel $tAy $r $cP $pg 1 ([int]$AYAT_SURAH) } } }
        if ($adaHd) { $r = 1; foreach ($h in $DATA.hadits) { $r++; $ks = @($h.k); if ($h.lagi) { $ks += $h.lagi }; $pg = Angka (($ks | ForEach-Object { Hal $_ } | Select-Object -Unique) -join '، '); if ($isiLama["h$r"] -ne $pg) { $isiLama["h$r"] = $pg; $ubah++; Sel $tHd $r $cH $pg 1 ([int]$HADITS_RINGKAS) } } }
        foreach ($fNama in $fihrisNama) { $r = 1; foreach ($a in $fNama.baris) { $r++; $pg = Angka (Rentang @(@($a.k) | ForEach-Object { Hal $_ } | Select-Object -Unique)); $idIsi = "$($fNama.jenis)$r"; if ($isiLama[$idIsi] -ne $pg) { $isiLama[$idIsi] = $pg; $ubah++; Sel $fNama.tbl $r 2 $pg 1 0 } } }
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

    # ---------- 5. Simpan ----------
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
    # Dokumen selalu berakhir dengan satu paragraf kosong: sisa TypeParagraph sesudah blok terakhir, atau paragraf wajib
    # Word sesudah tabel terakhir (فهرس). Isi yang pas memenuhi halaman mendorongnya ke halaman baru: PDF berakhir dengan
    # halaman kosong yang hanya bernomor. Sesudah paragraf biasa (bahts tanpa المصادر dan فهرس), tanda paragraf
    # sebelumnya dihapus: paragraf kosong itu hilang, dan paragraf terakhir tetap memakai formatnya sendiri (diuji di
    # Word: perataan, bingkai #T, ukuran, bookmark). Mengecilkannya sampai 1 pt tidak cukup kalau baris terakhir tepat di
    # tepi bawah (naskah 50 baris pendek). Sesudah tabel paragraf itu tidak bisa dibuang: dikecilkan sampai setinggi 1 pt
    $ekor = $doc.Paragraphs.Last
    $tanda = if ($ekor.Range.Start -gt 0) { $doc.Range($ekor.Range.Start - 1, $ekor.Range.Start) }
    if ($ekor.Range.Text.Trim().Length -eq 0 -and $tanda -and $tanda.Text -eq "`r" -and -not $tanda.Information(12)) {
        [void]$tanda.Delete()                            # 12 = wdWithInTable; «`r» = bukan pemisah bagian Word
    }
    elseif ($ekor.Range.Text.Trim().Length -eq 0) {
        Huruf $ekor.Range.Font $null 1
        $ekor.SpaceBefore = 0; $ekor.SpaceAfter = 0; $ekor.LineSpacingRule = 4; $ekor.LineSpacing = 1   # 4 = wdLineSpaceExactly
    }
    $pages = $doc.ComputeStatistics(2)
    # halaman isi = المقدمة s.d. الخاتمة; tanpa المصادر dan فهرس = halaman terakhir. Ada المقدمة atau nomor tercetak dua
    # jenis (@nomor): dihitung dari halaman fisik, supaya #K sebelum المقدمة (الإهداء، الملخص) tidak ikut terhitung
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
    # paragraf khulasah {X} (bookmark x_n): distabilo kuning sesudah .docx dan .pdf utama tersimpan, lalu diekspor ke
    # salinan -PdfKhulasah; `rakit` (rakit.py) memotong salinan itu menjadi halaman-halaman khulasah saja. .docx tetap tanpa stabilo.
    # Potongan --fasl bisa tidak mulai dari x_1 (penomoran x_n se-naskah), jadi semua bookmark x_* yang ada dibaca berurutan.
    $khulasah = @()
    $xBm = @($doc.Bookmarks | Where-Object { $_.Name -match '^x_(\d+)$' } | Sort-Object { [int]($_.Name.Substring(2)) })
    foreach ($bm in $xBm) {
        $par = $bm.Range.Paragraphs(1).Range
        $par.HighlightColorIndex = 7                        # 7 = wdYellow
        $hA = $doc.Range($par.Start, $par.Start).Information(3); $hB = $doc.Range($par.End - 1, $par.End - 1).Information(3)
        $khulasah += "$hA-$hB"
    }
    if ($khulasah.Count) {
        $doc.ExportAsFixedFormat($PdfKhulasah, 17)
        [IO.File]::AppendAllLines($Laporan, [string[]]@("KHULASAH=" + ($khulasah -join ',')))
    }
    $doc.Close($false)
}
finally {
    try { if ($draft) { $doc.ActiveWindow.View.Type = 3 } } catch {}
    try { foreach ($d in @($word.Documents)) { $d.Close($false) } } catch {}
    try { $word.Options.ArabicNumeral = $numeralLama } catch {}
    try { $word.Quit([ref]0) } catch {}                   # Quit menerima argumen ref; Quit(0) selalu gagal
    try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) } catch {}
    try { Bersihkan-WordRakit $CATATAN_WORD } catch { Write-Output "PERINGATAN: Word milik rakit belum berhenti; catatannya disimpan: $($_.Exception.Message)" }
    try { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue } catch {}
    try { $pegangKunci.Close() } catch {}
}
