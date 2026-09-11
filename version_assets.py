"""Version the asset URLs in every page.

here.now serves assets with `cache-control: public, max-age=3600,
stale-while-revalidate=86400`. That lets a browser -- or the CDN edge -- keep handing out
the *old* app.js for an hour after a deploy, and up to a day while it revalidates in the
background. The pages themselves are `no-cache`, so they are always fresh.

The fix is to make each page point at a new URL whenever an asset changes:

    assets/app.js  ->  assets/app.js?v=8f3a91c2

A content hash, not a timestamp: if the asset did not change, the URL does not change, and
nothing gets re-downloaded for no reason. Both hosts serve a query string fine.

Idempotent -- an existing ?v= token is replaced -- so it can run on every deploy.

    python3 version_assets.py
"""
import hashlib
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = ["assets/style.css", "assets/extra.css", "assets/app.js"]
PAGES = ["index.html", "bets.html", "results.html", "method.html",
         "week-01.html", "protocol.html", "seal-client.html"]


def digest(rel):
    with open(os.path.join(HERE, rel), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def main():
    versions = {a: digest(a) for a in ASSETS}

    # Only touch references that end at a quote, so "assets/app.js" cannot match
    # something like "assets/app.js.map".
    patterns = {
        a: re.compile(r"(" + re.escape(a) + r")(?:\?v=[0-9a-f]+)?(?=[\"'])")
        for a in ASSETS
    }

    rewritten = []
    for page in PAGES:
        path = os.path.join(HERE, page)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        new = text
        for asset, pattern in patterns.items():
            new = pattern.sub(asset + "?v=" + versions[asset], new)
        if new != text:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            rewritten.append(page)

    for asset in ASSETS:
        print(f"  {asset:<22} v={versions[asset]}")
    print(f"  pages rewritten: {len(rewritten)}" +
          (f" ({', '.join(rewritten)})" if rewritten else " (already current)"))


main()
