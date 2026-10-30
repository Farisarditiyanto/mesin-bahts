# Jalankan startup rakit yang asli sebelum Word dibuat: hanya Word yatim yang dicatat rakit lama yang dihentikan,
# proses aplikasi lain tidak boleh disentuh.
$ErrorActionPreference = 'Stop'
$rakit = Join-Path $PSScriptRoot '..\mesin\rakit.ps1'
$token = $null; $galat = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($rakit, [ref]$token, [ref]$galat)
if ($galat) { throw 'rakit.ps1 tidak bisa diurai' }
$buatWord = $ast.Find({
    param($a)
    $a -is [System.Management.Automation.Language.AssignmentStatementAst] -and
    $a.Left.Extent.Text -eq '$word' -and $a.Right.Extent.Text -match 'New-Object\s+-ComObject\s+Word.Application'
}, $true)
if (-not $buatWord) { throw 'Titik sebelum pembuatan Word tidak ditemukan; perbarui uji startup' }
$asal = Get-Content -LiteralPath $rakit -Raw -Encoding UTF8
$uji = Join-Path ([IO.Path]::GetTempPath()) ('bahts-word-startup-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path (Join-Path $uji '_tmp') -Force | Out-Null
$startup = Join-Path $uji 'startup.ps1'
[IO.File]::WriteAllText($startup, $asal.Substring(0, $buatWord.Extent.StartOffset), (New-Object Text.UTF8Encoding $true))
$build = Join-Path $uji 'build.json'
$format = Get-Content -LiteralPath (Join-Path (Split-Path $rakit) 'format.json') -Raw -Encoding UTF8 | ConvertFrom-Json
@{
    meta = @{ berkas = 'uji'; judul = 'uji'; angka = 'hindi' }
    format = $format.imam
    ayat = @(); hadits = @(); pustaka = @()
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $build -Encoding UTF8
# catatan rakit yang dimatikan paksa: 999002 = Word-nya yang masih hidup; 999003 = nomornya sudah dipakai proses lain
$mulai = [datetime]::new(638000000000000000)
Set-Content -LiteralPath (Join-Path $uji '_tmp\rakit.word') -Encoding ASCII -Value "999002|$($mulai.Ticks)", "999003|$($mulai.Ticks)"
$jalankan = Join-Path $uji 'jalankan.ps1'
@'
param($Startup, $Build, $Folder, [long]$Mulai)
$ErrorActionPreference = 'Stop'
$global:dihentikan = @()
function Get-CimInstance {
    param($ClassName, $Filter)
    [pscustomobject]@{ ProcessId = 999001; CommandLine = 'WINWORD.EXE /Automation aplikasi_lain' }
}
function Get-Process {
    param($Name, $Id, $ErrorAction)
    $lain = [pscustomobject]@{ Id = 999001; ProcessName = 'WINWORD'; StartTime = [datetime]::new($Mulai) }
    $yatim = [pscustomobject]@{ Id = 999002; ProcessName = 'WINWORD'; StartTime = [datetime]::new($Mulai) }
    $dipakaiUlang = [pscustomobject]@{ Id = 999003; ProcessName = 'WINWORD'; StartTime = [datetime]::new($Mulai + 1) }
    if ($Id) { @($lain, $yatim, $dipakaiUlang) | Where-Object { $_.Id -in $Id } } else { $lain, $yatim, $dipakaiUlang }
}
function Stop-Process {
    param($Id, [switch]$Force, $ErrorAction)
    $global:dihentikan += $Id
}
. $Startup -Build $Build -Folder $Folder
if ("$global:dihentikan" -ne '999002') { throw "Startup menghentikan [$global:dihentikan]; seharusnya hanya Word yatim 999002" }
if (Test-Path -LiteralPath (Join-Path $Folder '_tmp\rakit.word')) { throw 'Catatan Word rakit lama tidak dibuang' }
'@ | Set-Content -LiteralPath $jalankan -Encoding UTF8
& powershell -NoProfile -ExecutionPolicy Bypass -File $jalankan -Startup $startup -Build $build -Folder $uji -Mulai $mulai.Ticks
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output 'uji startup Word: hanya Word yatim catatan rakit lama yang dihentikan; otomasi aplikasi lain tidak disentuh (Word tidak dijalankan)'
