# Saites tab — klikšķis = fokus uz kartiņu

**Datums:** 2026-05-02
**Skartās lapas:** `politiki/{slug}.html` (individuālie politiķu profili) — Saites tab
**Skartās kartiņas:** Uzbrukumi / Spriedzes / Atbalsts kartiņas zem mini-grafa

## Problēma

Individuālā profila Saites tabā mini-grafs (`templates/politician.html.j2:439–455`) parāda līdz 8 saistīto politiķu mezglus, katrs ietīts `<a xlink:href="../politiki/{slug}.html">`. Klikšķis uz mezgla = tūlītēja navigācija uz tā politiķa profilu. Divi UX defekti:

1. **Mezglos nav vārdu redzami.** Tikai krāsainas aplis ar `<title>` browser-tooltipu (uz mobilā nav). Lietotājs klikšķē "akli" — nezina, kurš ir kurš, kamēr nav teleportējies.
2. **Klikšķis = pēkšņa navigācija bez konteksta.** Pat ja vārds būtu redzams, klikšķis aizved prom no šī profila pirms lietotājs ir izlasījis, KĀPĒC šī saite eksistē (kāds bija uzbrukums/spriedze/atbalsts, par kādu tēmu, kad).

## Mērķis

Klikšķis uz mezgla aizved lietotāju uz **eksistējošo saites kartiņu zem grafa** ar vienlaidu scroll un īsu vizuālu highlight, nevis prom no lapas. Vārdu etiķetes paliek redzamas zem mezgliem. Atvērt cita politiķa profilu paliek iespējams kā skaidra, atsevišķa darbība — poga katrā kartiņā.

Nulle JS. Native `:target` + smooth-scroll + URL fragments.

## Uzvedība

1. Lietotājs atver Saites tabu un redz mini-grafu — katrs neighbor mezgls ar vārda etiķeti zem apļa.
2. Klikšķis (vai Tab + Enter) uz neighbor mezgla → URL maina uz `#saites-{pid}` → browser smooth-scrollē uz attiecīgo kartiņu sarakstā zem grafa → kartiņa īsi izgaismojas (~2s subtle background flash).
3. Kartiņa parāda pilnu kontekstu: tipa kategorija (Uzbrukums/Spriedze/Atbalsts), tēma, datums, apraksts, avota saite un poga **"Skatīt profilu →"** ar saiti uz `politiki/{other_slug}.html`.
4. Lietotājs grib uz profilu — nospiež pogu. Browser back-button atgriež uz iepriekšējo URL stāvokli (anchor scroll position vai ārpus profila).

**Centra mezgls** (pats politiķis) paliek bez `<a>` — nav klikšķams, ir tikai vizuāls fokuss.

**Klaviatūras navigācija:** mezgli ir iekšā `<a>` tagā, kas ir nativi fokusējams (Tab) un aktivējams (Enter). Nav vajadzīgs `tabindex` vai `role`.

**Mobile:** tap = klikšķis, viss strādā tāpat (`<a>` ir nativs).

## Tehniskā realizācija

### Arhitektūras princips

Nulle JavaScript. Visa interakcija notiek caur native browser primitīvus: `<a href="#fragment">`, `:target` CSS pseudo-class, `scroll-behavior: smooth` (jau ieslēgts globāli — `assets/style.css:49`). Datu plūsma — Jinja render-time, ne runtime.

### Backend delta — `src/render/politicians.py`

Funkcija `_fetch_saites_for_profile` (`politicians.py:220–287`) jāpaplašina divos punktos:

**1. Katras saites kartiņas dictā pievieno `other_pid`, `other_slug`, `is_anchor`:**

`anchored_pids` ir lokāls funkcijas state — fresh komplektā katram `_fetch_saites_for_profile` izsaukumam, tāpēc starp dažādu politiķu profilu renderēšanu nav noplūdes.

```python
# Pseidokods Pjūtonā — strukturāla izmaiņa, ne literāla
anchored_pids: set[int] = set()
def _annotate_card(t: dict, current_pid: int) -> dict:
    if t.get("source_pid") == current_pid:
        other_pid = t.get("target_pid")
        other_name = t.get("target_name")
    else:
        other_pid = t.get("source_pid")
        other_name = t.get("source_name")
    is_anchor = other_pid is not None and other_pid not in anchored_pids
    if is_anchor:
        anchored_pids.add(other_pid)
    return {
        **t,
        "other_pid": other_pid,
        "other_slug": _slugify(other_name) if other_name else "",
        "is_anchor": is_anchor,
    }

uzbrukumi = [_annotate_card(t, pid) for t in uzbrukumi]
spriedzes = [_annotate_card(t, pid) for t in spriedzes]
atbalsts  = [_annotate_card(t, pid) for t in atbalsts]
```

