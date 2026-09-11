"""Build the data layer for the Pig Skin Punts site (Week 1).

Writes assets/data/week01.json into the site repo. Everything the site renders
numerically comes from here, so no number on the site is hand-typed:
  - tonight's game (TAB markets + US fair)
  - all Week 1 sides with edges under proportional and power de-vig
  - key-number audit: one-sided (decisive) vs two-sided counts
"""
import csv
import json
import os
import statistics
import sys

sys.path.insert(0, "/Users/cerebral/Documents/Betting/scripts")
import us_lines as U  # noqa: E402

OUT = os.path.expanduser("~/Documents/pigskin-punts/assets/data/week01.json")
DATES = ["20260910", "20260913", "20260914"]
GAMES_CSV = "/tmp/nfl_games.csv"


def power_probs(prices):
    imp = [1 / p for p in prices]
    if sum(imp) <= 1:
        return imp
    lo, hi = 0.5, 3.0
    for _ in range(200):
        k = (lo + hi) / 2
        if sum(i ** k for i in imp) > 1:
            lo = k
        else:
            hi = k
    k = (lo + hi) / 2
    return [i ** k for i in imp]


# ---------------- tonight: TAB markets swept 11 Sep, US fair ----------------
TONIGHT = {
    "away": "San Francisco 49ers",
    "home": "Los Angeles Rams",
    "kickoff_nz": "Fri 11 Sep, 12:35pm NZ",
    "swept": "11 Sep 2026, 10:37am NZ",
    "markets": [
        {"market": "Moneyline", "side": "Rams", "tab": 1.48, "fair": 1.556,
         "us_line": "US fair is the 9-book no-vig median"},
        {"market": "Moneyline", "side": "49ers", "tab": 2.65, "fair": 2.798,
         "us_line": "US fair is the 9-book no-vig median"},
        {"market": "Line", "side": "Rams -3.5", "tab": 1.88, "fair": 1.981,
         "us_line": "US consensus -3.5"},
        {"market": "Line", "side": "49ers +3.5", "tab": 1.92, "fair": 2.020,
         "us_line": "US consensus -3.5"},
        {"market": "Total", "side": "Over 48", "tab": 1.94, "fair": 2.100,
         "us_line": "US consensus 47.5 - TAB a half point against us, so the "
                    "fair for Over 48 carries the ~2.6% cost of losing the push on 48"},
        {"market": "Total", "side": "Under 48", "tab": 1.88, "fair": 2.014,
         "us_line": "US consensus 47.5 - identical outcome to Under 47.5, so no adjustment"},
    ],
}
for m in TONIGHT["markets"]:
    m["edge_pct"] = round((m["tab"] / m["fair"] - 1) * 100, 2)

# ---------------- Week 1 edges, both de-vig methods ----------------
names = U.books_map()
us = {}
for key, e in U.collect(DATES).items():
    prop, pw = [], []
    for o in e["books"]:
        dh, da = U.us_to_dec(o.get("ml_home")), U.us_to_dec(o.get("ml_away"))
        if not (dh and da):
            continue
        if names.get(o.get("book_id")) in ("Consensus", "Open"):
            continue
        imp = [1 / dh, 1 / da]
        tot = sum(imp)
        prop.append([i / tot for i in imp])
        pw.append(power_probs([dh, da]))
    if not prop:
        continue
    us[key] = {
        "home": e["home"], "away": e["away"], "n_books": len(prop),
        "prop_home": statistics.median([1 / r[0] for r in prop]),
        "pw_home": statistics.median([1 / r[0] for r in pw]),
        "prop_away": statistics.median([1 / r[1] for r in prop]),
        "pw_away": statistics.median([1 / r[1] for r in pw]),
    }

