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
#   ./deploy.sh "what changed"
set -euo pipefail

REPO="/Users/cerebral/Documents/pigskin-punts"
DIST="/tmp/psp-dist"
PUBLISH="/Users/cerebral/.hermes/skills/productivity/here-now/scripts/publish.sh"
SLUG="waking-walrus-3vcd"
GH="https://ringoaigit.github.io/pigskin-punts"
HN="https://waking-walrus-3vcd.here.now"
SITE_FILES="index.html bets.html results.html method.html week-01.html protocol.html seal-client.html reply-to-curly.md README.md .nojekyll assets"
PAGES=" bets.html results.html method.html week-01.html protocol.html seal-client.html"

MSG="${1:-Site update}"
cd "$REPO"

echo "1. build stamp"
python3 stamp.py > /dev/null
echo "   $(python3 -c "import json;print(json.load(open('assets/data/build.json'))['built_human'])")"

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
gh_commit=$(curl -s --compressed "$GH/assets/data/build.json" | python3 -c "import json,sys;print(json.load(sys.stdin)['built_utc'])")
hn_commit=$(curl -s --compressed "$HN/assets/data/build.json" | python3 -c "import json,sys;print(json.load(sys.stdin)['built_utc'])")
echo "   github   $gh_commit"
echo "   here.now $hn_commit"
[ "$gh_commit" = "$hn_commit" ] || { echo "   MISMATCH - the two hosts are serving different builds"; fail=1; }

if [ "$fail" = "0" ]; then
  echo
  echo "both hosts serving the same build."
else
  echo
  echo "SOMETHING IS WRONG - see above. Pages can lag a minute or two behind a push."
  exit 1
fi
