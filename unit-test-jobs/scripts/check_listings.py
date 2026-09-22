#!/usr/bin/env python3
"""Check whether job listings are live, closed, blocked or dead.

Usage:
    python3 check_listings.py urls.json          # JSON array of URLs, or of row dicts with "Job URL"
    python3 check_listings.py urls.json --json   # machine-readable output

Why this exists rather than a curl one-liner in the skill body: an HTTP status
code alone cannot tell you a listing is closed. Wellfound, YC and LinkedIn all
return 200 for a filled role and only say "no longer accepting applications" in
the page body -- so a status-only check silently keeps dead roles in the table.
It also fixes a real failure mode: the ad-hoc shell version of this check had
broken quoting and returned an empty result set, which nearly let 104 unchecked
rows through on 2026-09-22.

Verdicts:
    live     -- 200 and no closed-marker found in the body
    closed   -- body contains a closed/filled/expired marker (drop it)
    dead     -- 404/410 (drop it)
    blocked  -- 403/406/429/timeout: bot protection, NOT evidence the role is gone.
                Keep the row and tag it for manual checking. Never drop on this.
"""
import json
import re
import subprocess
import sys
import concurrent.futures as cf
from collections import Counter

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

# Phrases that mean the role is gone. Kept deliberately specific: a loose pattern
# like "closed" alone matches ordinary page furniture and would drop live roles.
CLOSED_MARKERS = [
    r"no longer accepting applications",
    r"no longer available",
    r"no longer active",
    r"no longer hiring",
    r"this job (post(ing)?|listing)? ?(is|has been) (closed|filled|removed|expired)",
    r"position (has been|was) filled",
    r"role (has been|was) filled",
    r"applications? (are|is) closed",
    r"we('| a)re no longer",
    r"this (job|posting|listing) has expired",
    r"job not found",
    r"listing not found",
]
CLOSED_RE = re.compile("|".join(CLOSED_MARKERS), re.I)


def check(url):
    try:
        proc = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "25", "-A", UA,
             "-w", "\n__HTTP_STATUS__%{http_code}", url],
            capture_output=True, text=True, timeout=40, errors="ignore")
    except Exception:
        return url, "blocked", "timeout"

    out = proc.stdout or ""
    status = out.rsplit("__HTTP_STATUS__", 1)[-1].strip() if "__HTTP_STATUS__" in out else "000"
    body = out.rsplit("\n__HTTP_STATUS__", 1)[0]

    if status in ("404", "410"):
        return url, "dead", status
    if status in ("403", "406", "429", "999", "000"):
        return url, "blocked", status

    m = CLOSED_RE.search(body)
    if m:
        return url, "closed", m.group(0)[:60]
    return url, "live", status


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    data = json.load(open(sys.argv[1]))
    urls = [d["Job URL"] if isinstance(d, dict) else d for d in data]
    urls = [u for u in urls if u]

    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(check, urls))

    verdicts = {u: {"verdict": v, "detail": d} for u, v, d in results}

    if "--json" in sys.argv:
        print(json.dumps(verdicts, indent=1))
    else:
        for u, v, d in sorted(results, key=lambda r: r[1]):
            print(f"{v:8} {d[:45]:47} {u}")
    print(f"\n{dict(Counter(v for _, v, _ in results))}", file=sys.stderr)


if __name__ == "__main__":
    main()
