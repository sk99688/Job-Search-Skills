#!/usr/bin/env python3
"""Check peer lists against the under-50-employee rule before they are written.

Usage:
    python3 validate_peers.py peers.json            # human-readable
    python3 validate_peers.py peers.json --json     # machine-readable
    python3 validate_peers.py peers.json --clean    # print the lists with FAIL lines removed

Input is a JSON object mapping company name -> a peer block, one peer per line as
`Name — https://url — short clause`.

Peers must be SMALL companies, under 50 people. The point of a peer is that it is
a place the user could plausibly apply and get the same kind of role; a large
corporate fails that on every count -- different hiring process, different work,
and it would not clear the roster's own size rule either. The bar here is
deliberately tighter than the roster's under-200 rule, because a peer is a
speculative lead rather than a role already found.

A regex cannot know a private startup's headcount. What it CAN do is catch the
two ways big companies actually get in:
  1. Named corporates and household-name platforms, via a denylist.
  2. Scale language in the clause -- "incumbent", "several hundred", "enterprise
     leader" -- which is how a finder signals size without stating a number.

Everything else needs a human or verifier judgment, so this exits with FLAG
rather than pretending to certainty it does not have.
"""
import json
import re
import sys
from collections import Counter

# Household names and large platforms. Not exhaustive and not meant to be -- it is
# the floor, not the ceiling, of what should be excluded.
BIG_NAMES = r"""
salesforce|microsoft|google|amazon|\baws\b|meta\b|facebook|apple\b|oracle|\bsap\b|adobe|ibm\b|
workday|servicenow|atlassian|zoom\b|slack\b|dropbox|shopify|stripe\b|twilio|datadog|snowflake|
databricks|mongodb|elastic\b|hubspot|zendesk|freshworks|intercom|notion\b|asana|monday\.com|
otter\.ai|grammarly|canva|figma|gitlab|github|docusign|okta\b|crowdstrike|palo alto|
accenture|deloitte|infosys|\btcs\b|wipro|cognizant|capgemini|hcl\b|tech mahindra|
indeed|linkedin|glassdoor|ziprecruiter|upwork|fiverr|toptal|
uber\b|lyft|airbnb|booking\.com|expedia|doordash|instacart|
bright ?data|zyte|apify|oxylabs|smartproxy|
veeva|clarivate|iqvia|epic systems|cerner|athenahealth|
bullhorn|greenhouse|lever\b|workable|smartrecruiters
"""
BIG_RE = re.compile("|".join(x.strip() for x in BIG_NAMES.split("|") if x.strip()), re.I)

# How a finder signals "this is big" without giving a number.
SCALE_LANGUAGE = (r"incumbent|market leader|category leader|enterprise leader|"
                  r"several hundred|hundreds of (staff|employees)|thousands of (staff|employees)|"
                  r"publicly traded|public company|nasdaq|nyse|fortune \d+|"
                  r"\bmnc\b|multinational|over the (size )?cap|far over|well over|"
                  r"large (established|nonprofit|company|firm)|\bcorporate\b")

# An explicit headcount at or above 50.
BIG_NUMBER = r"\b(?:[5-9]\d|\d{3,})\s*(?:\+)?\s*(?:people|employees|staff|headcount)\b|\b(?:5[01]|[6-9]\d|\d{3,})-\d+\s*(?:people|employees)\b"

CONTEXT_MARK = r"\bCONTEXT\b"


def check_line(line):
    """Return (verdict, reason) for one peer line."""
    s = line.strip()
    if not s or s.lower().startswith("note:"):
        return "SKIP", ""
    # "no product space" (agencies) and "few direct peers" (genuinely thin spaces)
    # are both legitimate recorded outcomes, not malformed peer lines.
    if re.search(r"no product space|few (direct|verified|surviving)? ?peers|no (direct )?peers", s, re.I):
        return "SKIP", ""

    # Match the denylist against the COMPANY NAME only, never the description.
    # "Datapao — European Databricks consultancy" is a small shop that works with
    # Databricks; matching the whole line rejected it as though it were Databricks.
    name = re.split(r"\s+[—–-]\s+", s, maxsplit=1)[0].strip()

    # CONTEXT existed to admit large incumbents as orientation. That mechanism was
    # removed when the under-50 rule landed -- such a peer is simply out now.
    if re.search(CONTEXT_MARK, s, re.I):
        return "FAIL", "CONTEXT marker: large incumbents are no longer admitted at all"
    if BIG_RE.search(name):
        return "FAIL", f"named large company/platform: {BIG_RE.search(name).group(0)!r}"
    if re.search(SCALE_LANGUAGE, s, re.I):
        return "FAIL", f"scale language: {re.search(SCALE_LANGUAGE, s, re.I).group(0)!r}"
    if re.search(BIG_NUMBER, s, re.I):
        return "FAIL", f"headcount at or above 50: {re.search(BIG_NUMBER, s, re.I).group(0)!r}"
    if not re.search(r"https?://", s):
        return "FAIL", "no URL on the line"
    # No size signal either way. A regex cannot settle a private startup's size.
    if not re.search(r"\b(seed|pre-seed|series a|yc [wsf]\d{2}|founded 20\d\d|\d{1,2}\s*(people|employees))\b", s, re.I):
        return "FLAG", "no size or stage signal — verifier should confirm it is under 50"
    return "PASS", ""


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    data = json.load(open(sys.argv[1]))
    out, cleaned = [], {}

    for company, block in data.items():
        kept = []
        for line in str(block).split("\n"):
            verdict, reason = check_line(line)
            if verdict == "SKIP":
                kept.append(line)
                continue
            out.append({"company": company, "line": line.strip(), "verdict": verdict, "reason": reason})
            if verdict != "FAIL":
                kept.append(line)
        cleaned[company] = "\n".join(l for l in kept if l.strip())

    if "--clean" in sys.argv:
        print(json.dumps(cleaned, indent=1, ensure_ascii=False))
    elif "--json" in sys.argv:
        print(json.dumps(out, indent=1, ensure_ascii=False))
    else:
        for o in out:
            if o["verdict"] == "PASS":
                continue
            print(f"{o['verdict']:5} {o['company'][:20]:22} {o['line'][:60]:62} {o['reason'][:50]}")

    print(f"\n{dict(Counter(o['verdict'] for o in out))}", file=sys.stderr)


if __name__ == "__main__":
    main()
