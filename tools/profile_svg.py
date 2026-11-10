"""Render the debugger-styled SVGs used by the profile README.

    python tools/profile_svg.py header --out assets      # static hexdump banner
    python tools/profile_svg.py stats --user 0xLaileb --out dist
    python tools/profile_svg.py icons --out assets/icons/dark  # dark-page icon tiles
    python tools/profile_svg.py all --out dist             # every live card + data.json
    python tools/profile_svg.py all --out <dir> --demo     # same, offline sample data

`stats` and `activity` read GitHub GraphQL with GITHUB_TOKEN (or GH_TOKEN). With
the default Actions token only public repositories count toward languages and
stars; a token that can read private repositories adds them to the language map.
Contribution totals include private contributions whenever the profile shows them.
The call stack in `activity` lists public, non-fork repositories only.

`memory` and `fame` are the two visitor games. Their state is not stored in the
repository: it is rebuilt on every render from closed issues that the workflow
(tools/play.py) labelled `poke` or `solved`. Only the workflow and the owner can
set labels, so a label is the proof that an issue was validated.

`all` renders stats, activity, memory and fame in one pass and writes data.json,
which the Pages site (site/index.html) reads.

`icons` copies every icon from --src whose tile is the stock skill-icons #242938
with a lighter tile: on GitHub's dark canvas the stock one barely stands out.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import random
import re
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

W = 820
FONT = "ui-monospace,SFMono-Regular,'Cascadia Mono',Consolas,'Liberation Mono',Menlo,monospace"

THEMES = {
    "dark": dict(
        bg="#0d1117", panel="#161b22", bar="#1c2128", border="#30363d", text="#c9d1d9",
        muted="#8b949e", dim="#484f58", accent="#bc8cff", ascii="#7ee787", addr="#79c0ff",
        warn="#d29922", mod="#ff7b72", sel="#bc8cff", tile="#343a46",
    ),
    "light": dict(
        bg="#ffffff", panel="#f6f8fa", bar="#eaeef2", border="#d0d7de", text="#1f2328",
        muted="#656d76", dim="#8c959f", accent="#8250df", ascii="#1a7f37", addr="#0969da",
        warn="#9a6700", mod="#cf222e", sel="#8250df", tile="#242938",
    ),
}

# The crackme: one dump row is the flag XORed with a repeating key. The plaintext is
# deliberately absent from the repository; flag() derives it when a proof is checked.
KEY = b"\x13\x37"
CIPHER = bytes.fromhex("234f5f4c610427534c5a6a6861037e4a")

# Every row is exactly 16 bytes: one line of a memory dump.
ROWS = [
    b"0xLaileb" + b"\x00" * 8,
    b"C#/.NET/C++/SQL\x00",
    b"backend/realtime",
    b"vpn/xray/proxies",
    b"trading & crypto",
    b"vibe-coding w/AI",
    CIPHER,
    b"without a trace.",
]
BASE = 0x00007FF60A11EB00  # 0A11EB reads as "0AILEB"
ROW_H = 22

# Issue titles are the only visitor input. Both patterns are matched with fullmatch.
POKE = re.compile(r"poke\s+(?:0x)?([0-9a-f]{1,2})\s+(?:0x)?([0-9a-f]{1,2})", re.I)
PROOF = re.compile(r"crackme\s+([0-9a-f]{64})", re.I)


def flag():
    return bytes(b ^ KEY[i % len(KEY)] for i, b in enumerate(CIPHER)).decode()


def proof(login):
    """What a solver submits: tied to their login, so a public issue spoils nothing."""
    return hashlib.sha256(f"{flag()}:{login.lower()}".encode()).hexdigest()


def parse_poke(title):
    m = POKE.fullmatch(title.strip())
    return (int(m[1], 16), int(m[2], 16)) if m else None


def parse_proof(title):
    m = PROOF.fullmatch(title.strip())
    return m[1].lower() if m else None

REDUCED = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


def t(x, y, s, cls="", extra=""):
    c = f' class="{cls}"' if cls else ""
    return f'<text x="{x:g}" y="{y:g}"{c}{extra}>{escape(s)}</text>'


def frame(c, h, title, tabs):
    """Window chrome shared by both cards: title bar, tab strip, status bar."""
    out = [
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="10" fill="{c["panel"]}" stroke="{c["border"]}"/>',
        f'<path d="M1 32V11a10 10 0 0 1 10-10h{W - 22}a10 10 0 0 1 10 10v21z" fill="{c["bar"]}"/>',
        f'<line x1="1" y1="32.5" x2="{W - 1}" y2="32.5" stroke="{c["border"]}"/>',
        t(16, 21, title, "m"),
    ]
    x = 16
    for i, name in enumerate(tabs):
        width = len(name) * 7.6 + 20
        if i == 0:
            out.append(f'<rect x="{x:g}" y="40" width="{width:g}" height="22" rx="4" fill="{c["bg"]}" stroke="{c["border"]}"/>')
        out.append(t(x + 10, 55, name, "" if i == 0 else "m"))
        x += width + 6
    return out


def attr(s):
    return escape(s, {'"': "&quot;"})


def svg(c, h, label, body, css):
    style = (
        f"text{{font-family:{FONT};font-size:13px;fill:{c['text']};white-space:pre}}"
        f".m{{fill:{c['muted']}}}.d{{fill:{c['dim']}}}.ac{{fill:{c['accent']}}}.ad{{fill:{c['addr']}}}"
        f".as{{fill:{c['ascii']}}}.md{{fill:{c['mod']}}}.b{{font-weight:600}}" + css + REDUCED
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{attr(label)}">'
        f"<title>{escape(label)}</title><style>{style}</style>" + "".join(body) + "</svg>"
    )


def render_header(c):
    top, hex_x, ascii_x = 96, 196, 636
    rows_end = top + ROW_H * len(ROWS)
    h = rows_end + 44
    last = len(ROWS) - 1

    n = len(ROWS)
    css = (
        f"@keyframes bin{{0%{{opacity:0;fill:{c['accent']}}}35%{{opacity:1;fill:{c['accent']}}}100%{{opacity:1}}}}"
        "@keyframes ain{0%{opacity:0}100%{opacity:1}}"
        f"@keyframes sel{{from{{transform:translateY(0)}}to{{transform:translateY({ROW_H * n}px)}}}}"
        "@keyframes gone{0%,55%{opacity:1}58%{opacity:.25}60%{opacity:1}63%{opacity:.15}70%,90%{opacity:0}100%{opacity:1}}"
        "@keyframes ghost{0%,63%{opacity:0}70%,90%{opacity:1}100%{opacity:0}}"
        ".x{animation:bin .6s ease-out both}.y{animation:ain .12s linear both}"
        f".sel{{animation:sel {1.6 * n:g}s steps({n},end) 5s infinite}}"
        ".gone{animation:gone 8s ease-in-out 5.5s infinite}.ghost{opacity:0;animation:ghost 8s ease-in-out 5.5s infinite}"
    )

    body = frame(c, h, "0xLaileb.exe  ·  PID 1337  ·  Module: 0xlaileb.exe  ·  Thread: Main",
                 ["Dump 1", "Dump 2", "Watch 1", "Locals", "Struct"])
    body += [
        t(20, top - 12, "Address", "m"), t(hex_x, top - 12, "Hex", "m"), t(ascii_x, top - 12, "ASCII", "m"),
        f'<line x1="1" y1="{top - 6.5}" x2="{W - 1}" y2="{top - 6.5}" stroke="{c["border"]}"/>',
        f'<line x1="{hex_x - 12.5}" y1="{top - 28}" x2="{hex_x - 12.5}" y2="{rows_end}" stroke="{c["border"]}"/>',
        f'<line x1="{ascii_x - 12.5}" y1="{top - 28}" x2="{ascii_x - 12.5}" y2="{rows_end}" stroke="{c["border"]}"/>',
        f'<rect class="sel" x="8" y="{top - 4}" width="{W - 16}" height="{ROW_H}" rx="3" fill="{c["sel"]}" fill-opacity=".13"/>',
    ]

    for r, data in enumerate(ROWS):
        y = top + 12 + r * ROW_H
        start = 0.5 + r * 0.55
        name_row = r == 0
        cipher_row = data is CIPHER  # drawn like bytes a debugger marks as modified
        addr = f"{BASE + r * 16:016X}"
        row = [t(20, y, f"{addr[:8]}`{addr[8:]}", "ad")]
        for i, byte in enumerate(data):
            x = hex_x + i * 25.5 + (8 if i >= 8 else 0)
            cls = "x md" if cipher_row else "x b ac" if name_row and byte else ("x d" if byte == 0 else "x")
            row.append(t(x, y, f"{byte:02X}", cls, f' style="animation-delay:{start + i * 0.025:.3f}s"'))
        for i, byte in enumerate(data):
            ch = chr(byte) if 32 <= byte < 127 else "."
            cls = "y md" if cipher_row else "y b ac" if name_row and byte else ("y d" if byte == 0 else "y as")
            row.append(t(ascii_x + i * 9.8, y, ch, cls, f' style="animation-delay:{start + 0.35 + i * 0.02:.3f}s"'))
        if r == last:
            body.append('<g class="gone">' + "".join(row) + "</g>")
            ghost = [t(hex_x + i * 25.5 + (8 if i >= 8 else 0), y, "??", "d") for i in range(16)]
            ghost += [t(ascii_x + i * 9.8, y, "?", "d") for i in range(16)]
            body.append('<g class="ghost">' + "".join(ghost) + "</g>")
        else:
            body += row

    sy = rows_end + 10
    body += [
        f'<line x1="1" y1="{sy - 0.5}" x2="{W - 1}" y2="{sy - 0.5}" stroke="{c["border"]}"/>',
        f'<rect x="12" y="{sy + 7}" width="62" height="20" rx="4" fill="{c["warn"]}" fill-opacity=".18" stroke="{c["warn"]}" stroke-opacity=".6"/>',
        t(21, sy + 21, "Paused", "b", f' style="fill:{c["warn"]}"'),
        t(86, sy + 21, f"INT3 breakpoint at <0xlaileb.main> ({BASE:016X})!", "m"),
        t(W - 16, sy + 21, "Time Wasted Debugging: 13:37:00", "d", ' text-anchor="end"'),
    ]
    return svg(c, h, "0xLaileb: C#/.NET/C++/SQL, backend/realtime, vpn/xray/proxies, trading & crypto, vibe-coding w/AI", body, css)


QUERY = """
query($login: String!, $cursor: String, $first: Boolean!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    contributionsCollection @include(if: $first) {
      restrictedContributionsCount
      commitContributionsByRepository(maxRepositories: 100) { repository { isPrivate } contributions { totalCount } }
      issueContributionsByRepository(maxRepositories: 100) { repository { isPrivate } contributions { totalCount } }
      pullRequestContributionsByRepository(maxRepositories: 100) { repository { isPrivate } contributions { totalCount } }
      pullRequestReviewContributionsByRepository(maxRepositories: 100) { repository { isPrivate } contributions { totalCount } }
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
    repositories(ownerAffiliations: OWNER, first: 100, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name pushedAt isFork isPrivate stargazerCount
        primaryLanguage { name color }
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def closed_issues(repo, token, label):
    """Closed issues carrying a label, oldest first. Works without a token on a public repository."""
    headers = {"User-Agent": "profile-svg", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"bearer {token}"
    out, page = [], 1
    while True:
        query = urllib.parse.urlencode({"state": "closed", "labels": label, "sort": "created",
                                        "direction": "asc", "per_page": 100, "page": page})
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues?{query}", headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            batch = json.load(resp)
        out += [i for i in batch if "pull_request" not in i]
        if len(batch) < 100:
            return out
        page += 1


def collect_play(repo, token):
    """Replay the validated issues into the shared memory and the hall of fame."""
    mem, painters, last, pokes = bytearray(256), set(), None, 0
    for issue in closed_issues(repo, token, "poke"):
        hit = parse_poke(issue["title"])
        if hit:
            mem[hit[0]] = hit[1]
            painters.add(issue["user"]["login"].lower())
            last = {"login": issue["user"]["login"], "addr": hit[0], "value": hit[1]}
            pokes += 1
    fame, seen = [], set()
    for issue in closed_issues(repo, token, "solved"):
        login = issue["user"]["login"]
        if login.lower() not in seen:
            seen.add(login.lower())
            fame.append({"login": login, "date": issue["created_at"][:10]})
    return {"memory": bytes(mem), "pokes": pokes, "painters": len(painters), "last": last, "fame": fame}


def demo():
    """Deterministic sample data so every card can be rendered and inspected offline."""
    rnd = random.Random(1337)
    today = dt.date.today()
    day = today - dt.timedelta(days=364 + (today.weekday() + 1) % 7)  # a Sunday
    weeks = []
    while day <= today:
        week = []
        for _ in range(7):
            if day > today:
                break
            count = rnd.choice([0, 0, 0, 1, 2, 3, 5, 8, 13]) if day.weekday() < 5 else rnd.choice([0, 0, 1])
            week.append({"date": day.isoformat(), "count": count, "level": min(4, (count + 2) // 3)})
            day += dt.timedelta(days=1)
        weeks.append(week)
    mem = bytearray(256)
    for i in range(256):
        row, col = divmod(i, 16)
        if (row - 7.5) ** 2 + (col - 7.5) ** 2 < 40:
            mem[i] = (row // 2 << 5) | (col // 2 << 2) | 3
    mem[0x77] = 0xE3
    return {
        "weeks": weeks,
        "repos": [
            {"name": "sample-service", "lang": "C#", "color": "#178600", "stars": 42, "pushed": today.isoformat()},
            {"name": "sample-tooling", "lang": "Python", "color": "#3572A5", "stars": 7,
             "pushed": (today - dt.timedelta(days=9)).isoformat()},
            {"name": "sample-native", "lang": "C++", "color": "#f34b7d", "stars": 0,
             "pushed": (today - dt.timedelta(days=80)).isoformat()},
        ],
        "contributions": sum(d["count"] for w in weeks for d in w), "private": 512, "current": 4, "longest": 21,
        "stars": 49, "public": 12, "followers": 33, "years": 8,
        "langs": [("C#", (700_000, "#178600")), ("Python", (200_000, "#3572A5")), ("C++", (90_000, "#f34b7d"))],
        "updated": "demo data",
        "memory": bytes(mem), "pokes": 61, "painters": 9, "last": {"login": "sample-user", "addr": 0x77, "value": 0xE3},
        "fame": [{"login": "sample-user", "date": today.isoformat()}, {"login": "another-one", "date": today.isoformat()}],
    }


def export(s, user, repo):
    """The JSON the Pages site reads. Only public facts go in here."""
    return {
        "user": user, "repo": repo, "updated": s["updated"], "base": f"{BASE:016X}",
        "rows": [row.hex() for row in ROWS], "flag_sha256": hashlib.sha256(flag().encode()).hexdigest(),
        "stats": {k: s[k] for k in ("contributions", "private", "current", "longest", "stars", "public", "followers", "years")},
        "langs": [{"name": n, "size": size, "color": color} for n, (size, color) in s["langs"][:8]],
        "weeks": s["weeks"], "repos": s["repos"], "memory": s["memory"].hex(), "pokes": s["pokes"],
        "painters": s["painters"], "last": s["last"], "fame": s["fame"],
    }


def graphql(token, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-svg"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    if not payload["data"]["user"]:
        raise RuntimeError(f"GitHub user {variables['login']!r} not found")
    return payload["data"]["user"]


def collect(login, token):
    user, repos, cursor = None, [], None
    while True:
        page = graphql(token, {"login": login, "cursor": cursor, "first": user is None})
        user = user or page
        repos += page["repositories"]["nodes"]
        info = page["repositories"]["pageInfo"]
        if not info["hasNextPage"]:
            break
        cursor = info["endCursor"]

    days = [d for w in user["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    tail = days[:-1] if days and not days[-1]["contributionCount"] else days  # today may still be empty
    for d in reversed(tail):
        if not d["contributionCount"]:
            break
        current += 1

    langs = {}
    for repo in repos:
        if repo["isFork"]:
            continue
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            size, color = langs.get(name, (0, e["node"]["color"]))
            langs[name] = (size + e["size"], color or "#8b949e")

    public = [r for r in repos if not r["isPrivate"]]
    created = dt.date.fromisoformat(user["createdAt"][:10])
    cal = user["contributionsCollection"]
    # Restricted contributions are the private ones the token cannot see; the ones it
    # can see (a token of the profile owner) only show up per repository.
    private = cal["restrictedContributionsCount"] + sum(
        r["contributions"]["totalCount"]
        for kind in ("commit", "issue", "pullRequest", "pullRequestReview")
        for r in cal[f"{kind}ContributionsByRepository"]
        if r["repository"]["isPrivate"]
    )
    recent = sorted((r for r in public if not r["isFork"] and r["pushedAt"]),
                    key=lambda r: r["pushedAt"], reverse=True)[:6]
    return {
        "weeks": [
            [{"date": d["date"], "count": d["contributionCount"], "level": LEVELS.get(d["contributionLevel"], 0)}
             for d in w["contributionDays"]]
            for w in cal["contributionCalendar"]["weeks"]
        ],
        "repos": [
            {"name": r["name"], "lang": (r["primaryLanguage"] or {}).get("name") or "",
             "color": (r["primaryLanguage"] or {}).get("color") or "#8b949e",
             "stars": r["stargazerCount"], "pushed": r["pushedAt"][:10]}
            for r in recent
        ],
        "contributions": cal["contributionCalendar"]["totalContributions"],
        "private": private,
        "current": current,
        "longest": longest,
        "stars": sum(r["stargazerCount"] for r in public),
        "public": len(public),
        "followers": user["followers"]["totalCount"],
        "years": (dt.datetime.now(dt.timezone.utc).date() - created).days // 365,
        "langs": sorted(langs.items(), key=lambda kv: -kv[1][0]),
        "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def human(n):
    for unit in ("B", "KB", "MB"):
        if n < 1024 or unit == "MB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def luminance(color):
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def render_stats(c, s):
    top = 96
    regs = [
        ("RAX", s["contributions"], "contributions (1y)"),
        ("RBX", s["private"], "in private repos"),
        ("RCX", s["current"], "current streak, days"),
        ("RDX", s["longest"], "longest streak, days"),
        ("RSI", s["stars"], "stars earned"),
        ("RDI", s["public"], "public repos"),
        ("R8", s["followers"], "followers"),
        ("R9", s["years"], "years on GitHub"),
    ]
    h = top + ROW_H * (len(regs) + 1) + 40
    split = 452

    css = (
        "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
        ".bar{transform-box:fill-box;transform-origin:left;animation:grow 1.2s cubic-bezier(.2,.7,.2,1) both}"
    )
    body = frame(c, h, "0xLaileb.exe  ·  CPU  ·  Thread: Main",
                 ["Registers", "Memory Map", "Call Stack", "SEH"])
    body += [
        t(20, top - 12, "Registers", "m"), t(split + 16, top - 12, "Memory Map: languages", "m"),
        f'<line x1="1" y1="{top - 6.5}" x2="{W - 1}" y2="{top - 6.5}" stroke="{c["border"]}"/>',
        f'<line x1="{split + 0.5}" y1="{top - 28}" x2="{split + 0.5}" y2="{h - 34}" stroke="{c["border"]}"/>',
    ]
    for i, (reg, value, note) in enumerate(regs):
        y = top + 12 + i * ROW_H
        body += [
            t(20, y, reg, "b"),
            t(58, y, f"{value:016X}", "md" if i == 0 else ""),
            t(204, y, note, "m"),
            t(split - 14, y, f"{value:,}", "b ac", ' text-anchor="end"'),
        ]
    y = top + 12 + len(regs) * ROW_H
    top_lang = s["langs"][0][0] if s["langs"] else "?"
    body += [t(20, y, "RIP", "b"), t(58, y, f"{BASE:016X}", "ad"), t(204, y, "<0xlaileb.main>", "m"),
             t(split - 14, y, top_lang, "b ac", ' text-anchor="end"')]

    shown = s["langs"][:7]
    rest = sum(size for _, (size, _) in s["langs"][7:])
    if rest:
        shown.append(("Other", (rest, c["dim"])))
    total = sum(size for _, (size, _) in s["langs"]) or 1
    # Some linguist colors (PowerShell #012456) vanish on the dark panel.
    shown = [(n, (size, color if luminance(color) > 0.2 or c is THEMES["light"] else c["muted"]))
             for n, (size, color) in shown]
    bar_x, bar_w = split + 118, 96
    for i, (name, (size, color)) in enumerate(shown):
        y = top + 12 + i * ROW_H
        share = size / total
        body += [
            f'<rect x="{split + 16}" y="{y - 9}" width="10" height="10" rx="2" fill="{color}"/>',
            t(split + 34, y, name),
            f'<rect x="{bar_x}" y="{y - 9}" width="{bar_w}" height="10" rx="2" fill="{c["bar"]}"/>',
            f'<rect class="bar" x="{bar_x}" y="{y - 9}" width="{max(bar_w * share, 2):.1f}" height="10" rx="2" fill="{color}" style="animation-delay:{0.2 + i * 0.1:.1f}s"/>',
            t(W - 16, y, f"{share * 100:5.1f}% {human(size):>8}", "m", ' text-anchor="end"'),
        ]

    sy = h - 34
    body += [
        f'<line x1="1" y1="{sy - 0.5}" x2="{W - 1}" y2="{sy - 0.5}" stroke="{c["border"]}"/>',
        t(16, sy + 21, "Contributions include private repositories.", "d"),
        t(W - 16, sy + 21, f"updated {s['updated']}", "d", ' text-anchor="end"'),
    ]
    label = (f"{s['contributions']} contributions in the last year, {s['stars']} stars, "
             f"top languages: {', '.join(n for n, _ in shown)}")
    return svg(c, h, label, body, css)


def ago(day):
    n = (dt.datetime.now(dt.timezone.utc).date() - dt.date.fromisoformat(day)).days
    for size, unit in ((365, "y"), (30, "mo"), (7, "w"), (1, "d")):
        if n >= size:
            return f"{n // size}{unit} ago"
    return "today"


def render_activity(c, s):
    """Contribution calendar as a memory map, recent public repositories as a call stack."""
    top, cell, pitch, gx = 96, 12, 14, 46
    weeks = s["weeks"][-53:]
    repos = s["repos"][:5]
    gy = top + 18
    stack_y = gy + 7 * pitch + 8
    sy = stack_y + 30 + ROW_H * max(len(repos), 1)
    h = sy + 34

    css = "@keyframes ain{0%{opacity:0}100%{opacity:1}}.w{animation:ain .5s ease-out both}"
    body = frame(c, h, "0xLaileb.exe  ·  Memory Map  ·  Thread: Main",
                 ["Memory Map", "Call Stack", "Threads", "Handles"])
    body += [
        t(20, top - 12, "Memory Map: contributions, last 53 weeks", "m"),
        f'<line x1="1" y1="{top - 6.5}" x2="{W - 1}" y2="{top - 6.5}" stroke="{c["border"]}"/>',
        t(W - 126, top - 12, "less", "d", ' text-anchor="end"'), t(W - 16, top - 12, "more", "d", ' text-anchor="end"'),
    ]
    shade = [f'fill="{c["bar"]}"'] + [f'fill="{c["accent"]}" fill-opacity="{o}"' for o in (".3", ".5", ".75", "1")]
    for level in range(5):
        body.append(f'<rect x="{W - 120 + level * pitch}" y="{top - 22}" width="{cell}" height="{cell}" rx="2" {shade[level]}/>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        body.append(t(16, gy + row * pitch + 10, name, "d", ' style="font-size:11px"'))

    label_x = -100
    for w, week in enumerate(weeks):
        x = gx + w * pitch
        first = dt.date.fromisoformat(week[0]["date"])
        if first.day <= 7 and x - label_x > 40:
            body.append(t(x, top + 10, first.strftime("%b"), "d", ' style="font-size:11px"'))
            label_x = x
        cells = []
        for d in week:
            row = (dt.date.fromisoformat(d["date"]).weekday() + 1) % 7  # Sunday on top, like GitHub
            cells.append(f'<rect x="{x}" y="{gy + row * pitch}" width="{cell}" height="{cell}" rx="2" {shade[d["level"]]}/>')
        body.append(f'<g class="w" style="animation-delay:{0.2 + w * 0.02:.2f}s">' + "".join(cells) + "</g>")

    body += [
        f'<line x1="1" y1="{stack_y - 0.5}" x2="{W - 1}" y2="{stack_y - 0.5}" stroke="{c["border"]}"/>',
        t(20, stack_y + 16, "Call Stack: recently pushed public repositories", "m"),
        f'<line x1="1" y1="{stack_y + 22.5}" x2="{W - 1}" y2="{stack_y + 22.5}" stroke="{c["border"]}"/>',
    ]
    if not repos:
        body.append(t(20, stack_y + 40, "<no public frames>", "d"))
    for i, repo in enumerate(repos):
        y = stack_y + 40 + i * ROW_H
        addr = f"{BASE + 0x1000 * (i + 1):016X}"
        color = repo["color"] if luminance(repo["color"]) > 0.2 or c is THEMES["light"] else c["muted"]
        body += [
            t(20, y, f"#{i}", "d"), t(52, y, f"{addr[:8]}`{addr[8:]}", "ad"),
            t(204, y, f"{repo['name'][:30]}!main", "b" if i == 0 else ""),
            t(690, y, f"★ {repo['stars']:,}", "m", ' text-anchor="end"'),
            t(W - 16, y, ago(repo["pushed"]), "m", ' text-anchor="end"'),
        ]
        if repo["lang"]:
            body += [f'<rect x="500" y="{y - 9}" width="10" height="10" rx="2" fill="{color}"/>',
                     t(518, y, repo["lang"][:14], "m")]

    days = [d for week in weeks for d in week]
    busiest = max(days, key=lambda d: d["count"]) if days else {"date": "?", "count": 0}
    body += [
        f'<line x1="1" y1="{sy - 0.5}" x2="{W - 1}" y2="{sy - 0.5}" stroke="{c["border"]}"/>',
        t(16, sy + 21, f"{len(days)} days mapped  ·  busiest {busiest['date']} ({busiest['count']})", "d"),
        t(W - 16, sy + 21, f"updated {s['updated']}", "d", ' text-anchor="end"'),
    ]
    label = (f"Contribution calendar of the last {len(weeks)} weeks and recently pushed repositories: "
             f"{', '.join(r['name'] for r in repos) or 'none'}")
    return svg(c, h, label, body, css)


def rgb332(byte):
    return f"#{(byte >> 5) * 255 // 7:02x}{((byte >> 2) & 7) * 255 // 7:02x}{(byte & 3) * 85:02x}"


def render_memory(c, s):
    """256 bytes any visitor can write, shown as a hexdump and as a 16x16 RGB332 picture."""
    top, row_h, hex_x, px_x = 96, 17, 76, 516
    mem, last = s["memory"], s["last"]
    rows_end = top + 16 * row_h
    h = rows_end + 44

    body = frame(c, h, "0xLaileb.exe  ·  Dump 2  ·  shared memory, writable by anyone",
                 ["Dump 2", "Dump 1", "Watch 1", "Locals"])
    body += [
        t(20, top - 12, "Offs", "m"), t(hex_x, top - 12, "Hex", "m"), t(px_x, top - 12, "Pixels (RGB332)", "m"),
        f'<line x1="1" y1="{top - 6.5}" x2="{W - 1}" y2="{top - 6.5}" stroke="{c["border"]}"/>',
        f'<line x1="{hex_x - 12.5}" y1="{top - 28}" x2="{hex_x - 12.5}" y2="{rows_end + 10}" stroke="{c["border"]}"/>',
        f'<line x1="{px_x - 12.5}" y1="{top - 28}" x2="{px_x - 12.5}" y2="{rows_end + 10}" stroke="{c["border"]}"/>',
        f'<rect x="{px_x - 0.5}" y="{top + 1.5}" width="{16 * row_h}" height="{16 * row_h}" fill="{c["bar"]}" stroke="{c["border"]}"/>',
    ]
    for i, byte in enumerate(mem):
        r, col = divmod(i, 16)
        y = top + 2 + r * row_h
        if col == 0:
            body.append(t(20, y + 12, f"{i:04X}", "ad"))
        cls = "md b" if last and last["addr"] == i else ("d" if byte == 0 else "")
        body.append(t(hex_x + col * 25.5 + (8 if col >= 8 else 0), y + 12, f"{byte:02X}", cls))
        if byte:
            body.append(f'<rect x="{px_x + col * row_h}" y="{y}" width="{row_h - 1}" height="{row_h - 1}" fill="{rgb332(byte)}"/>')

    sy = rows_end + 10
    note = f"{s['pokes']:,} pokes by {s['painters']:,} visitors"
    if last:
        note += f"  ·  last: @{last['login']} wrote {last['value']:02X} at {last['addr']:02X}"
    body += [
        f'<line x1="1" y1="{sy - 0.5}" x2="{W - 1}" y2="{sy - 0.5}" stroke="{c["border"]}"/>',
        t(16, sy + 21, note, "d"),
        t(W - 16, sy + 21, "poke <addr> <value>", "ac", ' text-anchor="end"'),
    ]
    return svg(c, h, f"Shared 256-byte memory painted by visitors: {note}", body, "")


def render_fame(c, s):
    """Everyone whose crackme proof the workflow accepted, first solver on top."""
    top, fame = 96, s["fame"]
    shown = fame[:8]
    sy = top + ROW_H * max(len(shown), 2) + 10
    h = sy + 34

    body = frame(c, h, "0xLaileb.exe  ·  crackme  ·  Hall of Fame", ["Hall of Fame", "Breakpoints", "Log"])
    body += [
        t(20, top - 12, "#", "m"), t(60, top - 12, "Solver", "m"), t(420, top - 12, "Solved", "m"),
        f'<line x1="1" y1="{top - 6.5}" x2="{W - 1}" y2="{top - 6.5}" stroke="{c["border"]}"/>',
    ]
    if not shown:
        body += [t(20, top + 12, "No one has decoded the flag yet.", "m"),
                 t(20, top + 12 + ROW_H, "One row of the header dump is not what it seems.", "d")]
    for i, entry in enumerate(shown):
        y = top + 12 + i * ROW_H
        body += [t(20, y, f"{i + 1:02}", "d"), t(60, y, f"@{entry['login']}", "b ac" if i == 0 else ""),
                 t(420, y, entry["date"], "m")]
        if i == 0:
            body.append(t(W - 16, y, "first blood", "b", f' text-anchor="end" style="fill:{c["warn"]}"'))

    more = f"  ·  +{len(fame) - len(shown)} more" if len(fame) > len(shown) else ""
    body += [
        f'<line x1="1" y1="{sy - 0.5}" x2="{W - 1}" y2="{sy - 0.5}" stroke="{c["border"]}"/>',
        t(16, sy + 21, f"{len(fame):,} solved{more}", "d"),
        t(W - 16, sy + 21, "crackme <sha256(flag:login)>", "ac", ' text-anchor="end"'),
    ]
    names = ", ".join(e["login"] for e in shown) or "nobody yet"
    return svg(c, h, f"Crackme hall of fame: {names}", body, "")


def render_icons(src, out):
    """Re-tile the dark-tiled icons for GitHub's dark theme; colored tiles are fine as they are."""
    stock, tile = THEMES["light"]["tile"], THEMES["dark"]["tile"]
    for icon in sorted(src.glob("*.svg")):
        doc = icon.read_text(encoding="utf-8")
        if doc.count(stock) != 1:
            continue
        (out / icon.name).write_text(doc.replace(stock, tile), encoding="utf-8")
        print(out / icon.name)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("what", choices=["header", "stats", "activity", "memory", "fame", "all", "icons"])
    p.add_argument("--out", required=True)
    p.add_argument("--user", default="0xLaileb")
    p.add_argument("--repo", help="repository holding the game issues; default GITHUB_REPOSITORY or <user>/<user>")
    p.add_argument("--src", default="assets/icons", help="icons: directory with the stock icons")
    p.add_argument("--demo", action="store_true", help="render the live cards from built-in sample data")
    a = p.parse_args()

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what == "icons":
        return render_icons(pathlib.Path(a.src), out)

    cards = ["stats", "activity", "memory", "fame"] if a.what == "all" else [a.what]
    repo = a.repo or os.environ.get("GITHUB_REPOSITORY") or f"{a.user}/{a.user}"
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    data = {}
    if a.demo:
        data = demo()
    else:
        if {"stats", "activity"} & set(cards):
            if not token:
                raise SystemExit("GITHUB_TOKEN or GH_TOKEN is required")
            data.update(collect(a.user, token))
        if {"memory", "fame"} & set(cards):
            data.update(collect_play(repo, token))

    render = {"header": lambda c, _: render_header(c), "stats": render_stats, "activity": render_activity,
              "memory": render_memory, "fame": render_fame}
    for card in cards:
        for name, colors in THEMES.items():
            (out / f"{card}-{name}.svg").write_text(render[card](colors, data), encoding="utf-8")
            print(out / f"{card}-{name}.svg")
    if a.what == "all":
        (out / "data.json").write_text(json.dumps(export(data, a.user, repo), separators=(",", ":")), encoding="utf-8")
        print(out / "data.json")


if __name__ == "__main__":
    main()
