#!/usr/bin/env python3
"""Targeted push to hectorchanht/watchthenight via the GitHub Git Data API.

Usage: push.py "<commit message>" <file...>   (paths relative to repo root ~/workspace/sites/skygear)
Only files whose content differs from the remote main tree are pushed.
Requires: ~/workspace/skills/github-pat/bin/ghapi
"""
import base64, hashlib, json, os, subprocess, sys

REPO_ID = "1408626059"
ROOT = os.path.expanduser("~/workspace/sites/skygear")
GHAPI = os.path.expanduser("~/workspace/skills/github-pat/bin/ghapi")
GHPOST = os.path.join(ROOT, "bin", "ghpost.py")

def api(method, path, data=None):
    if data is not None:
        # pipe big JSON bodies via stdin: argv entries are capped at 128KB
        # (breaks large blob uploads through `ghapi --data`)
        out = subprocess.run(
            [sys.executable, GHPOST, method, f"/repositories/{REPO_ID}{path}"],
            input=json.dumps(data), capture_output=True, text=True, check=True,
        ).stdout
    else:
        cmd = [GHAPI, method, f"/repositories/{REPO_ID}{path}"]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(out)

def main():
    msg = sys.argv[1]
    files = sys.argv[2:]
    os.chdir(ROOT)

    # current head
    head = api("GET", "/git/refs/heads/main")["object"]["sha"]
    tree = api("GET", f"/git/trees/{head}?recursive=1")["tree"]
    remote = {t["path"]: t["sha"] for t in tree if t["type"] == "blob"}

    changed = []
    for f in files:
        if not os.path.isfile(f):
            print(f"skip (missing): {f}", file=sys.stderr); continue
        with open(f, "rb") as fh:
            raw = fh.read()
        local_sha = hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()
        if remote.get(f) == local_sha:
            continue  # unchanged
        blob = api("POST", "/git/blobs", {
            "content": base64.b64encode(raw).decode(), "encoding": "base64"})
        sha = blob.get("sha")
        assert sha, f"empty blob sha for {f} — refusing (would delete file)"
        changed.append({"path": f, "mode": "100644", "type": "blob", "sha": sha})

    if not changed:
        print("no changes vs remote main")
        return

    new_tree = api("POST", "/git/trees", {"base_tree": head, "tree": changed})["sha"]
    commit = api("POST", "/git/commits", {
        "message": msg, "tree": new_tree, "parents": [head]})["sha"]
    api("PATCH", "/git/refs/heads/main", {"sha": commit})
    print(f"pushed {commit} ({len(changed)} files)")

if __name__ == "__main__":
    main()
