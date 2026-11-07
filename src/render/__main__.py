"""CLI entry-point: ``python -m src.render``.

Targeted re-renders without paying the full ~12 min generate_public_site
cost. Use ``--only=DOMAIN1,DOMAIN2`` to select scope.

Examples
--------
    # Full site (same as bare generate_public_site call)
    python -m src.render

    # Brief 229 deployed (touches blog/* + index hero "Jaunākie pārskati")
    python -m src.render --only=blog,dashboard

    # parties.coalition_status flip (touches partijas + personas + balsojumi
    # + pretrunas + pozicijas + index)
    python -m src.render --only=partijas,personas,balsojumi,pretrunas,pozicijas,dashboard

    # List valid domains
    python -m src.render --list-domains

    # Proofread an UNAPPROVED brief in rendered HTML (never deploy this tree)
    python -m src.render --only=blog,dashboard,static --drafts --output=.scratch/drafts
"""
from __future__ import annotations

import argparse
import sys

from src.render._orchestrator import KNOWN_DOMAINS, generate_public_site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.render",
        description=(
            "Render the atmina.lv static site. Use --only to scope to a "
            "subset of render domains and skip the rest. See module docstring "
            "for canonical narrow-render scopes per change type."
        ),
    )
    parser.add_argument(
        "--only",
        help=(
            "Comma-separated render domains to run. Everything else is "
            "skipped. Run with --list-domains to see valid names. "
            "Omit for a full render."
        ),
    )
    parser.add_argument(
        "--list-domains",
        action="store_true",
        help="Print valid --only domain names and exit.",
    )
    parser.add_argument("--db", help="Override path to atmina.db.")
    parser.add_argument("--output", help="Override path to output/ directory.")
    parser.add_argument(
        "--drafts",
        action="store_true",
        help=(
            "Also render briefs WITHOUT a publish approval, for proofreading. "
            "Use with --output pointing into .scratch/ — the resulting tree "
            "must NOT be deployed."
        ),
    )
    args = parser.parse_args(argv)

    if args.list_domains:
        for d in sorted(KNOWN_DOMAINS):
            print(d)
        return 0

    only: set[str] | None = None
    if args.only:
        only = {d.strip() for d in args.only.split(",") if d.strip()}
        unknown = only - KNOWN_DOMAINS
        if unknown:
            parser.error(
                f"Unknown --only domain(s): {sorted(unknown)}. "
                f"Valid: {sorted(KNOWN_DOMAINS)}"
            )

    if args.drafts and not args.output:
        # Melnraksts noklusējuma output/ kokā = nākamais deploy to aizsūtītu
        # (vai publish-gate to bloķētu). Stop beats write.
        parser.error("--drafts prasa --output (piem. .scratch/drafts): noklusējuma output/ ir deploy koks")
    if args.drafts:
        print(
            "BRĪDINĀJUMS: --drafts renderē arī NEAPSTIPRINĀTUS pārskatus. "
            "Šo koku NEDRĪKST deployēt — tikai korektūrai "
            f"(--output={args.output}).",
            file=sys.stderr,
        )

    generate_public_site(
        db_path=args.db, output_dir=args.output, only=only, include_drafts=args.drafts
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
