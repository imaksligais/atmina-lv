# claim-extractor — glabāšanas mehānika

Lasi pirms pirmā `save_analysis` izsaukuma sesijā. Kodols: `.claude/agents/claim-extractor.md`.

## Dokumentu lauki

- `documents` kolonnas: `id`, `content` (teksts; tvītiem saturs ir ŠEIT), `title` (web rakstiem; tvītiem VIENMĒR NULL), `platform` ('web' | 'twitter' | 'x_mention' | 'saeima' | 'video'), `source_url`, `source_domain`, `published_at`, `scraped_at`, `language`, `summary`, `word_count`. Kolonnas `text` nav.
- Tvītu neatzīmē tukšu tāpēc, ka `title` ir NULL — lasi `content`.
- `get_politician_documents()` neatgriež `title`. Virsrakstu, ja vajag, ņem no `documents.title`.
- Ja dict ir `queue_total`, rindā ir vairāk dokumentu nekā atgriezts (`max_results` noklusējums 20). Izsauc vēlreiz ar `max_results=queue_total`.
- `platform` nav autorības pierādījums: `x_mention` var būt paša politiķa tvīts. Autorību pārbaudi pret `source_url` un `social_accounts`.

## Nogriezts avots (stub)

`platform='web'` dokuments zem ~600 zīmēm / ~80 vārdiem parasti ir virsraksts + ievads bez raksta (piem., `pmo.ee` saīsnes no TVNet RSS). Pozīcija no virsraksta nav droša — raksts bieži to precizē vai apgriež.
1. Ekstraktē tikai tad, ja nostāja ir skaidra un pilna tekstā (pilns citēts teikums, ne pārfrāzēts virsraksts).
2. Tad `reasoning` sāc ar `NEEDS_REVIEW: truncated-source (content_len=N)`.
3. Citādi — `empty_doc_ids` ar piezīmi `truncated-stub` (labojums ir atkārtota ielāde: `scripts/fix_pmo_truncated_docs.py`).

Paywall pazīmes: «Lai turpinātu lasīt», «Pilno rakstu lasiet», teksts beidzas teikuma vidū. Tādam avotam confidence reti > 0.6.

## Vide

- Tikai `.venv/Scripts/python.exe`. Svešā venv `save_analysis()` atgriež `status="failed"` (`transaction_rolled_back`), bet zero-claim izsaukums tur izdodas — tukšs rezultāts izskatās pareizs.
- Latvisko tekstu nelaid caur `python -c` (čaula var nomest garumzīmes; tas NAV konteksta dreifs). Raksti UTF-8 skriptu scratchpad mapē.
- Faila nosaukumā — tavi pid (`ext_<pid>_<pid>_<datums>.py`), jo datums un uzdevums ir vienādi visiem viļņa aģentiem. Nekad nenosauc skriptu pakotnes vārdā (`h11.py`, `httpx.py`, `json.py`) — tas aizēno īsto pakotni.
- Skripta sākumā: `import os, sys; os.chdir(r"E:\atmina"); sys.path.insert(0, r"E:\atmina")`. Bez tā `from src…` krīt, un relatīvs DB ceļš izveido tukšu failu citur.

## `save_analysis`

```python
from src.analyze import save_analysis
result = save_analysis(
    pid=3, analysis_date="2026-04-06", sentiment=0.0,  # VIENMĒR 0.0
    topics=["Vēlēšanas"], quotes=["citāts"], brief="Analīze...", confidence=0.9,
    claims=[{
        "document_id": 2534, "topic": "Vēlēšanas",
        "stance": "Atbalsta manuālu balsu skaitīšanu.",
        "support": ["Es atbalstu, ka balsis skaita ar rokām"],
        "quote": "Es atbalstu, ka balsis skaita ar rokām.", "confidence": 0.85,
        "reasoning": "Paša tvīts; skaidra nostāja.",
        "salience": 0.7, "stated_at": "2026-04-06",
    }],
    empty_doc_ids=[2535, 2536],  # izlasīti, bez pozīcijas
)
# {"status": "success"|"partial"|"failed", "analysis_id", "claim_ids",
#  "contradiction_ids", "failures"}
```

- `source_url` nenorādi: to ņem no `documents.source_url` (agrāk aģenti izdomāja URL).
- `claim_type` nenorādi — noklusējums `position`. `saeima_vote` rezervēts `@saeima-tracker`; `commentary` slēgts.
- Nezināma atslēga claim dict tiek klusi izmesta. `support` IR zināma atslēga — to pārbauda.
- **Atomiskums:** analīze + claims + `reviewed_at` ir viena transakcija. Katastrofāla kļūda → `status="failed"`, `transaction_rolled_back`, nekas netiek saglabāts. Validācijas izlaidumi → `status="partial"` bez rollback.

### `failures` tipi

| Tips | Nozīme | Ko darīt |
|---|---|---|
| `missing_source_url` | dokumentam nav URL, claim nomests | reāls zudums — ziņo |
| `silent_dedup` | divas pozīcijas vienā `(pid, source_url, topic)` saplūda | apvieno vienā stance vai sadali pa tēmām tikai ar atšķirīgu pamatojumu; tēmu nelokiet, lai izvairītos |
| `missing_support` | pozīcijai nav `support` | pievieno fragmentus, saglabā vēlreiz |
| `support_not_in_source` | fragments nav ŠĪ dokumenta tekstā | kopē burtiski no teksta; ja stance balstās uz ko citu — stance ir nepareizs, labo stance |
| `possible_duplicate` | ļoti līdzīgs claim ±5 d | sk. `datumi-dublikati.md` |

Atkārtots izsaukums ir drošs: `store_claim()` ir idempotents uz `(opponent_id, source_url, topic)`.

## Pretrunu pārbaude (obligāta, CLAUDE.md inv #7)

`save_analysis()` pretrunas nemeklē. Katrai glabātajai pozīcijai:

```python
from src.tools import search_similar_claims, store_contradiction
search_similar_claims(opponent_id=57, claim_text=stance, top_k=8,
                      claim_type_filter=['position'])  # -> JSON virkne
```

- Parametri ir `claim_text` un `top_k` (nav `query=`/`limit=`). Rezultātos ir `distance` (mazāks = tuvāks), nav `similarity` lauka. Lem pēc SATURA, ne pēc sliekšņa.
- Reālai pretrunai:
  ```python
  store_contradiction(opponent_id=5, old_claim_id=10, new_claim_id=55,
      topic="Budžets un finanses", summary="Iepriekš atbalstīja X, tagad iebilst pret X",
      severity="reversal", salience=0.7)
  ```
  `severity`: `minor_shift` (niansēta maiņa), `reversal` (būtisks pavērsiens), `direct_contradiction` (pretēji apgalvojumi).
- Jautā sev: vai to var godīgi izskaidrot kā attīstību? Vai konteksts ir pietiekami atšķirīgs? Vai tas izturētu žurnālista jautājumu? Ja neesi drošs — tā NAV pretruna.

## Regresiju audits

`.venv/Scripts/python.exe scripts/audit_quote_fidelity.py --min-confidence 0.85`