Anotācijas kārtība — Uzbrukumi → Spriedzes → Atbalsts. Pirmā kartiņa pārim (Lapsa↔Čakša) saņem `is_anchor=True`. Tas konsistenti virza klikšķi uz "skaļāko" attiecību tipu, ja viens pāris parādās vairākos sarakstos.

**2. Mini-grafa neighbors saraksts paliek nemainīts.** Mezgla `pid` jau pieejams kā `n.pid` template — to izmantosim klikšķa `href` ģenerēšanā.

Nekādas datu paplašināšanas saites detaļām (topic, description, date, source_url) — visa info jau ir kartiņās. Spec atklāti noraida B varianta detail-card duplikāciju.

### Markup delta — `templates/politician.html.j2`

**Mini-grafa mezgli (`templates/politician.html.j2:449–454`)** — divas izmaiņas:

```html
{# Esošais (line 449-454) #}
<a xlink:href="../politiki/{{ n.slug }}.html">
  <circle cx="{{ n.x }}" cy="{{ n.y }}" r="9" fill="{{ n.party_color }}" stroke="#fff" stroke-width="1.5"/>
  <title>{{ n.name }} ({{ n.tension_type }})</title>
</a>

{# Pēc izmaiņām #}
<a xlink:href="#saites-{{ n.pid }}" aria-label="{{ n.name }} ({{ n.tension_type }}) — skatīt detaļas">
  <circle cx="{{ n.x }}" cy="{{ n.y }}" r="9" fill="{{ n.party_color }}" stroke="#fff" stroke-width="1.5"/>
  <title>{{ n.name }} ({{ n.tension_type }})</title>
</a>
<text x="{{ n.x }}" y="{{ n.y + 22 }}" text-anchor="middle" font-size="9"
      fill="var(--text-muted)" class="saites-node-label">{{ n.name.split()[0] }}</text>
```

Vārda etiķete: pirmais vārds (kā centra mezglā), zem apļa par 22px. Mazs font (9px), jo viewBox ir 400×280 un mezgli ir tuvu — pilna vārda izmērs varētu pārklāties ar kaimiņu.

**Saites kartiņas (`templates/politician.html.j2:458–507`)** — katrai no trim sekcijām (Uzbrukumi/Spriedzes/Atbalsts) viens un tas pats pattern. Diff vienai (atkārtot trim):

```html
{# Pirms (line 462) #}
<div class="card" style="margin-bottom:0.5rem;">

{# Pēc #}
<div class="card saites-card{% if t.is_anchor %} saites-card-anchor{% endif %}"
     {% if t.is_anchor %}id="saites-{{ t.other_pid }}"{% endif %}
     style="margin-bottom:0.5rem;">
```

Un kartiņas apakšā, blakus eksistējošajam `Avots ↗` linkam:

```html
{% if t.other_slug %}
<a href="../politiki/{{ t.other_slug }}.html"
   class="saites-card-profile-btn"
   style="font-size:0.8rem; margin-left:0.5rem;">Skatīt profilu →</a>
{% endif %}
```

`commentary_about` un `vote_alignment_top/bottom` sekcijas — **netiek anotētas**. Tās nav saistītas ar mini-grafa mezgliem (commentators nav mezgli; alignment ir tikai deputiem un parāda procentu, ne tension-style relāciju).

### CSS delta — `assets/style.css`

Pievieno aiz eksistējošā saites bloka (~rinda 1840):

```css
/* Saites tab — anchor highlight + node labels (B-lite) */
.saites-card-anchor:target {
  animation: saites-card-flash 2s ease-out;
  scroll-margin-top: 80px;  /* under sticky .nav (assets/style.css:82) */
}

@keyframes saites-card-flash {
  0%   { background-color: rgba(255, 215, 0, 0.18); box-shadow: 0 0 0 2px rgba(255, 215, 0, 0.35); }
  100% { background-color: transparent;            box-shadow: 0 0 0 0 transparent; }
}

@media (prefers-reduced-motion: reduce) {
  .saites-card-anchor:target { animation: none; background-color: rgba(255, 215, 0, 0.10); }
}

.saites-node-label { pointer-events: none; user-select: none; }
.mini-saites-graph a:hover circle { stroke-width: 2.5; cursor: pointer; }
.mini-saites-graph a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
```

`scroll-margin-top` nodrošina, ka pēc anchor scroll kartiņa neaiziet zem sticky `.nav` (60–80px augsta — `assets/style.css:82–89`).

`prefers-reduced-motion` — atstāj statisku gaišu fonu bez animācijas, lai lietotājam ar samazinātu kustību joprojām redz, kura kartiņa tika atlasīta.

### JavaScript

Nav. Tas ir patiesais B-lite pievilcības punkts — visa interakcija ir DOM + CSS native.

## Pieejamība

