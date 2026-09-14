#!/bin/bash
# One command, both doors.
#
# The site has one source of truth (this repo) and two hosts:
#   - GitHub Pages rebuilds itself from the repo on push. No publish step at all.
#   - here.now needs an explicit publish, so it is the one that could fall behind.
#
# That asymmetry is the only way the two could ever drift, so this script removes it by
# doing both in one go and then checking both, rather than trusting either.
#
# Pages lags a push by a minute or two, so the check polls for the rebuild instead of
# calling the lag a failure.
#
#   ./deploy.sh "what changed"
set -euo pipefail

REPO="/Users/cerebral/Documents/pigskin-punts"
DIST="/tmp/psp-dist"
PUBLISH="/Users/cerebral/.hermes/skills/productivity/here-now/scripts/publish.sh"
SLUG="waking-walrus-3vcd"
GH="https://ringoaigit.github.io/pigskin-punts"
HN="https://waking-walrus-3vcd.here.now"
SITE_FILES="index.html bets.html results.html method.html week-01.html protocol.html seal-client.html reply-to-curly.md README.md .nojekyll assets"
PAGES="index.html bets.html results.html method.html week-01.html protocol.html seal-client.html"
PAGES_WAIT_TRIES=12      # 12 x 15s = 3 minutes of grace for the Pages rebuild

MSG="${1:-Site update}"
cd "$REPO"

echo "0. refresh the games the form offers (snapshot of the live TAB slate)"
if python3 build_slate.py; then :; else echo "   slate refresh failed — shipping the previous snapshot"; fi

echo "0b. rebuild the board — every price we checked, ranked best first"
if python3 build_board.py; then :; else echo "   board build failed — shipping the previous board"; fi

echo "1. build stamp + asset versions"
python3 stamp.py > /dev/null
echo "   $(python3 -c "import json;print(json.load(open('assets/data/build.json'))['built_human'])")"
# here.now caches assets for an hour, so the pages point at a content-hashed URL. Without
# this a deploy can take up to a day to reach a browser that already has the old file.
python3 version_assets.py

echo "2. commit + push (this is what updates GitHub Pages)"
git add -A
if git diff --cached --quiet; then
  echo "   nothing to commit"
else
  git commit -q -m "$MSG"
  echo "   committed: $(git log --oneline -1)"
fi
git push -q origin main
echo "   pushed to main"

echo "3. publish to here.now (the host that needs telling)"
rm -rf "$DIST" && mkdir -p "$DIST"
for f in $SITE_FILES; do cp -R "$f" "$DIST"/; done
# The Site Data manifest has to sit at the root of what gets published, so the page's own
# record store ships with the site. It is here.now-only: GitHub Pages ignores it.
mkdir -p "$DIST/.herenow"
cp site-data.json "$DIST/.herenow/data.json"
bash "$PUBLISH" "$DIST" --slug "$SLUG" --client hermes 2>&1 | grep -E "publish_result\.(persistence|auth_mode|action)" | sed 's/^/   /'

echo "4. verify BOTH hosts actually serve the site"
fail=0
for p in $PAGES; do
  gh_code=$(curl -s -o /dev/null -w "%{http_code}" "$GH/$p")
  hn_code=$(curl -s -o /dev/null -w "%{http_code}" "$HN/$p")
  [ "$gh_code" = "200" ] || fail=1
  [ "$hn_code" = "200" ] || fail=1
  printf "   %-18s github %s   here.now %s\n" "/$p" "$gh_code" "$hn_code"
done

echo "5. do they agree on which build is live?"
stamp_of() {
  curl -s --compressed "$1/assets/data/build.json" 2>/dev/null \
    | python3 -c "import json,sys;print(json.load(sys.stdin).get('built_utc',''))" 2>/dev/null \
    || echo ""
}
hn_utc=$(stamp_of "$HN")
echo "   here.now $hn_utc  (published just now)"
gh_utc=$(stamp_of "$GH")
i=0
while [ "$gh_utc" != "$hn_utc" ] && [ "$i" -lt "$PAGES_WAIT_TRIES" ]; do
  i=$((i + 1))
  sleep 15
  gh_utc=$(stamp_of "$GH")
  echo "   github   $gh_utc  (waiting for the rebuild, $i/$PAGES_WAIT_TRIES)"
done
if [ "$gh_utc" = "$hn_utc" ]; then
  echo "   github   $gh_utc  (caught up)"
else
  echo "   github   $gh_utc  - STILL BEHIND after $((PAGES_WAIT_TRIES * 15 / 60)) minutes"
  fail=1
fi

echo
if [ "$fail" = "0" ]; then
  echo "both hosts serving the same build."
else
  echo "SOMETHING IS WRONG - see above."
  exit 1
fi
