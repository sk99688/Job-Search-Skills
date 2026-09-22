---
name: unit-test-jobs
description: Audits the current repository's test suite — maps source files to their unit tests, flags untested exports, stale mocks, and coverage gaps introduced by recent commits, then compiles a prioritized backlog. Use when asked to review test coverage, audit the test suite, or invokes /unit-test-jobs.
---

# Find Remote Jobs

Repeats the job-search sweep built for this user, most recently overridden on 2026-09-21. Goal: surface **volume** of live, relevant postings, not a curated top-5 — the user wants as many real candidates as possible to screen themselves. **Output is stored in Airtable via the `airtable` MCP tools — never a Claude Artifact.** Do not call the `Artifact` tool anywhere in this skill. The old local file at `~/job-search/remote-roster.html` is deprecated as of 2026-09-21 (kept only as a historical snapshot) — Airtable is now the single source of truth, not a second copy kept in sync with it.

## Filters (rules 2-6 are hard drops; rule 1 is a 50%-match threshold — read the difference carefully)

1. **Role — include on a ~50% match, don't demand an exact one.** Target areas: **Full Stack**, **AI Engineering**, **Applied AI**, **Gen AI**, and **Data Engineering**. The user would rather screen a few loose matches themselves than never see a role because its title was worded oddly, so the bar here is deliberately generous: if you can make a reasonable case that roughly half the role maps to one of those areas, include it and tag `Match` as `Partial (~50%)`. Only when the whole role clearly sits in one of the target areas does it get `Match: Direct`.
   - Include on partial match: "Software Engineer, AI Platform", "Backend Engineer (LLM products)", "MLOps Engineer", "Analytics Engineer", "Forward Deployed Engineer", "Founding Engineer" at an AI company, "Product Engineer" where the stack is clearly full-stack.
   - Still drop outright: roles in a different discipline entirely — PM, design, marketing, sales/sales-engineering, recruiting, support, QA-only, pure DevOps/SRE with no data or application work. A 50% threshold is about generous *interpretation* of engineering titles, not about admitting non-engineering roles.
   - When genuinely torn, include it and let `Match: Partial (~50%)` carry the uncertainty — a row the user skims past costs them seconds, a role never surfaced costs them the opportunity.
2. **Salary floor: $40,000 USD/year minimum.**
   - Annualize anything quoted hourly/monthly/as a contract rate before comparing (state the assumption, e.g. "$25/hr × 40hr × 52wk ≈ $52k").
   - If a listing explicitly states a range or fixed pay **below** $40k, drop it entirely.
   - If a listing states **no salary at all** (common on Wellfound/YC), keep it — tag it `Salary: not disclosed — verify ≥$40k before applying`. Do not fabricate a number.
3. **Posting age: within the last 30 days.** If the platform shows a post date or "posted X ago" (LinkedIn listings usually do; individual Wellfound/Arc job pages sometimes do), drop anything older than 30 days. If no date is exposed at all (common on YC/Wellfound category pages), keep it but tag `Posted: date unknown — check listing page for freshness` rather than guessing a date. Prefer fetching the individual job page over the category page when you need the actual post date.
4. **No US work authorization / US-only restriction.** The user is based in India and wants overseas-friendly roles, not US-tied ones. Drop any listing that:
   - explicitly requires US citizenship, a US work permit, or "must be authorized to work in the US", or
   - is scoped to a US location. **"Scoped to" means the listing names a US place at all** — "Remote, United States", "Remote only, US", "Onsite or remote, New York City +2", "Remote, San Francisco +1", "Onsite or remote, California +1" are all drops. A named city or state is a location constraint even when the word "only" is absent and even when "remote" appears alongside it, because a company that lists specific US offices is hiring into those offices' jurisdiction.
   - This rule caused a real leak on 2026-09-22: 21 US-city-anchored rows were kept as `Unclear` on the reasoning that "New York City +2" wasn't an *explicit* US-only signal. That reading is wrong. If a US place is named, drop it.
