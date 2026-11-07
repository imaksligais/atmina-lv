"""LSM atraduma avotu arhīvs 2026-11-01.

1) Katru melnrakstā citēto ārējo saiti lejupielādē → kopijas/<nr>_<host>.<ext>, manifest.json, SHA256SUMS.
2) Saitēm, kas nav oficiāls reģistrs (titania, likumi.lv), Wayback «Save Page Now», tad CDX pārbaude:
   vai ir uzņēmums ar TIEŠI atgriezto laika zīmogu (noteikums 2026-10-31: SPN adrese ≠ pierādījums).

"""
import re, json, hashlib, sys, time, datetime
from pathlib import Path
from urllib.parse import urlparse
import httpx

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
COP = OUT / "kopijas"
COP.mkdir(parents=True, exist_ok=True)
DRAFT = ROOT / "content/analizes/lsm-2026-skaitlos.md"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
      "Accept-Language": "lv,en;q=0.8"}
REGISTRY = ("saeima.lv", "likumi.lv", "vestnesis.lv")  # oficiāli, nearhivē (operators 2026-11-01)

urls = sorted({u.rstrip('.,;:»*') for u in re.findall(r'https?://[^\s)>\]"\'<`|]+', DRAFT.read_text(encoding="utf-8"))})
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
SPN_ONLY = "--spn-only" in sys.argv
COPIES_ONLY = "--copies-only" in sys.argv
man = [] if not SPN_ONLY else json.load(open(OUT / "manifest.json", encoding="utf-8"))
for i, u in ([] if SPN_ONLY else enumerate(urls, 1)):
    rec = {"nr": i, "url": u, "fetched_utc": now()}
    try:
        r = httpx.get(u, headers=UA, follow_redirects=True, timeout=60)
        ct = r.headers.get("content-type", "")
        ext = "pdf" if "pdf" in ct else "docx" if "wordprocessing" in ct else "html"
        f = COP / f"{i:03d}_{re.sub(r'[^A-Za-z0-9.-]', '_', urlparse(u).netloc.replace('www.', ''))}.{ext}"
        rec.update(status=r.status_code, final=str(r.url), content_type=ct, bytes=len(r.content),
                   sha256=hashlib.sha256(r.content).hexdigest())
        if r.status_code == 200:
            f.write_bytes(r.content); rec["file"] = f.name
    except Exception as e:
        rec["error"] = repr(e)
    print(rec.get("status", rec.get("error")), u[:110], flush=True)
    man.append(rec)

def save():
    json.dump(man, open(OUT / "manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    (OUT / "SHA256SUMS").write_text("".join(f"{m['sha256']}  kopijas/{m['file']}\n" for m in man if m.get("file")), encoding="utf-8")
save()
if COPIES_ONLY:
    print("kopijas:", sum(1 for m in man if m.get("file")), "no", len(man)); sys.exit(0)
for rec in man:
    u = rec["url"]
    if urlparse(u).netloc.endswith(REGISTRY) or "web.archive.org" in u:
        continue
    w = rec.get("wayback") or {}
    if w.get("exact") and w.get("head_no_redirect") == 200:
        continue
    if (rec.get("spn") or {}).get("ts"):
        continue  # saglabāts jau agrāk — atkārto tikai pārbaudi zemāk
    for attempt in range(3):
        try:
            r = httpx.get(f"https://web.archive.org/save/{u}", headers=UA, timeout=180, follow_redirects=False)
            loc = r.headers.get("content-location") or r.headers.get("location") or ""
            m = re.search(r'/web/(\d{14})', loc)
            rec["spn"] = {"http": r.status_code, "ts": m.group(1) if m else None, "at": now()}
            if r.status_code in (200, 302) and m:
                break
        except Exception as e:
            rec["spn"] = {"error": repr(e), "at": now()}
        time.sleep(60)
    print("SPN", rec.get("spn"), u[:90], flush=True)
    time.sleep(20)

time.sleep(60)
for rec in man:
    ts = (rec.get("spn") or {}).get("ts")
    if not ts:
        continue
    rows = []
    for attempt in range(4):
        try:
            r = httpx.get("https://web.archive.org/cdx/search/cdx", params={"url": rec["url"], "from": ts[:8], "to": ts[:8],
                          "output": "json", "fl": "timestamp,statuscode,mimetype"}, timeout=60)
            if r.status_code == 200:
                rows = r.json()[1:] if r.text.strip() else []
                break
        except Exception:
            pass
        time.sleep(30)
    wb = f"https://web.archive.org/web/{ts}/{rec['url']}"
    try:
        h = httpx.head(wb, headers=UA, timeout=60, follow_redirects=False).status_code
    except Exception as e:
        h = repr(e)
    rec["wayback"] = {"url": wb, "cdx_same_day": rows, "exact": any(x[0] == ts for x in rows), "head_no_redirect": h}
    print("CDX", rec["wayback"]["exact"], h, wb[:120], flush=True)
    time.sleep(30)

json.dump(man, open(OUT / "manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
(OUT / "SHA256SUMS").write_text("".join(f"{m['sha256']}  kopijas/{m['file']}\n" for m in man if m.get("file")), encoding="utf-8")
ok = [m for m in man if (m.get("wayback") or {}).get("exact") and m["wayback"]["head_no_redirect"] == 200]
need = [m for m in man if not urlparse(m["url"]).netloc.endswith(REGISTRY)]
print(f"saites {len(man)}; kopijas {sum(1 for m in man if m.get('file'))}; Wayback vajadzīgas {len(need)}, pārbaudītas OK {len(ok)}")
