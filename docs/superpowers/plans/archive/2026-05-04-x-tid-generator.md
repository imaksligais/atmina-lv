# X transaction-id generator — scoped plan (RESOLVED — NOT IMPLEMENTED)

> **STATUS: RESOLVED 2026-05-08 (without implementing this plan).**
> Upstream `d60/twikit#410` (publicēts 2026-03-18) atrisināja root cause —
> X mainīja `ondemand.s.js` lookup formātu, nevis to noņēma. atmina
> pielietoja PR #410 izmaiņas kā Patch 5 (commit `9d5a26a`, 2026-05-08).
> Reālais TID tiek ģenerēts atkal; `SearchTimeline` un `UserTweetsAndReplies`
> strādā bez šī plāna implementācijas.
>
> Plāns paliek arhīvā kā references piemērs reverse-engineering pieejai —
> ja X nākotnē mainīs algoritmu tā, ka upstream nepalīdz, šis plāns var
> kalpot kā startpoint. Sk. `wiki/CHANGELOG.md § 2026-05-08` un
> `wiki/operations/twikit-notes.md § 2026-05-08`.

---

_Status: stub. Drafted 2026-05-04 during operacionālā audit sesijā. Nav izpildīts._

## Konteksts

Patch 4 (2026-04-28) `src/patch_twikit.py` pievienoja graceful fallback uz stub TID (`x-client-transaction-id`) gadījumam, kad twikit `ClientTransaction.init()` neizdodas (X izņēma `ondemand.s` referenci no home page ~2026-04-25). Stub strādā uz **lenient endpoints** (`UserTweets`, `UserByScreenName`), bet ne uz **strict endpoints** (`SearchTimeline`, `UserTweetsAndReplies`), kas atgriež 404 uz katru pieprasījumu.

Sekas:
- `@mentions-monitor` zaudēja 3rd-party mention coverage (sk. twikit-notes.md § 2026-04-29)
- `fetch_user_replies` zaudēja replies coverage (sk. x_scraper.py docstring 2026-05-04 update)
- Reālo TID generator-u ir grūti reverse-engineerēt, jo X to pārvietoja no `ondemand.s.*a.js` uz iekšēju webpack chunk

## Mērķis

Izveidot reālu `x-client-transaction-id` ģeneratoru, kas X strict-validē. Kad tas darbosies, gan SearchTimeline, gan UserTweetsAndReplies atjaunosies bez papildu koda izmaiņām (twikit funkcijas saglabājas).

## Ne-mērķi

- Twikit lib pārrakstīšana
- TID logikas paralēlizācija starp slot-iem (TID ir per-request, ne per-session)
- Browser automation (vajag tīru reproducible algoritmu, ne Playwright)

## Pierādījumi un izejas dati

1. **Reāls TID validē.** Hardcodējot DevTools cURL capture iegūto `x-client-transaction-id` (zināms `SearchTimeline` strādā uzreiz). Tas pierādīja, ka problēma ir tikai šī header lauka ģenerēšana, ne plašāka TLS fingerprint vai feature flag drift.
2. **Webpack chunk.** TID indices pārvietojušies no `ondemand.s.*a.js` failā uz iekšēju webpack-bundled chunk. Algoritma core (HMAC-SHA256 ar konkrētiem indices uz path + animation_key) joprojām derīgs; tikai indices source ir mainījies.
3. **Animation key.** Aprēķina daļa, kas balstās uz Twitter's grafiskās animācijas SVG path vērtībām. Šo X nesen nav mainījis.

## Plāns (4 fāzes)

### F1: Indices ekstrakcija (~2-3 dienas)

- Iztaukomu `index.html` no `https://x.com/` 
- Identificēt webpack runtime chunk (parasti `runtime.{hash}.js`) un main bundle chunk
- Atrast TID indices array (4 baitu masīvs, pirmreizēja iteration pamatojoties uz `KEY_BYTE_INDICES_LENGTH = 4` konstanti)
- Validēt: indices iegūtie pret reālu DevTools capture jāsakrīt

**Risks:** webpack chunk hash rotē regulāri (dažos gadījumos pat vairākas reizes dienā). Indices ekstrakcijai jābūt robusta uz hash drift.

### F2: TID compute funkcija (~1 diena)

Implementēt Python funkciju `compute_tid(method, path, animation_key, time_now) -> str`:

```python
def compute_tid(method: str, path: str, animation_key: str, time_now: int | None = None) -> str:
    """Compute x-client-transaction-id matching X's strict validation."""
    indices = _get_kbi_indices()  # F1 result, cached
    time_bytes = (time_now or int(time.time() * 1000)).to_bytes(8, "big")
    payload = f"{method}!{path}!{time_now}{animation_key}".encode()
    digest = hmac_sha256(animation_key.encode(), payload)
    selected = bytes(digest[i] for i in indices)
    return base64_url(time_bytes + selected).rstrip("=")
```

**Validation:** Pretī DevTools capture-iem 5+ pieprasījumiem (Search, UserTweetsAndReplies, vairāki dažādi paths). Bit-exact match obligāts.

### F3: Twikit integrācija (~1 diena)

Pārvietot `compute_tid` uz `src/x_tid.py`. Mainīt `patch_twikit.py` Patch 4:
- Ja `compute_tid` pieejams un indices cache uzturēts, lietot reālo TID
- Saglabāt stub fallback gadījumam, ja indices ekstrakcija neizdodas

### F4: Endpoints atjaunošana (~0.5 dienas)

- `src/x_mentions.py` atgriezties uz SearchTimeline endpoint (rollback no per-politician scan)
- `fetch_user_replies` paliek bez izmaiņām (kods jau strādās, tiklīdz X validē TID)
- Atjaunot mentions ingest log par 3rd-party mentions atjaunošanos

## Riska novērtējums

| Risks | Iespējamība | Sekas | Mitigācija |
|---|---|---|---|
| X pārvieto indices uz cita chunk | Augsta | F1 jāatkārto | F1 implementācija aprakstīta arhitektoniski, nevis hardcoded; refresh skripts |
| Jauns animation_key sources | Vidēja | F2 vairs nestrādā | Capture animation_key arī DevTools, fall-back mechanism |
| TLS fingerprint papildus | Zema | F3 nestrādā pat ar pareizu TID | Detect via 403 vs 404 — atšķirīgs simptoms |

## Atkarības

- Reverse-engineering speciālists vai vairāku dienu mērķtiecīgs darbs ar DevTools + chunk-walker
- Tests pret reāliem X capture-iem (operatoram jāuztur sample-pool)

## Apsvēršana

Šis nav prioritārs ja:
- Mentions ingest no per-politician scan ir pietiekama (90% tracked-to-tracked interakcijas)
- Replies coverage zudums neietekmē brief kvalitāti

Šis ir prioritārs ja:
- Sākam zaudēt nozīmīgu rhetorical signāla daļu
- 3rd-party kritika (žurnālisti, sabiedrība uz tracked politiķiem) kļūst kritiska atmiņa platformai
- Ja Patch 4 fallback nestrādā arī uz "lenient" endpoints (eskalācija)

## Status

NOT STARTED. Plan stub uzrakstīts 2026-05-04 kā pievienojums ikdienas audit sesijai. Eskalēt prioritāti, kad būs operacionāls iemesls.
