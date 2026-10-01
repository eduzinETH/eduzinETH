from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STATS_API = "https://github-readme-stats-five-sandy-47.vercel.app/api"


def fetch_stats_commit_count(
    username: str,
    *,
    include_all_commits: bool = False,
    commits_year: int | None = None,
) -> int:
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
        svg = response.read().decode("utf-8")

    match = re.search(
        r"""data-testid=["']commits["'][^>]*>\s*([^<]+?)\s*</text>""",
        svg,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise RuntimeError("Could not find commit count in GitHub stats SVG")

    raw_value = match.group(1)
    digits = re.sub(r"[^0-9]", "", raw_value)
    if not digits:
        raise RuntimeError(f"Invalid commit count returned by stats service: {raw_value!r}")

    return int(digits)


def compact_number(value: int) -> str:
    return f"{value:,}"


def make_svg(total: int, this_year: int, previous_year: int, now: datetime) -> str:
    orange = "#ff9d00"
    background = "#0d1117"
    border = "#30363d"
    text = "#f0f6fc"
    muted = "#8b949e"

    current_year = now.year
    previous_year_label = current_year - 1
    center_value = compact_number(this_year)
    center_size = 25 if len(center_value) <= 3 else 21

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="180" viewBox="0 0 495 180" role="img" aria-label="GitHub commit statistics">
  <rect x="0.5" y="0.5" width="494" height="179" rx="8" fill="{background}" stroke="{border}"/>
  <line x1="165" y1="28" x2="165" y2="152" stroke="{border}"/>
  <line x1="330" y1="28" x2="330" y2="152" stroke="{border}"/>

  <g font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" text-anchor="middle">
    <text x="82.5" y="75" fill="{text}" font-size="28" font-weight="700">{escape(compact_number(total))}</text>
    <text x="82.5" y="105" fill="{text}" font-size="13" font-weight="600">Total Commits</text>
    <text x="82.5" y="127" fill="{muted}" font-size="10">all-time</text>

    <circle cx="247.5" cy="74" r="34" fill="none" stroke="{orange}" stroke-width="6"/>
    <circle cx="247.5" cy="34" r="4" fill="{orange}"/>
    <text x="247.5" y="82" fill="{text}" font-size="{center_size}" font-weight="700">{escape(center_value)}</text>
    <text x="247.5" y="132" fill="{orange}" font-size="13" font-weight="700">{current_year} Commits</text>
    <text x="247.5" y="151" fill="{muted}" font-size="10">current year</text>

    <text x="412.5" y="75" fill="{text}" font-size="28" font-weight="700">{escape(compact_number(previous_year))}</text>
    <text x="412.5" y="105" fill="{text}" font-size="13" font-weight="600">{previous_year_label} Commits</text>
    <text x="412.5" y="127" fill="{muted}" font-size="10">previous year</text>
  </g>
</svg>
"""


def main() -> None:
    username = os.environ["GITHUB_USER"]
    now = datetime.now(timezone.utc)

    total = fetch_stats_commit_count(username, include_all_commits=True)
    this_year = fetch_stats_commit_count(username, commits_year=now.year)
    previous_year = fetch_stats_commit_count(username, commits_year=now.year - 1)

    print(
        f"Commit stats source=github-readme-stats "
        f"total={total} current_year={this_year} previous_year={previous_year}"
    )

    output = Path("dist/commit-stats.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(make_svg(total, this_year, previous_year, now), encoding="utf-8")


if __name__ == "__main__":
    main()
