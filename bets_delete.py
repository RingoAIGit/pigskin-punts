"""Read and delete records in the site's bet store.

The collection is owner-only for update and delete, so this is the only way a saved bet
goes away, and it needs the API key that only Ringo holds. Records are never edited --
a logged price stays as logged -- so delete is deliberately the only mutation here.

  python3 bets_delete.py --list        show every record with its id
  python3 bets_delete.py rec_01ABC...  delete exactly that one
  python3 bets_delete.py --test        show anything that looks like a test entry (no action)
  python3 bets_delete.py --test --yes  delete those

A test entry is one with TEST anywhere in its game, selection or note.
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
BASE = f"{API}/api/v1/publishes/{SLUG}/data/{COLLECTION}"


def key():
    with open(CREDS) as f:
        return f.read().strip()


def call(url, method="GET"):
    req = urllib.request.Request(url, method=method,
                                 headers={"Authorization": "Bearer " + key()})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode()
            return r.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]


def all_records():
    out, cursor = [], None
    while True:
        url = BASE + "?limit=100" + ("&cursor=" + cursor if cursor else "")
        st, body = call(url)
        if st != 200 or not isinstance(body, dict):
            print(f"read failed: HTTP {st} {body}")
            sys.exit(1)
        out.extend(body.get("records") or [])
        cursor = body.get("nextCursor")
        if not cursor:
            return out


def looks_like_test(r):
    d = r.get("data", {})
    blob = " ".join(str(d.get(k, "")) for k in ("game", "selection", "note")).upper()
    return "TEST" in blob


def show(recs):
    if not recs:
        print("  (nothing in the store)")
        return
    for r in recs:
        d = r["data"]
        print(f"  {r['id']}  {r['createdAt']}")
        print(f"    {d.get('placed_on','?')}  {d.get('game','?')}  {d.get('selection','?')}"
              f"  @{d.get('price','?')}  NZ${d.get('stake_nz','?')}"
              f"  by {d.get('placed_by') or '?'} / {d.get('called_by') or '?'}")
        if d.get("note"):
            print(f"    note: {d['note']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record_id", nargs="?", help="exact record id to delete")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--test", action="store_true", help="anything with TEST in it")
    ap.add_argument("--yes", action="store_true", help="actually delete (--test only)")
    a = ap.parse_args()

    if a.list:
        recs = all_records()
        print(f"{len(recs)} record(s)")
        show(recs)
        return 0

    if a.test:
        recs = [r for r in all_records() if looks_like_test(r)]
        print(f"{len(recs)} record(s) look like test entries")
        show(recs)
        if not recs or not a.yes:
            if recs:
                print("\nnothing deleted — re-run with --yes to remove them")
            return 0
        for r in recs:
            st, _ = call(f"{BASE}/{r['id']}", "DELETE")
            print(f"  deleted {r['id']} -> HTTP {st}")
        print(f"records left: {len(all_records())}")
        return 0

    if not a.record_id:
        ap.print_help()
        return 2

    ids = {r["id"] for r in all_records()}
    if a.record_id not in ids:
        print(f"no record with id {a.record_id} — run --list to see what is there")
        return 1
    st, _ = call(f"{BASE}/{a.record_id}", "DELETE")
    print(f"  deleted {a.record_id} -> HTTP {st}")
    print(f"records left: {len(all_records())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
