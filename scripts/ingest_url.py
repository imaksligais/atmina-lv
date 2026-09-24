"""Generic historic-article ingest CLI.

Generalizes the hardcoded retrofetch_* scripts into one tested tool:
fetch -> clean (trafilatura) -> backdate -> insert_document -> link politicians.

  python scripts/ingest_url.py --url URL [--politician-id N]
  python scripts/ingest_url.py --manifest items.jsonl   # {"url": "...", "politician_id": N}

`politician_id` / `--politician-id` marks that politician as the article's
SUBJECT — the speaker (an interviewee, an op-ed author), not a topic tag. It
is stored as a 'subject' junction at insert; the matcher scan afterwards
still links the other names in the text but cannot add a conflicting role
for the asserted pid (matcher.py::link_politicians_to_documents).

Idempotent: skips URLs already in `documents`; insert_document dedups by content_hash.
Additive only (insert_document's URL-first update aside) -> no rollback SQL required.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import DB_PATH, get_db, insert_document  # noqa: E402
from src.matcher import link_politicians_to_documents  # noqa: E402
from src.soft_404 import looks_like_soft_404  # noqa: E402

MIN_CHARS = 150
# Party election programs (the PDF path below) run long — a 30-page manifesto is
# easily 60-90k chars. The old 50k inline cap silently dropped the tail, so it is
# raised here. insert_document has no length limit; this only bounds pathological
# inputs for this manual ingest tool.
MAX_CHARS = 200_000
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "lv,en;q=0.5",
}

# Set by ingest_manifest() before it calls link_fn — lets an injected link_fn in
# tests know which freshly-ingested doc ids to "link" without a real matcher run.
_LAST_INGESTED_IDS: list[int] = []

# Set by _default_fetch() on every call — same out-of-band convention as
# _LAST_INGESTED_IDS. _default_fetch returns None for EVERY failure class, so
# a caller that must tell them apart (scripts/backfill_truncated_docs.py
# reports soft_404 separately from fetch_error in its denominator) reads this
# after a None return. Values: None on success, else "http: …" / "soft_404: …"
# / "pdf: …".
_LAST_FETCH_ERROR: Optional[str] = None


def _published_at_from_url(url: str) -> Optional[str]:
    """Best-effort date from a /YYYY/MM/DD/ or /YYYY/ path. Rare for LSM/TVNet."""
    m = re.search(r"/(20\d{2})/(\d{2})/(\d{2})/", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"/(20\d{2})/", url)
    if m:
        return f"{m.group(1)}-01-01"
    return None


def _extract_pdf(pdf_bytes: bytes) -> dict:
    """Extract text + title from a PDF byte stream via pymupdf. Party programs are
    frequently published as PDFs, which trafilatura (HTML-only) cannot read.

    Was `pypdf` until 2026-08-02, but pypdf has never been installed in this
    venv and appears in neither requirements.txt nor pyproject.toml — so the
    ImportError was caught by the call site's `except Exception`, printed to
    stderr, and returned None. A PDF ingest therefore looked like a skipped
    URL rather than a failure, which means the Data Contract #4a party-program
    PDF path has never actually worked. pymupdf was already present as a
    transitive dependency; it is now declared explicitly so this cannot
    silently regress.
    """
    import pymupdf

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        text = "\n\n".join(page.get_text() for page in doc).strip()
        title = (doc.metadata or {}).get("title")
        title = title.strip() or None if title else None
    finally:
        doc.close()
    return {"text": text, "title": title}


def _extract_article_text(html_text: str) -> tuple[str | None, str]:
    """Trafilatura ekstrakcija ar atkāpšanās ķēdi.

    Noklusējums (`deduplicate=True`, bez tabulām) uz sarakstu-veida lapām
    (SV-AJ programma dublējas divreiz; ST — īsi bloki) atgriež <150 zīmju un
    ingests reģistrē `thin`, lai gan lapa atgriež 200 ar pilnu tekstu
    (diagnostika 2026-09-20: SV-AJ default 0 z. → recall 22 907 z.;
    ST default 0 → recall 6 040). Atkāpšanās ieslēdzas TIKAI tad, kad
    noklusējums ir zem `MIN_CHARS` sliekšņa — strādājošs ceļš nekad nemainās.
    Atgriež (teksts, variants), kur variants ∈ {"default", "recall"}.
    """
    import trafilatura

    text = trafilatura.extract(
        html_text, include_comments=False, include_tables=False, deduplicate=True
    )
    if text and len(text) >= MIN_CHARS:
        return text, "default"
    recall = trafilatura.extract(
        html_text, include_comments=False, include_tables=True,
        deduplicate=False, favor_recall=True,
    )
    if recall and len(recall) >= MIN_CHARS:
        return recall, "recall"
    return text, "default"


def _default_fetch(url: str) -> Optional[dict]:
    """Real network path: httpx GET -> trafilatura (HTML) or pypdf (PDF) +
    title + published_at. None on error — the failure class is recorded in
    ``_LAST_FETCH_ERROR`` for callers that need it."""
    import httpx
    import trafilatura

    from src.ingest import _extract_published_at
    from src.title_extract import extract_title

    global _LAST_FETCH_ERROR
    _LAST_FETCH_ERROR = None

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True, headers=HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        _LAST_FETCH_ERROR = f"http: {e}"
        print(f"  ERR fetch {url[:80]}: {e}", file=sys.stderr)
        return None

    # Soft-404 (e.g. lsm.lv 301s a dead article id to the homepage, HTTP 200)
    # — same treatment as a fetch error so the error page never becomes content.
    reason = looks_like_soft_404(resp.text, None, url, str(resp.url))
    if reason:
        _LAST_FETCH_ERROR = f"soft_404: {reason}"
        print(f"  ERR fetch {url[:80]}: soft-404 ({reason})", file=sys.stderr)
        return None

    # PDF path — detect by Content-Type or .pdf URL. Programs have no HTML meta,
    # so published_at falls back to the URL-path heuristic.
    content_type = resp.headers.get("content-type", "").lower()
    if "application/pdf" in content_type or url.lower().split("?")[0].endswith(".pdf"):
        try:
            pdf = _extract_pdf(resp.content)
        except ImportError:
            # An absent PDF library is an environment fault, not a bad URL.
            # Swallowing it here is what made the whole PDF path look like a
            # run of skipped URLs for months — let it stop the caller instead.
            raise
        except Exception as e:  # noqa: BLE001 — a corrupt PDF is a real per-URL skip
            _LAST_FETCH_ERROR = f"pdf: {e}"
            print(f"  ERR pdf-parse {url[:80]}: {e}", file=sys.stderr)
            return None
        return {
            "text": pdf["text"],
            "title": pdf["title"],
            "published_at": _published_at_from_url(url),
        }

    text, variant = _extract_article_text(resp.text)
    pub = _extract_published_at(resp.text) or _published_at_from_url(url)
    return {"text": text, "title": extract_title(resp.text), "published_at": pub,
            "variant": variant}


def ingest_one(
    url: str,
    politician_id: Optional[int] = None,
    *,
    fetch_fn: Callable[[str], Optional[dict]] = _default_fetch,
    db_path: str = DB_PATH,
) -> dict:
    """Ingest one URL. Returns {url, status, doc_id, published_at, title}.

    status: ingested | already_present | dupe | thin | fetch_error

    `politician_id` marks that politician as the article's SUBJECT (speaker)
    — stored as a 'subject' junction via insert_document's politician_links.
    """
    out = {"url": url, "status": None, "doc_id": None, "published_at": None, "title": None}

    existing = get_db(db_path).execute(
        "SELECT id FROM documents WHERE source_url=?", (url,)
    ).fetchone()
    if existing:
        out["status"] = "already_present"
        out["doc_id"] = existing["id"]
        return out

    parsed = fetch_fn(url)
    if parsed is None:
        out["status"] = "fetch_error"
        return out

    text = parsed.get("text") or ""
    if len(text) < MIN_CHARS:
        out["status"] = "thin"
        return out

    out["published_at"] = parsed.get("published_at")
    out["title"] = parsed.get("title")
    out["variant"] = parsed.get("variant", "default")
    doc_id = insert_document(
        content=text[:MAX_CHARS],
        source_id=None,
        platform="web",
        language="lv",
        source_url=url,
        published_at=parsed.get("published_at"),
        title=parsed.get("title"),
        # --politician-id N means "N is the SUBJECT (speaker) of this article"
        # — stored as a 'subject' junction at insert, so a later matcher
        # rescan cannot re-derive him as 'mentioned' (doc-111520 class).
        politician_links=(
            [(politician_id, "subject")] if politician_id is not None else None
        ),
        db_path=db_path,
    )
    if doc_id is None:
        out["status"] = "dupe"
        return out
    out["status"] = "ingested"
    out["doc_id"] = doc_id
    return out


def parse_manifest(path: str) -> list[dict]:
    """Read a JSONL manifest of {url, politician_id?}. Bad lines skipped with a warning."""
    items: list[dict] = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if "url" not in obj:
                raise ValueError("no url")
            items.append({"url": obj["url"], "politician_id": obj.get("politician_id")})
        except Exception as e:  # noqa: BLE001
            print(f"  SKIP bad manifest line {n}: {e}", file=sys.stderr)
    return items


def ingest_manifest(
    items: list[dict],
    *,
    fetch_fn: Callable[[str], Optional[dict]] = _default_fetch,
    link_fn: Callable = link_politicians_to_documents,
    db_path: str = DB_PATH,
) -> dict:
    """Ingest all items, link politicians once, return an aggregate summary dict."""
    global _LAST_INGESTED_IDS
    results = [
        ingest_one(it["url"], it.get("politician_id"), fetch_fn=fetch_fn, db_path=db_path)
        for it in items
    ]
    _LAST_INGESTED_IDS = [r["doc_id"] for r in results if r["status"] == "ingested"]

    linked = link_fn(days=1, rescan_all=True) if _LAST_INGESTED_IDS else {}
    linked_to: dict[int, list[int]] = {}
    for doc_id, pids in (linked or {}).items():
        for pid in pids:
            linked_to.setdefault(pid, []).append(doc_id)

    return {
        "ingested": sum(r["status"] == "ingested" for r in results),
        "already_present": sum(r["status"] == "already_present" for r in results),
        "dupe": sum(r["status"] == "dupe" for r in results),
        "thin": sum(r["status"] == "thin" for r in results),
        "fetch_error": sum(r["status"] == "fetch_error" for r in results),
        "dateless": [r["doc_id"] for r in results
                     if r["status"] == "ingested" and not r["published_at"]],
        "linked_to": linked_to,
        "results": results,
    }


def main(argv: Optional[list[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Latvian titles
    ap = argparse.ArgumentParser(
        description="Historic article ingest (fetch -> backdate -> link)."
    )
    ap.add_argument("--url", help="single URL to ingest")
    ap.add_argument(
        "--politician-id", type=int, default=None,
        help="pid of the politician who is the SUBJECT (speaker) of --url",
    )
    ap.add_argument(
        "--manifest",
        help="JSONL of {url, politician_id?}; politician_id = the subject",
    )
    ap.add_argument("--db", default=DB_PATH, help="DB path (default: live)")
    args = ap.parse_args(argv)

    if not args.url and not args.manifest:
        ap.print_usage(sys.stderr)
        print("error: one of --url or --manifest is required", file=sys.stderr)
        return 2

    items = (
        [{"url": args.url, "politician_id": args.politician_id}]
        if args.url
        else parse_manifest(args.manifest)
    )
    summary = ingest_manifest(items, db_path=args.db)
    for r in summary["results"]:
        print("RESULT_JSON:" + json.dumps(r, ensure_ascii=False))
    printable = {k: v for k, v in summary.items() if k != "results"}
    print("SUMMARY_JSON:" + json.dumps(printable, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
