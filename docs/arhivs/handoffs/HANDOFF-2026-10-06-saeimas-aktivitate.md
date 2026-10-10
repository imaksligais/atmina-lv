# Handoff 2026-10-06 — profila bildes, partiju lapa, Saeimas aktivitāte

## Izdarīts (viss live + pushots)
- 63 profila bildes (0 trūkst no 252); `fetch_profile_photos` pārkodē uz īstu JPEG + sargs `tests/test_profile_photos_jpeg.py`.
- Partiju lapa: LV reģistrs nosaukumos, kārtojums pēc balsīm; SV/AJ kartīte (mājaslapa, krāsa, ideoloģija). Koalīcijas statusi NEmainīti — 14. Saeima strādā līdz 15. sanākšanai.
- Deploy runbook bez rsync (`deploy.md` 343→163; Namecheap → `deploy-namecheap-arhivs.md`).
- **Saeimas aktivitāte** (plāns `docs/plans/2026-10-06-saeimas-aktivitate.md`): amati 1053, debates 9262, jautājumi 401 / saites 3281; 3 bloki profila Saeimas cilnē; nedēļas rutīnā `-m scripts.ingest_saeima_activity --what all`.

## Gaida operatoru
- **X pavedieni (nepostēti):** `docs/tweet_bank/2026-10-06-dienas-parskats-social.md` (pārskats 10-05) un `docs/tweet_bank/2026-10-06-saeimas-aktivitate-social.md` (jaunā funkcija). Bildes `output/images/threads/2026-10-06-thread-*`.
- 6. oktobra dienas pārskats — vakara rutīnā.
- CVK oficiālais saraksts līdz 10-19 (vārti B); vecā hostinga Task 9 līdz 10-16.

## Zināmie robi
- Briškena `role` (Tautsaimniecības komisijas priekšsēdētājs) — amats beidzies 09.06.2026 pēc titania; T6, backlog «Pilna amatu pārskatīšana».
- Saeimas cilnes skaitlis = balsojumi → jaunajiem deputātiem novembrī «0».
- `check.sh` uz šīs mašīnas: `CHECK_PYTEST_WORKERS=3` (os error 1455 pie auto).
