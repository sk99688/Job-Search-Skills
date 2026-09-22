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
    "Remote Fit": {"Worldwide", "Multi-country", "Unclear"},   # "India" retired 2026-09-22
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
INDIA_PLACES = (r"\bindia\b|bangalore|bengaluru|mumbai|delhi|\bpune\b|noida|indore|bhopal|"
                r"hubli|chennai|gurgaon|hyderabad|kolkata|ahmedabad|jaipur|surat")
WORLDWIDE = r"worldwide|anywhere in the world|remote only, everywhere|\bglobal\b|10\+ countries"
# A timezone overlap with no place named is a working-hours constraint, not a
# geographic one -- someone in India can meet it, so it is not a fail.
TZ_ONLY = r"^\s*(overlap with|min\.? \d+ ?hr overlap)"

SIZE_OVER_CAP = r"\b(2[0-9]{2}|[3-9][0-9]{2}|[0-9]{4,})\b|201-500|500\+|1000\+|\b1k\+"
# Any wording that means "we did not establish a headcount". Kept broad on purpose:
# a sourcing agent wrote "Headcount unverified" and silently bypassed this gate,
# because the phrasing is the agent's free choice while the rule is not.
SIZE_UNKNOWN = (r"unknown|unverified|unconfirmed|disputed|conflicting|not verified|not confirmed|check page|"
                r"not shown|not disclosed|undisclosed|n/?a|hides|tbd|\?")

# A long country list that is entirely one region is regional, not worldwide. A
# 20-country all-European list passed the "10+ countries" shortcut while offering
# no India eligibility at all.
REGION_BOUND = r"\beurope|european|\bEEA\b|\bEU\b|\bLATAM\b|latin america|\bAPAC-only|\bnordic"


MONTHLY_FLOOR = 4000     # USD/month
ANNUAL_FLOOR = 48000     # USD/year, the same floor expressed annually
INR_PER_USD = 88         # rough; only used to reject figures far below the floor

# Pay that cannot be annualised honestly. Rule 2 says to annualise hourly rates,
# but applying that to per-task or per-project gig pay manufactures a salary that
# does not exist -- mercor was recorded as "$85/hour ≈ $176k/yr" when the listing
# actually said $400 per accepted task at ~15hr/week.
GIG = r"per (accepted )?(task|project|assignment|gig|milestone)|per-task|piece[- ]rate|\bbounty\b"


