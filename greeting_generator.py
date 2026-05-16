"""
Generates personalized greetings via the Claude API.
Uses Haiku 4.5 — fast and cheap, perfect for short witty outputs.
"""

import random
from anthropic import AsyncAnthropic

SYSTEM_PROMPT = """You write one-line greetings for a developer's portfolio website.

YOUR VOICE:
- Witty, observant, slightly dry. Like a sharp friend, not a corporate welcome bot.
- Confident but warm. Never sycophantic.
- You notice things and call them out subtly.

HARD RULES:
- 1 sentence. Maximum 22 words. Often shorter is better.
- NEVER use: "Hello!", "Welcome!", "Hi there!", emojis, exclamation marks (unless genuinely earned), em-dashes used as crutch punctuation.
- NEVER explain or label the context — weave it in naturally.
- NEVER sound like a chatbot. No "I noticed that..." or "Based on...".
- Reference AT MOST 2 context signals. Don't list — observe.
- Output ONLY the greeting line itself. No quotes, no preamble, no explanation.

VOICE EXAMPLES (do not copy verbatim, but match the energy):
- "Third visit this week — either I'm doing something right or you forgot to bookmark."
- "Rainy Tuesday morning in London, LinkedIn tab open. I'll guess recruiter mode."
- "Night owl reading code on a Saturday. Respect — I'm three commits deep right now too."
- "Konbanwa from across the world. Morning here, coffee #2."
- "Came from Hacker News? Brave. Stay a while."
- "Friday at 5pm and you're checking out portfolios. Workaholic solidarity."

Now generate ONE greeting line for this visitor."""


def _context_to_prompt(ctx: dict) -> str:
    lines = [
        f"Local time: {ctx.get('local_time_iso')} ({ctx.get('time_of_day')}, {ctx.get('day_of_week')})",
        f"Vibe: {ctx.get('vibe')}",
        f"Came from: {ctx.get('source')}",
        f"Visit number: {ctx.get('visit_count')} ({'returning' if ctx.get('is_returning') else 'new visitor'})",
    ]
    if ctx.get('city'):
        loc = ctx['city']
        if ctx.get('country'):
            loc += f", {ctx['country']}"
        lines.append(f"Location: {loc}")
    if ctx.get('weather_summary'):
        lines.append(f"Weather there: {ctx['weather_summary']}")
    if ctx.get('language'):
        lines.append(f"Browser language: {ctx.get('language')}")
    if ctx.get('dev_live_status'):
        lines.append(f"What the dev is doing right now: {ctx.get('dev_live_status')}")

    return "\n".join(lines)


async def generate_greeting(ctx: dict, api_key: str) -> str:
    client = AsyncAnthropic(api_key=api_key)
    user_prompt = _context_to_prompt(ctx)

    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=120,
        temperature=1.0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text_parts = []
    for block in getattr(message, "content", []):
        if isinstance(block, dict):
            text = block.get("text") or block.get("content") or ""
        else:
            text = getattr(block, "text", None) or getattr(block, "content", "")
        if text:
            text_parts.append(text)

    greeting = " ".join(text_parts).strip()
    greeting = greeting.strip('"').strip("'").strip()
    greeting = greeting.split("\n")[0].strip()

    if not greeting:
        return fallback_greeting(ctx)

    return greeting


FALLBACK_GREETINGS = {
    "late_night": [
        "Late-night browsing. Same energy here.",
        "Coding hours. Welcome to the club.",
        "The internet at this hour hits different.",
    ],
    "deep_night": [
        "3am portfolio scrolling. Whatever brought you here, I respect it.",
        "Either insomnia or inspiration. Either works.",
    ],
    "morning": [
        "Morning. Coffee's good today.",
        "Productive hours. Make yourself at home.",
    ],
    "evening": [
        "Evening browsing. Pull up a chair.",
        "Winding down hours. Same.",
    ],
    "default": [
        "Glad you're here. Have a look around.",
        "Take your time and enjoy the tour.",
        "Good to see you.",
    ],
}


def fallback_greeting(ctx: dict) -> str:
    tod = ctx.get("time_of_day", "default")
    pool = FALLBACK_GREETINGS.get(tod, FALLBACK_GREETINGS["default"])
    return random.choice(pool)
