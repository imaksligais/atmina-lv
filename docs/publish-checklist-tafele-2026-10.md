# Izpētes tāfele + LZA + S-Baltic — publicēšana (tikai pēc operatora «jā»)

Divi bloki. **1. bloks** pārslēdz melnrakstus, renderē un pārbauda; tad operators skatās renderētās lapas pārlūkā. **2. bloks** (tikai pēc tam) apstiprina, komitē un publicē. Pirms 1. bloka: `[DATUMS]` divās vietās zemāk aizstāj ar publicēšanas dienu (piem., «26. oktobrī»). Ja publicē 28.10. vai vēlāk, vispirms abos rakstos sadaļā «Komentāru lūgumi» jānomaina «publicējām pirms termiņa» un jāieliek saņemtās atbildes.

## 1. bloks — sagatavot un parādīt

```powershell
$ErrorActionPreference = 'Stop'
if ((Get-Date).Date -ge [datetime]'2026-10-28') { throw 'Komentāru termiņš pagājis: vispirms labo «Komentāru lūgumi» abos rakstos.' }
Set-Location -LiteralPath 'E:\atmina'
$env:PYTHONUTF8 = '1'
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PATH = 'C:\Program Files\Git\bin;' + $env:PATH

@'
from pathlib import Path
from src.render._common.filters import _parse_frontmatter

for slug in (
    'lza-ieteikums-ekonomikas-instituts-2026',
    's-baltic-uzturesanas-atlaujas-2026',
    'saites-visvanati-2026',
):
    path = Path('content/analizes') / f'{slug}.md'
    text = path.read_text(encoding='utf-8')
    frontmatter, _ = _parse_frontmatter(text)
    assert frontmatter.get('draft') is True, path
    assert text.count('\ndraft: true\n') == 1, path
    path.write_text(text.replace('\ndraft: true\n', '\ndraft: false\n', 1), encoding='utf-8')
'@ | & '.venv/Scripts/python.exe' '-'
if ($LASTEXITCODE -ne 0) { throw 'Rakstu melnrakstu pārslēgšana neizdevās.' }

New-Item -ItemType Directory -Force -Path 'content/tafeles' | Out-Null
git mv -- 'docs/drafts/tafeles/visvanati-2026.yaml' 'content/tafeles/visvanati-2026.yaml'
if ($LASTEXITCODE -ne 0) { throw 'Tāfeles datu pārvietošana neizdevās.' }

@'
from pathlib import Path
import yaml

path = Path('content/tafeles/visvanati-2026.yaml')
text = path.read_text(encoding='utf-8')
assert yaml.safe_load(text)['draft'] is True
assert text.count('\ndraft: true\n') == 1
path.write_text(text.replace('\ndraft: true\n', '\ndraft: false\n', 1), encoding='utf-8')

def add_backlinks(path, items, note):
    assert '[DATUMS]' not in note, 'Aizstāj [DATUMS] ar publicēšanas dienu.'
    path = Path(path)
    text = path.read_text(encoding='utf-8')
    for item in items:
        assert item not in text, (path, item)
    start = text.index('<aside class="post-brief"')
    end = text.index('</aside>', start)
    text = text[:end].rstrip() + '\n' + '\n'.join(items) + '\n\n' + text[end:]
    text = text.rstrip() + '\n' + note + '\n'
    assert text.index(note) > text.index('\n## Labojumi'), path
    path.write_text(text, encoding='utf-8')

add_backlinks(
    'content/analizes/visvanati-pilsoniba-2026.md',
    [
        '- Kas sagatavoja ziņas LZA ieteikumam Divjas Kananas Višvanatas pilsonībai — [atsevišķā rakstā](/analizes/lza-ieteikums-ekonomikas-instituts-2026.html); portāls euresidencies.com un 50 000 € ieguldījumi — [S-Baltic rakstā](/analizes/s-baltic-uzturesanas-atlaujas-2026.html).',
        '- Visas saites vienā skatā — [Izpētes tāfele](/analizes/saites-visvanati-2026.html)',
    ],
    r'- 2026\. gada [DATUMS] pievienotas saites uz rakstiem par LZA ieteikumu un S-Baltic un uz izpētes tāfeli.',
)
add_backlinks(
    'content/analizes/kanans-visvanats-nopelni-2023.md',
    ['- Kas sagatavoja ziņas LZA ieteikumam viņa sievas pilsonībai — [Kas sagatavoja ziņas LZA ieteikumam?](/analizes/lza-ieteikums-ekonomikas-instituts-2026.html)'],
    r'- 2026\. gada [DATUMS] pievienota saite uz rakstu «Kas sagatavoja ziņas LZA ieteikumam?».',
)
'@ | & '.venv/Scripts/python.exe' '-'
if ($LASTEXITCODE -ne 0) { throw 'Tāfeles un Višvanatu raksta sagatavošana neizdevās.' }

& '.venv/Scripts/python.exe' 'scripts/lint_analysis.py' 'content/analizes/lza-ieteikums-ekonomikas-instituts-2026.md'
if ($LASTEXITCODE -ne 0) { throw 'LZA raksta valodas pārbaude neizdevās.' }
& '.venv/Scripts/python.exe' 'scripts/lint_analysis.py' 'content/analizes/s-baltic-uzturesanas-atlaujas-2026.md'
if ($LASTEXITCODE -ne 0) { throw 'S-Baltic raksta valodas pārbaude neizdevās.' }
& '.venv/Scripts/python.exe' 'scripts/lint_analysis.py' 'content/analizes/saites-visvanati-2026.md'
if ($LASTEXITCODE -ne 0) { throw 'Tāfeles ievadlapas valodas pārbaude neizdevās.' }

& '.venv/Scripts/python.exe' '-m' 'src.render' '--only=analizes,dashboard,static'
if ($LASTEXITCODE -ne 0) { throw 'Renderēšana neizdevās.' }

@'
from pathlib import Path
from urllib.parse import unquote, urlsplit
from bs4 import BeautifulSoup
from src.render._common.filters import _parse_frontmatter
from src.render.analyses import _validate_atradums
from src.tafele.model import load_board, validate_board

root = Path('output/atmina').resolve()
slugs = (
    'visvanati-pilsoniba-2026',
    'lza-ieteikums-ekonomikas-instituts-2026',
    's-baltic-uzturesanas-atlaujas-2026',
    'saites-visvanati-2026',
)
for slug in slugs:
    page = root / 'analizes' / f'{slug}.html'
    assert page.is_file(), page
    fm, body = _parse_frontmatter(Path('content/analizes', f'{slug}.md').read_text(encoding='utf-8'))
    assert not fm.get('draft'), slug
    _validate_atradums(slug, body)
    html = page.read_text(encoding='utf-8')
    if slug == 'saites-visvanati-2026':
        assert 'Saite nav pārkāpums.' in html, slug
    if slug in slugs[1:3]:
        soup = BeautifulSoup(html, 'html.parser')
        images = soup.select('main img')
        assert len(images) >= 2, (slug, len(images))
        sources = [img['src'] for img in images]
        for source in soup.select('main source[srcset]'):
            sources.extend(part.strip().split()[0] for part in source['srcset'].split(','))
        for src in sources:
            path = (page.parent / unquote(urlsplit(src).path)).resolve()
            assert path.is_relative_to(root) and path.is_file(), (slug, src)

board = load_board(Path('content/tafeles/visvanati-2026.yaml'))
assert not board.draft
validate_board(board, Path('content/analizes'), require_published=True)
soup = BeautifulSoup((root / 'analizes/saites-visvanati-2026.html').read_text(encoding='utf-8'), 'html.parser')
assert len(soup.select('.tf-book .tf-link')) == len(board.links)
assert len(soup.select('.tf-book .tf-entity')) == len(board.entities)
print('Pārbaudītas 4/4 lapas, abu rakstu attēli un pilna tāfeles datu kopa.')
'@ | & '.venv/Scripts/python.exe' '-'
if ($LASTEXITCODE -ne 0) { throw 'Lapu, attēlu vai tāfeles pārbaude neizdevās.' }

Start-Process 'output/atmina/analizes/lza-ieteikums-ekonomikas-instituts-2026.html'
Start-Process 'output/atmina/analizes/s-baltic-uzturesanas-atlaujas-2026.html'
Start-Process 'output/atmina/analizes/saites-visvanati-2026.html'
```

