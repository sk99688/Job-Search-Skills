# Job-Search-Skills

Claude Code skills used for automating the job search — remote role sourcing, filtering, and tracking.

## Skills

- **`unit-test-jobs/`** — searches Wellfound, Arc.dev, YC's Work at a Startup, LinkedIn and general remote job boards for Full Stack / AI Engineer / Data Engineer roles, applies hard filters (role match, $40k+ salary, posted within 30 days, no US work-authorization requirement, ≤50 employee company size, Worldwide/India-only remote scope), verifies each listing's URL is still live, and writes results to an Airtable base. Install by copying the folder into `~/.claude/skills/`.

## Conventions

`CONVENTIONS.md` documents the house standard followed when writing these skills — frontmatter/description rules, progressive disclosure, field-ownership rules for skills that write to shared data, and writing style.
