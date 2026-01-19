import os
import random
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# These are provided by GitHub Actions Secrets
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])
THREAD_ID = int(os.environ["THREAD_ID"])  # Topic (sub-channel) ID for "Weekly Call"

TZ = ZoneInfo("America/New_York")

# EDIT THIS LIST (names that can be randomly assigned)
# Add/remove names as you like.
NAMES_POOL = [
    "Devbhai",
    "Prathambhai",
    "Dhruvbhai C",
    "Krishbhai",
    "Prithvibhai",
    "Rudrakshbhai",
    "Sohambhai",
    "Tilakbhai",
    "Shivambhai",
    "Tirthbhai"
]

# Fixed roles stay the same
HARIBHAI_NAME = "Haribhai"

def get_next_tuesday(dt: datetime) -> datetime:
    """Return the date/time for the next (or current) Tuesday in the same timezone."""
    # Monday=0, Tuesday=1, ..., Sunday=6
    days_until_tuesday = (1 - dt.weekday()) % 7
    return dt + timedelta(days=days_until_tuesday)

def get_tuesday_short_and_seed() -> tuple[str, str]:
    """
    Returns:
      - Tuesday short format: 'Jan 13'
      - Seed key for weekly deterministic random assignment: 'YYYY-MM-DD'
    """
    now = datetime.now(TZ)
    tuesday = get_next_tuesday(now)
    tuesday_short = tuesday.strftime("%b %d")        # e.g., 'Jan 13'
    seed_key = tuesday.strftime("%Y-%m-%d")          # e.g., '2026-01-13'
    return tuesday_short, seed_key

def weekly_assignments() -> tuple[str, str, str]:
    """
    Pick names for:
      1) Sholka and Jaynaad
      2) Prasang
      3) Ending Sholka

    Deterministic per week (same assignments on Monday + Tuesday) by seeding with Tuesday's date.
    """
    _, seed_key = get_tuesday_short_and_seed()
    rng = random.Random(seed_key)

    # Prefer unique names if possible; otherwise allow repeats.
    if len(NAMES_POOL) >= 3:
        picks = rng.sample(NAMES_POOL, 3)
    else:
        picks = [rng.choice(NAMES_POOL) for _ in range(3)]

    shlok_jaynaad, prasang, ending_shlok = picks
    return shlok_jaynaad, prasang, ending_shlok

def send_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "message_thread_id": THREAD_ID,  # <-- This is what targets the Weekly Call topic
        "text": text,
    }
    r = requests.post(url, data=payload, timeout=20)
    r.raise_for_status()

def build_message(day_word: str) -> str:
    """
    day_word: "Tomorrow" (Monday) or "Today" (Tuesday)
    """
    tuesday_short, _ = get_tuesday_short_and_seed()
    shlok_jaynaad, prasang, ending_shlok = weekly_assignments()

    return f"""Reminder Weekly Call
Tuesday {tuesday_short}
{day_word} @9

Agenda:

📮Sholka and Jaynaad ({shlok_jaynaad})
📮Prasang ({prasang})
📮Shaba Overview
( {HARIBHAI_NAME} )
📮Announcements ( {HARIBHAI_NAME} )
📮Ending Sholka  ({ending_shlok})

Link:
https://teams.microsoft.com/meet/21298270215852?p=wPQ3hDZ6bGsQt2djIf
"""

def monday_message():
    send_message(build_message("Tomorrow"))

def tuesday_message():
    send_message(build_message("Today"))

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 weekly_call_bot.py monday|tuesday")
        raise SystemExit(1)

    arg = sys.argv[1].strip().lower()

    if arg == "monday":
        monday_message()
    elif arg == "tuesday":
        tuesday_message()
    else:
        print("Invalid arg. Use monday or tuesday.")
        raise SystemExit(1)