**STOP.** Operators izlasa trīs lapas (dators + telefons) un apstiprina attēlus. Tikai tad 2. bloks.

## 2. bloks — apstiprināt, komitēt, publicēt

```powershell
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'E:\atmina'
$env:PYTHONUTF8 = '1'
$env:PATH = 'C:\Program Files\Git\bin;' + $env:PATH

& '.venv/Scripts/python.exe' 'scripts/approve_publish.py' 'analizes/visvanati-pilsoniba-2026'
if ($LASTEXITCODE -ne 0) { throw 'Višvanatu raksta apstiprināšana neizdevās.' }
& '.venv/Scripts/python.exe' 'scripts/approve_publish.py' 'analizes/lza-ieteikums-ekonomikas-instituts-2026'
if ($LASTEXITCODE -ne 0) { throw 'LZA raksta apstiprināšana neizdevās.' }
& '.venv/Scripts/python.exe' 'scripts/approve_publish.py' 'analizes/s-baltic-uzturesanas-atlaujas-2026'
if ($LASTEXITCODE -ne 0) { throw 'S-Baltic raksta apstiprināšana neizdevās.' }
& '.venv/Scripts/python.exe' 'scripts/approve_publish.py' 'analizes/saites-visvanati-2026'
if ($LASTEXITCODE -ne 0) { throw 'Tāfeles apstiprināšana neizdevās.' }

git add -- 'content/analizes/lza-ieteikums-ekonomikas-instituts-2026.md' 'content/analizes/s-baltic-uzturesanas-atlaujas-2026.md' 'content/analizes/saites-visvanati-2026.md' 'content/analizes/visvanati-pilsoniba-2026.md' 'content/analizes/kanans-visvanats-nopelni-2023.md' 'content/tafeles/visvanati-2026.yaml' 'docs/drafts/tafeles/visvanati-2026.yaml'
# Pirms commit: wiki/CHANGELOG.md ieraksts (≤5 rindas) par izpētes tāfeles publicēšanu; git add arī to.
# Commit ziņu raksta failā: git commit -F <fails>

& 'C:\Program Files\Git\bin\bash.exe' 'scripts/deploy.sh'
if ($LASTEXITCODE -ne 0) { throw 'Publicēšana neizdevās.' }
```
