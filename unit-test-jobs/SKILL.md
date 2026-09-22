---
name: unit-test-jobs
description: Audits the current repository's test suite — maps source files to their unit tests, flags untested exports, stale mocks, and coverage gaps introduced by recent commits, then compiles a prioritized backlog. Use when asked to review test coverage, audit the test suite, or invokes /unit-test-jobs.
---

# Find Remote Jobs

Repeats the job-search sweep built for this user, most recently overridden on 2026-09-21. Goal: surface **volume** of live, relevant postings, not a curated top-5 — the user wants as many real candidates as possible to screen themselves. **Output is stored in Airtable via the `airtable` MCP tools — never a Claude Artifact.** Do not call the `Artifact` tool anywhere in this skill. The old local file at `~/job-search/remote-roster.html` is deprecated as of 2026-09-21 (kept only as a historical snapshot) — Airtable is now the single source of truth, not a second copy kept in sync with it.

## Hard filters (apply all six — a listing failing any one is dropped, not just deprioritized)

1. **Role**: Full Stack Engineer, AI Engineer (incl. ML Engineer / LLM Engineer), or Data Engineer only. Skip PM, ops, marketing, sales-engineer, generic "software engineer" postings that don't map to one of these three.
2. **Salary floor: $40,000 USD/year minimum.**
   - Annualize anything quoted hourly/monthly/as a contract rate before comparing (state the assumption, e.g. "$25/hr × 40hr × 52wk ≈ $52k").
   - If a listing explicitly states a range or fixed pay **below** $40k, drop it entirely.
   - If a listing states **no salary at all** (common on Wellfound/YC), keep it — tag it `Salary: not disclosed — verify ≥$40k before applying`. Do not fabricate a number.
3. **Posting age: within the last 30 days.** If the platform shows a post date or "posted X ago" (LinkedIn listings usually do; individual Wellfound/Arc job pages sometimes do), drop anything older than 30 days. If no date is exposed at all (common on YC/Wellfound category pages), keep it but tag `Posted: date unknown — check listing page for freshness` rather than guessing a date. Prefer fetching the individual job page over the category page when you need the actual post date.
4. **No US work authorization / US-only restriction.** The user is based in India and wants overseas-friendly roles, not US-tied ones. Drop any listing that:
   - explicitly requires US citizenship, a US work permit, or "must be authorized to work in the US", or
   - is scoped only to a US location ("Remote, United States", "Remote only, US", or a specific US city like New York, San Francisco, Boston, Chicago, LA with no wider remote language).
   When location is ambiguous/unstated, keep it tagged `Unclear — verify on listing` rather than dropping it; only drop on an explicit US-only signal.
5. **Company size cap: ≤50 employees only.** Drop any listing whose company size is disclosed as more than 50 people (e.g. Wellfound/LinkedIn size bands like "51-200", "201-500", "500+"). This only applies to a *real disclosed* headcount — YC listings that never expose team size on the list view are not "large" by default; keep those but tag `Size unknown — verify small team on listing` rather than dropping or guessing a number.
6. **No single-country / regional restriction.** Drop any listing scoped to one specific non-US country or region (e.g. "Remote only, Canada", "Remote, Europe", "Remote only, Mexico City", "Remote, LatAm", "London +1"). Only **Worldwide** (remote/everywhere, 10+ countries) and **India**-tagged roles clear this filter now — a role that used to be kept and tagged `Regional` (non-US but country/region-specific) is now dropped entirely, not just tagged. Roles with unstated/ambiguous location scope are still kept, tagged `Unclear — verify on listing`.

## Sourcing — go beyond the 4 named platforms

Don't stop at Wellfound / Arc.dev / YC / LinkedIn. Also run general web search for companies anywhere (US-HQ'd companies that hire globally are fine — the filter is about the *role's* eligibility, not the company's home country) hiring remote for these three roles (Google-style queries mixing role + "remote" + "hiring" + "worldwide"/"international", plus boards that surfaced usefully before: Himalayas, We Work Remotely, Built In, Glassdoor, ZipRecruiter, Indeed, Turing.com). Any remote opening that clears the six hard filters above is in scope, not just postings from the four named platforms.

## Resolving "company-only" results

YC's Work at a Startup and some LinkedIn/Google results often surface only a **company** (name, website, LinkedIn company page) rather than a specific job listing — e.g. a "Jobs at X (batch)" company page. Never list a bare company name as if it were a role. When you hit one of these:

1. Fetch the company's actual jobs/careers page (own site) or LinkedIn Jobs tab.
2. Pull the real open role(s) that match Full Stack / AI Engineer / Data Engineer.
3. Apply the salary and posting-age filters to what you find there before including it.
4. If you can't get past the company-page level (no accessible jobs list), don't write it to Airtable at all — a company page isn't a role, and a row without a real listing pollutes the table. Collect these and mention them in the step 7 report as companies worth checking manually.

## Steps

1. **Search each platform** with WebSearch, `allowed_domains` scoped per platform, one query per role (Full Stack / AI Engineer / Data Engineer): `wellfound.com`, `arc.dev`, `workatastartup.com`, `linkedin.com`, plus at least one unrestricted query per role mixing "remote" + "startup" + "$" salary language + "India" for general web coverage.

