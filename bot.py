import os
import json
import random
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Fetching secrets securely
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
THREAD_ID = os.environ.get("THREAD_ID")
GCP_CREDENTIALS_JSON = os.environ.get("GCP_CREDENTIALS")

# Matches your exact sheet name
SHEET_NAME = "Weekly Call Tracker"

TZ = ZoneInfo("America/New_York")
NAMES_POOL = ["Devbhai", "Prathambhai", "Dhruvbhai C", "Krishbhai", "Prithvibhai", "Rudrakshbhai", "Sohambhai", "Tilakbhai", "Shivambhai", "Tirthbhai"]
HARIBHAI_NAME = "Haribhai"

def get_next_tuesday(dt):
    days_until_tuesday = (1 - dt.weekday()) % 7
    return dt + timedelta(days=days_until_tuesday)

def connect_to_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GCP_CREDENTIALS_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

def get_weekly_assignments():
    now = datetime.now(TZ)
    tuesday = get_next_tuesday(now)
    tuesday_str = tuesday.strftime("%b %d, %Y")
    
    sheet = connect_to_sheet()
    
    # Gets all data assuming Row 1 contains your manually typed headers
    records = sheet.get_all_records()
    
    # 1. Check if we already picked names for THIS upcoming Tuesday
    if records and str(records[-1].get("Week Of")) == tuesday_str:
        return records[-1].get("Shlok & Jaynaad", ""), records[-1].get("Prasang", ""), records[-1].get("Ending Shlok", ""), tuesday.strftime("%b %d")

    # 2. Calculate frequencies by counting names in the log
    frequencies = {name: 0 for name in NAMES_POOL}
    for row in records:
        for role in ["Shlok & Jaynaad", "Prasang", "Ending Shlok"]:
            if row.get(role) in frequencies:
                frequencies[row[role]] += 1
                
    # 3. Figure out who went last week
    last_week_names = []
    if records:
        last_week_names = [records[-1].get("Shlok & Jaynaad"), records[-1].get("Prasang"), records[-1].get("Ending Shlok")]
        last_week_names = [n for n in last_week_names if n] # Filter out empty blanks
        
    # 4. Filter out last week's participants and sort by frequency
    available_names = [n for n in NAMES_POOL if n not in last_week_names]
    random.shuffle(available_names) # Shuffle to break ties randomly
    available_names.sort(key=lambda x: frequencies[x])
    
    # 5. Pick the top 3 and assign roles
    picks = available_names[:3]
    random.shuffle(picks)
    shlok, prasang, ending = picks[0], picks[1], picks[2]
    
    # 6. Format the automated data for the sheet
    generated_on = now.strftime("%b %d, %Y %I:%M %p")
    pool_size = len(available_names)
    cooldown_str = ", ".join(last_week_names) if last_week_names else "None"
    
    # 7. Save the new week's data to the Google Sheet (automatically appends to the first empty row!)
    new_row = [
        tuesday_str,         # Week Of
        generated_on,        # Generated On
        shlok,               # Shlok & Jaynaad
        prasang,             # Prasang
        ending,              # Ending Shlok
        HARIBHAI_NAME,       # Shaba Overview
        pool_size,           # Eligible Pool Size
        cooldown_str,        # On Cooldown
        "",                  # Total Attendance (Leave blank for manual entry)
        ""                   # Speaker No-Shows (Leave blank for manual entry)
    ]
    sheet.append_row(new_row)
    
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
    return "Upcoming Tuesday @ 9:30 PM EST"

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