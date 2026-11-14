#!/usr/bin/env bash
# Aptur pamestus pytest procesus, kas palaisti no šī repo .venv, PIRMS jauna
# check.sh skrējiena. Sauc scripts/check.sh; var palaist arī atsevišķi.
#
# Kāpēc (2026-11-11/12): pārtraukts check.sh (sesijas restarts, noildze) atstāj
# pytest + xdist darbinieku koku darbojamies (~6 GB). Nākamais skrējiens virs tā
# krīt ar `EEE` un «Windows fatal exception: access violation», un tas izskatās
# pēc testu kļūdas, nevis pēc atmiņas trūkuma. 12.11. rītā tādi bija 16 procesi
# no diviem skrējieniem.
#
# Tvērums: tikai procesi, kuru komandrindā ir ŠĪ repo `.venv\Scripts\python.exe`
# un `-m pytest`; to bērnus (xdist darbiniekus) aizver `taskkill /T`. Citu
# projektu pytest netiek aiztikts. Vienlaicīgs check.sh no worktree ar to pašu
# .venv arī tiktu apturēts — divi skrējieni reizē šajā datorā tāpat nav droši.
#
# Izslēgt: CHECK_KEEP_PYTEST=1. Ārpus Windows (nav powershell.exe) — neko nedara.
#
# Usage: bash scripts/kill_stale_pytest.sh <ceļš uz .venv python>
set -u

PY="${1:-}"
if [ "${CHECK_KEEP_PYTEST:-0}" = "1" ]; then
    echo "    pamestie pytest: pārbaude izslēgta (CHECK_KEEP_PYTEST=1)"
    exit 0
fi
if [ -z "$PY" ] || ! command -v powershell.exe >/dev/null 2>&1 || ! command -v cygpath >/dev/null 2>&1; then
    exit 0
fi

VENV_PY_WIN="$(cygpath -w "$PY")"
export VENV_PY_WIN

# PowerShell 5.1 izvadē garumzīmes pazūd, tāpēc tas atgriež tikai skaitļus
# ("PID <n>" rindas un "FOUND <n> LEFT <m>"), bet tekstu raksta bash.
OUT="$(powershell.exe -NoProfile -NonInteractive -Command '
$ErrorActionPreference = "Stop"
$needle = $env:VENV_PY_WIN
function Get-Roots {
    @(Get-CimInstance Win32_Process |
        Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -and $_.CommandLine.Contains($needle) -and $_.CommandLine.Contains("-m pytest") })
}
$roots = @(Get-Roots)
foreach ($r in $roots) {
    Write-Output ("PID {0}" -f $r.ProcessId)
    & taskkill.exe /PID $r.ProcessId /T /F | Out-Null
}
if ($roots.Count -gt 0) { Start-Sleep -Seconds 2 }
$left = @(Get-Roots)
Write-Output ("FOUND {0} LEFT {1}" -f $roots.Count, $left.Count)
' | tr -d '\r')" || { echo "    pamestie pytest: procesu vaicājums neizdevās"; exit 1; }

SUMMARY="$(printf '%s\n' "$OUT" | grep '^FOUND ' || true)"
if [ -z "$SUMMARY" ]; then
    echo "    pamestie pytest: procesu vaicājums neatgrieza rezultātu"
    printf '%s\n' "$OUT"
    exit 1
fi
printf '%s\n' "$OUT" | grep '^PID ' | while read -r _ pid; do
    echo "    apturu pamestu pytest koku: PID $pid"
done
FOUND="$(echo "$SUMMARY" | cut -d' ' -f2)"
LEFT="$(echo "$SUMMARY" | cut -d' ' -f4)"
echo "    pamestie pytest: atrasti $FOUND, pēc apturēšanas palikuši $LEFT"
[ "$LEFT" = "0" ]
