#!/bin/bash
# Daily auto-update for Watch the Night: regenerate tonight's sky data,
# rebuild the site, and push changed deploy files via the GitHub Git Data API.
# Cloudflare Pages auto-deploys on push to main. New products/guides are NOT
# auto-added — those go through Hector's draft -> approve loop.
set -e
cd ~/workspace/sites/skygear
GH=~/workspace/skills/github-pat/bin/ghapi
RID=1408626059

python3 tonight.py
python3 build.py

FILES="dist/index.html dist/sitemap.xml src/tonight.json"
HEAD=$($GH GET /repos/hectorchanht/watchthenight/git/ref/heads/main | python3 -c "import json,sys;print(json.load(sys.stdin)['object']['sha'])")
TREE=$($GH GET /repos/hectorchanht/watchthenight/git/commits/$HEAD | python3 -c "import json,sys;print(json.load(sys.stdin)['tree']['sha'])")
ENTRIES=""
for f in $FILES; do
  B64=$(python3 -c "import base64,sys;print(base64.b64encode(open(sys.argv[1],'rb').read()).decode())" "$f")
  SHA=$($GH POST /repositories/$RID/git/blobs --data "{\"content\":\"$B64\",\"encoding\":\"base64\"}" | python3 -c "import json,sys;print(json.load(sys.stdin)['sha'])")
  [ -n "$SHA" ] || { echo "EMPTY SHA for $f"; exit 1; }
  ENTRIES="$ENTRIES{\"path\":\"$f\",\"mode\":\"100644\",\"type\":\"blob\",\"sha\":\"$SHA\"},"
done
ENTRIES="[${ENTRIES%,}]"
NEW_TREE=$($GH POST /repositories/$RID/git/trees --data "{\"base_tree\":\"$TREE\",\"tree\":$ENTRIES}" | python3 -c "import json,sys;print(json.load(sys.stdin)['sha'])")
NEW_COMMIT=$($GH POST /repositories/$RID/git/commits --data "{\"message\":\"daily: tonight's sky $(date +%F)\",\"tree\":\"$NEW_TREE\",\"parents\":[\"$HEAD\"]}" | python3 -c "import json,sys;print(json.load(sys.stdin)['sha'])")
$GH PATCH /repositories/$RID/git/refs/heads/main --data "{\"sha\":\"$NEW_COMMIT\"}" >/dev/null
echo "daily update pushed: $NEW_COMMIT"
