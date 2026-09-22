#!/usr/bin/env python3
"""Insert job rows into the Remote Roster Airtable table, skipping duplicates.

Usage:
    python3 sync_to_airtable.py candidates.json
    python3 sync_to_airtable.py -            # read JSON from stdin

`candidates.json` is a JSON array of field dicts matching the table schema, e.g.:

    [
      {"Title": "AI Engineer", "Company": "PlutusAI", "Category": "AI Engineer",
       "Platform": "Wellfound", "Size": "11-50", "Salary": "Not disclosed",
       "Posted": "Unknown", "Location Scope": "Remote only, Everywhere",
       "Remote Fit": "Worldwide", "Job URL": "https://...", "Status": "New"}
    ]

Why a script instead of one create_record call per row: a run can surface dozens of
new listings, and Airtable's REST endpoint takes 10 records per POST. Doing it here
costs one process instead of dozens of tool calls, and keeps the dedup rule in one
place rather than re-derived by hand each run.

Dedup follows the skill's rule -- same (Company, Title) means skip. When a duplicate
is found whose URL differs from the stored one, it's reported rather than written:
that's an update case for `update_records`.

This script only ever creates new records, never updates existing ones. That's the
whole reason it's safe to run unattended: the user's Applied / Status / Notes fields
only exist on rows that already exist, and a create-only tool structurally cannot
clobber them.

The token is read from Claude Code's own config rather than duplicated into this file
or into the repo. Override with the AIRTABLE_API_KEY env var if running elsewhere.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

CLAUDE_CONFIG = os.path.expanduser("~/.claude.json")
BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "appNA1YixBgwXUGMY")
TABLE_ID = os.environ.get("AIRTABLE_TABLE_ID", "tblagnwEFzc1SWwm5")
API_ROOT = "https://api.airtable.com/v0"


def get_token():
    token = os.environ.get("AIRTABLE_API_KEY")
    if token:
        return token
    try:
        with open(CLAUDE_CONFIG) as f:
            cfg = json.load(f)
        return cfg["mcpServers"]["airtable"]["env"]["AIRTABLE_API_KEY"]
    except (OSError, KeyError) as e:
        sys.exit(
            f"Could not read AIRTABLE_API_KEY from {CLAUDE_CONFIG} ({e}). "
            "Set the AIRTABLE_API_KEY env var instead."
        )


def dedup_key(fields):
    return (
        fields.get("Company", "").strip().lower(),
        fields.get("Title", "").strip().lower(),
    )


def fetch_existing(token):
    """Return {(company, title): {"id", "url"}} for every record already in the table."""
    existing = {}
    offset = None
    headers = {"Authorization": f"Bearer {token}"}
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        url = f"{API_ROOT}/{BASE_ID}/{TABLE_ID}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                page = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            sys.exit(f"Failed reading existing records: {e.code} {e.read().decode()}")
        for rec in page.get("records", []):
            existing[dedup_key(rec["fields"])] = {
                "id": rec["id"],
                "url": rec["fields"].get("Job URL"),
            }
        offset = page.get("offset")
        if not offset:
            return existing


def load_candidates(path):
    raw = sys.stdin.read() if path == "-" else open(path).read()
    records = json.loads(raw)
    if not isinstance(records, list):
        sys.exit("Expected a JSON array of field dicts.")
    return records


def chunked(items, n):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)

    token = get_token()
    candidates = load_candidates(sys.argv[1])
    existing = fetch_existing(token)
    print(f"Table currently holds {len(existing)} record(s).")

    to_create, url_changed, skipped = [], [], 0
    for fields in candidates:
        key = dedup_key(fields)
        match = existing.get(key)
        if match:
            skipped += 1
            if fields.get("Job URL") and fields["Job URL"] != match["url"]:
                url_changed.append((match["id"], fields["Company"], fields["Title"], fields["Job URL"]))
            continue
        to_create.append(fields)

    for rec_id, company, title, new_url in url_changed:
        print(f"URL CHANGED (update {rec_id} via update_records): {company} — {title} -> {new_url}")

    if not to_create:
        print(f"Nothing new to add. {skipped} skipped as duplicates.")
        return

    created = 0
    url = f"{API_ROOT}/{BASE_ID}/{TABLE_ID}"
    for chunk in chunked(to_create, 10):
        body = json.dumps({"records": [{"fields": f} for f in chunk]}).encode()
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            sys.exit(f"Create failed after {created} record(s): {e.code} {e.read().decode()}")
        created += len(result.get("records", []))
        print(f"Created {len(result.get('records', []))} record(s).")

    print(f"Done. Created: {created}, skipped as duplicates: {skipped}, "
          f"URL-changed needing update: {len(url_changed)}.")


if __name__ == "__main__":
    main()
