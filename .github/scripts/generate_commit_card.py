from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen


GRAPHQL_API = "https://api.github.com/graphql"


def graphql(token: str, query: str, variables: dict) -> dict:
    request = Request(
        GRAPHQL_API,
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "eduzinETH-profile-readme",
        },
        method="POST",
    )

    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {payload['errors']}")

    return payload["data"]


def get_account_created_at(username: str, token: str) -> datetime:
    query = """
    query($login: String!) {
      user(login: $login) {
        createdAt
      }
    }
    """
    data = graphql(token, query, {"login": username})
    user = data.get("user")
    if not user:
        raise RuntimeError(f"GitHub user not found: {username}")
    return datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))


def commit_contributions(
    username: str,
    token: str,
    from_dt: datetime,
    to_dt: datetime,
) -> int:
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
        }
      }
    }
    """
    variables = {
        "login": username,
        "from": from_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "to": to_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    data = graphql(token, query, variables)
    user = data.get("user")
    if not user:
        raise RuntimeError(f"GitHub user not found: {username}")
    return int(user["contributionsCollection"]["totalCommitContributions"])


def compact_number(value: int) -> str:
    return f"{value:,}"


def fmt_day(value: date) -> str:
    return value.strftime("%b %d").replace(" 0", " ")


def make_svg(total: int, this_year: int, last_30_days: int, today: date) -> str:
    orange = "#ff9d00"
    background = "#0d1117"
    border = "#30363d"
    divider = "#30363d"
    text = "#f0f6fc"
    muted = "#8b949e"

    start_30 = today - timedelta(days=29)
    year_label = str(today.year)
    year_range = f"Jan 1 – {fmt_day(today)}"
    rolling_range = f"{fmt_day(start_30)} – {fmt_day(today)}"

    center_value = compact_number(this_year)
    center_size = 25 if len(center_value) <= 3 else 21

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="180" viewBox="0 0 495 180" role="img" aria-label="GitHub commit statistics">
  <rect x="0.5" y="0.5" width="494" height="179" rx="8" fill="{background}" stroke="{border}"/>
  <line x1="165" y1="28" x2="165" y2="152" stroke="{divider}"/>
  <line x1="330" y1="28" x2="330" y2="152" stroke="{divider}"/>

  <g font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" text-anchor="middle">
    <text x="82.5" y="75" fill="{text}" font-size="28" font-weight="700">{escape(compact_number(total))}</text>
    <text x="82.5" y="105" fill="{text}" font-size="13" font-weight="600">Total Commits</text>
    <text x="82.5" y="127" fill="{muted}" font-size="10">GitHub contribution history</text>

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
    now = datetime.now(timezone.utc)
    today = now.date()

    created_at = get_account_created_at(username, token)
    first_year = created_at.year

    yearly_counts: dict[int, int] = {}
    for year in range(first_year, today.year + 1):
        start = max(created_at, datetime(year, 1, 1, tzinfo=timezone.utc))
        if year == today.year:
            end = now
        else:
            end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        if start <= end:
            yearly_counts[year] = commit_contributions(username, token, start, end)

    total = sum(yearly_counts.values())
    this_year = yearly_counts.get(today.year, 0)

    last_30_start = now - timedelta(days=29)
    last_30_days = commit_contributions(username, token, last_30_start, now)

    print(
        json.dumps(
            {
                "username": username,
                "totalCommitContributions": total,
                "thisYear": this_year,
                "last30Days": last_30_days,
                "yearly": yearly_counts,
            },
            sort_keys=True,
        )
    )

    output = Path("dist/commit-stats.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        make_svg(total, this_year, last_30_days, today),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
