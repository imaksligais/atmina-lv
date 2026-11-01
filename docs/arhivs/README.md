# docs/arhivs — arhivētie dokumenti

Šajā mapē glabājas dokumenti, kas vairs netiek uzturēti. Tie ir saglabāti vēsturei; to saturs var būt novecojis un neatbilst pašreizējam kodam vai procesiem.

## 2026-09-27

Arhivēti 61 dokuments, uz kuriem repozitorijā nebija nevienas atsauces: `audits/` 18 (ieskaitot visu `2026-09-23-routine/` mapi), `superpowers/` 39 (plāni un specifikācijas; Jev pretrunu filtra plāns atgriezts, jo projekts ir atvērts), `research/` 3 un `eval/` 1. Faili pārvietoti ar `git mv`, saglabājot apakšceļu (`docs/<mape>/<ceļš>` → `docs/arhivs/<mape>/<ceļš>`). Šie faili netiek uzturēti un var būt novecojuši; relatīvās saites no tiem tagad atrodas vienu līmeni dziļāk un var vairs nestrādāt. Tajā pašā dienā dzēsti 282 veci sociālo tīklu melnraksti no `docs/social/` un `docs/tweet_bank/` (281 datēts pirms 2026-08-28, viens bez datuma); tie joprojām pieejami git vēsturē: `git log --diff-filter=D -- docs/social docs/tweet_bank`.

## Handoff dokumentu dzīves cikls

Handoff tiek rakstīts repozitorijā kā `docs/HANDOFF-<datums>.md`, nevis privātajā atmiņā. Kad tas ir noslēgts, failu pārvieto uz `docs/arhivs/handoffs/`. Abas mapes ir publiskas, tāpēc pirms publiskā spoguļa sinhronizācijas katram handoff jāiziet identitātes pārbaude (sk. [`docs/funding/repo-sync.md`](../funding/repo-sync.md)).
