from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API = "https://api.github.com/search/commits"


def github_search_count(username: str, token: str, extra_query: str = "") -> int:
    query = f"author:{username}"
    if extra_query:
        query += f" {extra_query}"

    url = f"{API}?{urlencode({'q': query, 'per_page': 1})}"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "eduzinETH-profile-readme",
        },
    )

    with urlopen(request, timeout=20) as response:
        payload = json.load(response)

    return int(payload["total_count"])


def compact_number(value: int) -> str:
    return f"{value:,}"


def make_svg(total: int, this_year: int, last_30_days: int, today: date) -> str:
    orange = "#ff9d00"
    background = "#0d1117"
    border = "#30363d"
    text = "#f0f6fc"
    muted = "#8b949e"

    start_30 = today - timedelta(days=29)
    year_label = str(today.year)
    year_range = f"Jan 1 – {today.strftime('%b %-d')}"
    rolling_range = f"{start_30.strftime('%b %-d')} – {today.strftime('%b %-d')}"

    center_value = compact_number(this_year)
    center_size = 25 if len(center_value) <= 3 else 21

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="180" viewBox="0 0 495 180" role="img" aria-label="GitHub commit statistics">
  <rect x="0.5" y="0.5" width="494" height="179" rx="8" fill="{background}" stroke="{border}"/>
  <line x1="165" y1="28" x2="165" y2="152" stroke="{border}"/>
  <line x1="330" y1="28" x2="330" y2="152" stroke="{border}"/>

  <g font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" text-anchor="middle">
    <text x="82.5" y="75" fill="{text}" font-size="28" font-weight="700">{escape(compact_number(total))}</text>
    <text x="82.5" y="105" fill="{text}" font-size="13" font-weight="600">Total Commits</text>
    <text x="82.5" y="127" fill="{muted}" font-size="10">public default branches</text>

    <circle cx="247.5" cy="74" r="34" fill="none" stroke="{orange}" stroke-width="6"/>
    <circle cx="247.5" cy="34" r="4" fill="{orange}"/>
    <text x="247.5" y="82" fill="{text}" font-size="{center_size}" font-weight="700">{escape(center_value)}</text>
    <text x="247.5" y="132" fill="{orange}" font-size="13" font-weight="700">{escape(year_label)} Commits</text>
    <text x="247.5" y="151" fill="{muted}" font-size="10">{escape(year_range)}</text>

    <text x="412.5" y="75" fill="{text}" font-size="28" font-weight="700">{escape(compact_number(last_30_days))}</text>
    <text x="412.5" y="105" fill="{text}" font-size="13" font-weight="600">Last 30 Days</text>
    <text x="412.5" y="127" fill="{muted}" font-size="10">{escape(rolling_range)}</text>
  </g>
</svg>
"""


def main() -> None:
    username = os.environ["GITHUB_USER"]
    token = os.environ["GITHUB_TOKEN"]
    today = datetime.now(timezone.utc).date()

    year_start = date(today.year, 1, 1)
    last_30_start = today - timedelta(days=29)

    total = github_search_count(username, token)
    this_year = github_search_count(
        username,
        token,
        f"author-date:{year_start.isoformat()}..{today.isoformat()}",
    )
    last_30_days = github_search_count(
        username,
        token,
        f"author-date:{last_30_start.isoformat()}..{today.isoformat()}",
    )

    output = Path("dist/commit-stats.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        make_svg(total, this_year, last_30_days, today),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
