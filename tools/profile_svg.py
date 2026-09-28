"""Render the debugger-styled SVGs used by the profile README.

    python tools/profile_svg.py header --out assets      # static hexdump banner
    python tools/profile_svg.py stats --user 0xLaileb --out dist

`stats` reads GitHub GraphQL with GITHUB_TOKEN (or GH_TOKEN). With the default
Actions token only public repositories count toward languages and stars; a
token that can read private repositories adds them to the language map.
Contribution totals include private contributions whenever the profile shows them.
"""

import argparse
import datetime as dt
import json
import os
import pathlib
import urllib.request
from xml.sax.saxutils import escape

W = 820
FONT = "ui-monospace,SFMono-Regular,'Cascadia Mono',Consolas,'Liberation Mono',Menlo,monospace"

THEMES = {
    "dark": dict(
        bg="#0d1117", panel="#161b22", bar="#1c2128", border="#30363d", text="#c9d1d9",
        muted="#8b949e", dim="#484f58", accent="#bc8cff", ascii="#7ee787", addr="#79c0ff",
        warn="#d29922", mod="#ff7b72", sel="#bc8cff",
    ),
    "light": dict(
        bg="#ffffff", panel="#f6f8fa", bar="#eaeef2", border="#d0d7de", text="#1f2328",
        muted="#656d76", dim="#8c959f", accent="#8250df", ascii="#1a7f37", addr="#0969da",
        warn="#9a6700", mod="#cf222e", sel="#8250df",
    ),
}

# Every row is exactly 16 bytes: one line of a memory dump.
ROWS = [
    b"0xLaileb" + b"\x00" * 8,
    b"C#/.NET/C++/SQL\x00",
    b"reverse engineer",
    b"vpn/xray/proxies",
    b"trading & crypto",
    b"vibe-coding w/AI",
    b"without a trace.",
]
BASE = 0x00007FF60A11EB00  # 0A11EB reads as "0AILEB"
ROW_H = 22

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


def svg(c, h, label, body, css):
    style = (
        f"text{{font-family:{FONT};font-size:13px;fill:{c['text']};white-space:pre}}"
        f".m{{fill:{c['muted']}}}.d{{fill:{c['dim']}}}.ac{{fill:{c['accent']}}}.ad{{fill:{c['addr']}}}"
        f".as{{fill:{c['ascii']}}}.md{{fill:{c['mod']}}}.b{{font-weight:600}}" + css + REDUCED
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{escape(label)}">'
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
        addr = f"{BASE + r * 16:016X}"
        row = [t(20, y, f"{addr[:8]}`{addr[8:]}", "ad")]
        for i, byte in enumerate(data):
            x = hex_x + i * 25.5 + (8 if i >= 8 else 0)
            cls = "x b ac" if name_row and byte else ("x d" if byte == 0 else "x")
            row.append(t(x, y, f"{byte:02X}", cls, f' style="animation-delay:{start + i * 0.025:.3f}s"'))
        for i, byte in enumerate(data):
            ch = chr(byte) if 32 <= byte < 127 else "."
            cls = "y b ac" if name_row and byte else ("y d" if byte == 0 else "y as")
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
    return svg(c, h, "0xLaileb: C#/.NET/C++/SQL, reverse engineer, vpn/xray/proxies, trading & crypto, vibe-coding w/AI", body, css)


QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    contributionsCollection {
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(ownerAffiliations: OWNER, first: 100, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        isFork isPrivate stargazerCount
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


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
    return payload["data"]["user"]


def collect(login, token):
    user, repos, cursor = None, [], None
    while True:
        page = graphql(token, {"login": login, "cursor": cursor})
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
    return {
        "contributions": cal["contributionCalendar"]["totalContributions"],
        "private": cal["restrictedContributionsCount"],
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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("what", choices=["header", "stats"])
    p.add_argument("--out", required=True)
    p.add_argument("--user", default="0xLaileb")
    a = p.parse_args()

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what == "stats":
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN or GH_TOKEN is required")
        data = collect(a.user, token)
    for name, colors in THEMES.items():
        doc = render_header(colors) if a.what == "header" else render_stats(colors, data)
        (out / f"{a.what}-{name}.svg").write_text(doc, encoding="utf-8")
        print(out / f"{a.what}-{name}.svg")


if __name__ == "__main__":
    main()
