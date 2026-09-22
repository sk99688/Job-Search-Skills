# Skill-writing conventions

House standard for any SKILL.md written or edited in this environment. Based on Anthropic's own skill-authoring guidance (the skill-creator skill), plus patterns that proved themselves in practice on `unit-test-jobs`.

## 1. File shape

```
skill-name/
├── SKILL.md            (required)
├── scripts/             (optional — executable helpers for deterministic/repetitive work)
├── references/          (optional — docs loaded only when needed, e.g. per-platform quirks)
└── assets/               (optional — templates, icons, fonts used in output)
```

Only reach for `scripts/`/`references/`/`assets/` when the skill actually needs them. A short, single-purpose skill is just a SKILL.md.

## 2. Frontmatter

```yaml
---
name: kebab-case-name
description: <what it does> + <when to use it>
---
```

- **`name`** — kebab-case, matches the folder name, becomes the `/slash-command`.
- **`description`** — this is the *entire* triggering mechanism. Claude decides whether to consult the skill based on this line alone (the body only loads after it's already triggered). Two consequences:
  - State both *what the skill does* and *when to use it* ("Use when the user asks to X, mentions Y, or invokes /skill-name").
  - Write it a little "pushy" — Claude under-triggers skills by default. Prefer "make sure to use this whenever the user mentions X, even if they don't explicitly ask for it" over a flat capability statement.
  - All "when to use" logic belongs in the description, not buried in the body — the body doesn't get read until after the trigger decision is already made.

## 3. Progressive disclosure — respect the three load levels

1. **Metadata** (name + description) — always in context, every turn. Keep it tight (~100 words).
2. **SKILL.md body** — loaded only once the skill triggers. Keep it under ~500 lines. If it's creeping past that, split detail into `references/*.md` and leave a one-line pointer in the body ("see references/wellfound.md for platform-specific quirks").
3. **Bundled resources** — loaded on demand, effectively unlimited. Scripts can *execute* without ever being loaded into context — that's the right place for anything deterministic and repetitive (see §6).

Don't front-load everything into the body just because it's convenient to write — that's what references/ is for.

## 4. Body structure that's worked well

- **A numbered `## Steps` section** for the actual run sequence — one step per distinct phase, not one giant paragraph.
- **A "hard filters" or equivalent section** when the skill has non-negotiable rules a result must clear — spell out each rule, what happens when data is ambiguous vs. explicitly disqualifying (don't guess-drop on ambiguity; keep-and-flag instead), and *why* the rule exists.
- **A dated "Known quirks (learned YYYY-MM-DD)" section** for tacit, hard-won knowledge (a platform's rendering quirks, a tool's inconsistent behavior) — append to it over time rather than rewriting the skill's logic each time a new quirk surfaces.
- **An explicit output-target guardrail line** whenever the skill's destination has changed or could be confused with a deprecated one — e.g. "Output is Airtable — never a Claude Artifact, and no longer the old local HTML file." State it plainly near the top, not just implied by later steps, so a future run doesn't drift back to the old pattern.
- **A migration note with a date** whenever the output target or a core rule changes, one line explaining *why* — future edits (by you or Claude) need the reasoning, not just the new rule, to judge edge cases correctly.

## 5. Field/data ownership (any skill writing to a shared resource)

If the skill writes into something a human also edits by hand — a spreadsheet, a table, a shared doc — explicitly enumerate which fields are machine-owned (safe to overwrite every run) vs. human-owned (status flags, notes, checkboxes the user fills in themselves). State plainly that the skill must never overwrite the human-owned fields on a re-run. This is easy to get wrong silently — a naive "update in place" step will happily clobber a user's own tracking data unless told not to.

## 6. Scripts over repeated tool calls

If a task involves the same mechanical operation repeated many times (e.g., writing 30+ records one by one), that's a signal to bundle a script rather than instructing dozens of individual tool calls per run. A script:
- reads credentials from wherever they're already stored (never duplicate a secret into the script itself),
- does the dedup/batch/error-handling logic once,
- is faster and more reliable than N interactive tool calls.

Write it once into `scripts/`, reference it from the body, and never re-derive the same logic ad hoc in a future run.

## 7. Writing style

- **Imperative voice.** "Fetch the live page" not "The live page should be fetched."
- **Explain the why, not just the rule.** A rule stated with reasoning ("keep it tagged rather than dropping it, since guessing a date we don't have is worse than flagging it unknown") lets a future run judge edge cases the rule didn't anticipate. A bare ALL-CAPS MUST doesn't.
- **Generalize, don't overfit.** A skill built around one example run should still make sense for the next hundred — avoid instructions so specific to today's data that they stop applying tomorrow.
- **Define output format explicitly** when there's a fixed structure to hit (exact headings, exact field list) — show the template, don't describe it in prose.

## 8. Testing (only when it's worth it)

Skills with objectively verifiable output (data extraction, fixed transforms, schema-shaped results) benefit from a couple of test prompts run through the skill-creator eval loop. Skills with subjective output (tone, style, art direction) usually don't need formal evals — a quick manual read is enough. Don't force a benchmark onto something that needs human judgment.

## 9. Description optimization (optional, do last)

Once the skill's logic is settled, it's worth running the skill-creator's description-optimization loop (a handful of should-trigger / should-not-trigger test queries, iterated automatically) to sharpen triggering accuracy — but only after the body logic itself is stable. Optimizing a description around a skill that's still changing wastes the loop's iterations.
