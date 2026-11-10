"""Validate one visitor issue for the profile games and answer it.

Run by the workflow on `issues: opened`. Everything the visitor controls arrives through
environment variables and is matched against the fixed patterns in profile_svg; the title
is never passed to a shell and never echoed back unless it matched.

    ISSUE_NUMBER, ISSUE_TITLE, ISSUE_AUTHOR, GITHUB_REPOSITORY, GITHUB_TOKEN

A valid issue gets the `poke` or `solved` label and is closed; the render step later rebuilds
the cards from those labels. Writes `accepted=true|false` to GITHUB_OUTPUT.
"""

import datetime as dt
import json
import os
import urllib.parse
import urllib.request

import profile_svg

DAILY_POKES = 32


def decide(title, author, pokes_today=0, already_solved=False):
    """Pure decision: (label, accepted, state_reason, comment)."""
    hit = profile_svg.parse_poke(title)
    if hit:
        if pokes_today >= DAILY_POKES:
            return ("rate-limited", False, "not_planned",
                    f"Write fault: {DAILY_POKES} pokes per 24 hours per visitor. Try again later.")
        addr, value = hit
        return ("poke", True, "completed",
                f"`mov byte ptr [0x{addr:02X}], 0x{value:02X}` executed. "
                "The memory card on the profile is re-rendered within a few minutes.")
    given = profile_svg.parse_proof(title)
    if given:
        if given != profile_svg.proof(author):
            return ("invalid", False, "not_planned",
                    "Access violation: wrong proof. It must be `sha256(\"<flag>:<your login in lowercase>\")` as 64 hex digits.")
        if already_solved:
            return ("duplicate", False, "not_planned", "You are already in the hall of fame.")
        return ("solved", True, "completed",
                f"Breakpoint hit. Welcome to the hall of fame, @{author}. Please keep the flag to yourself.")
    return ("invalid", False, "not_planned",
            "Could not parse that. Use `poke <addr> <value>` (two hex bytes, for example `poke 3F E0`) "
            "or `crackme <64 hex digits>`.")


def api(method, path, body=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": "profile-svg",
                 "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def labelled(author, label):
    query = urllib.parse.urlencode({"creator": author, "labels": label, "state": "all", "per_page": 100})
    return [i for i in api("GET", f"/issues?{query}") if "pull_request" not in i]


def main():
    number, title, author = int(os.environ["ISSUE_NUMBER"]), os.environ["ISSUE_TITLE"], os.environ["ISSUE_AUTHOR"]
    day_ago = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    pokes_today = sum(i["created_at"] >= day_ago for i in labelled(author, "poke"))
    label, accepted, reason, comment = decide(title, author, pokes_today, bool(labelled(author, "solved")))

    api("POST", f"/issues/{number}/labels", {"labels": [label]})
    api("POST", f"/issues/{number}/comments", {"body": comment})
    api("PATCH", f"/issues/{number}", {"state": "closed", "state_reason": reason})
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        out.write(f"accepted={'true' if accepted else 'false'}\n")
    print(label)


if __name__ == "__main__":
    main()