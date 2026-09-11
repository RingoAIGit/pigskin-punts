"""Write assets/data/build.json — the build stamp every page reports.

Rule 5 of the agreed seal protocol: each generated page says when it was built and which
sources it was built from. "Current" then means "as of the last build", which is the only
honest reading of a static site.

Run before publishing. Preserves the sources list from the existing file.

    python3 stamp.py
"""
import datetime
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets", "data", "build.json")

DEFAULT = {
    "sources": [
        "TAB feed — 11 Sep 2026 10:37 NZ",
        "US market, 9-book no-vig median — 11 Sep 2026 10:37 NZ",
        "nflverse REG 2011–2025, n=3,919 (half-point values)",
        "Drive cards/: none — week 1 predates the seal",
    ],
    "ledger": "assets/data/ledger.json — no bets placed",
    "note": "Drive is the record. This site is a view of it — if the two ever disagree, Drive wins and this gets rebuilt.",
}


def main():
    data = dict(DEFAULT)
    if os.path.exists(OUT):
        try:
            with open(OUT) as f:
                data.update(json.load(f))
        except Exception:
            pass

    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    data["built_utc"] = now.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["built_nz"] = now.strftime("%-d %b %Y %H:%M %Z").replace("NZST", "NZ").replace("NZDT", "NZ")
    data["built_human"] = now.strftime("%a %-d %b %Y, %-I:%M%p %Z")

    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                             capture_output=True, text=True, timeout=10).stdout.strip()
        if rev:
            data["commit"] = rev
    except Exception:
        pass

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("build stamp written:", OUT)
    print("  built_nz:", data["built_nz"])
    print("  commit  :", data.get("commit", "-"))
    print("  sources :", len(data["sources"]), "listed")


main()
