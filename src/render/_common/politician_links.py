"""Politiķa vārds raksta tekstā → saite uz profilu ar lodziņa datiem.

Tīra funkcija bez DB. Saiti saņem tikai izsaucēja padotie cilvēki, un tikai
PILNAIS vārds burtiski ar vārdu robežām — uzvārdu un locījumu meklēšanas nav
(T1). Saistīta tiek pirmā derīgā pieminēšana: ne `<a>`, virsraksta, `code`
vai `pre` iekšā. HTMLParser tikai atrod vietu; saite tiek iešūta oriģinālajā
virknē, tāpēc entītijas un pārējais HTML paliek burtiski.
"""

from __future__ import annotations

import html as _html
import re
from html.parser import HTMLParser
from typing import Any

_SKIP_TAGS = frozenset({"a", "h1", "h2", "h3", "h4", "h5", "h6", "code", "pre", "script", "style"})


class _TextFinder(HTMLParser):
    """Savāc (sākums, beigas, cilvēks) katram vārdam tā pirmajā derīgajā vietā."""

    def __init__(self, source: str, patterns: list[tuple[re.Pattern[str], dict[str, Any]]]) -> None:
        # convert_charrefs=False: teksts nāk gabalos līdz katrai entītijai,
        # un getpos() rāda tieši uz gabala sākumu oriģinālajā virknē.
        super().__init__(convert_charrefs=False)
        self._line_starts = [0] + [m.end() for m in re.finditer("\n", source)]
        self._todo = list(patterns)
        self._skip: list[str] = []
        self.hits: list[tuple[int, int, dict[str, Any]]] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        # Stekā tikai izslēgtie tagi — tukšie elementi (<br>) to nesabojā.
        if tag in _SKIP_TAGS:
            self._skip.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip:
            while self._skip and self._skip.pop() != tag:
                pass

    def handle_data(self, data: str) -> None:
        # Atribūtu vērtības (piem., href=".../ViktorsValainis/...") šeit nenonāk.
        if self._skip or not self._todo:
            return
        line, col = self.getpos()
        base = self._line_starts[line - 1] + col
        for item in list(self._todo):
            m = item[0].search(data)
            if m:
                self.hits.append((base + m.start(), base + m.end(), item[1]))
                self._todo.remove(item)


def _anchor(person: dict[str, Any], text: str, href_prefix: str) -> str:
    attrs = [
        ("class", "pol-link"),
        ("href", f"{href_prefix}{person['slug']}.html"),
        *((f"data-{k}", str(v)) for k, v in (person.get("data") or {}).items()),
    ]
    rendered = " ".join(f'{k}="{_html.escape(v, quote=True)}"' for k, v in attrs)
    return f"<a {rendered}>{text}</a>"


def link_politicians(
    html: str, people: list[dict[str, Any]], href_prefix: str = "../politiki/",
) -> tuple[str, dict[str, Any]]:
    """Iešuj `<a class="pol-link">` katra cilvēka pirmajā pieminēšanā.

    `people`: {name, slug, data: {data-* atslēga: vērtība}}. Atgriež HTML un
    report {resolved, linked: [slug], missing: [vārds]} — neatrasts vārds ir
    brīdinājums izsaucējam, ne izņēmums.
    """
    patterns = [
        (re.compile(rf"(?<!\w){re.escape(p['name'])}(?!\w)"), p) for p in people if p.get("name")
    ]
    finder = _TextFinder(html, patterns)
    finder.feed(html)
    finder.close()
    out = html
    for start, end, person in sorted(finder.hits, key=lambda h: h[0], reverse=True):
        out = out[:start] + _anchor(person, out[start:end], href_prefix) + out[end:]
    linked = {id(h[2]) for h in finder.hits}
    report = {
        "resolved": len(people),
        "linked": [h[2]["slug"] for h in sorted(finder.hits, key=lambda h: h[0])],
        "missing": [p.get("name") or p.get("slug") for p in people if id(p) not in linked],
    }
    return out, report
