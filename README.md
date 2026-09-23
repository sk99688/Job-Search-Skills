# Job-Search-Skills

Claude Code skills used for automating the job search — remote role sourcing, filtering, and tracking.

## Skills

- **`unit-test-jobs/`** — searches Wellfound, Arc.dev, YC's Work at a Startup, Himalayas, We Work Remotely, Built In and LinkedIn hiring posts for Full Stack / AI Engineering / Applied AI / Gen AI / Data Engineering roles. Roles are admitted on a ~50% match rather than an exact title; everything else is a hard drop — **$4,000/month** pay floor, posted within 30 days, no US work-authorization requirement, **under 200 employees**, and **international scope only** (worldwide or multi-country — India-only listings are excluded, since the goal is international remote work rather than the domestic market). Verifies each listing is still live *and still open* before writing, and stores results in Airtable. Install by copying the folder into `~/.claude/skills/`.

  Runs as a pipeline with finding and verification separated: sourcing agents propose rows, then `scripts/validate_rows.py` gates them mechanically and an independent verifier agent resolves what a regex cannot. That split exists because agents grading their own sourcing let 27 geographically-restricted rows and 11 over-cap rows through in a single run.

- **`peer-companies/`** — maps the competitive landscape around a company: finds startups solving the same problem for the same customer and records their websites. Built on the premise that a company worth applying to is a pointer to its competitors, who build the same things, need the same skills, and are often hiring the same roles without appearing on any job board. Runs as two finder agents plus one verifier whose job is to cut weak matches rather than add to them.

## Conventions

`CONVENTIONS.md` documents the house standard followed when writing these skills — frontmatter/description rules, progressive disclosure, field-ownership rules for skills that write to shared data, and writing style.

`tools/check_skill.py` enforces the mechanical half of it:

```bash
python3 tools/check_skill.py --all --strict
```

Run it before committing a skill change. It checks frontmatter, the context budget, step structure, and that every bundled script is both referenced and documented — the things that drift unnoticed once there is more than one skill to keep track of.
