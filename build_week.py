#!/usr/bin/env python3
"""Stamp the site with the week that is actually current.

Why this exists (Neil, 17 September 2026 — "the webpage doesn't seem to be updating
with the latest info"). Everything *numeric* on the site was already generated: the
board, the slate, the ledger, the build stamp. But the words around those numbers —
the week chip, "This week's picks", "Tonight's game", the footer date — were typed
into the HTML by hand when the site was built for Week 1, and nothing regenerated
them. So by Week 2 the page showed a live board for the coming weekend sitting under
a headline that still said Week 1 and a "tonight's game" that had kicked off six days
earlier.

This writes the week-scoped part of every page from live data, so it advances on its
own. It is a view of numbers already measured, like build_board.py, and it fails soft
in the same way: no data, unreadable log, or a missing marker block leaves the
previous week.json in place and never fails a deploy.

    python3 build_week.py [--log PATH] [--out PATH]

Writes assets/data/week.json, which app.js renders. Sources:
  - the marks log (2-hourly)  -> the week number, and the next game's line/total
  - the board (2-hourly)      -> the moneyline, the count, and what cleared the bar
  - the slate snapshot        -> the week's date label
  - the price log (2-hourly)  -> the spread of TAB's cut across the week's games
  - the ledger                -> whether anything has been placed yet
  - assets/data/picks.json    -> the two filed picks, once the reveal step writes it
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
BETTING = os.path.expanduser("~/Documents/Betting/data")
MARKS = os.path.join(BETTING, "marks_history.jsonl")
ODDS = os.path.join(BETTING, "odds_history.jsonl")
OUT = os.path.join(HERE, "assets", "data", "week.json")
PICKS = os.path.join(HERE, "assets", "data", "picks.json")
NZ = ZoneInfo("Pacific/Auckland")

STAMP = re.compile(r"^(\w{3})\s+(\d{1,2})\s+(\w{3})\s+(\d{1,2}):(\d{2})\s*(am|pm)", re.I)
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def kickoff_nz(text, now):
    """'Fri 18 Sep 12:15pm' -> an aware NZ datetime, or None.

    The logs carry no year, so the year is whichever one puts the date nearest to now.
    Same rule as build_board.py, and right everywhere it matters."""
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


def long_day(dt):
    """Fri 18 Sep 12:15pm -> 'Friday 18 September, 12:15pm'."""
    return (f"{dt.strftime('%A')} {dt.day} {dt.strftime('%B')}, "
            f"{dt.strftime('%-I:%M%p').lower()}")


def read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue  # a torn last line from a killed job is not a reason to fail
    return rows


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def money(v, dp=2):
    return f"{v:.{dp}f}"


def read_nz(ts):
    """'2026-09-17T20:50:17+12:00' -> '17 Sep, 8:50PM NZ'."""
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(NZ)
    except (ValueError, AttributeError):
        return ts or ""
    return dt.strftime("%-d %b, %-I:%M%p NZ")


# ---------------------------------------------------------------- prose helpers

def gap_words(pct):
    """A gap in the bettor's favour, in plain words."""
    if pct is None:
        return "no true price to compare it with"
    if pct >= 0:
        return f"the price is {abs(pct):.2f}% better than the true one"
    return f"the price falls {abs(pct):.2f}% short of the true one"


def short_gap(pct):
    """Same fact as gap_words, as a predicate: 'falls 2.85% short of the true price'."""
    if pct is None:
        return "has no true price to compare with"
    return (f"is {abs(pct):.2f}% better than the true price" if pct >= 0
            else f"falls {abs(pct):.2f}% short of the true price")


def signed(v, plus=True):
    """3 -> '+3', -5.5 -> '−5.5'. The spread range reads as signs, not magnitudes."""
    if v is None:
        return "?"
    return f"+{v:g}" if v >= 0 and plus else (f"−{abs(v):g}" if v < 0 else f"{v:g}")


