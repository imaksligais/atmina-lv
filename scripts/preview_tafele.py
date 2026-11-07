"""Melnraksta tāfeles priekšskatījums ārpus output/atmina/ (T15).

Lietošana:
  PYTHONUTF8=1 .venv/Scripts/python.exe scripts/preview_tafele.py docs/drafts/tafeles/visvanati-2026.yaml --serve
"""
from __future__ import annotations

import argparse
import http.server
import shutil
import sys
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.render._orchestrator import _make_env  # noqa: E402
from src.render.analyses import _load_analyses, render_analyses  # noqa: E402
from src.render.tafeles import render_board  # noqa: E402
from src.tafele.model import BoardError, load_board, validate_board  # noqa: E402

PREVIEW = ROOT / ".scratch" / "tafele" / "preview"


def build_preview(yaml_path: Path, out_dir: Path = PREVIEW, articles_dir: Path = ROOT / "content" / "analizes",
                  extra_persons: set[str] | None = None) -> Path:
    out_dir = Path(out_dir).resolve()
    if out_dir.is_relative_to((ROOT / "output").resolve()):
        raise BoardError("Priekšskatījums nedrīkst atrasties output mapē.")
    board = load_board(Path(yaml_path))
    validate_board(board, articles_dir, require_published=False,
                   extra_persons=frozenset(extra_persons or ()))
    atmina = Path(out_dir) / "atmina"
    src_assets = ROOT / "output" / "atmina" / "assets"
    shutil.copytree(ROOT / "assets", atmina / "assets", dirs_exist_ok=True)
    if (src_assets / "fonts").exists():
        shutil.copytree(src_assets / "fonts", atmina / "assets" / "fonts", dirs_exist_ok=True)
    src_an = ROOT / "output" / "atmina" / "analizes"
    if src_an.exists():
        (atmina / "analizes").mkdir(parents=True, exist_ok=True)
        for f in src_an.glob("*.html"):
            shutil.copy2(f, atmina / "analizes" / f.name)
    # Renderē arī atsauces melnrakstus; parastās vietnes vārti nemainās.
    analyses = _load_analyses(articles_dir=articles_dir, include_drafts=True, slugs=set(board.articles))
    images = atmina / "images" / "analizes"
    images.mkdir(parents=True, exist_ok=True)
    for article in analyses:
        # Rakstos ir arī shēmas un to mobilie varianti ar tā paša sluga prefiksu.
        for directory in (ROOT / "output" / "images" / "analizes",
                          ROOT / "output" / "atmina" / "images" / "analizes"):
            for src in directory.glob(f"{article['slug']}*"):
                if src.is_file():
                    shutil.copy2(src, images / src.name)
    env = _make_env()
    render_analyses(env, atmina, analyses)
    return render_board(env, atmina, board)


def _csp() -> str:
    for line in (ROOT / "assets" / "_headers").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("Content-Security-Policy:"):
            return line.split(":", 1)[1].strip()
    raise SystemExit("CSP galvene nav atrasta assets/_headers")


class _CSPHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Content-Security-Policy", _csp())
        super().end_headers()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("yaml")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    page = build_preview(Path(a.yaml))
    rel = page.relative_to(PREVIEW / "atmina").as_posix()
    print(f"Priekšskatījums: {page}")
    if a.serve:
        handler = partial(_CSPHandler, directory=str(PREVIEW / "atmina"))
        url = f"http://127.0.0.1:{a.port}/{rel}"
        print(url)
        import threading, webbrowser
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()  # operators atver lokāli (24.10.)
        with http.server.ThreadingHTTPServer(("127.0.0.1", a.port), handler) as server:
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
