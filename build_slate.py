"""Snapshot this week's games so the bet form can offer them instead of free text.

The TAB slate is a live rolling feed -- games drop off it as they kick off -- so the site
needs a snapshot taken when the site is built. Writes assets/data/slate.json.

    python3 build_slate.py

Exits 0 even if the feed is down, leaving the previous snapshot in place: a stale list of
games beats no list, and the deploy should not fail over it.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys

sys.path.insert(0, "/Users/cerebral/Documents/Betting/scripts")

OUT = os.path.expanduser("~/Documents/pigskin-punts/assets/data/slate.json")
STAMP = re.compile(r"^(\w{3})\s+(\d{1,2})\s+(\w{3})\s+(\d{1,2}):(\d{2})\s*(am|pm)", re.I)


def sort_key(start):
    """'Mon 14 Sep 05:00am' -> (day, 24h, minute) so the list reads in kickoff order."""
    m = STAMP.match((start or "").strip())
    if not m:
        return (99, 99, 99)
    _, day, _mon, hh, mm, ap = m.groups()
    h24 = int(hh) % 12 + (12 if ap.lower() == "pm" else 0)
    return (int(day), h24, int(mm))


def day_of(start):
    m = STAMP.match((start or "").strip())
    return " ".join(m.groups()[:3]) if m else "Kickoff to be confirmed"


def main():
    try:
        import us_lines as U
        events = U.tab_slate()
    except Exception as e:  # network, markup change, TAB being TAB
        print(f"slate refresh FAILED ({type(e).__name__}: {e})")
        if os.path.exists(OUT):
            print(f"keeping the previous snapshot at {os.path.relpath(OUT)}")
        else:
            print("no previous snapshot to keep — the form will fall back to typing the game")
        return 0

    games = []
    for ev in events:
        sides = ev.get("sides") or []
        home = next((s["name"] for s in sides if (s.get("role") or "").upper() == "HOME"), None)
        away = next((s["name"] for s in sides if (s.get("role") or "").upper() == "AWAY"), None)
        if not home or not away:
            continue
        games.append({
            "label": f"{away} @ {home}",
            "away": away,
            "home": home,
            "day": day_of(ev.get("start_nz")),
            "kickoff_nz": ev.get("start_nz") or "",
            "market": ev.get("market") or "",
            "tab_margin_pct": ev.get("margin_pct"),
            "tab_prices": {s["name"]: s.get("price") for s in sides},
            "tab_url": ev.get("url") or "",
        })

    if not games:
        print("slate refresh returned no usable games — keeping the previous snapshot")
        return 0

    games.sort(key=lambda g: sort_key(g["kickoff_nz"]))
    now = datetime.datetime.now(datetime.timezone.utc)
    data = {
        "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_nz": now.astimezone(datetime.timezone(datetime.timedelta(hours=12)))
                           .strftime("%-d %b %Y, %-I:%M%p NZ"),
        "source": "TAB slate sweep (live feed)",
        "note": "Rolling feed: a game leaves this list once it kicks off, so this is a snapshot.",
        "count": len(games),
        "games": games,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")

    print(f"slate: {len(games)} games -> {os.path.relpath(OUT, os.path.expanduser('~/Documents/pigskin-punts'))}")
    for d in dict.fromkeys(g["day"] for g in games):
        n = sum(1 for g in games if g["day"] == d)
        print(f"  {d}: {n} game(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
