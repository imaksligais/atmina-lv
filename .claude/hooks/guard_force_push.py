#!/usr/bin/env python3
"""PreToolUse(Bash) guard: block force-push to the master branch.

Reads the hook JSON from stdin, inspects the Bash command, and DENIES (via the
PreToolUse ``permissionDecision`` protocol) ONLY when the command force-pushes
to ``master``. It allows:
  - ``--force-with-lease`` (the safe variant),
  - force-pushing any non-master / feature branch,
  - every non-push command.

Enforces the long-standing project rule: never force-push master without
explicit per-action authorization. Always exits 0 — a parse error or missing
git is fail-OPEN (never blocks normal work).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

_SEP = re.compile(r"&&|\|\||;|\n|\|")
_ENV_PREFIX = re.compile(r"^\s*(sudo\s+)?([A-Za-z_]\w*=\S+\s+)*")


def _deny_reason(cmd: str) -> str | None:
    """Return a deny reason if *cmd* force-pushes to master, else None."""
    # Scan each shell segment so e.g. `echo "git push -f master"` is ignored.
    for seg in _SEP.split(cmd):
        s = _ENV_PREFIX.sub("", seg).strip()
        if not re.match(r"git\s+push(\s|$)", s):
            continue
        toks = s.split()
        has_force = any(
            t in ("--force", "-f") or re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", t)
            for t in toks
        )
        has_lease = any(t.startswith("--force-with-lease") for t in toks)
        plus_master = any(t.startswith("+") and "master" in t for t in toks)
        positionals = [t for t in toks[2:] if not t.startswith("-")]  # after 'git push'
        mentions_master = any("master" in t for t in positionals)
        has_explicit_refspec = (
            plus_master
            or any(("master" in t or ":" in t) for t in positionals)
            or len(positionals) >= 2  # remote + refspec
        )

        force = (has_force and not has_lease) or plus_master
        if not force:
            continue

        if mentions_master or plus_master:
            return (
                "BLOCKED: force-push to master. Project rule: "
                "never force-push master. Use a corrective commit, or --force-with-lease "
                "on a feature branch. If this is truly intended, the operator must run it "
                "manually (e.g. via `! git push ...`)."
            )
        if not has_explicit_refspec:
            # Bare `git push -f` pushes the CURRENT branch — block if on master.
            try:
                cur = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                ).stdout.strip()
            except Exception:
                cur = ""
            if cur == "master":
                return (
                    "BLOCKED: bare force-push while on master (`git push -f` would rewrite "
                    "master). Project rule: no force-push on master. Use a corrective commit; "
                    "override must be run manually by the operator."
                )
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # unparseable input → fail-open (allow)
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if "push" not in cmd:  # fast path
        sys.exit(0)
    reason = _deny_reason(cmd)
    if reason:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }))
    sys.exit(0)


if __name__ == "__main__":
    main()
