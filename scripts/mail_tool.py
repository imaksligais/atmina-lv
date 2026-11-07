"""Projekta pastkaste: nolasīt iesūtni un nosūtīt vēstuli (IMAP/SMTP, tikai stdlib).

Konfigurācija: `.env.mail` repo saknē (gitignored) vai ceļš env mainīgajā ATMINA_MAIL_ENV.
Atslēgas: MAIL_USER, MAIL_PASSWORD, IMAP_HOST, IMAP_PORT, SMTP_HOST, SMTP_PORT, MAIL_FROM_NAME.

    .venv/Scripts/python.exe scripts/mail_tool.py inbox [--n 10]
    .venv/Scripts/python.exe scripts/mail_tool.py read <uid>
    .venv/Scripts/python.exe scripts/mail_tool.py send --to X --subject S --body-file F [--cc Y] --yes
    .venv/Scripts/python.exe scripts/mail_tool.py remind      # SessionStart hook: atgādina, ja šodien `inbox` nav skatīts

`inbox` atzīmē skatīšanas dienu un lielāko uid failā `.scratch/mail_state.json`.

Sūtīšana ir ārēja darbība: `--yes` tikai pēc operatora apstiprinājuma konkrētajai vēstulei.
Katra nosūtītā vēstule tiek saglabāta arī mapē «Sent» (ja serveris to atļauj).
"""

from __future__ import annotations

import argparse
import datetime as dt
import email
import json
import imaplib
import os
import smtplib
import ssl
import sys
import time
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".scratch" / "mail_state.json"


def _state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(st: dict) -> None:
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(st), encoding="utf-8")


def load_config() -> dict[str, str]:
    path = Path(os.environ.get("ATMINA_MAIL_ENV", ROOT / ".env.mail"))
    cfg = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            cfg[k.strip()] = v.strip()
    missing = [k for k in ("MAIL_USER", "MAIL_PASSWORD", "IMAP_HOST", "SMTP_HOST") if not cfg.get(k)]
    if missing:
        sys.exit(f"{path}: trūkst {', '.join(missing)}")
    return cfg


def _dec(value: str | None) -> str:
    return str(make_header(decode_header(value))) if value else ""


def imap_connect(cfg):
    m = imaplib.IMAP4_SSL(cfg["IMAP_HOST"], int(cfg.get("IMAP_PORT", 993)), ssl_context=ssl.create_default_context())
    m.login(cfg["MAIL_USER"], cfg["MAIL_PASSWORD"])
    return m


def cmd_inbox(cfg, n: int) -> None:
    m = imap_connect(cfg)
    m.select("INBOX", readonly=True)
    _, data = m.uid("search", None, "ALL")
    uids = data[0].split()
    print(f"INBOX: {len(uids)} vēstules; pēdējās {min(n, len(uids))}:")
    for uid in reversed(uids[-n:]):
        _, msg = m.uid("fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        h = email.message_from_bytes(msg[0][1])
        print(f"  {uid.decode():>6}  {_dec(h['Date'])[:31]:31}  {_dec(h['From'])[:40]:40}  {_dec(h['Subject'])}")
    m.logout()
    st = _state()
    st["last_check"] = dt.date.today().isoformat()
    st["last_uid"] = max([int(u) for u in uids] + [st.get("last_uid", 0)])
    _save_state(st)


def cmd_remind() -> None:
    """SessionStart hook: klusē, ja šodien jau skatīts; tīkla kļūda nav fatāla."""
    st = _state()
    now = dt.datetime.now()
    if st.get("last_check") == now.date().isoformat():
        return
    new = "?"
    try:
        import socket
        socket.setdefaulttimeout(8)
        m = imap_connect(load_config())
        m.select("INBOX", readonly=True)
        _, data = m.uid("search", None, "ALL")
        new = sum(1 for u in data[0].split() if int(u) > st.get("last_uid", 0))
        m.logout()
    except Exception:
        pass
    print(f"[atgādinājums] redakcija@atmina.lv šodien vēl nav skatīta; jaunas vēstules kopš pēdējās reizes: {new}. "
          "Pasaki operatoram un piedāvā palaist `scripts/mail_tool.py inbox`.")


def cmd_read(cfg, uid: str) -> None:
    m = imap_connect(cfg)
    m.select("INBOX", readonly=True)
    _, msg = m.uid("fetch", uid, "(BODY.PEEK[])")
    if not msg or msg[0] is None:
        sys.exit(f"uid {uid} nav atrasts")
    e = email.message_from_bytes(msg[0][1])
    for k in ("From", "To", "Cc", "Date", "Subject"):
        if e[k]:
            print(f"{k}: {_dec(e[k])}")
    print()
    part = e.get_body(preferencelist=("plain", "html")) if hasattr(e, "get_body") else None
    if part is None:
        part = next((p for p in e.walk() if p.get_content_type() == "text/plain"), e)
    payload = part.get_payload(decode=True) or b""
    print(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    m.logout()


def cmd_send(cfg, to: list[str], cc: list[str], subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = formataddr((cfg.get("MAIL_FROM_NAME", ""), cfg["MAIL_USER"]))
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=cfg["MAIL_USER"].split("@")[-1])
    msg.set_content(body)
    with smtplib.SMTP_SSL(cfg["SMTP_HOST"], int(cfg.get("SMTP_PORT", 465)), context=ssl.create_default_context()) as s:
        s.login(cfg["MAIL_USER"], cfg["MAIL_PASSWORD"])
        refused = s.send_message(msg)
    if refused:
        sys.exit(f"serveris atteica adresātus: {refused}")
    print(f"nosūtīts: {msg['Message-ID']} → {msg['To']}" + (f", cc {msg['Cc']}" if cc else ""))
    try:
        m = imap_connect(cfg)
        saved = False
        for box in ("INBOX.Sent", "Sent", "Sent Items"):
            typ, _ = m.append(box, "\\Seen", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
            if typ == "OK":
                print(f"kopija mapē {box}")
                saved = True
                break
        if not saved:
            print("BRĪDINĀJUMS: kopija mapē Sent NAV saglabāta", file=sys.stderr)
        m.logout()
    except Exception as exc:  # nosūtīšana jau notikusi; kopijas kļūda nav fatāla, bet jāredz
        print(f"BRĪDINĀJUMS: kopija mapē Sent NAV saglabāta: {exc}", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("inbox")
    pi.add_argument("--n", type=int, default=10)
    sub.add_parser("remind")
    pr = sub.add_parser("read")
    pr.add_argument("uid")
    ps = sub.add_parser("send")
    ps.add_argument("--to", action="append", required=True)
    ps.add_argument("--cc", action="append", default=[])
    ps.add_argument("--subject", required=True)
    ps.add_argument("--body-file", required=True)
    ps.add_argument("--yes", action="store_true", help="operators apstiprinājis tieši šo vēstuli")
    a = p.parse_args()
    if a.cmd == "remind":
        cmd_remind()
        return
    cfg = load_config()
    if a.cmd == "inbox":
        cmd_inbox(cfg, a.n)
    elif a.cmd == "read":
        cmd_read(cfg, a.uid)
    else:
        if not a.yes:
            sys.exit("sūtīšana bez --yes atteikta (vajag operatora apstiprinājumu)")
        cmd_send(cfg, a.to, a.cc, a.subject, Path(a.body_file).read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
