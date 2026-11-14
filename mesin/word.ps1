# SPDX-License-Identifier: AGPL-3.0-or-later
# Word exposes Hwnd on a document window, not on Application; a new application has no document window yet.
function Id-ProsesWord($Jendela) {
    if (-not ('Bahts.WordWindow' -as [type])) {
        Add-Type -Name WordWindow -Namespace Bahts -MemberDefinition '[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(System.IntPtr hwnd, out uint processId);'
    }
    [uint32]$nomor = 0
    $utas = [Bahts.WordWindow]::GetWindowThreadProcessId([IntPtr]$Jendela.Hwnd, [ref]$nomor)
    if (-not $utas -or -not $nomor) { throw 'Proses Word milik rakit tidak dapat dikenali dari jendelanya.' }
    return [int]$nomor
}

function Catat-WordRakit($Word, [string]$Catatan) {
    $dokumen = $Word.Documents.Add()
    try {
        $p = Get-Process -Id (Id-ProsesWord $dokumen.ActiveWindow) -ErrorAction Stop
        try {
            if ($p.ProcessName -ne 'WINWORD') { throw 'Jendela Word menunjuk proses selain WINWORD.' }
            $identitas = "$($p.Id)|$($p.StartTime.Ticks)"
            Set-Content -LiteralPath $Catatan -Encoding ASCII -Value $identitas
            return $identitas
        }
        finally { $p.Dispose() }
    }
    finally { $dokumen.Close([ref]0) }
}

function Hentikan-WordRakit([string]$Identitas) {
    if ($Identitas -notmatch '^(\d+)\|(\d+)$') { return }
    [int]$nomor = 0; [long]$mulai = 0
    if (-not [int]::TryParse($Matches[1], [ref]$nomor) -or -not [long]::TryParse($Matches[2], [ref]$mulai)) { return }
    $p = Get-Process -Id $nomor -ErrorAction SilentlyContinue
    if (-not $p) { return }
    try {
        # Holding the process handle makes the identity check and stop refer to the same OS process, even after PID reuse.
        [void]$p.Handle
        if ($p.ProcessName -ne 'WINWORD' -or $p.StartTime.Ticks -ne $mulai) { return }
        if (-not $p.WaitForExit(500)) { Stop-Process -InputObject $p -Force -ErrorAction Stop }
    }
    finally { $p.Dispose() }
}

function Bersihkan-WordRakit([string]$Catatan) {
    if (-not (Test-Path -LiteralPath $Catatan)) { return }
    foreach ($identitas in Get-Content -LiteralPath $Catatan) { Hentikan-WordRakit $identitas }
    # A failed stop must keep the ownership record, so the next build can recover the orphan.
    Remove-Item -LiteralPath $Catatan -Force
}
