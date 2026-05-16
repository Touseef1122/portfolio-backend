"""
Fetches the developer's latest GitHub activity to power the live status line.
Uses the public REST API — no token needed for low traffic.

For higher rate limits, set GITHUB_TOKEN in env.
"""

import os
import httpx
from datetime import datetime, timezone

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def _humanize_age(iso_ts: str) -> str:
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except Exception:
        return ""
    delta = datetime.now(timezone.utc) - ts
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 7:
        return f"{days}d ago"
    return f"{days // 7}w ago"


async def fetch_github_status(username: str) -> dict | None:
    if not username:
        return None

    url = f"https://api.github.com/users/{username}/events/public"
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            events = response.json()
    except Exception as e:
        print(f"[github] fetch failed: {e}")
        return None

    if not events:
        return None

    interesting_types = {
        "PushEvent",
        "PullRequestEvent",
        "CreateEvent",
        "ReleaseEvent",
        "IssuesEvent",
    }
    event = next((e for e in events if e.get("type") in interesting_types), events[0])

    event_type = event.get("type", "Activity")
    repo_full = event.get("repo", {}).get("name", "a repo")
    repo_name = repo_full.split("/")[-1]
    created_at = event.get("created_at", "")
    age = _humanize_age(created_at)

    if event_type == "PushEvent":
        commits = event.get("payload", {}).get("commits", [])
        if commits:
            latest_msg = commits[-1].get("message", "").split("\n")[0][:80]
            status_line = f"Just pushed to {repo_name}: \"{latest_msg}\" ({age})"
        else:
            status_line = f"Just pushed to {repo_name} ({age})"
    elif event_type == "PullRequestEvent":
        action = event.get("payload", {}).get("action", "updated")
        status_line = f"{action.title()} a PR on {repo_name} ({age})"
    elif event_type == "CreateEvent":
        ref_type = event.get("payload", {}).get("ref_type", "branch")
        status_line = f"Started something new — created a {ref_type} on {repo_name} ({age})"
    elif event_type == "ReleaseEvent":
        status_line = f"Shipped a release on {repo_name} ({age})"
    elif event_type == "IssuesEvent":
        action = event.get("payload", {}).get("action", "touched")
        status_line = f"{action.title()} an issue on {repo_name} ({age})"
    else:
        status_line = f"Active on {repo_name} ({age})"

    return {
        "status_line": status_line,
        "repo": repo_name,
        "type": event_type,
        "age": age,
    }
