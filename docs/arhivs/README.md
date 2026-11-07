# docs/arhivs — arhivētie dokumenti

Šajā mapē glabājas dokumenti, kas vairs netiek uzturēti. Tie ir saglabāti vēsturei; to saturs var būt novecojis un neatbilst pašreizējam kodam vai procesiem.

## 2026-09-27

Arhivēti 61 dokuments, uz kuriem repozitorijā nebija nevienas atsauces: `audits/` 18 (ieskaitot visu `2026-09-23-routine/` mapi), `superpowers/` 39 (plāni un specifikācijas; Jev pretrunu filtra plāns atgriezts, jo projekts ir atvērts), `research/` 3 un `eval/` 1. Faili pārvietoti ar `git mv`, saglabājot apakšceļu (`docs/<mape>/<ceļš>` → `docs/arhivs/<mape>/<ceļš>`). Šie faili netiek uzturēti un var būt novecojuši; relatīvās saites no tiem tagad atrodas vienu līmeni dziļāk un var vairs nestrādāt. Tajā pašā dienā dzēsti 282 veci sociālo tīklu melnraksti no `docs/social/` un `docs/tweet_bank/` (281 datēts pirms 2026-08-28, viens bez datuma); tie joprojām pieejami git vēsturē: `git log --diff-filter=D -- docs/social docs/tweet_bank`.

## 2026-11-02

Arhivēti 14 dokumenti, uz kuriem ārpus arhīva neatsaucas nekas (vai tikai CHANGELOG ieraksts par pabeigtu darbu — tā saite nomainīta): `superpowers/specs/` 12 (aprīļa–jūlija dizaini, ieskaitot 2026-06-01 nedēļas pārskata formu, ko 11-01 aizstāja «Nedēļas stāsti»), `research/` 1 un `eval/` 1. Tīrs `git mv`, saturs nav mainīts. Tajā pašā dienā: 4 izpildīti plāni uz `docs/plans/archive/` (tās README), 6 handoffi uz `handoffs/` (tās README).

Paliek, kaut izskatās veci: dokumenti, uz kuriem atsaucas kods, testi, `data/*.sql`, backlogs vai neiesaldēti pieraksti (piem., `docs/refactor/` — `tests/test_schema.py`, `verdikti-*` — `data/fix_*`). `docs/drafts/` nepārvieto: mape ir izslēgta no publiskā spoguļa, `arhivs/drafts` nebūtu.

## Handoff dokumentu dzīves cikls

Handoff tiek rakstīts repozitorijā kā `docs/HANDOFF-<datums>.md`, nevis privātajā atmiņā. Kad tas ir noslēgts, failu pārvieto uz `docs/arhivs/handoffs/`. Abas mapes ir publiskas, tāpēc pirms publiskā spoguļa sinhronizācijas katram handoff jāiziet identitātes pārbaude (sk. [`docs/funding/repo-sync.md`](../funding/repo-sync.md)).