def check_salary(sal):
    """Return (verdict, detail) for a salary string against the monthly floor."""
    s = sal.strip()
    if not s or re.search(r"not disclosed|undisclosed|no salary|not stated", s, re.I):
        return "OK", ""                      # rule 2 keeps undisclosed pay, tagged

    if re.search(GIG, s, re.I):
        return "RESEARCH", f"gig/per-task pay cannot be annualised into a salary: {s!r}"

    if re.search(r"likely below|below \$?4?0?k|under \$?4?0?k", s, re.I):
        return "FAIL", f"flagged below the pay floor: {s!r}"

    # Monthly figures are where the floor actually bites -- a $900/month role read
    # as "not disclosed" is how an ~$11k/yr listing passed a $40k filter once.
    for m in re.finditer(r"(?:US)?\$\s*([\d,]+(?:\.\d+)?)\s*(?:k)?\s*(?:/|per |a )\s*(?:month|mo\b)", s, re.I):
        val = float(m.group(1).replace(",", ""))
        if "k" in m.group(0).lower():
            val *= 1000
        if val < MONTHLY_FLOOR:
            return "FAIL", f"${val:,.0f}/month is below the ${MONTHLY_FLOOR:,}/month floor: {s!r}"

    for m in re.finditer(r"(?:₹|INR|Rs\.?)\s*([\d,]+)\s*(?:k)?\s*(?:/|per |a )\s*(?:month|mo\b)", s, re.I):
        val = float(m.group(1).replace(",", ""))
        if "k" in m.group(0).lower():
            val *= 1000
        if val / INR_PER_USD < MONTHLY_FLOOR:
            return "FAIL", f"₹{val:,.0f}/month ≈ ${val/INR_PER_USD:,.0f} is below the floor: {s!r}"

    # A figure already judged as monthly must not be re-read as an annual one:
    # "$5,000 per month" is $60k/yr and passes, but looks like a failing annual
    # number if the period is ignored.
    if re.search(r"(?:/|per |a )\s*(?:month|mo\b)", s, re.I):
        return "OK", ""

    # Annual figures, including ranges -- judge on the bottom of the range.
    lows = []
    for m in re.finditer(r"(?:US)?\$\s*([\d,]+(?:\.\d+)?)\s*(k|,000)?", s, re.I):
        val = float(m.group(1).replace(",", ""))
        if m.group(2):
            val *= 1000
        if val >= 1000:
            lows.append(val)
    if lows and max(lows) < ANNUAL_FLOOR and not re.search(r"/\s*(hr|hour)", s, re.I):
        return "FAIL", f"top figure ${max(lows):,.0f} is below the ${ANNUAL_FLOOR:,}/yr floor: {s!r}"

    return "OK", ""


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

    # Company LinkedIn must be the company page. A personal profile or a search URL
    # looks right at a glance and is useless (or misleading) when clicked.
    li = str(row.get("Company LinkedIn", "")).strip()
    if li:
        if "/company/" not in li:
            problems.append(f"Company LinkedIn is not a /company/ page: {li!r}")
        elif re.search(r"/in/|/search/|/jobs/", li):
            problems.append(f"Company LinkedIn points at a profile/search/job, not the company: {li!r}")

    raw_loc = str(row.get("Location Scope", ""))
    # Parenthetical notes are our own annotations ("verify not LatAm-only"), not the
    # listing's stated location. Matching them produced false FAILs on rows whose
    # location was actually unstated, so they are stripped before place-matching.
    loc = re.sub(r"\([^)]*\)", "", raw_loc).strip()

    # "Argentina +16 locations" is 17 countries, which is the skill's definition of
    # worldwide -- the leading country name must not make it look single-country.
    plus_n = re.search(r"\+\s*(\d+)\s*(?:more\s*)?locations?", loc, re.I)
    many_locations = bool(plus_n) and int(plus_n.group(1)) >= 9
    # ...unless every one of those countries sits in a single region, in which case
    # the breadth is illusory and the role is still not open to a candidate in India.
    if re.search(REGION_BOUND, loc, re.I):
        many_locations = False

    # India-scoped listings are excluded as of 2026-09-22: the user wants international
    # remote work, not the Indian domestic market, whose local rates rarely reach the
    # pay floor. But India-INCLUDED is not India-ONLY -- a role open to several
    # countries, one being India, is exactly what to keep.
    #
    # Deciding which is which by "is any word left after striking India out?" does not
    # work: "Remote, Bangalore Urban" leaves the word "Urban" and looks multi-country.
    # So ask the narrower question instead -- is any OTHER RECOGNISED PLACE named?
    india_named = bool(re.search(INDIA_PLACES, loc, re.I))
    without_india = re.sub(INDIA_PLACES, " ", loc, flags=re.I)
    other_place_named = bool(
        re.search(US_PLACES, without_india, re.I)
        or re.search(OTHER_PLACES, without_india, re.I)
        or re.search(r"\bapac\b|asia[- ]pacific|north america|oceania|\bjersey\b|\bgeorgia\b", without_india, re.I)
        or many_locations
    )

    if india_named and not other_place_named:
        problems.append(f"India-only scope: the user wants international remote work, not domestic: {raw_loc!r}")

    # A list naming India alongside other countries is multi-country, so the US/region
    # checks below must not then fail it for containing "United States".
    multi_country = india_named and other_place_named
    apac = re.search(r"\bapac\b|asia[- ]pacific", loc, re.I)

    if loc and not multi_country and not apac and not many_locations \
       and not re.search(WORLDWIDE, loc, re.I) and not re.search(TZ_ONLY, loc, re.I):
        if re.search(US_PLACES, loc, re.I):
            problems.append(f"names a US location with no India eligibility: {raw_loc!r}")
        elif re.search(OTHER_PLACES, loc, re.I):
            problems.append(f"single-country/regional scope: {raw_loc!r}")

    # Strip parentheticals before matching: "~170 employees (Apr 2026)" was failing
    # as over-cap because the four-digit branch matched the YEAR, not a headcount.
    size = re.sub(r"\([^)]*\)", "", str(row.get("Size", ""))).strip()
    if re.search(SIZE_OVER_CAP, size) and not re.search(r"1-10|11-50|51-200|[1-9][0-9]?-", size):
        problems.append(f"company at/over the 200-employee cap: {size!r}")
    elif not size or re.search(SIZE_UNKNOWN, size, re.I):
        research.append("headcount not disclosed — verifier must research it before this row is trusted")

    verdict, detail = check_salary(str(row.get("Salary", "")))
    if verdict == "FAIL":
        problems.append(detail)
    elif verdict == "RESEARCH":
        research.append(detail)

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