sides = []
for ev in U.tab_slate():
    ss = [s for s in ev["sides"] if s["price"]]
    if len(ss) < 2:
        continue
    key = frozenset(U.norm(s["name"]) for s in ss[:2])
    u = us.get(key)
    if not u:
        continue
    for s in ss:
        is_home = U.norm(s["name"]) == U.norm(u["home"])
        fp = u["prop_home"] if is_home else u["prop_away"]
        fw = u["pw_home"] if is_home else u["pw_away"]
        sides.append({
            "game": f"{u['away']} @ {u['home']}",
            "kickoff": ev["start_nz"],
            "team": s["name"].split()[-1],
            "tab": s["price"],
            "fair_prop": round(fp, 3),
            "fair_power": round(fw, 3),
            "edge_prop": round((s["price"] / fp - 1) * 100, 2),
            "edge_power": round((s["price"] / fw - 1) * 100, 2),
            "books": u["n_books"],
        })
sides.sort(key=lambda r: -max(r["edge_prop"], r["edge_power"]))

# ---------------- key-number audit ----------------
G = [r for r in csv.DictReader(open(GAMES_CSV))
     if r.get("game_type") == "REG" and r.get("spread_line") not in (None, "", "NaN")
     and r.get("home_score") not in (None, "", "NaN") and r["season"].isdigit()
     and 2011 <= int(r["season"]) <= 2025]


def fav_by(r):
    """nflverse spread_line: positive = home favoured (corr +0.439, verified)."""
    hm = int(r["home_score"]) - int(r["away_score"])
    sp = float(r["spread_line"])
    return hm if sp > 0 else -hm


keys = []
for k in (2, 3, 4, 6, 7, 10, 14):
    cond = [r for r in G if k - 1 <= abs(float(r["spread_line"])) <= k + 1]
    one = sum(1 for r in cond if fav_by(r) == k) / len(cond)
    two = sum(1 for r in cond
              if abs(int(r["home_score"]) - int(r["away_score"])) == k) / len(cond)
    keys.append({"key": k, "n": len(cond), "one_sided": round(one * 100, 2),
                 "two_sided": round(two * 100, 2),
                 "value_loss_push": round(one * 100, 1),
                 "value_push_win": round(one * 0.909 * 100, 1)})

push3 = [r for r in G if abs(float(r["spread_line"])) == 3]
push3_rate = round(sum(1 for r in push3 if fav_by(r) == 3) / len(push3) * 100, 2)

doc = {2: 1.5, 3: 8.0, 4: 1.5, 6: 3.0, 7: 4.0, 10: 2.0, 14: 1.5}
for row in keys:
    row["doc_said"] = doc[row["key"]]

data = {
    "generated": "11 Sep 2026",
    "bankroll": {"kitty": 62, "unit": 5, "currency": "NZD",
                 "unit_pct": round(5 / 62 * 100, 1),
                 "weekly_cap_units": 2, "weekly_cap_nz": 10,
                 "gate_pct": 4.0},
    "tonight": TONIGHT,
    "sides": sides,
    "key_numbers": {
        "source": "nflverse nfldata/data/games.csv - REG 2011-2025, n=3,919",
        "rows": keys,
        "push_rate_3": push3_rate,
        "push3_n": len(push3),
        "method": "conditional on |spread| within 1 of the key",
    },
    "summary": {
        "games_priced": 16,
        "sides_priced": len(sides),
        "qualifying_prop": sum(1 for r in sides if r["edge_prop"] >= 4),
        "qualifying_power": sum(1 for r in sides if r["edge_power"] >= 4),
        "best_prop": max(sides, key=lambda r: r["edge_prop"]),
        "best_power": max(sides, key=lambda r: r["edge_power"]),
    },
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(data, open(OUT, "w"), indent=1)
print("wrote", OUT)
print("sides:", len(sides), "| best prop:",
      data["summary"]["best_prop"]["team"], data["summary"]["best_prop"]["edge_prop"],
      "| best power:", data["summary"]["best_power"]["team"],
      data["summary"]["best_power"]["edge_power"])
print("push rate on a 3-line:", push3_rate, "(n=%d)" % len(push3))
for r in keys:
    print(f"  key {r['key']:>2}: one-sided {r['one_sided']:5.2f}%  "
          f"two-sided {r['two_sided']:5.2f}%  doc {r['doc_said']}")
