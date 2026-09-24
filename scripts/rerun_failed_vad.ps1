# Phase 1.5 — re-run atlikušos failed pids ar 60s cooldown starp katru.
# Hot-fix 8baf4a6 ierobežo retry uz 3 strikes per pid.
# pid 144 (Inga Bērziņa) jau pabeigts iepriekšējā re-run iterācijā.
$polIds = @(104, 138, 106, 155, 92, 25, 132, 107)
$root = "$env:USERPROFILE\atmina"
$py = "$env:USERPROFILE\atmina\.venv\Scripts\python.exe"
$ingest = "$env:USERPROFILE\atmina\.worktrees\vad-phase-1.5\scripts\ingest_vad_declarations.py"
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
$total_started = Get-Date
foreach ($polId in $polIds) {
    $name = & $py -c "import sqlite3; print(sqlite3.connect('data/atmina.db').execute('SELECT name FROM tracked_politicians WHERE id=?', ($polId,)).fetchone()[0])"
    Write-Output "============================================================"
    Write-Output "[run] pid=$polId $name (started $(Get-Date -Format 'HH:mm:ss'))"
    Write-Output "============================================================"
    $t0 = Get-Date
    & $py $ingest --politician $name 2>&1
    $elapsed = (Get-Date) - $t0
    Write-Output "[done] pid=$polId elapsed=$($elapsed.TotalSeconds.ToString('F1'))s"
    Start-Sleep -Seconds 60
}
$total_elapsed = (Get-Date) - $total_started
Write-Output ""
Write-Output "[ALL DONE] total elapsed: $($total_elapsed.TotalMinutes.ToString('F1')) min"
