"""Nolasa SEPLP 2026. gada plāna grozījumu 1. pielikumu (media/3802) un pārrēķina labojuma skaitļus."""
import hashlib
import sys
from pathlib import Path

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")
p = Path(sys.argv[1])
print("SHA-256", hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size, "B")
wb = openpyxl.load_workbook(p, data_only=True)
print(wb.sheetnames)
ws = wb.active
for r in range(1, 10):
    print(r, [(c.coordinate, c.value) for c in ws[r] if c.value is not None][:14])
for r in [17, 18, 116, 117, 126, 127, 133, 134, 180, 181]:
    print(r, repr(ws[f"A{r}"].value)[:70], repr(ws[f"B{r}"].value)[:40],
          "C", ws[f"C{r}"].value, "U", ws[f"U{r}"].value, "AM", ws[f"AM{r}"].value, "AO", ws[f"AO{r}"].value)
for r in range(230, 260):
    v = ws[f"A{r}"].value
    if v:
        print("NOTE", r, v)

def sh(num, den):
    return round(100 * ws[num].value / ws[den].value, 1)

print("LTV1 atk I", sh("C133", "C180"), "II", sh("U133", "U180"))
print("LTV7 atk I", sh("C134", "C181"), "II", sh("U134", "U181"))
print("LTV7 iepirkts I", sh("C127", "C181"), "II", sh("U127", "U181"), "gadā", sh("AM127", "AM181"))
print("LTV1 iepirkts I", sh("C126", "C180"), "II", sh("U126", "U180"), "gadā", sh("AM126", "AM180"))
for cell, days in [("C134", 181), ("U134", 184), ("C133", 181), ("U133", 184)]:
    h = ws[cell].value / days
    print(cell, "h/diennaktī", int(h), "h", round((h - int(h)) * 60), "min")