- **Klaviatūra:** `<a>` ir nativi Tab-fokusējams un Enter-aktivējams. SVG iekšā strādā tāpat kā ārpus.
- **Aria:** `aria-label="{Vārds} ({tipa kategorija}) — skatīt detaļas"` uz mezgla `<a>`. Nav `aria-live` vajadzīgs — kartiņa, uz ko scroll, jau ir DOM-redzama.
- **Reduced motion:** flash animācija nomainīta uz statisku highlight (skat. CSS).
- **Focus indikators:** `:focus-visible` kontūra uz mezgla.
- **Centra mezgls** — nav `<a>`, nav fokusējams. Korekti, jo nav darbības, ko aktivēt.

## Verifikācija

1. `bash scripts/check.sh` — ruff + pytest + render smoke joprojām paiet.
2. `python -c "from src.render import generate_public_site; generate_public_site()"` — output/atmina ģenerējas bez kļūdām.
3. `python serve.py` un manuāli pārbauda profilā ar saitēm (piem., Lato Lapsa — tā ir skicas piemērs):
   - Mezgliem redzami vārdu etiķetes.
   - Klikšķis uz mezgla → URL kļūst `#saites-{pid}` → smooth-scroll uz pirmo kartiņu ar to pid → kartiņa flash-highlight ~2s → animācija beidzas.
   - Kartiņā redzama "Skatīt profilu →" poga.
   - Klikšķis uz pogas → atver `politiki/{other_slug}.html`.
   - Back-button atgriež uz anchor stāvokli, ne prom no lapas.
4. Profilā ar 0 saitēm — mini-grafs joprojām nerenderējas (eksistējošais `{% if saites_data.mini_graph.neighbors %}` guard).
5. Profilā ar vairākām saites kategorijām vienam pārim (uzbrukums + spriedze) — `is_anchor=True` tikai pirmajai (uzbrukumam), klikšķis aizved tur. Spriedzes kartiņa redzama tieši zem.
6. Klaviatūra: Tab uz mini-grafa mezglu (`:focus-visible` outline) → Enter → tas pats anchor scroll + flash.
7. DevTools mobile responsive (375×812): tap uz mezgla scrollē uz kartiņu, animācija strādā, profila poga klikšķama ar pirkstu.
8. `prefers-reduced-motion: reduce` (DevTools rendering panel) — flash nomainās uz statisku gaišu fonu.

## Scope disciplīna (YAGNI)

**Izslēgts no šī spec:**
- Atsevišķa detail-kartiņa augšā pie grafa (B varianta bloat — info jau eksistē kartiņās zem).
- JS-vadīts mezgla highlight, kad kartiņa ir aktīva (zaudē "0 JS" princips; kartiņas highlight pietiekams).
- Multi-relation chips kartiņās ("+1 spriedze par X") — sarakstos visas saites jau redzamas atsevišķi.
- ESC / outside-click deselect handlers — nav state, ko deselect.
- Animācija mezglu radius/opacity izmaiņām pie atlases — nav state.
- Detail-kartiņas saturs `commentary_about` un `vote_alignment` sekcijām — nav saistītas ar mini-grafa mezgliem.
- URL hash sync uz citiem komponentiem (filters, etc.) — out of scope.
- Mini-grafa pārstrukturēšana uz spēka-grafu (force-directed) — pilnais grafs jau ir `saites.html`; mini-grafs paliek static SVG.

## Riski un nezināmie

- **Sticky nav augstums** var atšķirties pēc viewport platuma (mobile vs desktop). `scroll-margin-top: 80px` ir konservatīva vērtība — ja mobile nav ir mazāks, anchor parādīsies nedaudz zem nav, kas ir labāk nekā paslēpts aiz tā.
- **Multiple anchors edge case** — ja viens un tas pats `pid` parādās gan uzbrukumā, gan spriedzē, gan atbalstā, anchor iet uz pirmo (uzbrukumam). Nezūd info, jo pārējie ieraksti redzami tieši zem savā sekcijā.
- **First-name only labels** — diviem deputātiem ar to pašu vārdu (piem., divi Andri) etiķete būs neviennozīmīga. Pieņemamas izmaksas mazam grafam (max 8); tooltip joprojām dod pilnu vārdu. Ja problēma materializēsies, var pārslēgt uz "Andris B." formātu.
- **Atkārtots klikšķis uz tā paša mezgla** — URL fragment jau ir `#saites-{pid}`, tāpēc browser neaktivē `:target` no jauna un flash animācija nesāk no jauna. Vizuāli no-op. Pieņemami — pirmais klikšķis jau atklāja info, atkārtots nav nepieciešams. Ja kādreiz vajadzīgs re-flash, var pievienot triviālu JS hash-clear hack, bet šis spec to atklāti neietver.
