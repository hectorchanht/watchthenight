#!/usr/bin/env python3
"""POST/PUT/PATCH to the GitHub API reading the JSON body from stdin.

Same auth as ghapi (authd surrogate), but avoids the 128KB single-argv
limit that breaks large blob uploads via `ghapi --data`.

Usage: echo '{"content": "..."}' | ghpost.py POST /repositories/123/git/blobs
"""
import json
import sys
import urllib.request
import urllib.error

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response

BASE = "https://api.github.com"
CREDENTIAL = "custom.github-pat"
ALLOWED = ("api.github.com",)


def main() -> int:
    method = sys.argv[1].upper()
    path = sys.argv[2]
    data = sys.stdin.read().encode("utf-8")

    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "muse-github-pat-skill")
    req.add_header("Content-Type", "application/json")
    add_surrogate_to_request(req, CREDENTIAL, allowed_hosts=ALLOWED)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status == 204:
                print(json.dumps({"ok": True, "status": 204}))
                return 0
            print(json.dumps(read_json_response(resp), indent=2))
            return 0
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        print(f"HTTP {exc.code}: {body[:1000]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
