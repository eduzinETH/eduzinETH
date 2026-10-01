from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STATS_API = "https://github-readme-stats-five-sandy-47.vercel.app/api"
GITHUB_API = "https://api.github.com"
ORANGE = "#ff9d00"
ORANGE_2 = "#d97706"
ORANGE_3 = "#b45309"
ORANGE_4 = "#92400e"
ORANGE_5 = "#78350f"
BG = "#0d1117"
BORDER = "#30363d"
TEXT = "#f0f6fc"
MUTED = "#8b949e"
TRACK = "#161b22"


def http_json(url: str, token: str | None = None) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "eduzinETH-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_stats_svg(username: str, *, include_all_commits: bool = False, commits_year: int | None = None) -> str:
    params = {
        "username": username,
        "show_icons": "true",
        "count_private": "true",
        "number_format": "long",
        "hide_border": "true",
    }
    if include_all_commits:
        params["include_all_commits"] = "true"
    if commits_year is not None:
        params["commits_year"] = str(commits_year)

    request = Request(
        f"{STATS_API}?{urlencode(params)}",
        headers={
            "Accept": "image/svg+xml,text/plain;q=0.9,*/*;q=0.8",
            "User-Agent": "eduzinETH-profile-readme",
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def svg_metric(svg: str, test_id: str) -> int:
    match = re.search(
        rf'data-testid=["\']{re.escape(test_id)}["\'][^>]*>\s*([^<]+?)\s*</text>',
        svg,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise RuntimeError(f"Could not find {test_id!r} in GitHub stats SVG")

    digits = re.sub(r"[^0-9]", "", match.group(1))
    if not digits:
        raise RuntimeError(f"Invalid {test_id!r} value: {match.group(1)!r}")
    return int(digits)


def fetch_profile(username: str, token: str) -> dict:
    return http_json(f"{GITHUB_API}/users/{username}", token)


def fetch_top_languages(username: str) -> list[tuple[str, float]]:
    params = {
        "username": username,
        "layout": "compact",
        "langs_count": 5,
        "hide_border": "true",
    }
    request = Request(
        f"{STATS_API}/top-langs/?{urlencode(params)}",
        headers={
            "Accept": "image/svg+xml,text/plain;q=0.9,*/*;q=0.8",
            "User-Agent": "eduzinETH-profile-readme",
        },
    )
    with urlopen(request, timeout=30) as response:
        svg = response.read().decode("utf-8")

    items = []
    for raw in re.findall(
        r'data-testid=["\\']lang-name["\\'][^>]*>\\s*([^<]+?)\\s*</text>',
        svg,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        text = re.sub(r"\\s+", " ", raw).strip()
        match = re.match(r"(.+?)\\s+([0-9]+(?:\\.[0-9]+)?)%$", text)
        if not match:
            continue
        items.append((match.group(1).strip(), float(match.group(2))))
        if len(items) == 5:
            break

    if not items:
        raise RuntimeError("Could not parse languages from GitHub stats SVG")

    return items


def fmt(value: int) -> str:
    return f"{value:,}"


def pct(value: float) -> str:
    return f"{value:.1f}%" if value < 10 else f"{value:.0f}%"


def make_dashboard(
    username: str,
    total_commits: int,
    prs: int,
    public_repos: int,
    followers: int,
    current_year: int,
    current_year_commits: int,
    previous_year: int,
    previous_year_commits: int,
    languages: list[tuple[str, float]],
) -> str:
    width = 820
    height = 330

    max_year = max(current_year_commits, previous_year_commits, 1)
    year_bar_max = 285
    current_bar = max(4, round(year_bar_max * current_year_commits / max_year))
    previous_bar = max(4, round(year_bar_max * previous_year_commits / max_year))

    palette = [ORANGE, ORANGE_2, ORANGE_3, ORANGE_4, ORANGE_5]
    lang_total_width = 350
    lang_segments = []
    x = 438.0
    for index, (_, percentage) in enumerate(languages):
        segment = lang_total_width * percentage / 100
        if segment < 1.2:
            segment = 1.2
        lang_segments.append(
            f'<rect x="{x:.1f}" y="221" width="{segment:.1f}" height="8" rx="4" fill="{palette[index]}"/>'
        )
        x += segment

    lang_legend = []
    positions = [(438, 252), (610, 252), (438, 276), (610, 276), (438, 300)]
    for index, (language, percentage) in enumerate(languages):
        lx, ly = positions[index]
        lang_legend.append(
            f'<circle cx="{lx}" cy="{ly - 4}" r="4" fill="{palette[index]}"/>'
            f'<text x="{lx + 11}" y="{ly}" fill="{TEXT}" font-size="11">{escape(language)}</text>'
            f'<text x="{lx + 145}" y="{ly}" fill="{MUTED}" font-size="10" text-anchor="end">{pct(percentage)}</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Eduardo Rodrigues GitHub profile overview">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="{BG}" stroke="{BORDER}"/>

  <g font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif">
    <circle cx="29" cy="30" r="5" fill="{ORANGE}"/>
    <text x="44" y="36" fill="{TEXT}" font-size="20" font-weight="700">Eduardo Rodrigues</text>
    <text x="44" y="57" fill="{MUTED}" font-size="12">Software • Automation • AI • Growth</text>
    <text x="790" y="36" fill="{MUTED}" font-size="11" text-anchor="end">@{escape(username)}</text>

    <line x1="28" y1="78" x2="792" y2="78" stroke="{BORDER}"/>

    <g text-anchor="middle">
      <text x="108" y="121" fill="{TEXT}" font-size="27" font-weight="700">{escape(fmt(total_commits))}</text>
      <text x="108" y="143" fill="{MUTED}" font-size="11">Total commits</text>

      <text x="308" y="121" fill="{TEXT}" font-size="27" font-weight="700">{escape(fmt(prs))}</text>
      <text x="308" y="143" fill="{MUTED}" font-size="11">Pull requests</text>

      <text x="508" y="121" fill="{TEXT}" font-size="27" font-weight="700">{escape(fmt(public_repos))}</text>
      <text x="508" y="143" fill="{MUTED}" font-size="11">Public repos</text>

      <text x="708" y="121" fill="{TEXT}" font-size="27" font-weight="700">{escape(fmt(followers))}</text>
      <text x="708" y="143" fill="{MUTED}" font-size="11">Followers</text>
    </g>

    <line x1="208" y1="96" x2="208" y2="147" stroke="{BORDER}"/>
    <line x1="408" y1="96" x2="408" y2="147" stroke="{BORDER}"/>
    <line x1="608" y1="96" x2="608" y2="147" stroke="{BORDER}"/>

    <line x1="28" y1="169" x2="792" y2="169" stroke="{BORDER}"/>

    <text x="28" y="198" fill="{ORANGE}" font-size="12" font-weight="700">YEARLY COMMITS</text>
    <text x="438" y="198" fill="{ORANGE}" font-size="12" font-weight="700">LANGUAGES</text>

    <text x="28" y="224" fill="{TEXT}" font-size="12" font-weight="600">{current_year}</text>
    <rect x="76" y="213" width="{year_bar_max}" height="10" rx="5" fill="{TRACK}"/>
    <rect x="76" y="213" width="{current_bar}" height="10" rx="5" fill="{ORANGE}"/>
    <text x="374" y="223" fill="{TEXT}" font-size="12" font-weight="700" text-anchor="end">{escape(fmt(current_year_commits))}</text>

    <text x="28" y="257" fill="{TEXT}" font-size="12" font-weight="600">{previous_year}</text>
    <rect x="76" y="246" width="{year_bar_max}" height="10" rx="5" fill="{TRACK}"/>
    <rect x="76" y="246" width="{previous_bar}" height="10" rx="5" fill="{ORANGE_2}"/>
    <text x="374" y="256" fill="{TEXT}" font-size="12" font-weight="700" text-anchor="end">{escape(fmt(previous_year_commits))}</text>

    <text x="28" y="292" fill="{MUTED}" font-size="10">Commit totals stay synced with the profile stats source.</text>

    <rect x="438" y="221" width="{lang_total_width}" height="8" rx="4" fill="{TRACK}"/>
    {''.join(lang_segments)}
    {''.join(lang_legend)}
  </g>
</svg>
"""


def main() -> None:
    username = os.environ["GITHUB_USER"]
    token = os.environ["GITHUB_TOKEN"]
    now = datetime.now(timezone.utc)
    current_year = now.year
    previous_year = current_year - 1

    all_stats = fetch_stats_svg(username, include_all_commits=True)
    current_stats = fetch_stats_svg(username, commits_year=current_year)
    previous_stats = fetch_stats_svg(username, commits_year=previous_year)

    total_commits = svg_metric(all_stats, "commits")
    prs = svg_metric(all_stats, "prs")
    current_year_commits = svg_metric(current_stats, "commits")
    previous_year_commits = svg_metric(previous_stats, "commits")

    profile = fetch_profile(username, token)
    languages = fetch_top_languages(username)

    output = Path("dist/profile-dashboard.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        make_dashboard(
            username=username,
            total_commits=total_commits,
            prs=prs,
            public_repos=int(profile.get("public_repos", 0)),
            followers=int(profile.get("followers", 0)),
            current_year=current_year,
            current_year_commits=current_year_commits,
            previous_year=previous_year,
            previous_year_commits=previous_year_commits,
            languages=languages,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "total_commits": total_commits,
                "prs": prs,
                "public_repos": int(profile.get("public_repos", 0)),
                "followers": int(profile.get("followers", 0)),
                str(current_year): current_year_commits,
                str(previous_year): previous_year_commits,
                "languages": languages,
            }
        )
    )


if __name__ == "__main__":
    main()
