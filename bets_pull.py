"""Pull the bets people have saved on the site into the local ledger.

The site's form writes records into here.now Site Data. The collection is set to
read="owner", so the page itself cannot read them back and neither can a visitor: picks
can't leak before the reveal. This script is the owner reading them with the API key.

  python3 bets_pull.py            # show what's there
  python3 bets_pull.py --write    # fold them into assets/data/ledger.json

Idempotent: records are matched on their here.now id, so re-running never double-counts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://here.now"
SLUG = "waking-walrus-3vcd"
COLLECTION = "bets"
CREDS = os.path.expanduser("~/.herenow/credentials")
REPO = os.path.expanduser("~/Documents/pigskin-punts")
LEDGER = os.path.join(REPO, "assets", "data", "ledger.json")


def key():
    with open(CREDS) as f:
        return f.read().strip()


def get(path, k):
    req = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + k})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(body)
        except Exception:
            pass
        print(f"HTTP {e.code} on {path}: {body}")
        return None


def all_records(k):
    out, cursor = [], None
    while True:
        path = f"/api/v1/publishes/{SLUG}/data/{COLLECTION}?limit=100"
        if cursor:
            path += "&cursor=" + urllib.parse.quote(cursor)
        body = get(path, k)
        if not body:
            return out
        out.extend(body.get("records") or [])
        cursor = body.get("nextCursor")
        if not cursor:
            return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="fold records into ledger.json")
    a = ap.parse_args()

    k = key()
    records = all_records(k)
    print(f"{len(records)} saved bet record(s) in the site's store\n")
    for r in records:
        d = r.get("data", {})
        print(f"  {r['id']}  {r['createdAt']}")
        print(f"    {d.get('placed_on','?')}  {d.get('game','?')}  {d.get('selection','?')}"
              f"  @{d.get('price','?')}  NZ${d.get('stake_nz','?')}"
              f"  placed by {d.get('placed_by') or '?'}")
        if d.get("note"):
            print(f"    note: {d['note']}")
    if not records:
        print("  (nothing saved yet)")
        return 0

    if not a.write:
        print("\nrun with --write to fold these into assets/data/ledger.json")
        return 0

    # A saved bet names the game only; the kickoff comes from the slate snapshot, which is
    # also the audit trail of what was on offer when the bet was placed.
    slate = os.path.join(REPO, "assets", "data", "slate.json")
    kick = {}
    if os.path.exists(slate):
        for g in json.load(open(slate)).get("games", []):
            kick[g.get("label", "")] = g.get("kickoff_nz", "")

    ledger = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {"bets": []}
    existing = {b.get("record_id"): b for b in ledger.get("bets", []) if b.get("record_id")}
    added = 0
    for r in records:
        if r["id"] in existing:
            continue
        d = r.get("data", {})
        ledger.setdefault("bets", []).append({
            "record_id": r["id"],
            "logged_at": r["createdAt"],
            "placed_on": d.get("placed_on", ""),
            "game": d.get("game", ""),
            "kickoff_nz": kick.get(d.get("game", ""), ""),
            "market": d.get("market", ""),
            "selection": d.get("selection", ""),
            "price": d.get("price"),
            "stake_nz": d.get("stake_nz"),
            "stake_units": d.get("stake_units", 1),
            "placed_by": d.get("placed_by", ""),
            "called_by": d.get("called_by", ""),
            "rank": d.get("rank", 1),
            "note": d.get("note", ""),
            "result": None,
        })
        added += 1
    with open(LEDGER, "w") as f:
        json.dump(ledger, f, indent=2)
        f.write("\n")
    print(f"\n{added} new record(s) written into {os.path.relpath(LEDGER, REPO)}"
          f" ({len(ledger['bets'])} total)")
    return 0


if __name__ == "__main__":
    import urllib.parse  # noqa: E402  (only needed for cursor paging)
    sys.exit(main())
