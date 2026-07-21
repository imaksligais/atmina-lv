# Telegram brief

Kondensēts dienas pārskats publicēšanai Telegram kanālā [@atminalv](https://t.me/atminalv) (chat_id `-1003790492191`). Lietošana — manuāla, ārpus dienas rutīnas.

## Funkcija

`src.briefs.generate_telegram_brief(date=None, fmt='html', max_politicians=5)` — atgriež formatētu brief teksta virkni (~2000-3500 chars, < 4096 limita).

Sastāvdaļas:

1. **Header** — datums, `📰 Atmina dienas pārskats — DD.MM.YYYY`
2. **Stats** — dokumentu skaits, jaunās pozīcijas, pretrunu skaits
3. **Kopsavilkums** — `## Galvenais` paragrāfs no pilnā dienas pārskata, sadalīts bullet-pointos
4. **Aktīvākie politiķi** — top N (default 5), ar partijas tag, pozīciju skaitu, augstākās salience pozīcijas anotāciju, avota saiti
5. **Šodien izsludināts** — līdz 6 promulgēti tiesību akti no `vestnesis.lv` (Latvijas Vēstnesis JL), kuriem ir vismaz viena tracked-politician junction. Filtrēts caur `relationship_type` lai izlaistu municipālos saistošos noteikumus, izsoles, mantojumu ziņas. Sekcija izlaista, ja nav neviena atbilstoša akta. Sk. [[operacijas#Latvijas Vēstnesis (manuāla plūsma)|operacijas.md]].
6. **Pretrunas** — tikai ja šajā dienā detected jaunas (citādi sekcija pilnībā izlaista)
7. **Pilnais pārskats** — saite uz `atmina.lv/blog/YYYY-MM-DD.html`

## Formāti

- `fmt='html'` (default) — Telegram Bot API `parse_mode='HTML'`. Lietot ar `sendMessage` no Bot API tieši.
- `fmt='markdownv2'` — `parse_mode='MarkdownV2'`. Visi speciālie simboli auto-escapēti.

## CLI

```bash
python scripts/telegram_brief.py            # šodien, HTML
python scripts/telegram_brief.py 2026-04-18 # konkrēts datums, HTML
python scripts/telegram_brief.py --md2      # MarkdownV2
```

Izdrukā stdout (copy-paste vai pipe). `[N chars / 4096 limit, fmt=...]` paziņojums uz stderr.

## Postēšana kanālā

Bot tokens: `~/.claude/channels/telegram/.env` (TELEGRAM_BOT_TOKEN). MCP `reply` rīks neatklāj `format` parametru savā shēmā, tāpēc oficiālā postēšanā lietot `curl` tieši:

```bash
TOKEN="$(grep TELEGRAM_BOT_TOKEN ~/.claude/channels/telegram/.env | cut -d= -f2)"
CHAT="-1003790492191"
IMG="output/images/briefs/YYYY-MM-DD-dienas-parskats-XXXX.png"

# 1. Featured image augšā
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendPhoto" \
  -F "chat_id=${CHAT}" -F "photo=@${IMG}"

# 2. MarkdownV2 teksts apakšā
python scripts/telegram_brief.py 2026-04-18 --md2 > /tmp/brief.txt
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT}" \
  --data-urlencode "parse_mode=MarkdownV2" \
  --data-urlencode "text@/tmp/brief.txt"
```

Telegram nesalipina text + foto vienā ziņā (sendPhoto caption limits 1024 chars, brief parasti pārsniedz). Tāpēc 2 atsevišķi posti — featured image kā pirmais, teksts kā otrais.

> **NELIETO** MCP `mcp__plugin_telegram_telegram__reply` ar `files`+`text` kombinēti oficiālajiem content drops — tas sūta divas atsevišķas ziņas (image + text), neatklāj `parse_mode`, un nedod caption-uz-image. Lieto `curl` tieši (augšā).

Kļūdaini sūtītu ziņu dzēš:

```bash
curl -s "https://api.telegram.org/bot${TOKEN}/deleteMessage?chat_id=${CHAT}&message_id=<MSG_ID>"
```

## Atkarības

- Pilnam dienas pārskatam jābūt `context_notes` ar `note_type='daily_brief'` un `topic='dienas pārskats YYYY-MM-DD'` — `generate_telegram_brief` velk `## Galvenais` paragrāfu no šī ieraksta.
- Ja pilna brief nav (rutīna nav pabeigta), funkcija atgriež īsāku versiju bez kopsavilkuma sekcijas.
- Featured image nav obligāts, bet uzlabo kanāla noformējumu.

## Nav daļa no rutīnas

Šī funkcija netiek izsaukta automātiski no `daily_routine`. Lietot manuāli, kad gribi publicēt kanālā.
