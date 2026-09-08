# Logo drafti (NEPUBLICĒTI)

Drafti dzīvo šeit, nevis `assets/`, jo `assets/` tiek kopēts uz `output/` un deployots.
Lai apskatītu: atver `preview.html` pārlūkā.

| Fails | Koncepts |
|---|---|
| `01-lupa-fingerprint-refined.svg` | Pašreizējā logo uzlabota versija — tā pati lūpa + pirkstu nospiedums, tās pašas krāsas (#37474F / #B71C1C), bet tīra ģeometrija. Drop-in aizvietotājs (viewBox `0 0 64 64`). |
| `02-lupa-fingerprint-badge.svg` | Tas pats motīvs uz pilnas flīzes — avatariem (X, Telegram), OG kartēm. |
| `03-pretruna-loop.svg` | Divas pretējas bultas aplī — atmina (cikls) + pretrunas. Abstraktāks, bez lūpas. |
| `04-lupa-quotes.svg` | Lupa + latviskās pēdiņas „ “ — par to, kas tika teikts. Drafts ar serif fontu; finālam teksts jāpārveido kontūrās. |
| `05-wordmark.svg` | Horizontāls lockup (ikona + "atmina.lv") galvenei / OG. Tumšam fonam — gredzens #90A4AE, jo #37474F uz #0d1014 ir par tumšu. |

## Favicon kandidāti (16px)

Problēma: 01 nospieduma tievās līnijas 16px saplūst. Risinājumi:

| Fails | Koncepts |
|---|---|
| `06-favicon-fingerprint-simple.svg` | Tas pats motīvs, reducēts: punkts + 2 biezi loki. Saglabā nospieduma ideju. |
| `07-favicon-lens-dot.svg` | Lūpa + sarkans kodols ("fokuss"). Vislabāk salasāms 16px. |
| `08-favicon-lens-quote.svg` | Lūpa + viena bieza pēdiņa „. |
| `09-favicon-letter-a.svg` | Vienstāva burta 'a' monogramma + sarkans kodols. |

Ieteikums: galvenei 01 (vai 05), faviconam 06 vai 07 — viena faila nav jākalpo visiem izmēriem.

Ja izvēlies kādu, finālam: nokopē uz `assets/logo.svg` (vai `favicon.svg`), pārbaudi
`templates/base.html.j2` nav/OG atsauces, tad `generate_public_site()` + deploy.
