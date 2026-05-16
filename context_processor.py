"""
Turns raw visitor signals into a rich, structured context dict,
and computes 'context bucket' keys used for caching.
"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

REFERRER_MAP = {
    "linkedin.com": "linkedin",
    "github.com": "github",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "ycombinator.com": "hackernews",
    "news.ycombinator.com": "hackernews",
    "reddit.com": "reddit",
    "google.com": "google",
    "bing.com": "search",
    "duckduckgo.com": "search",
    "stackoverflow.com": "stackoverflow",
    "dev.to": "dev_community",
    "medium.com": "blog",
    "producthunt.com": "producthunt",
}


def _classify_referrer(referrer: Optional[str]) -> str:
    if not referrer:
        return "direct"
    ref_lower = referrer.lower()
    for domain, label in REFERRER_MAP.items():
        if domain in ref_lower:
            return label
    return "external"


def _time_of_day(hour: int) -> str:
    if 5 <= hour < 9:
        return "early_morning"
    if 9 <= hour < 12:
        return "morning"
    if 12 <= hour < 14:
        return "midday"
    if 14 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    if 22 <= hour or hour < 2:
        return "late_night"
    return "deep_night"


def _vibe_from_time(time_of_day: str) -> str:
    return {
        "early_morning": "fresh, just-woke-up energy",
        "morning": "productive caffeinated energy",
        "midday": "lunch-break headspace",
        "afternoon": "post-lunch focus mode",
        "evening": "winding-down energy",
        "late_night": "night-owl coding vibes",
        "deep_night": "3am why-are-you-still-awake territory",
    }.get(time_of_day, "")


def build_context(
    timezone: str,
    city: Optional[str],
    country: Optional[str],
    referrer: Optional[str],
    visit_count: int,
    is_returning: bool,
    language: Optional[str],
    weather: Optional[dict],
    github_activity: Optional[dict],
    dev_status_fallback: str,
) -> dict:
    try:
        now = datetime.now(ZoneInfo(timezone))
    except Exception:
        now = datetime.utcnow()

    hour = now.hour
    time_of_day = _time_of_day(hour)
    day_of_week = now.strftime("%A").lower()
    is_weekend = day_of_week in ("saturday", "sunday")

    source = _classify_referrer(referrer)

    weather_summary = None
    if weather:
        weather_summary = (
            f"{weather.get('description', 'unknown')}, "
            f"{weather.get('temperature_c')}°C"
        )

    dev_live_status = dev_status_fallback
    if github_activity:
        dev_live_status = github_activity.get("status_line", dev_status_fallback)

    return {
        "local_time_iso": now.isoformat(timespec="minutes"),
        "hour": hour,
        "time_of_day": time_of_day,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "vibe": _vibe_from_time(time_of_day),
        "timezone": timezone,
        "city": city,
        "country": country,
        "language": language,
        "source": source,
        "visit_count": visit_count,
        "is_returning": is_returning,
        "weather": weather,
        "weather_summary": weather_summary,
        "github_activity": github_activity,
        "dev_live_status": dev_live_status,
    }


def get_context_bucket(ctx: dict) -> str:
    parts = [
        ctx.get("time_of_day", "unknown"),
        "weekend" if ctx.get("is_weekend") else "weekday",
        ctx.get("source", "direct"),
        "returning" if ctx.get("is_returning") else "new",
    ]
    weather = ctx.get("weather") or {}
    desc = (weather.get("description") or "").lower()
    if "rain" in desc or "drizzle" in desc:
        parts.append("rainy")
    elif "snow" in desc:
        parts.append("snowy")
    elif "clear" in desc or "sun" in desc:
        parts.append("clear")
    elif "cloud" in desc or "overcast" in desc:
        parts.append("cloudy")

    return "|".join(parts)
