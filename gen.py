"""Renders assets/card-{dark,light}.svg from GitHub data. Run daily by .github/workflows/cards.yml.
Languages include private repos when the token can see them (STATS_TOKEN secret)."""
import json, os, urllib.request
from collections import Counter
from html import escape

LOGIN = os.environ.get("LOGIN", "LazerProOk1")
NOTE = "i build small things."  # edit me
SKIP_LANGS = {"HTML", "CSS", "SCSS", "Dockerfile", "NSIS", "Jupyter Notebook", "Makefile", "Batchfile", "Shell", "PowerShell", "GLSL", "GDShader", "GDScript", "Typst"}

QUERY = """query($login:String!){ user(login:$login){
  contributionsCollection{ totalCommitContributions restrictedContributionsCount
    commitContributionsByRepository(maxRepositories:25){ repository{ name nameWithOwner isPrivate owner{login} }
      contributions(first:1, orderBy:{field:OCCURRED_AT,direction:DESC}){ nodes{ occurredAt } } } }
  repositories(first:100, ownerAffiliations:[OWNER,COLLABORATOR,ORGANIZATION_MEMBER]){ nodes{
    isFork isPrivate stargazerCount owner{login}
    languages(first:10, orderBy:{field:SIZE,direction:DESC}){ edges{ size node{name} } } } } } }"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": "profile-card"},
    )
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]


def stats(u):
    repos = u["repositories"]["nodes"]
    pub = [r for r in repos if not r["isPrivate"]]
    own = [r for r in repos if r["owner"]["login"] == LOGIN and not r["isFork"]]
    sizes = Counter()
    for r in repos:  # own + collaborator repos; private ones only with STATS_TOKEN
        if r["isFork"]:
            continue
        for e in r["languages"]["edges"]:
            if e["node"]["name"] not in SKIP_LANGS:
                sizes[e["node"]["name"]] += e["size"]
    total = sum(sizes.values()) or 1
    cc = u["contributionsCollection"]
    # latest public repo you committed to (yours or someone else's), private names never shown
    recent = sorted(
        ((c["contributions"]["nodes"][0]["occurredAt"], c["repository"]) for c in cc["commitContributionsByRepository"]
         if c["contributions"]["nodes"] and not c["repository"]["isPrivate"] and c["repository"]["nameWithOwner"] != f"{LOGIN}/{LOGIN}"),
        key=lambda x: x[0], reverse=True)
    recent = [r["name"] if r["owner"]["login"] == LOGIN else r["nameWithOwner"] for _, r in recent]
    return {
        "langs": [(n.lower(), s / total) for n, s in sizes.most_common(6) if s / total >= .01],
        "nums": [
            (sum(r["stargazerCount"] for r in pub), "stars"),
            (cc["totalCommitContributions"] + cc["restrictedContributionsCount"], "commits this year"),
            (sum(not r["isPrivate"] for r in own), "repos"),
        ],
        "now": recent[0] if recent else "",
    }


THEMES = {
    "dark": dict(bg="#0d1117", border="#21262d", text="#e6edf3", muted="#7d8590", track="#161b22", accent="#a371f7"),
    "light": dict(bg="#ffffff", border="#d8dee4", text="#1f2328", muted="#6e7781", track="#f0f2f4", accent="#8250df"),
}


def render(s, t):
    W, H, X = 860, 300, 44
    LX, BX, BW = 480, 580, 190  # languages column: name, bar start, bar width
    o = [f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
text{{font-family:'JetBrains Mono','SF Mono',Consolas,'Liberation Mono',Menlo,monospace}}
.f{{opacity:0;animation:f .7s ease forwards}}@keyframes f{{to{{opacity:1}}}}
.c{{animation:c 1.1s steps(1) infinite}}@keyframes c{{50%{{opacity:0}}}}
.b{{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:b 1s cubic-bezier(.2,.8,.2,1) forwards}}@keyframes b{{to{{transform:scaleX(1)}}}}
@media (prefers-reduced-motion:reduce){{.f,.b,.c{{animation:none;opacity:1;transform:none}}}}
</style>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t['bg']}" stroke="{t['border']}"/>
<text x="{X}" y="122" font-size="56" font-weight="700" fill="{t['text']}">hi!</text>
<rect class="c" x="{X + 108}" y="112" width="30" height="7" rx="1" fill="{t['accent']}"/>
<text class="f" style="animation-delay:.3s" x="{X}" y="160" font-size="15" fill="{t['muted']}">{escape(NOTE)}</text>
<text class="f" x="{LX}" y="58" font-size="12" fill="{t['muted']}">// languages</text>"""]

    top = s["langs"][0][1] if s["langs"] else 1
    for i, (name, share) in enumerate(s["langs"]):
        y = 88 + i * 26
        d = .2 + .1 * i
        o.append(f'<g class="f" style="animation-delay:{d:.1f}s"><text x="{LX}" y="{y}" font-size="13" fill="{t["text"]}">{escape(name)}</text>'
                 f'<text x="{W - X}" y="{y}" font-size="12" fill="{t["muted"]}" text-anchor="end">{share * 100:.0f}%</text></g>'
                 f'<rect x="{BX}" y="{y - 8}" width="{BW}" height="6" rx="3" fill="{t["track"]}"/>'
                 f'<rect class="b" style="animation-delay:{d:.1f}s" x="{BX}" y="{y - 8}" width="{max(share / top * BW, 6):.1f}" height="6" rx="3" fill="{t["accent"]}" fill-opacity="{1 - i * .12:.2f}"/>')

    o.append(f'<line x1="{X}" y1="{H - 64}" x2="{W - X}" y2="{H - 64}" stroke="{t["border"]}"/>')
    parts = [f'<tspan fill="{t["text"]}" font-weight="700">{n}</tspan> {escape(label)}' for n, label in s["nums"]]
    if s["now"]:
        parts.append(f'now → <tspan fill="{t["accent"]}">{escape(s["now"])}</tspan>')
    o.append(f'<text class="f" style="animation-delay:.6s" x="{X}" y="{H - 30}" font-size="13" fill="{t["muted"]}" xml:space="preserve">'
             + '   ·   '.join(parts) + "</text></svg>")
    return "\n".join(o)


if __name__ == "__main__":
    s = stats(fetch())
    assert s["langs"] and s["nums"][1][0] >= 0, s
    os.makedirs("assets", exist_ok=True)
    for name, t in THEMES.items():
        with open(f"assets/card-{name}.svg", "w", encoding="utf-8") as f:
            f.write(render(s, t))
    print(s)
