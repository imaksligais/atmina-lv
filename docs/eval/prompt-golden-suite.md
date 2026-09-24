# Zelta kopas uzdevuma prompts (kanoniskais)

Šis ir teksts, ko padod modelim, kad mēra claim-extractor zelta kopu. Tas ir
**versionēts repo**, jo agrāk dzīvoja `.scratch/` — gitignorētā mapē, kas tiek
tīrīta, tāpēc recepte būtu sabrukusi pēc pirmās uzkopšanas (atrasts 2026-09-22).

Prompts pats nemainās starp kārtām — mainās tikai `.claude/agents/claim-extractor.md`,
ko modelis izlasa. Tā ir visa eksperimenta būtība: viens uzdevums, dažādi noteikumi.

```text
Tavi noteikumi ir failā `.claude/agents/claim-extractor.md` — izlasi to pilnībā. Tad izlasi `docs/eval/_golden-2026-09-16-NO-RUBRIC.md` (12 gadījumi) un izpildi tā instrukcijas: DRY-RUN, nekādu DB izsaukumu, nekādu citu failu lasīšanas. Atgriez TIKAI vienu JSON masīvu ar 12 objektiem secībā 1-12, katrs {"case": N, "decision": "extract"|"empty"|"needs_review", "claims": [{"topic","stance","quote","confidence","reasoning"}], "empty_reason": ...} — kā gadījumu fails prasa. Bez markdown apvalka.
```

## Lietošana

```bash
cd /e/atmina
P=docs/eval/prompt-golden-suite.md   # bloka saturu padod kā promptu

# Opus
sed -n '/^```text$/,/^```$/p' $P | sed '1d;$d' | claude -p --model opus \
  --allowedTools "Read,Glob,Grep" > docs/eval/_run-opus-$(date +%F).txt 2>&1

# SWE-2 max (Devin CLI) — sk. wiki/operations/devin.md par karogiem
sed -n '/^```text$/,/^```$/p' $P | sed '1d;$d' > .scratch/p.txt
/e/Devin/bin/devin.cmd --prompt-file .scratch/p.txt -p --model swe-2-max \
  --respect-workspace-trust false --permission-mode auto \
  > docs/eval/_run-swe2-$(date +%F).txt 2>&1

# Vērtēšana
.venv/Scripts/python.exe scripts/eval_claim_extractor_score.py docs/eval/_run-<m>-<datums>.txt
```

Rubrika un gadījumu apraksti: `claim-extractor-golden-cases-2026-09-16.md`.
Ko skripts nevērtē (tēmas, claim skaits) — `claim-extractor-prompt-v3-2026-09-22.md`.