5. **Company size cap: ≤50 employees only.** Drop any listing whose company size is disclosed as more than 50 people (e.g. Wellfound/LinkedIn size bands like "51-200", "201-500", "500+"). This only applies to a *real disclosed* headcount — YC listings that never expose team size on the list view are not "large" by default; keep those but tag `Size unknown — verify small team on listing` rather than dropping or guessing a number.
6. **No single-country / regional restriction.** Only three kinds of location clear this filter:
   - **Worldwide** — "remote, anywhere", "Anywhere in the World", or a list naming 10+ countries.
   - **India-inclusive** — names India, an Indian city, or a country list that contains India (e.g. "Georgia, India, Jersey, Mexico, United States" is fine; the user is eligible).
   - **Genuinely unstated** — the listing exposes no location at all. Tag `Unclear — verify on listing`.

   Everything else is a drop: "Remote only, Canada", "Remote, Europe", "Remote only, Mexico City", "Remote, LatAm", "London +1", "Remote only, Australia +4".

   **The critical distinction, and the one that has already gone wrong once:** `Unclear` means *no location was stated*. It does not mean *a location was stated and you weren't sure what to make of it*. A listing naming any specific city, state, or country has stated its location — if that location isn't India and isn't 10+ countries, drop it. Parking named-but-awkward locations in `Unclear` is what let 27 geographically-restricted rows into the table on 2026-09-22.

   A bare timezone-overlap requirement with no place named ("Min. 4 hr overlap with Eastern Time") is not a geographic restriction — keep it as `Unclear`, since a candidate in India can in principle meet it.

## Sourcing — weight every board, don't let two dominate

Every board in this list carries equal weight. Past runs drifted into being ~80% Wellfound plus a handful of YC rows, purely because those two are the easiest to scrape — that's a sampling artifact, not a reflection of where the jobs are, and it quietly hides whole sets of roles from the user.

Give each of these a real attempt every run, and record which one a row came from in `Platform`:

`wellfound.com` · `arc.dev` · `workatastartup.com` (YC) · `linkedin.com/posts/…` (see below) · `himalayas.app` · `weworkremotely.com` · `builtin.com`

**LinkedIn: hiring posts only, never the Jobs board.** Source from feed posts (`linkedin.com/posts/…`) where a founder or hiring manager announces a role, not from `linkedin.com/jobs/view/…`. The reason is measured, not theoretical: on 2026-09-22 ten LinkedIn Jobs rows were added and **nine were already closed when re-checked hours later** — that board's India listings churn far too fast to be worth a row. Hiring posts also tend to state compensation in the text, which the Jobs board almost never does.

Search them with queries scoped to `linkedin.com` that target post URLs and pair hiring language with a pay signal, e.g. `site:linkedin.com/posts "hiring" "remote" "full stack" "$"`, swapping in each target area and varying the pay wording (`$`, `USD`, `LPA`, `per annum`, `salary`, `compensation`). A post only earns a row when it names a real role **and** clears rule 2 on a stated figure — a "we're hiring, DM me" post with no pay and no role detail is a lead, not a row, so put it in the step 7 report instead. Set `Platform` to `LinkedIn` and put the post URL in `Job URL`.

**Never source from these — excluded 2026-09-22, do not reintroduce them:**
- `glassdoor.com` and `ziprecruiter.com` — excluded at the user's instruction. Don't write rows from them and don't cite their links.
- `indeed.com` — hard-blocks automated access (403 on search, 401 on individual pages), so any row from it would have to be fabricated rather than grounded.
- `turing.com` — a talent-marketplace funnel with no discrete dated postings; its job URLs 301-redirect to generic role landing pages.

Run at least one query per target area per board rather than exhausting one board before moving on, and in the step 7 report state the per-board counts — including the boards that returned nothing, since a persistent zero is a signal the approach for that board needs fixing (blocked fetch, wrong URL shape) rather than evidence it has no jobs.

