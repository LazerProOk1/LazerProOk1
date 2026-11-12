"""Renders assets/card-{dark,light}.svg from public GitHub data. Run by .github/workflows/cards.yml."""
import json, os, urllib.request
from collections import Counter
from html import escape

LOGIN = os.environ.get("LOGIN", "LazerProOk1")
SKIP_LANGS = {"HTML", "CSS", "SCSS", "Dockerfile", "NSIS", "Jupyter Notebook", "Makefile", "Batchfile", "Shell", "PowerShell"}

QUERY = """query($login:String!){ user(login:$login){
  repositoriesContributedTo(first:1, contributionTypes:[COMMIT,PULL_REQUEST,ISSUE,REPOSITORY]){totalCount}
  contributionsCollection{ totalCommitContributions restrictedContributionsCount }
  repositories(first:100, ownerAffiliations:[OWNER,COLLABORATOR,ORGANIZATION_MEMBER], privacy:PUBLIC){ nodes{
    isFork stargazerCount owner{login}
    languages(first:10, orderBy:{field:SIZE,direction:DESC}){ edges{ size node{name color} } } } } } }"""


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
    own = [r for r in repos if r["owner"]["login"] == LOGIN and not r["isFork"]]
    sizes, colors = Counter(), {}
    for r in own:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            if name not in SKIP_LANGS:
                sizes[name] += e["size"]
                colors[name] = e["node"]["color"] or "#8b949e"
    total = sum(sizes.values()) or 1
    langs = [(n, s / total, colors[n]) for n, s in sizes.most_common(6) if s / total >= .01]
    cc = u["contributionsCollection"]
    return {
        "nums": [
            ("stars", sum(r["stargazerCount"] for r in repos)),
            ("commits this year", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
            ("repos", len(own)),
            ("contributed to", u["repositoriesContributedTo"]["totalCount"]),
        ],
        "langs": langs,
    }


THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", text="#e6edf3", muted="#8b949e", track="#21262d"),
    "light": dict(bg="#ffffff", border="#d0d7de", text="#1f2328", muted="#656d76", track="#eaeef2"),
}


def render(s, t):
    W, H, X = 860, 250, 40
    out = [f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#a371f7"/><stop offset="1" stop-color="#58a6ff"/></linearGradient>
<clipPath id="bar"><rect x="{X}" y="168" width="{W - 2 * X}" height="8" rx="4"/></clipPath></defs>
<style>
text{{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif}}
.f{{opacity:0;animation:f .6s ease forwards}}
@keyframes f{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
.c{{animation:b 1s steps(1) infinite}}@keyframes b{{50%{{opacity:0}}}}
.s{{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:s .9s cubic-bezier(.2,.8,.2,1) forwards}}
@keyframes s{{to{{transform:scaleX(1)}}}}
</style>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="16" fill="{t['bg']}" stroke="{t['border']}"/>
<text x="{X}" y="112" font-size="64" font-weight="800" fill="url(#g)">hi!</text>
<rect class="c" x="{X + 108}" y="64" width="5" height="52" rx="2" fill="#58a6ff"/>"""]

    col = (W - X - 250) / len(s["nums"])
    for i, (label, n) in enumerate(s["nums"]):
        x = 250 + i * col
        out.append(f'<g class="f" style="animation-delay:{.15 * i:.2f}s">'
                   f'<text x="{x}" y="92" font-size="34" font-weight="700" fill="{t["text"]}">{n}</text>'
                   f'<text x="{x}" y="116" font-size="13" fill="{t["muted"]}">{escape(label)}</text></g>')

    out.append(f'<rect x="{X}" y="168" width="{W - 2 * X}" height="8" rx="4" fill="{t["track"]}"/><g clip-path="url(#bar)">')
    x = X
    for i, (name, share, color) in enumerate(s["langs"]):
        w = share * (W - 2 * X)
        out.append(f'<rect class="s" style="animation-delay:{.5 + .08 * i:.2f}s" x="{x:.1f}" y="168" width="{w + .5:.1f}" height="8" fill="{color}"/>')
        x += w
    out.append("</g>")

    x = X
    for i, (name, share, color) in enumerate(s["langs"]):
        label = f"{name} {share * 100:.0f}%"
        out.append(f'<g class="f" style="animation-delay:{.7 + .08 * i:.2f}s"><circle cx="{x + 5}" cy="{205}" r="5" fill="{color}"/>'
                   f'<text x="{x + 16}" y="210" font-size="13" fill="{t["muted"]}">{escape(label)}</text></g>')
        x += 16 + len(label) * 7.4 + 22  # ponytail: approximate text width, fine for 6 short labels
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    s = stats(fetch())
    assert s["nums"] and s["langs"], s
    os.makedirs("assets", exist_ok=True)
    for name, t in THEMES.items():
        with open(f"assets/card-{name}.svg", "w", encoding="utf-8") as f:
            f.write(render(s, t))
    print(s)
