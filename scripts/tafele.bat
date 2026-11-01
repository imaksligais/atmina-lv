@echo off
cd /d "%~dp0.."
set PYTHONUTF8=1
".venv\Scripts\python.exe" "scripts\preview_tafele.py" "docs\drafts\tafeles\visvanati-2026.yaml" --serve