def number_words(tab_number, us_mode, us_range, label):
    """What TAB's number is worth against what the US books are posting.

    Deliberately not a median comparison: books routinely split a half point, and a
    median lands on a number nobody posts. The mode and the range are the honest
    comparison, and "inside the range" means TAB is tracking the market.
    """
    if tab_number is None or us_mode is None:
        return "No US number to compare with."
    lo, hi = (us_range or [us_mode, us_mode])
    if tab_number == us_mode:
        if lo == hi:
            return (f"The US books are on {signed(us_mode)} as well, so there's "
                    f"nothing in the number here.")
        return (f"The US books post {signed(lo)} to {signed(hi)}, and {signed(us_mode)} "
                f"is the one most of them post — the same as TAB's.")
    if lo <= tab_number <= hi:
        return (f"The US books post {signed(lo)} to {signed(hi)}, so TAB's "
                f"{signed(tab_number)} is inside what they're posting — a different number, "
                f"not a better one.")
    better = abs(tab_number) < abs(us_mode)
    return (f"The US books post {signed(lo)} to {signed(hi)}, and TAB's "
            f"{signed(tab_number)} is {'better for us' if better else 'worse for us'} "
            f"than anything they're posting.")


# ---------------------------------------------------------------- the builders

def week_from_marks(marks, now):
    """The newest marks snapshot that knows its week number."""
    for snap in reversed(marks):
        if snap.get("games") and snap.get("week") is not None:
            return snap
    return None


def next_game_of(snap):
    """The soonest kickoff in the snapshot — the game the site leads with."""
    best = None
    for g in snap.get("games", []):
        ko = kickoff_nz(g.get("start"), datetime.datetime.now(NZ))
        if ko is None:
            continue
        if best is None or ko < best[0]:
            best = (ko, g)
    return best


def team_of(mark, which):
    for m in mark or []:
        if m.get("which") == which:
            return m
    return None


