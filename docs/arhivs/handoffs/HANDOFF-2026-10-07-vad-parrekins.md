# HANDOFF 2026-10-07 — VAD analīzes pilnais pārrēķins + publicēšana

Nākamās sesijas darbs. Operators 10-07: «vispirms pārrēķināsim visu», tad publicēt.

## Stāvoklis — PABEIGTS 2026-10-07

- Soļi 1–8 izdarīti. Visa lapa pārrēķināta (2776/201), operators deva «jā» publicēšanai; deploy versija `9c760fbb` (pēc commita `0f181e85`), live pārbaudīts: `analizes/vad-2026.html` 200, satur «2776» un «Īrē vai lieto».
- `audit_vad_profile_match.py` salabots jaunajam profila formātam (`67126365`): [OK] 60/60, mutācija pierādīta.
- Atvērts → `backlog/vad.md` § «VAD analīzes ģenerators § 5/§ 6 kārto citādi nekā profils».

### Sākotnējais stāvoklis

- `content/analizes/vad-2026.md` § 6e «Ārvalstu īpašumi» jau pārrēķināta (commiti `f7eb98f2`, `0917528b`):
  69 ieraksti / 9 politiķi, sadalīts «Pieder» / «Īrē vai lieto», katrs ieraksts pārbaudīts pret `raw_html`.
  **Nav deploy** — gaida pilno pārrēķinu.
- Pārējās sadaļas ir no 2026-09-20: lapā 2238 deklarācijas / 159 politiķi, DB **2776 / 201**
  (`scripts/vad_analysis_numbers.py --year 2025` § 1). Starpība = 15. Saeimas kohorta (seed 10-05).
- `scripts/audit_vad_profile_match.py --skip-render` → 1 nesakritība: § 5 Elīna Treija, uzņēmumi lapā 5, profilā 3.
  Pirms § 5 pārrakstīšanas izlasi, vai tā ir datu maiņa vai metodes atšķirība (audita piezīme: `compute_section_deltas`).

## Soļi (runbook `wiki/operations/vad-declarations.md` § Analīzes lapas atsvaidzināšana)

1. `.venv/Scripts/python.exe scripts/vad_analysis_numbers.py --year 2025` → visas tabulas.
   Gads: jaunākais, kurā ikgadējo deklarāciju skaits ≥ iepriekšējam — pārbaudi, vai joprojām 2025.
2. Katram JAUNAM tabulas politiķim (īpaši 15. Saeimas kohortai) — ģimenes-paraksta pārbaude
   (`docs/drafts/vad_15saeima_family_audit_{A,B,C}.md` jau sedz kohortu) + raw HTML katram pārsteigumam.
3. Pārraksti § 1–§ 9 tabulas + frontmatter `description` (2238/159 → jaunie skaitļi) + galvenes `Atjaunots`
   (noņem 10-07 piezīmi par § 6e, ja viss pārrēķināts vienā dienā). § 6e saglabā pašreizējo struktūru.
4. Vārti: `-m src.render --only=politiki` → `audit_vad_profile_match.py --skip-render` = `[OK]`.
5. `-m src.render --only=analizes,dashboard`; atver renderēto `output/atmina/analizes/vad-2026.html`
   (tabulas, saites, nav rindkopu, kas sākas ar «N. »); `REGEN=1 pytest tests/test_render_chars.py`; `bash scripts/check.sh`.
6. LV gramatikas + stilistikas pārbaude visam jaunajam tekstam.
7. Commit (`git commit -F`), CHANGELOG ≤5 rindas.
8. **Publicēšana — tikai ar operatora skaidru «jā» šai reizei** (escalation 7). Tad
   `bash scripts/deploy.sh --no-delete` (pilns lokālais koks → pārliecinies, ka koks pilns, T15 preflight).

## Saistītais, ko atrada 10-07

- ~~Saeimas balsojumu aprakstu kļūda~~ — NAV defekts: `BACKLOG.md` § Ne-darīt (summary pieder likumprojektam, iznākums = `saeima_votes.result`).
