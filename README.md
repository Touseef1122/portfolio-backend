# AI Greeting Backend

A FastAPI backend that generates context-aware personalized greetings for a portfolio site.

## What it includes

- `main.py` — FastAPI app with `/api/greeting` and `/api/greeting/clear-cache`
- `context_processor.py` — builds rich visitor context and cache bucket keys
- `greeting_generator.py` — calls Claude Haiku 4.5 with a tuned system prompt
- `cache.py` — in-memory greeting pools per context bucket
- `weather.py` — Open-Meteo weather enrichment (no API key required)
- `github_status.py` — optional live GitHub activity status
- `requirements.txt` — dependency list
- `.env.example` — environment variable template

## Setup

1. Install dependencies

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure env

```bash
copy .env.example .env
```

3. Run

```bash
uvicorn main:app --reload --port 8000
```

## API

- `GET /` — service info
- `GET /health` — health and config status
- `POST /api/greeting` — generate a greeting
- `POST /api/greeting/clear-cache` — flush the greeting cache

## Notes

- If `ANTHROPIC_API_KEY` is missing, the service returns fallback greetings.
- Add your portfolio frontend origin to `ALLOWED_ORIGINS` for browser access.
- In-memory caching is fine for a single-instance portfolio backend; swap to Redis for horizontal scale.
