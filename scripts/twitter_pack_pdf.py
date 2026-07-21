"""
Compile the @atmina_lv Twitter pack into a single PDF for review.

Each page: tweet image preview + copy + alt-text + posting notes.
Articles get hero image + body across one or two pages.

Generates:
  output/twitter-pack-2026-04-26.pdf
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.backends.backend_pdf import PdfPages

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

ROOT = Path(__file__).resolve().parent.parent
SOCIAL_DIR = ROOT / "output" / "images" / "social"
PDF_OUT = ROOT / "output" / "twitter-pack-2026-04-26.pdf"

CREAM = "#F2EBDC"
INK = "#1A1F3A"
INK_SOFT = "#3A3F5A"
ACCENT_RED = "#8B1A1A"
ACCENT_OCHRE = "#B8860B"

rcParams["font.family"] = "serif"
# DejaVu Serif first ensures arrow glyphs (→ ↓ ↑) render; Georgia for fallback
# would lack U+2192 et al. Listing Georgia second still gets used for chars
# where DejaVu lacks distinct LV diacritic styling — both have full LV.
rcParams["font.serif"] = ["DejaVu Serif", "Georgia"]

PAGE_W, PAGE_H = 8.27, 11.69  # A4 portrait, inches


def _new_page(pdf: PdfPages) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(PAGE_W, PAGE_H), dpi=120)
    fig.patch.set_facecolor(CREAM)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_facecolor(CREAM)
    ax.set_axis_off()
    return fig, ax


def _save_page(pdf: PdfPages, fig: plt.Figure) -> None:
    pdf.savefig(fig, facecolor=CREAM, bbox_inches=None)
    plt.close(fig)


def _wrap(text: str, width: int) -> str:
    # Preserve paragraph breaks
    paragraphs = text.split("\n")
    out: list[str] = []
    for p in paragraphs:
        if not p.strip():
            out.append("")
            continue
        out.extend(textwrap.wrap(p, width=width, break_long_words=False))
    return "\n".join(out)


def page_cover(pdf: PdfPages) -> None:
    fig, ax = _new_page(pdf)
    ax.text(
        50, 75, "atmina.lv",
        ha="center", va="center",
        fontsize=42, color=INK_SOFT, family="serif", style="italic",
    )
    ax.text(
        50, 65, "Twitter Pack",
        ha="center", va="center",
        fontsize=68, fontweight="bold", color=INK, family="serif",
    )
    ax.plot([20, 80], [56, 56], color=INK, linewidth=1.4)
    ax.text(
        50, 50, "6 tweets · 2 long-form articles",
        ha="center", va="center",
        fontsize=20, color=INK, family="serif", style="italic",
    )
    ax.text(
        50, 44,
        "3 data-viz · 3 designer ilustrācijas",
        ha="center", va="center",
        fontsize=16, color=INK_SOFT, family="serif",
    )

    # Bottom block — meta
    ax.plot([20, 80], [22, 22], color=INK, linewidth=0.8, alpha=0.6)
    ax.text(
        50, 17,
        "Sagatavots cilvēka pārskatīšanai pirms publicēšanas.",
        ha="center", va="center",
        fontsize=12, color=INK, family="serif", style="italic",
    )
    ax.text(
        50, 13,
        "Verified konts → 280 zīmju limits nav saistošs.",
        ha="center", va="center",
        fontsize=11, color=INK_SOFT, family="serif",
    )
    ax.text(
        50, 8,
        "2026-04-26",
        ha="center", va="center",
        fontsize=11, color=INK_SOFT, family="serif",
    )
    _save_page(pdf, fig)


def page_index(pdf: PdfPages) -> None:
    fig, ax = _new_page(pdf)
    ax.text(
        10, 92, "Saturs",
        fontsize=36, fontweight="bold", color=INK, family="serif",
    )
    ax.plot([10, 90], [88, 88], color=INK, linewidth=1.0)

    items = [
        ("Tweet 1 — atmina.lv skaitļos", "data-viz · stats poster"),
        ("Tweet 2 — Mediju aktīvākie pēdējās 7 dienās", "data-viz · bar chart"),
        ("Tweet 3 — Par ko runā Latvijas politiskā sfēra", "data-viz · bar chart"),
        ("Tweet 4 — Kāpēc atmina.lv? (Article A hook)", "designer · ilustrācija"),
        ("Tweet 5 — Kā strādā atmina.lv (Article B hook)", "designer · ilustrācija"),
        ("Tweet 6 — Pretruna ≠ viedokļa maiņa", "designer · ilustrācija"),
        ("Article A — Kāpēc mēs izveidojām atmina.lv", "long-form · ~750 v."),
        ("Article B — Kā strādā atmina.lv (bez tehniskā žargona)", "long-form · ~750 v."),
        ("Posting checklist + secība", "operatoram"),
    ]

    y = 80
    for title, sub in items:
        ax.text(
            10, y, title,
            fontsize=14, fontweight="bold", color=INK, family="serif",
        )
        ax.text(
            10, y - 3, sub,
            fontsize=11, color=INK_SOFT, family="serif", style="italic",
        )
        y -= 8

    _save_page(pdf, fig)


def page_tweet(
    pdf: PdfPages,
    *,
    number: int,
    title: str,
    image_path: Path,
    copy: str,
    alt_text: str,
    notes: str | None = None,
) -> None:
    fig, ax = _new_page(pdf)

    # Header
    ax.text(
        10, 95, f"Tweet {number}",
        fontsize=14, color=INK_SOFT, family="serif", style="italic",
    )
    ax.text(
        10, 91, title,
        fontsize=22, fontweight="bold", color=INK, family="serif",
    )
    ax.plot([10, 90], [88, 88], color=INK, linewidth=0.8)

    # Image preview
    if image_path.exists():
        img = mpimg.imread(image_path)
        # Place image as inset axes — center horizontally, top portion of page
        ax_img = fig.add_axes((0.10, 0.50, 0.80, 0.30))
        ax_img.imshow(img)
        ax_img.set_axis_off()

    # Copy block
    ax.text(
        10, 46, "Copy:",
        fontsize=12, fontweight="bold", color=INK, family="serif",
    )
    ax.text(
        10, 43, _wrap(copy, 78),
        fontsize=11, color=INK, family="serif",
        va="top",
    )

    # Alt-text
    ax.text(
        10, 19, "Alt-text:",
        fontsize=11, fontweight="bold", color=INK_SOFT, family="serif",
    )
    ax.text(
        10, 16, _wrap(alt_text, 90),
        fontsize=9, color=INK_SOFT, family="serif", style="italic",
        va="top",
    )

    # Notes
    if notes:
        ax.text(
            10, 7, _wrap(notes, 90),
            fontsize=9, color=ACCENT_RED, family="serif",
            va="top",
        )

    # Footer
    ax.text(
        50, 2, "atmina.lv · Twitter Pack",
        ha="center", va="center",
        fontsize=8, color=INK_SOFT, family="serif", style="italic",
    )
    _save_page(pdf, fig)


def page_article(
    pdf: PdfPages,
    *,
    label: str,
    title: str,
    hero_path: Path,
    body: str,
) -> list:
    """Render an article across as many pages as needed."""
    # Page 1: hero (which carries the visual title) + small label + first chunk
    fig, ax = _new_page(pdf)
    ax.text(
        10, 96, f"{label} · long-form",
        fontsize=11, color=INK_SOFT, family="serif", style="italic",
    )
    ax.plot([10, 90], [93, 93], color=INK, linewidth=0.6, alpha=0.5)

    if hero_path.exists():
        img = mpimg.imread(hero_path)
        ax_img = fig.add_axes((0.10, 0.62, 0.80, 0.26))
        ax_img.imshow(img)
        ax_img.set_axis_off()

    # Article title rendered as text below the hero
    ax.text(
        10, 56, title,
        fontsize=18, fontweight="bold", color=INK, family="serif",
    )
    ax.plot([10, 90], [52, 52], color=INK, linewidth=0.6, alpha=0.5)

    # Split body into character-budget-sized chunks per page.
    # First page sits below title (~1300 chars fit). Continuations: ~3800 chars.
    paragraphs = body.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    budget = 1300
    for p in paragraphs:
        plen = len(p) + 1  # newline
        if current_len + plen > budget and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
            budget = 3800
        current.append(p)
        current_len += plen
    if current:
        chunks.append("\n".join(current))

    # First chunk on the hero page (below title divider, ends ~y=10 above footer)
    body_text = _wrap(chunks[0], 88)
    ax.text(
        10, 49, body_text,
        fontsize=9.5, color=INK, family="serif",
        va="top",
    )

    ax.text(
        50, 3, "atmina.lv · Twitter Pack",
        ha="center", va="center",
        fontsize=8, color=INK_SOFT, family="serif", style="italic",
    )
    _save_page(pdf, fig)

    # Subsequent pages: text only
    for i, chunk in enumerate(chunks[1:], start=2):
        fig, ax = _new_page(pdf)
        ax.text(
            10, 95, f"{label} · turpinājums (lpp. {i})",
            fontsize=11, color=INK_SOFT, family="serif", style="italic",
        )
        ax.plot([10, 90], [92, 92], color=INK, linewidth=0.6)
        ax.text(
            10, 88, _wrap(chunk, 88),
            fontsize=9.5, color=INK, family="serif",
            va="top",
        )
        ax.text(
            50, 3, "atmina.lv · Twitter Pack",
            ha="center", va="center",
            fontsize=8, color=INK_SOFT, family="serif", style="italic",
        )
        _save_page(pdf, fig)

    return chunks


def page_checklist(pdf: PdfPages) -> None:
    fig, ax = _new_page(pdf)
    ax.text(
        10, 92, "Posting checklist",
        fontsize=30, fontweight="bold", color=INK, family="serif",
    )
    ax.plot([10, 90], [88, 88], color=INK, linewidth=1.0)

    sections = [
        (
            "Pirms posta",
            [
                "Pārbaudi, ka @atmina_lv nav verified-bezjēgas anglicismi (\"top-5\", \"claim\")",
                "Pārbaudi, ka URL prefiksi atbilst output/atmina/ struktūrai",
                "Pievieno alt-text katram attēlam (a11y obligāts)",
                "Pārbaudi, ka tweet copy pirmais vārds NAV @handle (atbalss feedback_x_no_leading_at.md)",
            ],
        ),
        (
            "Ieteicamā secība",
            [
                "Diena 1 — Tweet 1 (skaitļi) → spēcīgs hook par platformu",
                "Diena 2 — Article A + Tweet 4 → \"kāpēc\" launch story",
                "Diena 3 — Article B + Tweet 5 → \"kā strādā\"",
                "Diena 4 — Tweet 2 (top 7d) → kontaktpunkts ar konkrētiem cilvēkiem",
                "Diena 5 — Tweet 3 (tēmas) → aicinājums izpētīt",
                "Diena 6 — Tweet 6 (pretrunas) → reklāmu tipam, kas vienmēr seko atmina.lv",
            ],
        ),
        (
            "Pēc posta",
            [
                "Sagaidi sākotnējās reakcijas → uzraksti reply ar svarīgāko follow-up domu",
                "Ja kļūda atrasta — labosim atklātā komentārā, neslēpsim",
                "Ja kāds politiķis iebilst — atbildot, atsaucamies tieši uz avotu",
            ],
        ),
    ]

    y = 80
    for heading, bullets in sections:
        ax.text(
            10, y, heading,
            fontsize=14, fontweight="bold", color=INK, family="serif",
        )
        y -= 5
        for b in bullets:
            ax.text(
                12, y, "·",
                fontsize=12, color=INK, family="serif",
            )
            ax.text(
                14, y, _wrap(b, 80),
                fontsize=10, color=INK, family="serif",
                va="center",
            )
            # Move down by line count (rough — assume 1-2 lines)
            line_count = max(1, (len(b) // 80) + 1)
            y -= 3 + (line_count - 1) * 2.5
        y -= 4

    ax.text(
        50, 2, "atmina.lv · Twitter Pack",
        ha="center", va="center",
        fontsize=8, color=INK_SOFT, family="serif", style="italic",
    )
    _save_page(pdf, fig)


# -----------------------------------------------------------------------
# Content payload
# -----------------------------------------------------------------------

TWEETS = [
    {
        "number": 1,
        "title": "atmina.lv skaitļos",
        "image": SOCIAL_DIR / "tweet1-skaitlos.png",
        "copy": (
            "atmina.lv skaitļos:\n\n"
            "156 politiķi\n"
            "1 423 publiskās pozīcijas\n"
            "139 Saeimas balsojumi\n"
            "11 apstiprinātas pretrunas\n"
            "14 647 dokumenti\n\n"
            "Visi avoti pārbaudāmi. → atmina.lv"
        ),
        "alt": (
            "Editorial poster ar atmina.lv statistiku: 156 politiķi, "
            "1 423 pozīcijas, 139 Saeimas balsojumi, 11 pretrunas, 14 647 "
            "dokumenti. Pretrunas iezīmētas ar tumši sarkanu akcentu."
        ),
        "notes": None,
    },
    {
        "number": 2,
        "title": "Mediju aktīvākie pēdējās 7 dienās",
        "image": SOCIAL_DIR / "tweet2-top7d.png",
        "copy": (
            "Mediju aktīvākie pēdējās 7 dienās — pēc publiskām pozīcijām.\n\n"
            "Skaitām katru izteikumu, kas no medijiem nonāk politiskajā "
            "telpā. Pilns saraksts un katra izteikuma avots → "
            "atmina.lv/personas.html"
        ),
        "alt": (
            "Bar chart: top 8 politiķi pēc mediju izteikumu skaita "
            "pēdējās 7 dienās. Andris Kulbergs (18), Alvis Hermanis (15), "
            "Andris Sprūds (12), Baiba Braže (12), Guntars Vītols (11), "
            "Evika Siliņa (11), Lato Lapsa (9), Mārtiņš Krusts (9)."
        ),
        "notes": "Skaitļi atjaunoti datu ievades dienā. Dati svaigi.",
    },
    {
        "number": 3,
        "title": "Par ko runā Latvijas politiskā sfēra",
        "image": SOCIAL_DIR / "tweet3-tematu-top.png",
        "copy": (
            "Par ko Latvijas politiskā sfēra runā medijos visvairāk:\n\n"
            "1. Aizsardzība un drošība\n"
            "2. airBaltic\n"
            "3. Koalīcija un partijas\n"
            "4. Ukraina un Krievija\n"
            "5. Valsts pārvalde\n\n"
            "31 kanoniska tēma. Visas → atmina.lv/pozicijas.html"
        ),
        "alt": (
            "Bar chart: top 8 tēmas pēc pozīciju un komentāru skaita. "
            "Aizsardzība un drošība (152), airBaltic (125), Koalīcija un "
            "partijas (112), Ukraina un Krievija (103), Valsts pārvalde "
            "(96), Ārpolitika (82), Degviela un enerģētika (73), "
            "Vēlēšanas (71)."
        ),
        "notes": None,
    },
    {
        "number": 4,
        "title": "Kāpēc atmina.lv? (Article A hook)",
        "image": SOCIAL_DIR / "tweet4-kapec-atmina.png",
        "copy": (
            "Pirms 4 gadiem politiķis solīja vienu lietu. Pirms 6 mēnešiem "
            "nobalsoja par pretējo. Vakar publiski atkārtoja sākotnējo "
            "solījumu.\n\n"
            "Kurš to atceras?\n\n"
            "Kāpēc mēs izveidojām atmina.lv — pilns raksts apakšā ↓"
        ),
        "alt": (
            "Editorial ilustrācija: kremkrāsas papīra fons ar dokumentu "
            "kaudzi, no kuras viens akcentēts violets indekss izvirzās uz "
            "priekšu. Politiskā atmiņa — saglabāts vs. aizmirsts."
        ),
        "notes": "Pievieno Twitter Article A linku, kad publicēts.",
    },
    {
        "number": 5,
        "title": "Kā strādā atmina.lv (Article B hook)",
        "image": SOCIAL_DIR / "tweet5-ka-strada.png",
        "copy": (
            "Mediju raksts. X ieraksts. Saeimas balsojums. Visi pazūd "
            "vienlīdz ātri.\n\n"
            "atmina.lv šo izkliedēto plūsmu pārvērš par strukturētu "
            "ierakstu, kuru var meklēt, salīdzināt un citēt.\n\n"
            "Kā tas notiek — bez tehniskā žargona ↓"
        ),
        "alt": (
            "Letterpress stila kompozīcija: kremkrāsas papīra fons. "
            "Pa kreisi — izkliedēti tumši zili ģeometriski fragmenti "
            "(kvadrāti, svītriņas, punkti) dažādos leņķos, kā izmētātas "
            "tipogrāfiskas burtu literas. Centrā — vertikāla šuve. "
            "Pa labi — perfekti paralēlas horizontālas svītras "
            "(tipogrāfiska kolonna). Viena svītra iezīmēta ar tumi cyan "
            "akcentu — viena ieraksta ceļš caur sistēmu."
        ),
        "notes": "Pievieno Twitter Article B linku, kad publicēts.",
    },
    {
        "number": 6,
        "title": "Pretruna ≠ viedokļa maiņa",
        "image": SOCIAL_DIR / "tweet6-pretruna.png",
        "copy": (
            "Pretruna ≠ politiķis maina viedokli laika gaitā. Tas ir "
            "normāli un sagaidāmi.\n\n"
            "Pretruna = vienlaikus pastāvošas pozīcijas, kas viena otru "
            "izslēdz. Solījums un balsojums, kas savstarpēji nesaskan. "
            "Publiskās pozīcijas, kas neatbilst privāti deklarētajām.\n\n"
            "Mēs tādas fiksējam — automatizēti un manuāli pārbaudīti. "
            "11 apstiprinātas. → atmina.lv/pretrunas.html"
        ),
        "alt": (
            "Editorial ilustrācija: kremkrāsas papīra fons. Divi tumši zili "
            "ķīļveida bloki — viens no kreisās, otrs no labās — virzīti "
            "viens pret otru, bet nesaskaras. Centrā vertikāla tumši sarkana "
            "plaisas līnija ar koncentriskiem lokiem ap saskares punktu — "
            "pretruna kā irdens spriegums."
        ),
        "notes": None,
    },
]


ARTICLE_A_BODY = (
    "Pirms 4 gadiem politiķis publiski solīja konkrētu likuma grozījumu. "
    "Pirms 6 mēnešiem Saeimā nobalsoja par tieši pretējo redakciju. Vakar "
    "intervijā medijam atkārtoja sākotnējo solījumu, it kā balsojuma "
    "nebūtu bijis.\n"
    "\n"
    "Kurš to atceras? Kurš tam seko? Kurš to var pārbaudīt par 30 "
    "sekundēm?\n"
    "\n"
    "Atbilde, ko mēs sadūrāmies pieredzēt: gandrīz neviens. Latvijā nav "
    "publiska, strukturēta, bezmaksas resursa, kur var redzēt vienlaicīgi "
    "politiķa medijos teikto, viņa balsojumus Saeimā un viņa pozīciju "
    "izmaiņas laika gaitā. Žurnālisti to dara projektu līmenī. Pilsoniska "
    "sabiedrība — pa drupatām. Politiķi — labprāt aizmirst.\n"
    "\n"
    "Mēs ticam, ka demokrātija darbojas labāk, kad pilsoņiem ir pieejama "
    "strukturēta, pārbaudāma informācija par to, ko politiķi saka un kā "
    "viņi rīkojas. Tāpēc izveidojām atmina.lv.\n"
    "\n"
    "PIECI PRINCIPI\n"
    "\n"
    "1. Dati ir publiski. Visi, ko vācam, nāk no publiskiem avotiem — "
    "ziņu portāliem, X/Twitter, Saeimas balsojumiem, KNAB deklarācijām. "
    "Strukturējam un padarām pārskatāmus. Pilnīgi bezmaksas, bez "
    "reģistrācijas, bez reklāmām.\n"
    "\n"
    "2. Avoti ir pārbaudāmi. Katrs ieraksts satur saiti uz oriģinālo "
    "avotu. Ja kaut ko apgalvojam — to var pārbaudīt pats. Ja atrod "
    "kļūdu — rakstīsi mums, izlabosim.\n"
    "\n"
    "3. Analīze ir caurspīdīga. Lai identificētu pozīcijas un pretrunas, "
    "izmantojam mākslīgo intelektu. MI var kļūdīties. Tāpēc publicējam "
    "ticamības novērtējumus un atzīmējam, kad informācija ir "
    "MI-identificēta vs. cilvēka manuāli pārbaudīta.\n"
    "\n"
    "4. Perspektīva ir deklarēta. Jebkurā analīzē ir perspektīva. Atklāti "
    "to deklarējam. atmina.lv cenšas būt pēc iespējas objektīvāks — kad "
    "parādās vērtējums vai interpretācija, tā tiek atzīmēta kā tāda, "
    "nevis pasniegta kā fakts.\n"
    "\n"
    "5. Sistēma, ne cilvēks. Sekojam politiķu publiskām pozīcijām un "
    "balsojumiem. Nesekojam viņu privātajai dzīvei. Mūs interesē "
    "sistēmas darbība — vai solītais saskan ar darīto, vai izteikumi "
    "laika gaitā ir konsekventi, kā balso pretstatā tam, ko saka "
    "publiski.\n"
    "\n"
    "DAŽĀDĀS PAKĀPĒS VISI POLITIĶI\n"
    "\n"
    "90 no 156 sekoto politiķu pēdējos mēnešos parādījušies medijos. "
    "Pārējie 66 — klusē. Mēs viņus tāpat fiksējam — ar Saeimas "
    "balsojumiem, KNAB deklarācijām un partiju dokumentiem. Sistēma redz "
    "arī tos, kas mēģina nepamanāmi paslīdēt cauri.\n"
    "\n"
    "KĀ MĒS PELNĀM\n"
    "\n"
    "Publiskais saturs ir un paliks bezmaksas — bez reklāmām, bez "
    "reģistrācijas, bez maksas mūra. Platformas uzturēšanu sedzam paši.\n"
    "\n"
    "KĀ PIEDALĪTIES\n"
    "\n"
    "· Atradi kļūdu? → ziņo mums atmina.lv/kontakti.html lapā\n"
    "· Trūkst kāda politiķa? → ieteikums tajā pašā lapā\n"
    "· Žurnālists? → datu pieprasījumus sūti uz tiem pašiem kontaktiem; "
    "lielākoties varam dalīties\n"
    "\n"
    "atmina.lv neaizstāj žurnālistiku. Tā ir infrastruktūra zem "
    "žurnālistikas — strukturēta atmiņa, kuru pilsoņi un mediji var "
    "izmantot, lai sekotu līdzi tam, ko politiķi saka un dara.\n"
    "\n"
    "→ atmina.lv"
)

ARTICLE_B_BODY = (
    "Mediju raksts. X/Twitter ieraksts. Saeimas balsojums. Pārliecināšanas "
    "materiāls partijas mājaslapā. Latvijā šie informācijas plūdi katru "
    "dienu rit paralēli — un visi vienlīdz ātri pazūd no atmiņas.\n"
    "\n"
    "atmina.lv šo izkliedēto plūsmu pārvērš par vienu strukturētu "
    "ierakstu, kurā var meklēt, salīdzināt un citēt. Lūk, kā — četros "
    "soļos, bez tehniskā žargona.\n"
    "\n"
    "1. SOLIS: VĀCAM\n"
    "\n"
    "Katru dienu sistēma uzlasa jaunus rakstus no Latvijas mediju "
    "portāliem (Delfi, LSM, TVNet, Diena, Re:Baltica un citiem) un "
    "X/Twitter ierakstus no katra sekotā politiķa konta. Saeimas "
    "atklātās sēdes balsojumus iegūstam tieši no Saeimas vietnes. KNAB "
    "deklarācijas — no atklātajiem reģistriem.\n"
    "\n"
    "Tas ir mehāniski vienkārši: ap divi tūkstoši rakstu mēnesī. Bez šī "
    "darba nav iespējama nekāda struktūra.\n"
    "\n"
    "2. SOLIS: IZVELKAM POZĪCIJAS\n"
    "\n"
    "Šeit notiek visgrūtākais. Lielais valodas modelis (LLM) lasa katru "
    "rakstu un mēģina atbildēt: ko šis politiķis šeit faktiski apgalvo? "
    "Vai tā ir pozīcija (\"es atbalstu X\"), vai tikai komentārs "
    "(\"oponents teica X\")? Kāda ir tēma — drošība, ekonomika, "
    "ārpolitika? Un kāds ir avots, lai katru ierakstu pēc tam varētu "
    "atgriezt pie oriģināla?\n"
    "\n"
    "LLM kļūdās. Tāpēc — divas lietas:\n"
    "· Katrs izvilkums saglabā avota saiti, lai pats var pārbaudīt\n"
    "· Atsevišķs aģents pārskata, vai izvilkumi atbilst rakstam patiešām "
    "(mēs to saucam par devils-advocate soli)\n"
    "\n"
    "Ja izvilkums neiztur pārbaudi — to nepublicē.\n"
    "\n"
    "3. SOLIS: SALĪDZINĀM\n"
    "\n"
    "Šis ir atmina.lv unikālais solis. Katru jaunu pozīciju sistēma "
    "salīdzina ar visu, ko šis politiķis ir teicis vai darījis iepriekš. "
    "Salīdzinājuma pamatā: semantiskie iegulumi (matemātiski vektori, "
    "kas atspoguļo nozīmes tuvumu), un tad — atkal LLM, kas spriež: "
    "\"Vai šie divi izteikumi tiešām ir pretrunā, vai tikai tā šķiet?\".\n"
    "\n"
    "Trīs pretrunu tipi:\n"
    "· Tieša pretruna — apgalvojumi, kas nevar būt vienlaikus patiesi\n"
    "· Apvērsums — politiķis aktīvi atsakās no agrākās pozīcijas\n"
    "· Mazā novirze — viedokļa nianse, kas laika gaitā mainās\n"
    "\n"
    "Ne katra pretruna ir skandāls. Bieži tā ir godprātīga viedokļa "
    "attīstība. Mēs to atzīmējam, neapsūdzam.\n"
    "\n"
    "4. SOLIS: PUBLICĒJAM\n"
    "\n"
    "Statiska vietne, kas ielādējas ātri pat lēnā mobilajā savienojumā. "
    "Katra pozīcija ar avota saiti. Katra pretruna ar abiem citātiem un "
    "kontekstu. Katrs politiķis ar viņa profilu — partija, pozīcijas, "
    "balsojumi, pretrunas, KNAB.\n"
    "\n"
    "Galvenais princips: viss, kas tiek apgalvots, ir izsekojams līdz "
    "pirmavotam.\n"
    "\n"
    "KUR SISTĒMA VAR KĻŪDĪTIES\n"
    "\n"
    "Atklāti:\n"
    "· LLM dažreiz pārprot ironiju vai citētus svešus apgalvojumus\n"
    "· Sarunvalodā teiktais (X ieraksti) ir grūtāk apstrādājams nekā "
    "strukturēti raksti\n"
    "· Mazāk pamanāma politiķa retorika var palikt nepamanīta, ja "
    "avotu ir maz un tie nav reprezentatīvi\n"
    "\n"
    "Tāpēc katra pretruna pirms publikācijas iziet cauri otram cilvēka "
    "pārbaudes solim. Un, ja redzat kļūdu — lūdzu rakstiet. Labosim.\n"
    "\n"
    "KĀPĒC TAS SVARĪGI\n"
    "\n"
    "Mēs neaizstājam žurnālistiku. Esam infrastruktūra zem žurnālistikas — "
    "strukturēta atmiņa, kuru gan pilsoņi, gan mediji var izmantot, lai "
    "sekotu līdzi tam, kā politiķi saka un kā rīkojas.\n"
    "\n"
    "→ atmina.lv"
)


def main() -> None:
    print(f"Compiling PDF → {PDF_OUT}")
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(PDF_OUT) as pdf:
        page_cover(pdf)
        page_index(pdf)
        for t in TWEETS:
            page_tweet(
                pdf,
                number=t["number"],
                title=t["title"],
                image_path=t["image"],
                copy=t["copy"],
                alt_text=t["alt"],
                notes=t["notes"],
            )
        page_article(
            pdf,
            label="Article A",
            title="Kāpēc mēs izveidojām atmina.lv",
            hero_path=SOCIAL_DIR / "tweet4-kapec-atmina.png",
            body=ARTICLE_A_BODY,
        )
        page_article(
            pdf,
            label="Article B",
            title="Kā strādā atmina.lv — bez tehniskā žargona",
            hero_path=SOCIAL_DIR / "tweet5-ka-strada.png",
            body=ARTICLE_B_BODY,
        )
        page_checklist(pdf)

    print(f"Done. Size: {PDF_OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
