"""
AI-Powered Personalized Greeting API
A FastAPI backend that generates context-aware greetings for a portfolio website.

Run with: uvicorn main:app --reload --port 8000
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from context_processor import build_context, get_context_bucket
from greeting_generator import generate_greeting, fallback_greeting
from cache import GreetingCache
from weather import fetch_weather
from github_status import fetch_github_status

load_dotenv()

# ---------- Configuration ----------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "")
DEV_STATUS_FALLBACK = os.getenv("DEV_STATUS", "Building cool things")
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")
POOL_SIZE = int(os.getenv("POOL_SIZE", "8"))
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))

if not ANTHROPIC_API_KEY:
    print("WARNING: ANTHROPIC_API_KEY not set. The API will only return fallback greetings.")

# Shared cache instance
cache = GreetingCache(ttl_hours=CACHE_TTL_HOURS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks."""
    print(f"🚀 Greeting API starting. Allowed origins: {ALLOWED_ORIGINS}")
    yield
    print("👋 Greeting API shutting down.")


app = FastAPI(
    title="AI Greeting API",
    description="Generates context-aware personalized greetings for a portfolio site.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ---------- Request / Response Models ----------
class GreetingRequest(BaseModel):
    timezone: str = Field(..., description="IANA timezone, e.g. 'America/Los_Angeles'")
    latitude: Optional[float] = Field(None, description="For weather lookup (optional)")
    longitude: Optional[float] = Field(None, description="For weather lookup (optional)")
    city: Optional[str] = None
    country: Optional[str] = None
    referrer: Optional[str] = Field(None, description="document.referrer from the browser")
    visit_count: int = Field(1, ge=1)
    is_returning: bool = False
    language: Optional[str] = Field(None, description="navigator.language, e.g. 'en-US'")


class GreetingResponse(BaseModel):
    greeting: str
    live_status: Optional[str] = None
    context_used: dict
    cached: bool


# ---------- Routes ----------
@app.get("/")
async def root():
    return {
        "name": "AI Greeting API",
        "status": "ok",
        "endpoints": {
            "generate": "POST /api/greeting",
            "health": "GET /health",
        },
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "anthropic_configured": bool(ANTHROPIC_API_KEY),
        "github_configured": bool(GITHUB_USERNAME),
        "cache_size": cache.size(),
    }


@app.post("/api/greeting", response_model=GreetingResponse)
async def get_greeting(req: GreetingRequest, request: Request):
    """
    Generate a personalized greeting based on visitor context.

    Strategy:
      1. Build enriched context (time of day, weather, source, etc.)
      2. Compute a 'context bucket' key for caching
      3. If we have enough cached greetings for this bucket, return a random one
      4. Otherwise, generate a fresh greeting via Claude and add it to the pool
      5. Run live-status fetch (GitHub) in parallel for speed
    """
    weather_task = asyncio.create_task(
        fetch_weather(req.latitude, req.longitude) if req.latitude is not None and req.longitude is not None else _none()
    )
    github_task = asyncio.create_task(
        fetch_github_status(GITHUB_USERNAME) if GITHUB_USERNAME else _none()
    )

    weather = await weather_task
    github_status = await github_task

    context = build_context(
        timezone=req.timezone,
        city=req.city,
        country=req.country,
        referrer=req.referrer,
        visit_count=req.visit_count,
        is_returning=req.is_returning,
        language=req.language,
        weather=weather,
        github_activity=github_status,
        dev_status_fallback=DEV_STATUS_FALLBACK,
    )

    bucket_key = get_context_bucket(context)

    cached_greeting = cache.get_random(bucket_key, min_pool_size=POOL_SIZE)
    if cached_greeting:
        return GreetingResponse(
            greeting=cached_greeting,
            live_status=context.get("dev_live_status"),
            context_used=_safe_context(context),
            cached=True,
        )

    if not ANTHROPIC_API_KEY:
        return GreetingResponse(
            greeting=fallback_greeting(context),
            live_status=context.get("dev_live_status"),
            context_used=_safe_context(context),
            cached=False,
        )

    try:
        greeting = await generate_greeting(context, api_key=ANTHROPIC_API_KEY)
        cache.add(bucket_key, greeting)
        return GreetingResponse(
            greeting=greeting,
            live_status=context.get("dev_live_status"),
            context_used=_safe_context(context),
            cached=False,
        )
    except Exception as e:
        print(f"[greeting-error] {type(e).__name__}: {e}")
        return GreetingResponse(
            greeting=fallback_greeting(context),
            live_status=context.get("dev_live_status"),
            context_used=_safe_context(context),
            cached=False,
        )


@app.post("/api/greeting/clear-cache")
async def clear_cache():
    """Admin endpoint — clear the greeting cache (e.g., after tweaking the prompt)."""
    count = cache.size()
    cache.clear()
    return {"cleared": count}


async def _none():
    return None


def _safe_context(ctx: dict) -> dict:
    """Trim context for the response body — only return display-safe fields."""
    return {
        "time_of_day": ctx.get("time_of_day"),
        "day_of_week": ctx.get("day_of_week"),
        "source": ctx.get("source"),
        "weather_summary": ctx.get("weather_summary"),
        "is_returning": ctx.get("is_returning"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
