---
name: peer-companies
description: Maps the competitive landscape around a company — finds startups working in the same problem space with a similar product idea, and records their websites. Make sure to use this whenever the user names a company and asks who else is in that space, who the competitors or alternatives are, what the market map looks like, or wants to widen a search from one company to the companies adjacent to it, even if they don't use the word "competitor". Also runs over the Remote Roster table to populate its Peer Companies column.
---

# Peer companies

Given a company, find the other startups solving the same problem, and record where to find them.

The reason this exists is narrower than general market research, and it shapes every judgment below: a company worth applying to is a strong signal that **its competitors are worth applying to as well**. They build the same things, need the same skills, sit at a similar stage, and are frequently hiring the same roles at the same moment — often without ever appearing on the job boards the roster is built from. One interesting company is really a pointer to five.

## What counts as a peer

A peer solves the **same problem for the same kind of customer**. Not merely the same technology, and not merely the same industry.

- Peers of an AI meeting-notetaker are other meeting-notetakers — not "other companies using LLMs", which is most of them now and tells the user nothing.
- Peers of a healthcare-claims automation startup are other claims-automation startups, not hospital software generally.
- Shared tech stack is not kinship. "Also builds with React" is noise.

Aim for **3-5 peers**. Fewer than three usually means the space was read too narrowly; more than five means it was read too broadly and the list has stopped being useful.

## Size rule: peers must be small — under 50 people. No MNCs, no corporates.

A peer earns its place by being somewhere the user could plausibly apply and get the same kind of role. A large company fails that on every count: different hiring process, different work, different odds, and it would not clear the roster's own size rule either. So the bar is a hard one — **under 50 employees** — and it is deliberately tighter than the roster's under-200 cap, because a peer is a speculative lead the user has to spend effort investigating, while a roster row is a role already in hand.

Excluded outright, with no exceptions:
- **Multinationals and large corporates** — Salesforce, Microsoft, Oracle, Accenture, Infosys, TCS, Wipro and their peers.
- **Category-defining platforms**, however relevant they look: Otter.ai for notetakers, Bright Data and Apify for scraping, Veeva and Clarivate for life-sciences software, Bullhorn for recruiting tooling.
- **Large established nonprofits** — the size rule is about headcount, not about being commercial.

**There is no "context" exemption.** An earlier version of this skill let incumbents through tagged `CONTEXT`, on the theory that they oriented the user even if they were not leads. That was removed on 2026-09-24: in a column that gets scanned rather than read, a qualifier is easy to miss, and the cost of a missed one is the user spending time on a company that was never applicable. If a company is over 50 people, leave it out. The user can find the market leader in a space without help.

When exclusions leave you with two peers, record two. `Few direct peers found — niche space` remains a legitimate and useful result; inventing a fifth by reaching for a household name is not.

**Record a size or stage signal on every peer line** — "seed", "YC W24", "~20 people", "founded 2024". Without one the size rule cannot be checked by anyone downstream, and `scripts/validate_peers.py` will flag the line as unverifiable. A peer whose size you genuinely cannot establish is a weaker lead than one you can, and should be the first to go when trimming.

## When the "company" is not a company

Several roster rows are staffing agencies, talent marketplaces or brokered listings — Arc Exclusive, Lemon.io, A.Team, Proxify, Clera. These have no product space to map, and their competitors are other agencies, which is useless for this purpose.

Record `No product space — <agency/marketplace>, peers would be other agencies` and move on. Do not invent a landscape for them.

## Run it as three agents: two finders, one verifier

Split the company list in half between **two finder agents** working in parallel, then pass everything they produce to **one verifier agent that did no finding**.

Two finders is about throughput — the work is per-company and embarrassingly parallel, so splitting it halves the wall-clock without either agent needing to know what the other is doing.

The single verifier is about something else, and it is the part that matters. The characteristic failure of this skill is **padding with false kinship**: an agent asked for 3-5 peers will produce 3-5 peers, and when a space is genuinely thin it starts reaching — "also an AI company" quietly becomes a peer. The finder cannot catch this, because by the time the row exists it has already persuaded itself. A reader who did none of the finding, asked one blunt question, catches it immediately.

**Brief the verifier to delete, not to research.** This is the opposite of the verifier in the job-roster skill, whose job was to *resolve* unknown facts. Here almost everything unknown is already excluded; what remains is a list that is too long and too generous. For every peer it should ask:

1. **Same problem, same customer — or just same technology?** The test is whether this company would plausibly hire the same engineer for the same work. "Both use LLMs" fails. Cut it.
2. **Under 50 people?** An incumbent is not a peer of a seed-stage startup whatever the category page says, and there is no context exemption — cut it. Where the line carries no size signal at all, the size rule cannot be checked, so treat that as a weakness rather than a pass.
3. **Does the site actually load, and is the company alive?** A parked domain or a site last touched in 2019 is not a lead.
4. **Is the link the company's own product site**, rather than a Crunchbase/LinkedIn/directory page?

A verifier that returns every list unchanged has not done its job — the finders are generous by construction, so some cutting is the expected outcome, not a sign something went wrong. Equally, a verifier should not invent replacements for what it cuts: a three-peer list that survives scrutiny beats a five-peer list that does not.

## Steps

1. **Establish what the company actually does.** Read its own website first — its homepage headline is usually a better description of the space than any third-party summary. The roster's `Company Notes` gives a starting point but is often one line.
2. **Find peers.** Search for the problem in the company's own words ("AI meeting notes", "GST billing for SMEs"), plus alternatives-style queries ("X alternatives", "competitors to X", "like X for Y"). YC's directory is useful when the company is YC-backed, since batchmates cluster by space.
3. **Get each peer's own website.** Its product domain, never a Crunchbase, LinkedIn, or directory listing — the user wants to look at the product and find its careers page.
4. **Verify the peer is real and current.** A dead startup is not a lead. Fetch the site; if it 404s, parks, or has clearly been abandoned, drop it.
5. **Run the verifier pass** described above over everything both finders produced, and apply its cuts before anything is written.
6. **Write the result** into the roster's `Peer Companies` column, one peer per line:

   ```
   Granola — https://granola.ai — AI notepad for meetings, seed stage
   Circleback — https://circleback.ai — AI meeting notes and action items, YC-backed, ~15 people
   ```

   Keep each line to name, URL, and a short clause. This column is scanned, not read.

   Every line carries a size or stage signal, as the size rule above requires. Note how both examples do: "seed stage", "~15 people".

   The reason there is no marker for "big but relevant" is worth keeping in mind — an earlier version had one, and a finder wrote the qualifier as a trailing note *below* the list, so three over-cap companies scanned as ordinary leads. A qualifier that arrives after the thing it qualifies does not work in a column that gets scanned. Excluding outright removes the failure mode rather than formatting around it.

## Judgment

Leave a peer out rather than pad the list. A wrong or stale link costs the user a click and some trust; a list of four real peers is worth more than eight where half are noise. When a space genuinely has few comparable startups, say so — `Few direct peers found — niche space` is a real and useful finding, not a failure.
