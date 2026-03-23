import os
import sys
import random
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
THREAD_ID = os.environ.get("THREAD_ID")

TZ = ZoneInfo("America/New_York")
NAMES_POOL = ["Devbhai", "Prathambhai", "Dhruvbhai C", "Krishbhai", "Prithvibhai", "Rudrakshbhai", "Sohambhai", "Tilakbhai", "Shivambhai", "Tirthbhai"]
HARIBHAI_NAME = "Haribhai"

def get_next_tuesday(dt):
    days_until_tuesday = (1 - dt.weekday()) % 7
    return dt + timedelta(days=days_until_tuesday)

def weekly_assignments():
    now = datetime.now(TZ)
    tuesday = get_next_tuesday(now)
    seed_key = tuesday.strftime("%Y-%m-%d")
    rng = random.Random(seed_key)
    
    picks = rng.sample(NAMES_POOL, 3) if len(NAMES_POOL) >= 3 else [rng.choice(NAMES_POOL) for _ in range(3)]
    return picks[0], picks[1], picks[2], tuesday.strftime("%b %d")

def send_message(day_word):
    shlok_jaynaad, prasang, ending_shlok, tuesday_short = weekly_assignments()
    
    text = f"""Reminder Weekly Call
Tuesday {tuesday_short}
{day_word} @9

Agenda:

📮Sholka and Jaynaad ({shlok_jaynaad})
📮Prasang ({prasang})
📮Sabha Overview ( {HARIBHAI_NAME} )
📮Announcements ( {HARIBHAI_NAME} )
📮Ending Sholka ({ending_shlok})

Link:
https://teams.microsoft.com/meet/21298270215852?p=wPQ3hDZ6bGsQt2djIf"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": int(CHAT_ID),
        "message_thread_id": int(THREAD_ID),
        "text": text,
    }
    
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
    print(f"Message sent successfully for {day_word}!")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1].lower() not in ["monday", "tuesday"]:
        print("Usage: python bot.py [monday|tuesday]")
        sys.exit(1)
        
    day_arg = sys.argv[1].lower()
    day_word = "Tomorrow" if day_arg == "monday" else "Today"
    send_message(day_word)