2. **Fetch the live category/role pages** with WebFetch (not just search snippets) for real volume:
   - `https://wellfound.com/role/r/full-stack-developer`, `/role/r/ai-engineer`, `/role/r/data-engineer` (also `/role/l/<role>/india`)
   - `https://arc.dev/remote-jobs/full-stack`, `/ai`, `/data-engineer` (also `/en-in/remote-jobs`)
   - For workatastartup.com (JS-rendered SPA — WebFetch usually can't extract listings directly): use WebSearch scoped to `workatastartup.com` and trust only the structured **Links** array (title + URL), never the tool's prose summary (it has previously mismatched title/company — verify any claim against an actual title+URL pair before using it).

   Ground every row in a real title + URL pair. Never invent a company, size, salary, or URL from a prose summary alone.

3. **Apply the six hard filters** (role match, $40k+ or undisclosed, ≤30 days old or unknown-date-flagged, not US-only/US-authorization-restricted, ≤50 employees or size-unknown-flagged, Worldwide/India only — no single-country regional roles) and the company-only resolution step above.

4. **De-duplicate** against what's already in the Airtable table: same company + same title = skip, unless the URL changed (a changed URL means the listing was reposted, which is an update, not a new row). You don't hand-roll this lookup — `scripts/sync_to_airtable.py` performs it in step 6, fetching every existing record and filtering the candidate set before a single write goes out. What matters at this step is that you carry `Company` and `Title` on every candidate row so the script has something to match on.

5. **Verify each surviving URL is actually live before writing it to Airtable.** Run a link check on every row that made it through steps 3-4:
   `curl -s -o /dev/null -w "%{http_code}" -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36" -L --max-time 15 <url>`
   Interpret the result carefully — job platforms behave inconsistently under curl, so don't over-trust a single status code:
   - **404 / 410 / an explicit "not found" or "no longer available" response** → drop the row entirely, the listing is gone.
   - **200** → keep it, but this alone isn't proof the role is still open — Wellfound and YC often return 200 for a closed/expired listing because the "no longer accepting applications" state renders client-side, not server-side.
   - **403 / 999 / timeout / connection refused** (LinkedIn in particular blocks non-browser requests like this) → do **not** treat as dead. Keep the row but tag it `Link check: blocked by platform — verify manually`. Never silently drop a real listing just because curl got refused.
   - Run this on the final candidate set only (post-filter, post-dedup), not on every raw search result — no need to burn requests on rows that would've been dropped anyway.

6. **Write to Airtable — never the Artifact tool, never the old local HTML file.** This board lives in Airtable now (migrated 2026-09-22). Fixed IDs, don't look these up each run:
   - Base: `appNA1YixBgwXUGMY` ("Job Search Tracker")
   - Table: `tblagnwEFzc1SWwm5` ("Remote Roster")

   Field schema (all already created — never call `create_table` again for this base): `Title`, `Company` (single line text), `Category` (single select: Full Stack / AI Engineer / Data Engineer), `Platform` (single select: Wellfound / Work at a Startup (YC)), `Size`, `Salary`, `Posted`, `Location Scope` (single line text), `Remote Fit` (single select: Worldwide / India / Unclear), `Level`, `Job URL` (url), `Link Check` (single select: Live / Blocked - verify manually / Removed - verify), `Applied` (checkbox), `Status` (single select: New / Applied / Interviewing / Rejected / Offer), `Notes` (long text).

   Process each run — the dedup check happens inside the script, before anything is written:
   1. Write the surviving candidates from step 5 to a JSON array (a scratch file is fine), one object per role using the field names above.
   2. Run `python3 scripts/sync_to_airtable.py <that file>`. In one pass it fetches every existing record, drops any candidate matching an existing `(Company, Title)`, and only then POSTs what's left in batches of 10. Nothing reaches the table without clearing that check, so re-running the same candidate set is harmless.
   3. Read its output: it prints how many were skipped as duplicates, how many were created, and any duplicate whose `Job URL` changed — those are reposted listings, so follow up on each with `update_records` (job-data fields only).

   A single `create_record` call is fine for one or two stragglers, but don't hand-roll the dedup for them — check against the script's fetched list rather than assuming a row is new.
   - Existing rows that changed (URL, salary, posted-date, link-check result) → `update_records` with **only** the job-data fields.
   - **Never touch `Applied`, `Status`, or `Notes` on an update** — those are the user's own tracking fields; overwriting them destroys their work.
   - A row that no longer clears the six hard filters or fails the link check → set `Link Check` to `Removed - verify`, don't delete the record (preserves the user's notes/status on it).
   - Leave `Link Check` blank on a row rather than guessing "Live" if step 5 wasn't actually run against it this pass.

7. **Report back concisely**: how many new roles found per category/platform, how many were dropped for salary/age/size/region, how many were dropped or flagged by the link check, and call out anything especially good (Worldwide or India-tagged, senior-level, disclosed salary well above $40k). Don't re-paste the whole table in chat — the Airtable base is the deliverable.

## Bundled scripts

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
