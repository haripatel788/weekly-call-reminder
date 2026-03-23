import os
import json
import random
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Fetching secrets safely
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
THREAD_ID = os.environ.get("THREAD_ID")

TZ = ZoneInfo("America/New_York")
NAMES_POOL = ["Devbhai", "Prathambhai", "Dhruvbhai C", "Krishbhai", "Prithvibhai", "Rudrakshbhai", "Sohambhai", "Tilakbhai", "Shivambhai", "Tirthbhai"]
HARIBHAI_NAME = "Haribhai"
HISTORY_FILE = "history.json"

def get_next_tuesday(dt):
    days_until_tuesday = (1 - dt.weekday()) % 7
    return dt + timedelta(days=days_until_tuesday)

def load_or_init_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {
        "frequencies": {name: 0 for name in NAMES_POOL},
        "last_week": [],
        "current_week": {}
    }

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def get_weekly_assignments():
    now = datetime.now(TZ)
    tuesday = get_next_tuesday(now)
    tuesday_str = tuesday.strftime("%Y-%m-%d")
    
    history = load_or_init_history()
    
    # Check if we already picked for this upcoming Tuesday
    if history.get("current_week", {}).get("week_of") == tuesday_str:
        cw = history["current_week"]
        return cw["shlok_jaynaad"], cw["prasang"], cw["ending_shlok"], tuesday.strftime("%b %d")

    # --- New Week Rotation Logic ---
    # 1. Anyone who did it last week is on cooldown
    available_names = [n for n in NAMES_POOL if n not in history.get("last_week", [])]
    
    # 2. Sort by frequency (lowest first). Shuffle first to randomly break frequency ties.
    random.shuffle(available_names)
    available_names.sort(key=lambda x: history["frequencies"].get(x, 0))
    
    # 3. Pick top 3 and shuffle to assign their specific roles
    picks = available_names[:3]
    random.shuffle(picks)
    shlok, prasang, ending = picks[0], picks[1], picks[2]
    
    # 4. Update history state
    cw = history.get("current_week", {})
    history["last_week"] = [cw.get("shlok_jaynaad"), cw.get("prasang"), cw.get("ending_shlok")]
    
    history["current_week"] = {
        "week_of": tuesday_str,
        "shlok_jaynaad": shlok,
        "prasang": prasang,
        "ending_shlok": ending
    }
    
    for p in picks:
        history["frequencies"][p] = history["frequencies"].get(p, 0) + 1
        
    save_history(history)
    return shlok, prasang, ending, tuesday.strftime("%b %d")

def get_time_phrase():
    now = datetime.now(TZ)
    if now.weekday() == 0:  # Monday
        return "Tomorrow @ 9:30 PM EST"
    elif now.weekday() == 1:  # Tuesday
        if now.hour == 20:  # 8 PM EST
            return "Tonight @ 9:30 PM EST (Starts in 1 hour!)"
        else:
            return "Tonight @ 9:30 PM EST (Starts in 15 mins!)"
    return "Upcoming Tuesday @ 9:30 PM EST"  # Manual trigger fallback

def send_message():
    shlok_jaynaad, prasang, ending_shlok, tuesday_short = get_weekly_assignments()
    time_phrase = get_time_phrase()
    
    text = f"""Reminder Weekly Call
Tuesday {tuesday_short}
{time_phrase}

Agenda:

📮Sholka and Jaynaad ({shlok_jaynaad})
📮Prasang ({prasang})
📮Shaba Overview ( {HARIBHAI_NAME} )
📮Announcements ( {HARIBHAI_NAME} )
📮Ending Sholka ({ending_shlok})

Link:
https://teams.microsoft.com/meet/21298270215852?p=wPQ3hDZ6bGsQt2djIf"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": int(CHAT_ID) if CHAT_ID else 0,
        "message_thread_id": int(THREAD_ID) if THREAD_ID else 0,
        "text": text,
    }
    
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
    print(f"Message sent successfully: {time_phrase}")

if __name__ == "__main__":
    send_message()