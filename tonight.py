#!/usr/bin/env python3
"""Compute tonight's sky data -> src/tonight.json.

Moon phase is pure astronomy math (no API, never breaks). The observing tip
rotates daily from an evergreen list — always true, never stale.
"""
import json
import math
import os
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Denver")  # MDT — matches the site's home base
except Exception:
    TZ = timezone(timedelta(hours=-6))

SYNODIC = 29.530588853  # days
REF_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)

PHASES = [
    ("New Moon", "🌑"), ("Waxing Crescent", "🌒"), ("First Quarter", "🌓"),
    ("Waxing Gibbous", "🌔"), ("Full Moon", "🌕"), ("Waning Gibbous", "🌖"),
    ("Last Quarter", "🌗"), ("Waning Crescent", "🌘"),
]

TIPS = [
    "The Moon's terminator — the line between light and dark — is where craters look deepest. Observe along it.",
    "Give your eyes 20 minutes in the dark. One glance at a white phone screen resets the clock.",
    "Jupiter's four largest moons change position nightly — sketch them two nights in a row.",
    "The Orion Nebula is best with low power and a wide field. Don't crank the magnification.",
    "Split Albireo in Cygnus: a gold-and-blue double star, beautiful in any telescope.",
    "Saturn's rings tilt over the years — some seasons they're nearly edge-on. Catch them while they're open.",
    "Use averted vision: look slightly to the side of a faint object to see it better.",
    "Binoculars first, telescope second. Scan with 10x50s, then zoom in on what catches your eye.",
    "The Andromeda Galaxy is 2.5 million light-years away — the farthest thing you'll ever see with your own eyes.",
    "Let your telescope cool down outside for 30 minutes before serious observing.",
    "Star clusters resolve best at medium power — too much magnification just spreads the light.",
    "The Milky Way's dark lanes are interstellar dust. Binoculars reveal them beautifully.",
    "Track a satellite: they drift steadily and don't blink — planes blink, satellites don't.",
    "End the night with the Moon. After faint fuzzies, bright craters feel like a reward.",
]


def main():
    now = datetime.now(TZ)
    today = now.date()
    noon_utc = datetime(today.year, today.month, today.day, 12, tzinfo=TZ).astimezone(timezone.utc)
    age = ((noon_utc - REF_NEW_MOON).total_seconds() / 86400) % SYNODIC
    illum = (1 - math.cos(2 * math.pi * age / SYNODIC)) / 2
    name, emoji = PHASES[int((age / SYNODIC) * 8 + 0.5) % 8]
    tip = TIPS[today.timetuple().tm_yday % len(TIPS)]

    data = {
        "date": today.isoformat(),
        "moon_age_days": round(age, 1),
        "illumination_pct": round(illum * 100),
        "phase": name,
        "emoji": emoji,
        "tip": tip,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "tonight.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"tonight: {emoji} {name}, {round(illum*100)}% illuminated, age {round(age,1)}d -> {out}")


if __name__ == "__main__":
    main()
