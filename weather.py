"""
Fetches current weather using Open-Meteo — free, no API key required.
https://open-meteo.com/
"""

import httpx
from typing import Optional

WEATHER_CODES = {
    0: "clear sky",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "rain showers",
    81: "heavy rain showers",
    82: "violent rain showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "severe thunderstorm",
}


async def fetch_weather(lat: Optional[float], lon: Optional[float]) -> Optional[dict]:
    if lat is None or lon is None:
        return None

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print(f"[weather] fetch failed: {e}")
        return None

    current = data.get("current", {})
    code = current.get("weather_code")

    return {
        "temperature_c": current.get("temperature_2m"),
        "wind_kmh": current.get("wind_speed_10m"),
        "weather_code": code,
        "description": WEATHER_CODES.get(code, "unknown"),
    }