Also run unrestricted web searches for companies anywhere hiring remotely for these areas (US-HQ'd companies that hire globally are fine — the filter is about the *role's* eligibility, not the company's home country), mixing role + "remote" + "hiring" + "worldwide"/"international". Anything clearing the filters is in scope regardless of which board it came from; use `Platform: Other` when it came from somewhere not in the list above.

## Resolving "company-only" results

YC's Work at a Startup and some LinkedIn/Google results often surface only a **company** (name, website, LinkedIn company page) rather than a specific job listing — e.g. a "Jobs at X (batch)" company page. Never list a bare company name as if it were a role. When you hit one of these:

1. Fetch the company's actual jobs/careers page (own site) or LinkedIn Jobs tab.
2. Pull the real open role(s) that clear rule 1 — Full Stack / AI Engineering / Applied AI / Gen AI / Data Engineering, at the ~50% threshold.
3. Apply the salary and posting-age filters to what you find there before including it.
4. If you can't get past the company-page level (no accessible jobs list), don't write it to Airtable at all — a company page isn't a role, and a row without a real listing pollutes the table. Collect these and mention them in the step 7 report as companies worth checking manually.

## Steps

1. **Search every board** with WebSearch, `allowed_domains` scoped per board, at least one query per target area (Full Stack / AI Engineering / Applied AI / Gen AI / Data Engineering) against each domain in the sourcing list above — not just the first two that return results. Add unrestricted queries per area mixing "remote" + "startup" + "$" salary language + "India" for coverage beyond the named boards.

2. **Fetch the live category/role pages** with WebFetch (not just search snippets) for real volume:
   - `https://wellfound.com/role/r/full-stack-developer`, `/role/r/ai-engineer`, `/role/r/data-engineer` (also `/role/l/<role>/india`)
   - `https://arc.dev/remote-jobs/full-stack`, `/ai`, `/data-engineer` (also `/en-in/remote-jobs`)
   - For workatastartup.com (JS-rendered SPA — WebFetch usually can't extract listings directly): use WebSearch scoped to `workatastartup.com` and trust only the structured **Links** array (title + URL), never the tool's prose summary (it has previously mismatched title/company — verify any claim against an actual title+URL pair before using it).

   Ground every row in a real title + URL pair. Never invent a company, size, salary, or URL from a prose summary alone.

3. **Apply the filters**: rule 1 as a ~50% inclusion threshold (tagging `Match` Direct or Partial), then the five hard drops — $40k+ or undisclosed, ≤30 days old or unknown-date-flagged, not US-only/US-authorization-restricted, ≤50 employees or size-unknown-flagged, Worldwide/India only (no single-country regional roles) — plus the company-only resolution step above.

4. **De-duplicate** against what's already in the Airtable table: same company + same title = skip, unless the URL changed (a changed URL means the listing was reposted, which is an update, not a new row). You don't hand-roll this lookup — `scripts/sync_to_airtable.py` performs it in step 6, fetching every existing record and filtering the candidate set before a single write goes out. What matters at this step is that you carry `Company` and `Title` on every candidate row so the script has something to match on.

5. **Verify every surviving listing still exists and is still open**, before writing anything:

   ```bash
   python3 scripts/check_listings.py candidates.json --json > verdicts.json
   ```

   Don't hand-roll this with `curl` in the shell. A status code alone cannot tell you a role is closed — Wellfound, YC and LinkedIn all return **200** for a filled role and disclose it only in the page body, so a status-only check keeps dead roles. The script fetches the body and looks for closed/filled/expired markers as well as the status code. (It also exists because the ad-hoc shell version of this check had broken quoting, returned an empty result set, and nearly let 104 unverified rows through on 2026-09-22.)

   Act on each verdict:
   - **`live`** → write it.
   - **`closed`** → drop it. The listing exists but the role is filled or withdrawn; a closed role is noise, and the user has asked not to see them resurface.
   - **`dead`** (404/410) → drop it.
   - **`blocked`** (403/406/429/timeout) → **keep it**, tagged `Link Check: Blocked - verify manually`. Bot protection is not evidence the role is gone, and silently dropping a real listing because curl got refused is the worse error.

   Run it on the final candidate set only — post-filter, post-dedup — rather than on every raw search result.

   Re-run it over the existing table periodically too, not just on new candidates: rows go stale in place. A pass on 2026-09-22 found 9 closed and 3 newly-404 rows that had been live when first added.

6. **Write to Airtable — never the Artifact tool, never the old local HTML file.** This board lives in Airtable now (migrated 2026-09-22). Fixed IDs, don't look these up each run:
   - Base: `appNA1YixBgwXUGMY` ("Job Search Tracker")
   - Table: `tblagnwEFzc1SWwm5` ("Remote Roster")

   Field schema (all already created — never call `create_table` again for this base): `Title`, `Company` (single line text), `Category` (single select: Full Stack / AI Engineer / Applied AI / Gen AI / Data Engineer), `Match` (single select: Direct / Partial (~50%) — per rule 1), `Platform` (single select: Wellfound / Work at a Startup (YC) / Arc.dev / LinkedIn / Himalayas / We Work Remotely / Built In / Other — the Glassdoor, ZipRecruiter, Indeed and Turing options still exist in Airtable from earlier runs but are retired; never write them), `Size`, `Salary`, `Posted`, `Location Scope` (single line text), `Remote Fit` (single select: Worldwide / India / Unclear), `Level`, `Job URL` (url), `Company Website` (url), `Company Notes` (long text), `Link Check` (single select: Live / Blocked - verify manually / Removed - verify), `Applied` (checkbox), `Status` (single select: New / Applied / Interviewing / Rejected / Offer), `Notes` (long text).

   **`Company Website` and `Company Notes` are part of every row, not optional extras.** Most job boards show a company name and nothing else, which leaves the user unable to judge whether a role is worth an application without searching the company themselves for every single row. Fill `Company Website` with the company's own domain — its actual product site, never a Wellfound/LinkedIn/Crunchbase profile — and `Company Notes` with one line on what they do plus any team-size or funding-stage signal you found. The size signal matters especially, since rule 5 caps at 50 employees and most boards don't disclose headcount, so a note like "seed-stage, ~15 people per their about page" is often the only way that rule can be applied at all. Leave `Company Website` blank rather than guessing a plausible-looking domain — a wrong link is worse than an empty one, because the user will act on it. When the "company" is a staffing agency or talent marketplace (Lemon.io, A.Team, Toptal, Proxify, Arc Exclusive and similar), say so in `Company Notes`: the end client is unknown, so neither the size rule nor the company research means what it normally would.

   A single-select value that doesn't exist yet isn't a problem: the sync script sends `typecast: true`, so Airtable creates the option on write. This matters because Airtable's field-update API cannot edit select choices — typecast is the only programmatic way to add one. So a new job board or a role category you haven't used before just works; don't try to pre-register it.

   Process each run — the dedup check happens inside the script, before anything is written:
   1. Write the surviving candidates from step 5 to a JSON array (a scratch file is fine), one object per role using the field names above.
   2. Run `python3 scripts/sync_to_airtable.py <that file>`. In one pass it fetches every existing record, drops any candidate matching an existing `(Company, Title)`, and only then POSTs what's left in batches of 10. Nothing reaches the table without clearing that check, so re-running the same candidate set is harmless.
   3. Read its output: it prints how many were skipped as duplicates, how many were created, and any duplicate whose `Job URL` changed — those are reposted listings, so follow up on each with `update_records` (job-data fields only).

   A single `create_record` call is fine for one or two stragglers, but don't hand-roll the dedup for them — check against the script's fetched list rather than assuming a row is new.
   - Existing rows that changed (URL, salary, posted-date, link-check result) → `update_records` with **only** the job-data fields.
   - **Never touch `Applied`, `Status`, or `Notes` on an update** — those are the user's own tracking fields; overwriting them destroys their work.
   - A row that no longer clears the filters or fails the link check → set `Link Check` to `Removed - verify`, don't delete the record (preserves the user's notes/status on it).
   - Leave `Link Check` blank on a row rather than guessing "Live" if step 5 wasn't actually run against it this pass.

7. **Report back concisely**: new roles per target area and **per board — list every board including the ones that returned zero**, since a persistent zero means that board's approach needs fixing rather than that it had nothing. Also report the Direct vs Partial (~50%) split, how many were dropped for salary/age/size/region, how many the link check dropped or flagged, and any company-only leads worth checking by hand. Call out anything especially good (Worldwide or India-tagged, senior, disclosed salary well above $40k). Don't re-paste the whole table in chat — the Airtable base is the deliverable.

## Bundled scripts

- **`scripts/check_listings.py`** — takes a JSON array of URLs (or of row dicts with a `Job URL` key) and returns a verdict per listing: `live`, `closed`, `dead`, or `blocked`. It checks the response body for closed/filled/expired wording as well as the HTTP status, because every major board returns 200 for a filled role and only discloses it in the page text. Use it in step 5 on new candidates, and periodically over the whole table to catch rows that have gone stale in place.

  ```bash
  python3 scripts/check_listings.py candidates.json --json > verdicts.json
  ```

- **`scripts/sync_to_airtable.py`** — takes a JSON array of candidate rows (a file path, or `-` for stdin) and writes the new ones to Airtable. It fetches every existing record first, skips anything matching an existing `(Company, Title)`, batches 10 records per request, and prints any duplicate whose `Job URL` changed along with its record id so you can follow up with `update_records`. It only ever creates, never updates — which is precisely what makes it safe to run unattended, since it structurally cannot touch the user-owned `Applied` / `Status` / `Notes` fields on existing rows. Reads the token from `~/.claude.json` (or the `AIRTABLE_API_KEY` env var); the token is never stored in the script or the repo.

  ```bash
  python3 scripts/sync_to_airtable.py candidates.json
  ```

## Known platform quirks (learned 2026-09-18)

- Wellfound's `/role/r/<role>` pages are the highest-signal source: real company size and location tags. Post dates usually require opening the individual job page.
- Arc.dev's public remote-jobs pages skew toward staffing agencies and mid/large companies (Zillow, IBM, Capgemini, Luxoft) rather than small startups — cross-check size before including.
- workatastartup.com won't render its listings to a plain fetch; rely on WebSearch's Links array for title+URL. Many results are "Jobs at X" company pages, not specific roles — resolve per the "company-only results" section above instead of listing the company page as-is.
- LinkedIn search results returned via WebSearch are almost always category/aggregate pages (counts like "1,000+ roles"), not individual postings — surface them in the step 7 report as live search starting points rather than fabricating specific listings from them. When a specific LinkedIn job URL is found, its "posted X ago" text is usually reliable for the freshness filter.
- Company size only comes through as a real number on Wellfound/LinkedIn-style listings (bands like "51-200"). YC's workatastartup.com never exposes headcount on the list view — treat those as `Size unknown`, never assume small (or large) just because it's YC.