def next_game_block(snap, board, now):
    """Section 03: the next game, every market we priced, with a spoken summary."""
    found = next_game_of(snap)
    if not found:
        return None
    ko, g = found
    spread, total = g.get("spread") or [], g.get("total") or []
    away, home = team_of(spread, "away"), team_of(spread, "home")
    over, under = team_of(total, "over"), team_of(total, "under")

    market_rows = []
    for r in (board or {}).get("rows", []):
        if r.get("game") != g.get("game"):
            continue
        market_rows.append({"market": "Head To Head", "side": r.get("pick", ""),
                            "tab": r.get("tab"), "fair": r.get("fair"),
                            "edge_pct": r.get("gap_pct")})
        if len(market_rows) == 2:
            break
    for side, m in (("Line", away), ("Line", home)):
        if m:
            market_rows.append({
                "market": "Line",
                "side": f"{m['side']} {'+' if m['tab_number'] > 0 else '−'}{abs(m['tab_number']):g}",
                "tab": m.get("tab_price"), "fair": m.get("us_fair"),
                "edge_pct": (round((m["tab_price"] / m["us_fair"] - 1) * 100, 2)
                             if m.get("tab_price") and m.get("us_fair") else None)})
    for m in (over, under):
        if m:
            market_rows.append({
                "market": "Total",
                "side": f"{m['side'].capitalize()} {m['tab_number']:g}",
                "tab": m.get("tab_price"), "fair": m.get("us_fair"),
                "edge_pct": (round((m["tab_price"] / m["us_fair"] - 1) * 100, 2)
                             if m.get("tab_price") and m.get("us_fair") else None)})

    # Until 18 Sep 2026 the marks capture hardcoded the under's US price to nothing, so
    # Under rows landed here with no fair price. Fixed in marks_snapshot.py the same day;
    # the guard stays because an older snapshot in the log can still be the newest read.
    shown = [r for r in market_rows
             if r["tab"] is not None and r["fair"] is not None and r["edge_pct"] is not None]
    missing = [r["side"] for r in market_rows if r not in shown]

    panels = []
    if away and home:
        edge = (round((away["tab_price"] / away["us_fair"] - 1) * 100, 2)
                if away.get("tab_price") and away.get("us_fair") else None)
        panels.append({
            "meta": "Line",
            "title": f"TAB {away['side']} {'+' if away['tab_number'] > 0 else '−'}"
                     f"{abs(away['tab_number']):g} at {money(away['tab_price'])}",
            "body": f"{number_words(away['tab_number'], away.get('us_mode'), away.get('us_range'), 'a line of')} "
                    f"{gap_words(edge).capitalize()}.",
        })
    if over:
        under_txt = (f" over / {money(under['tab_price'])} under" if under else "")
        oedge = (round((over["tab_price"] / over["us_fair"] - 1) * 100, 2)
                 if over.get("tab_price") and over.get("us_fair") else None)
        uedge = (round((under["tab_price"] / under["us_fair"] - 1) * 100, 2)
                 if under and under.get("tab_price") and under.get("us_fair") else None)
        if g.get("us_total_num") is not None and over.get("tab_number") is not None:
            d = over["tab_number"] - g["us_total_num"]
            # Direction matters, and this said the opposite until 18 Sep 2026. Over 55 needs 56+
            # while over 54.5 wins on 55, so when TAB posts the HIGHER number the half point sits
            # with the under. The old wording called it "half a point our way on the over".
            if abs(d) < 0.01:
                where = "the same number the US books post"
            elif d > 0:
                where = (f"{abs(d):g} points above the US number, which sits with the under"
                         if d > 0.5 else
                         "half a point above the US number, which sits with the under")
            else:
                where = (f"{abs(d):g} points below the US number, which sits with the over"
                         if d < -0.5 else
                         "half a point below the US number, which sits with the over")
            if oedge is not None and uedge is not None and oedge < 0 and uedge < 0:
                both = (f" On price, both sides are short of the true one — the over by "
                        f"{abs(oedge):.2f}%, the under by {abs(uedge):.2f}%.")
            elif uedge is not None:
                both = (f" On price, the over {short_gap(oedge)} and the under "
                        f"{short_gap(uedge)}.")
            else:
                both = f" On price, the over {short_gap(oedge)}."
            body = (f"The US books post {g['us_total_num']:g} and TAB posts "
                    f"{over['tab_number']:g}, so TAB's number is {where}." + both)
        else:
            body = f"{gap_words(oedge).capitalize()}."
        panels.append({
            "meta": "Total",
            "title": f"TAB {over['tab_number']:g} at {money(over['tab_price'])}"
                     f"{under_txt}",
            "body": body,
        })

    read = read_nz(snap.get("ts"))
    extra = (f" ({', '.join(missing)} not shown — no US price for it in this read.)"
             if missing else "")
    return {
        "away": away["side"] if away else "",
        "home": home["side"] if home else "",
        "label": g.get("game", ""),
        "kickoff_nz": g.get("start", ""),
        "kickoff_long": long_day(ko),
        "panels": panels,
        "markets": shown,
        "caption": (f"NZ TAB read {read} — priced against the US no-vig median. "
                    f"Bar is +4%." + extra),
        "swept": read,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=MARKS, help="marks log to read the week from")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    now = datetime.datetime.now(NZ)
    marks = read_jsonl(args.log)
    snap = week_from_marks(marks, now)
    if snap is None:
        print("week: no marks snapshot carries a week number — keeping the previous week.json")
        return 0

    week = int(snap["week"])
    board = read_json(os.path.join(HERE, "assets", "data", "board.json")) or {}
    slate = read_json(os.path.join(HERE, "assets", "data", "slate.json")) or {}
    ledger = read_json(os.path.join(HERE, "assets", "data", "ledger.json")) or {}

    # the week's date label is the opening game's date, which is what the chip has
    # always shown (Week 1's read "11 Sep 2026", the Thursday game's date)
    first_ko = None
    for g in slate.get("games", []):
        ko = kickoff_nz(g.get("kickoff_nz"), now)
        if ko and (first_ko is None or ko < first_ko):
            first_ko = ko
    if first_ko is None:
        found = next_game_of(snap)
        first_ko = found[0] if found else now
    date_label = f"{first_ko.day} {first_ko.strftime('%b %Y')}"
    footer_date = f"{first_ko.day} {first_ko.strftime('%B %Y')}"

    rows = board.get("rows", [])
    count = board.get("count", len(rows))
    games = board.get("games", len({r.get("game") for r in rows}))
    cleared = [r for r in rows if r.get("cleared")]
    best = rows[0] if rows else None

    # TAB's cut across the week's games, from the newest price read
    cut_lo = cut_hi = None
    odds = [r for r in read_jsonl(ODDS) if r.get("sides")]
    if odds:
        margins = [s.get("tab_margin_pct") for s in odds[-1]["sides"]
                   if s.get("tab_margin_pct") is not None]
        if margins:
            cut_lo, cut_hi = min(margins), max(margins)

    picks = read_json(PICKS)
    filed = [p for p in (picks or {}).get("picks", []) if p]

    # ------------------------------------------------------------ section 01
    if filed:
        kicker = f"Week {week} — the picks"
        headline = f"{len(filed)} pick{'s' if len(filed) != 1 else ''} filed this week."
        body = ("Both sides filed before the lock and nothing can be changed now. "
                "Every price we checked is below, cleared or not.")
    else:
        kicker = f"Week {week} — the picks aren't out yet"
        headline = "No picks filed yet this week."
        body = ("Both sides file their picks on Saturday morning and they go public straight "
                f"after the lock, so nothing is hidden — there's just nothing filed yet. "
                f"What we can show you now is every price we've checked: {count} sides across "
                f"the {games} games TAB has up. ")
        if cleared:
            body += (f"{len(cleared)} of them has cleared the +4% bar, which is the marked set "
                     f"below — the call on whether to back one is yours.")
        else:
            body += "None of them has cleared the +4% bar."

    panels = []
    if cleared:
        for r in cleared[:2]:
            panels.append({
                "meta": "Cleared the bar",
                "cls": "accept",
                "title": f"{r['pick']} {money(r['tab'])} vs true {money(r['fair'], 3)}",
                "body": (f"<strong>{r['gap_pct']:+.2f}%.</strong> {r['game']}, "
                         f"{r['kickoff_nz']}. Better than the true price by more than the bar."),
            })
    # the two below the bar always get a showing, so a week with nothing through is
    # legible as a decision rather than an absence (the whole point of the board)
    for r in rows[:2]:
        if any(p["title"].startswith(r["pick"] + " ") for p in panels):
            continue
        label = "Best on the board" if not panels else "Second best"
        panels.append({
            "meta": label + (" (short of the bar)" if cleared else ""),
            "cls": "reject",
            "title": f"{r['pick']} {money(r['tab'])} vs true {money(r['fair'], 3)}",
            "body": (f"<strong>{r['gap_pct']:+.2f}%.</strong> {r['game']}, {r['kickoff_nz']}. "
                     + (f"Best of the {count} — and still a losing bet at that price."
                        if r is best else "Still short of the +4% bar.")),
        })

    if cleared:
        callout = {
            "kicker": "What cleared the bar",
            "body": (f"<strong>{len(cleared)}</strong> of the {count} sides we checked came in at "
                     f"or past <strong>+4%</strong> against the true US price. The numbers are in "
                     f"the board below; whether to back one is your call, not the bar's."),
        }
    else:
        cut = (f"<strong>{cut_lo:.2f}–{cut_hi:.2f}%</strong>" if cut_lo is not None
               else "about 5%")
        callout = {
            "kicker": "Why nothing has been bet yet",
            "body": (f"TAB's cut on these games is {cut}; the US books work on 2–3%. So every "
                     f"bet here starts behind before we've even looked at the two teams. The one "
                     f"advantage we can find is a price TAB hasn't got around to updating."),
        }

    placed = len(ledger.get("bets") or [])
    if placed:
        ledger_headline = f"{placed} bet{'s' if placed != 1 else ''} on the record"
        ledger_line = ("Every row keeps the odds we got at the time, and the last odds before "
                       "the game started, so we can see whether we beat them.")
    else:
        ledger_headline = "Nothing placed yet"
        ledger_line = ("No bets placed yet this season. This fills up from the first bet we put "
                       "on — the price, how much, who put it on, and whose pick it was.")

    next_block = next_game_block(snap, board, now)

    data = {
        "generated_utc": now.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_nz": now.strftime("%-d %b %Y, %-I:%M%p NZ"),
        "week": week,
        "week_label": f"Week {week}",
        "date_label": date_label,
        "state": "filed" if filed else "awaiting",
        "hero_class": "verdict" if cleared else "verdict empty",
        "kicker": kicker,
        "headline": headline,
        "body": body,
        "panels": panels,
        "callout": callout,
        "cut_label": (f"{cut_lo:.2f}% to {cut_hi:.2f}%" if cut_lo is not None else None),
        "ledger_headline": ledger_headline,
        "ledger_line": ledger_line,
        "footer_line": f"Week {week}, {footer_date}",
        "picks": filed,
        "next_game": next_block,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")

    print(f"week: Week {week} ({date_label}), state {data['state']} -> "
          f"{os.path.relpath(args.out, HERE)}")
    print(f"  board: {count} sides across {games} games, {len(cleared)} cleared the bar"
          + (f" (best {best['pick']} {best['gap_pct']:+.2f}%)" if best else ""))
    if next_block:
        print(f"  next game: {next_block['label']} — {next_block['kickoff_long']}, "
              f"{len(next_block['markets'])} prices tabled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
