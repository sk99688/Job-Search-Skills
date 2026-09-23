#!/usr/bin/env python3
"""Check a skill against the house conventions in CONVENTIONS.md.

Usage:
    python3 tools/check_skill.py <skill-dir> [<skill-dir> ...]
    python3 tools/check_skill.py --all          # every skill folder in this repo
    python3 tools/check_skill.py --all --strict # exit 1 on any FAIL

Exists because conventions drift silently. One skill is easy to keep in line by
reading it; five are not, and the failure is invisible -- a skill that has grown
past its context budget or lost its "when to use" triggers still works, it just
works worse, and nobody notices until a run goes wrong for reasons nobody
connects back to the file.

Checks only what can be settled mechanically. Whether a rule is well-reasoned,
or a description well-targeted, is a judgment this cannot make and does not try.
"""
import re
import sys
from pathlib import Path

BODY_LINE_BUDGET = 500      # CONVENTIONS.md section 3
DESC_WORD_BUDGET = 120      # metadata rides in context every turn; keep it tight
REFERENCE_TOC_LINES = 300   # a reference file longer than this needs a contents list


def check(skill_dir: Path):
    fails, warns = [], []
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return [f"{skill_dir.name}: no SKILL.md"], []

    text = md.read_text()
    parts = text.split("---")
    if len(parts) < 3 or not text.startswith("---"):
        fails.append("frontmatter missing or malformed (must open with ---)")
        return fails, warns
    fm, body = parts[1], "---".join(parts[2:])

    # --- frontmatter -------------------------------------------------------
    name_m = re.search(r"^name:\s*(\S+)\s*$", fm, re.M)
    if not name_m:
        fails.append("frontmatter has no `name`")
    else:
        name = name_m.group(1)
        if name != skill_dir.name:
            fails.append(f"`name: {name}` does not match folder `{skill_dir.name}`")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
            fails.append(f"`name: {name}` is not kebab-case")

    desc_m = re.search(r"^description:\s*(.+?)(?=^\w+:|\Z)", fm, re.M | re.S)
    if not desc_m:
        fails.append("frontmatter has no `description` — this is the entire trigger mechanism")
    else:
        desc = " ".join(desc_m.group(1).split())
        words = len(desc.split())
        if words > DESC_WORD_BUDGET:
            warns.append(f"description is {words} words; it rides in context every turn")
        # The description is the only thing read before the skill triggers, so
        # "when to use" has to live there rather than in the body.
        if not re.search(r"use (this |it )?when|make sure to use|triggers? on|invokes? /", desc, re.I):
            fails.append("description states no trigger condition ('Use when…') — it will under-trigger")

    # --- body --------------------------------------------------------------
    n_lines = len(body.strip().splitlines())
    refs = skill_dir / "references"
    if n_lines > BODY_LINE_BUDGET:
        fails.append(f"body is {n_lines} lines, over the {BODY_LINE_BUDGET} budget — split detail into references/")
    elif n_lines > BODY_LINE_BUDGET * 0.8:
        warns.append(f"body is {n_lines} lines, approaching the {BODY_LINE_BUDGET} budget")

    if not re.search(r"^## Steps", body, re.M):
        warns.append("no `## Steps` section — the run sequence should be numbered and explicit")

    # --- bundled resources -------------------------------------------------
    scripts = sorted((skill_dir / "scripts").glob("*.py")) if (skill_dir / "scripts").exists() else []
    for s in scripts:
        if s.name not in body:
            fails.append(f"scripts/{s.name} is bundled but never referenced from SKILL.md")
        if not re.match(r'\s*(#!.*\n)?\s*("""|\'\'\')', s.read_text()):
            warns.append(f"scripts/{s.name} has no module docstring saying why it exists")

    if refs.exists():
        for r in sorted(refs.glob("*.md")):
            if r.name not in body:
                warns.append(f"references/{r.name} is never pointed to from SKILL.md")
            if len(r.read_text().splitlines()) > REFERENCE_TOC_LINES and "## Contents" not in r.read_text():
                warns.append(f"references/{r.name} is long and has no `## Contents` list")

    return fails, warns


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = Path(__file__).resolve().parent.parent
    if "--all" in sys.argv:
        dirs = sorted(d for d in root.iterdir() if (d / "SKILL.md").exists())
    else:
        dirs = [Path(a) for a in args]
    if not dirs:
        sys.exit(__doc__)

    any_fail = False
    for d in dirs:
        fails, warns = check(d)
        status = "FAIL" if fails else ("WARN" if warns else "OK")
        any_fail |= bool(fails)
        print(f"\n{status}  {d.name}")
        for f in fails:
            print(f"   FAIL  {f}")
        for w in warns:
            print(f"   warn  {w}")

    if "--strict" in sys.argv and any_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
