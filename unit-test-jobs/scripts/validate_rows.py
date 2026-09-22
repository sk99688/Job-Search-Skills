#!/usr/bin/env python3
"""Mechanically validate candidate rows against the skill's rules before they are written.

Usage:
    python3 validate_rows.py candidates.json            # human-readable
    python3 validate_rows.py candidates.json --json     # machine-readable
    python3 validate_rows.py candidates.json --strict   # exit 1 if any FAIL

Exists because the sourcing pass grades its own homework and is measurably bad at
it: on 2026-09-22 the sourcing agents reported applying every filter, yet 27
geographically-restricted rows and 11 rows at over-cap companies reached the
table. Anything a regex can settle should be settled by a regex, so the human
verification effort is spent only on genuine judgment calls.

This catches MECHANICAL violations only. It cannot tell you whether a role is
really full-stack, or whether a company with no published headcount is under 200
-- that is the independent verifier agent's job (step 5 of the skill).

Verdicts per row:
    FAIL   -- breaks a rule outright; do not write it
    RESEARCH -- cannot be decided from the row alone; the verifier must resolve it
    PASS   -- no mechanical violation found
"""
import json
import re
import sys
from collections import Counter

REQUIRED = ["Title", "Company", "Category", "Platform", "Job URL", "Remote Fit", "Match"]

VALID = {
    "Category": {"Full Stack", "AI Engineer", "Applied AI", "Gen AI", "Data Engineer"},
    "Match": {"Direct", "Partial (~50%)"},
    "Remote Fit": {"Worldwide", "India", "Unclear"},
    "Platform": {"Wellfound", "Work at a Startup (YC)", "Arc.dev", "LinkedIn",
                 "Himalayas", "We Work Remotely", "Built In", "Other"},
}

RETIRED_PLATFORMS = {"Glassdoor", "ZipRecruiter", "Indeed", "Turing"}

# Places that disqualify a row when India is not also named. Not exhaustive by
# design -- the verifier agent is the backstop for anything this misses.
US_PLACES = (r"New York|Los Angeles|\bBoston\b|Chicago|San Francisco|Bay Area|Seattle|"
             r"Austin|Denver|\bNovi\b|\bTexas\b|California|Massachusetts|"
             r"United States|\bUSA?\b|U\.S\.")
OTHER_PLACES = (r"\bCanada\b|\bAustralia\b|\bLondon\b|\bEurope\b|LatAm|LATAM|\bMexico\b|"
                r"\bBrazil\b|Argentina|\bGermany\b|\bBerlin\b|\bUK\b|United Kingdom|"
                r"\bIreland\b|\bColombia\b|\bDubai\b|\bSingapore\b")
WORLDWIDE = r"worldwide|anywhere in the world|remote only, everywhere|\bglobal\b|10\+ countries"
# A timezone overlap with no place named is a working-hours constraint, not a
# geographic one -- someone in India can meet it, so it is not a fail.
TZ_ONLY = r"^\s*(overlap with|min\.? \d+ ?hr overlap)"

SIZE_OVER_CAP = r"\b(2[0-9]{2}|[3-9][0-9]{2}|[0-9]{4,})\b|201-500|500\+|1000\+|\b1k\+"
SIZE_UNKNOWN = r"unknown|check page|not shown|n/?a|hides"


def validate(row):
    problems, research = [], []

    for f in REQUIRED:
        if not str(row.get(f, "")).strip():
            problems.append(f"missing required field: {f}")

    for field, allowed in VALID.items():
        v = row.get(field)
        if v and v not in allowed:
            if field == "Platform" and v in RETIRED_PLATFORMS:
                problems.append(f"retired board: {v} is excluded, never write rows from it")
            else:
                problems.append(f"invalid {field}: {v!r}")

    url = str(row.get("Job URL", ""))
    if "linkedin.com" in url and "/jobs/view" in url:
        problems.append("LinkedIn Jobs URL: source from linkedin.com/posts hiring posts instead")

    raw_loc = str(row.get("Location Scope", ""))
    # Parenthetical notes are our own annotations ("verify not LatAm-only"), not the
    # listing's stated location. Matching them produced false FAILs on rows whose
    # location was actually unstated, so they are stripped before place-matching.
    loc = re.sub(r"\([^)]*\)", "", raw_loc).strip()

    # "Argentina +16 locations" is 17 countries, which is the skill's definition of
    # worldwide -- the leading country name must not make it look single-country.
    plus_n = re.search(r"\+\s*(\d+)\s*(?:more\s*)?locations?", loc, re.I)
    many_locations = bool(plus_n) and int(plus_n.group(1)) >= 9

    # APAC contains India, so an APAC-inclusive scope is India-eligible.
    has_india = re.search(r"\bindia\b|\bapac\b|asia[- ]pacific", loc, re.I)

    if loc and not has_india and not many_locations \
       and not re.search(WORLDWIDE, loc, re.I) and not re.search(TZ_ONLY, loc, re.I):
        if re.search(US_PLACES, loc, re.I):
            problems.append(f"names a US location with no India eligibility: {raw_loc!r}")
        elif re.search(OTHER_PLACES, loc, re.I):
            problems.append(f"single-country/regional scope: {raw_loc!r}")

    size = str(row.get("Size", ""))
    if re.search(SIZE_OVER_CAP, size) and not re.search(r"1-10|11-50|51-200|[1-9][0-9]?-", size):
        problems.append(f"company at/over the 200-employee cap: {size!r}")
    elif not size or re.search(SIZE_UNKNOWN, size, re.I):
        research.append("headcount not disclosed — verifier must research it before this row is trusted")

    sal = str(row.get("Salary", ""))
    if re.search(r"below \$40k|under \$40k", sal, re.I):
        research.append(f"salary flagged below the $40k floor: {sal!r}")

    if problems:
        return "FAIL", problems
    if research:
        return "RESEARCH", research
    return "PASS", []


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rows = json.load(open(sys.argv[1]))
    out = []
    for i, r in enumerate(rows):
        verdict, reasons = validate(r)
        out.append({"index": i, "company": r.get("Company"), "title": r.get("Title"),
                    "verdict": verdict, "reasons": reasons})

    if "--json" in sys.argv:
        print(json.dumps(out, indent=1, ensure_ascii=False))
    else:
        for o in out:
            if o["verdict"] == "PASS":
                continue
            print(f"{o['verdict']:8} {str(o['company'])[:22]:24} {str(o['title'])[:40]:42}")
            for why in o["reasons"]:
                print(f"         - {why}")

    counts = Counter(o["verdict"] for o in out)
    print(f"\n{dict(counts)}", file=sys.stderr)
    if "--strict" in sys.argv and counts.get("FAIL"):
        sys.exit(1)


if __name__ == "__main__":
    main()
