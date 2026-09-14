#!/usr/bin/env python3
"""Publish the board — every price we checked this week, ranked best first.

Why this exists (Neil, 14 September 2026): the site showed only the two picks we file on
the card, so a quiet week looked like nothing had been checked at all. He wants the whole
ranked board visible, with the picks that cleared the bar marked apart from the ones that
didn't — so a week where nothing clears is legible as a decision rather than an absence,
and so the top of the list is there to look at when he chooses to go against the system.

It is a view of numbers we already compute, not a new measurement. The 2-hourly TAB price
log (`~/Documents/Betting/data/odds_history.jsonl`) already holds, per snapshot, TAB's price
against the US no-vig fair for every side on the slate. This reads the newest good snapshot
and ranks it.

    python3 build_board.py [--week 2] [--log PATH]

Writes assets/data/board.json.

Exits 0 even when the log is missing or unreadable, leaving the previous board in place: a
stale board beats a blank one, and a deploy must not fail over a display module.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

LOG = os.path.expanduser("~/Documents/Betting/data/odds_history.jsonl")
OUT = os.path.expanduser("~/Documents/pigskin-punts/assets/data/board.json")
NZ = ZoneInfo("Pacific/Auckland")

# The bar, as agreed in the operating document: TAB at or above fair x 1.04. Kept as a
# number here rather than read from anywhere, because a bar that moves by itself would move
# the word "cleared" on a page both agents read.
BAR_PCT = 4.0

# A snapshot with fewer sides than this is the tail end of a weekend — games drop off TAB's
# rolling feed as they kick off — so it is not the week's board. MIN_SIDES keeps the board
# on the last full slate instead of trailing off to one game by Tuesday.
MIN_SIDES = 6
LOOKBACK_DAYS = 7

STAMP = re.compile(r"^(\w{3})\s+(\d{1,2})\s+(\w{3})\s+(\d{1,2}):(\d{2})\s*(am|pm)", re.I)
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def kickoff_nz(text, now):
    """'Mon 14 Sep 08:25am' -> an aware NZ datetime, or None if it will not parse.

    The log stores no year, so the year is whichever one puts the date nearest to now —
    which is right either side of New Year's and wrong nowhere else that matters."""
    m = STAMP.match((text or "").strip())
    if not m:
        return None
    _, day, mon, hh, mm, ap = m.groups()
    month = MONTHS.get(mon.lower()[:3])
    if not month:
        return None
    h24 = int(hh) % 12 + (12 if ap.lower() == "pm" else 0)
    best = None
    for year in (now.year - 1, now.year, now.year + 1):
        try:
            dt = datetime.datetime(year, month, int(day), h24, int(mm), tzinfo=NZ)
        except ValueError:
            continue
        if best is None or abs(dt - now) < abs(best - now):
            best = dt
    return best


def snapshots(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue  # a torn last line from a killed job is not a reason to fail
            ts = d.get("ts")
            if not ts or not d.get("sides"):
                continue
            try:
                when = datetime.datetime.fromisoformat(ts)
            except ValueError:
                continue
            rows.append((when, d))
    rows.sort(key=lambda r: r[0])
    return rows


def pick_snapshot(rows, now):
    """The week's board: the newest read that still holds the whole slate.

    Games drop off TAB's rolling feed as they kick off, so mid-weekend the newest line in
    the log is the tail of the slate, not the board — publish that and a Tuesday read shows
    one game. A snapshot is therefore measured against its own neighbours (±24h) rather than
    against the week: it has to hold almost as many sides as the readings around it. The
    newest one that clears that test is the board, which stays put from the lock until the
    next slate arrives.
    """
    cutoff = now - datetime.timedelta(days=LOOKBACK_DAYS)
    recent = [(w, d) for w, d in rows if w >= cutoff] or rows

    def local_max(when):
        lo, hi = when - datetime.timedelta(hours=24), when + datetime.timedelta(hours=24)
        near = [len(d["sides"]) for w, d in rows if lo <= w <= hi]
        return max(near) if near else 0

    for when, d in reversed(recent):
        n = len(d["sides"])
        if n >= MIN_SIDES and n >= 0.9 * local_max(when):
            return when, d
    return recent[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, default=None,
                    help="week number to label the board with (optional)")
    ap.add_argument("--log", default=LOG)
    args = ap.parse_args()

    now = datetime.datetime.now(NZ)
    if not os.path.exists(args.log):
        print(f"board: no price log at {args.log} — keeping the previous board")
        return 0
    try:
        rows = snapshots(args.log)
    except OSError as e:
        print(f"board: could not read the price log ({e}) — keeping the previous board")
        return 0
    if not rows:
        print("board: the price log has no usable snapshots — keeping the previous board")
        return 0

    when, snap = pick_snapshot(rows, now)
    if snap is None:
        print("board: nothing to publish — keeping the previous board")
        return 0

    board = []
    for s in snap["sides"]:
        try:
            tab, fair = float(s["tab"]), float(s["fair"])
            gap = round((tab / fair - 1) * 100, 2)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
        ko = kickoff_nz(s.get("start"), now)
        board.append({
            "pick": s.get("side") or "",
            "game": s.get("game") or "",
            "kickoff_nz": s.get("start") or "",
            "tab": tab,
            "fair": fair,
            "gap_pct": gap,
            "cleared": gap >= BAR_PCT,
            "started": bool(ko and ko <= now),
        })
    if not board:
        print("board: the newest snapshot had no usable sides — keeping the previous board")
        return 0

    board.sort(key=lambda r: r["gap_pct"], reverse=True)
    for i, r in enumerate(board, 1):
        r["rank"] = i

    cleared = [r for r in board if r["cleared"]]
    data = {
        "generated_utc": now.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_nz": now.strftime("%-d %b %Y, %-I:%M%p NZ"),
        "priced_at_nz": when.astimezone(NZ).strftime("%-d %b %Y, %-I:%M%p NZ"),
        "priced_at_utc": when.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "week": args.week,
        "source": "TAB price log (2-hourly snapshot of TAB against the US no-vig fair)",
        "bar_pct": BAR_PCT,
        "count": len(board),
        "games": len({r["game"] for r in board}),
        "cleared": len(cleared),
        "best_pct": board[0]["gap_pct"],
        "best_pick": board[0]["pick"],
        "still_to_start": len([r for r in board if not r["started"]]),
        "note": ("Every price we checked, ranked best first. A pick clears the bar at "
                 "+4% or better against the true US price; only clearing picks can be bet, "
                 "and everything below the bar is a contest pick with no money on it."),
        "rows": board,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")

    print(f"board: {data['count']} picks across {data['games']} games from the "
          f"{data['priced_at_nz']} read -> {os.path.relpath(OUT, os.path.expanduser('~/Documents/pigskin-punts'))}")
    print(f"  cleared the +{BAR_PCT}% bar: {data['cleared']}"
          + ("" if cleared else f"  (best: {data['best_pick']} {data['best_pct']:+.2f}%)"))
    print(f"  still to kick off: {data['still_to_start']} of {data['count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
