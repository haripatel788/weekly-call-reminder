import os
import json
import random
import requests
import gspread
from google.oauth2.service_account import Credentials
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
HARIBHAI_NAME = "Haribhai"
HARIBHAI_TAG = "@haripatel788"

def get_next_tuesday(dt):
    days_until_tuesday = (1 - dt.weekday()) % 7
    return dt + timedelta(days=days_until_tuesday)

def connect_to_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GCP_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME) 

def get_weekly_assignments():
    now = datetime.now(TZ)
    tuesday = get_next_tuesday(now)
    tuesday_str = tuesday.strftime("%b %d, %Y")
    
    spreadsheet = connect_to_sheet()
    
    # Target all three tabs
    main_sheet = spreadsheet.get_worksheet(0)           # Logs
    freq_sheet = spreadsheet.worksheet("Frequency Tracker") # Chart
    roster_sheet = spreadsheet.worksheet("Roster")      # New Roster
    
    # --- BULLETPROOF ROSTER FIX: Using get_all_values() ---
    roster_values = roster_sheet.get_all_values()
    # Skip the header row (index 0)
    roster_rows = roster_values[1:] if len(roster_values) > 1 else []
    
    all_names = []
    eligible_pool = []
    name_to_tag = {}
    
    for row in roster_rows:
        if not row:
            continue # Skip completely empty rows
            
        # Safely grab the data by column index
        name = str(row[0]).strip() if len(row) > 0 else ""
        if not name:
            continue
            
        tag = str(row[1]).strip() if len(row) > 1 else ""
        status = str(row[2]).strip().lower() if len(row) > 2 else ""
        
        all_names.append(name)
        # Fallback to standard name if they don't have a Telegram tag yet
        name_to_tag[name] = tag if tag else name 
        
        if status != "vacation":
            eligible_pool.append(name)
    
    # --- Existing Logic ---
    records = main_sheet.get_all_records()
    
    if records and str(records[-1].get("Week Of")) == tuesday_str:
        return (
            records[-1].get("Shlok & Jaynaad", ""), 
            records[-1].get("Prasang", ""), 
            records[-1].get("Ending Shlok", ""), 
            tuesday.strftime("%b %d"),
            name_to_tag # Pass the dictionary to tag them in the message
        )

    # Detailed frequencies tracking ALL names (even those on vacation)
    detailed_freqs = {name: {"Shlok & Jaynaad": 0, "Prasang": 0, "Ending Shlok": 0, "Total": 0} for name in all_names}
    
    for row in records:
        for role in ["Shlok & Jaynaad", "Prasang", "Ending Shlok"]:
            person = row.get(role)
            if person in detailed_freqs:
                detailed_freqs[person][role] += 1
                detailed_freqs[person]["Total"] += 1
                
    last_week_names = []
    if records:
        last_week_names = [records[-1].get("Shlok & Jaynaad"), records[-1].get("Prasang"), records[-1].get("Ending Shlok")]
        last_week_names = [n for n in last_week_names if n]
        
    # Filter out last week's participants from the ACTIVE eligible pool
    available_names = [n for n in eligible_pool if n not in last_week_names]
    random.shuffle(available_names) 
    available_names.sort(key=lambda x: detailed_freqs[x]["Total"])
    
    # Pick the top 3
    picks = available_names[:3]
    random.shuffle(picks)
    shlok, prasang, ending = picks[0], picks[1], picks[2]
    
    detailed_freqs[shlok]["Shlok & Jaynaad"] += 1
    detailed_freqs[shlok]["Total"] += 1
    detailed_freqs[prasang]["Prasang"] += 1
    detailed_freqs[prasang]["Total"] += 1
    detailed_freqs[ending]["Ending Shlok"] += 1
    detailed_freqs[ending]["Total"] += 1
    
    # Save standard data to logs (Uses REAL names, not tags)
    generated_on = now.strftime("%b %d, %Y %I:%M %p")
    pool_size = len(available_names)
    cooldown_str = ", ".join(last_week_names) if last_week_names else "None"
    
    new_row = [
        tuesday_str, generated_on, shlok, prasang, ending,
        HARIBHAI_NAME, pool_size, cooldown_str, "", ""
    ]
    main_sheet.append_row(new_row)
    
    # Rebuild Frequency Tracker
    freq_data = [["Name", "Shlok & Jaynaad", "Prasang", "Ending Shlok", "Total"]]
    sorted_names = sorted(all_names, key=lambda x: detailed_freqs[x]["Total"], reverse=True)
    
    for name in sorted_names:
        freq_data.append([
            name,
            detailed_freqs[name]["Shlok & Jaynaad"],
            detailed_freqs[name]["Prasang"],
            detailed_freqs[name]["Ending Shlok"],
            detailed_freqs[name]["Total"]
        ])
        
    freq_sheet.clear() 
    freq_sheet.append_rows(freq_data) 
    
    return shlok, prasang, ending, tuesday.strftime("%b %d"), name_to_tag

def get_time_phrase():
    now = datetime.now(TZ)
    if now.weekday() == 0:  
        return "Tomorrow @ 9:30 PM EST"
    elif now.weekday() == 1:  
        if now.hour == 20: 
            return "Tonight @ 9:30 PM EST (Starts in 1 hour!)"
        else:
            return "Tonight @ 9:30 PM EST (Starts in 15 mins!)"
    return "Upcoming Tuesday @ 9:30 PM EST"

def send_message():
    shlok, prasang, ending, tuesday_short, name_to_tag = get_weekly_assignments()
    time_phrase = get_time_phrase()
    shlok_tag = name_to_tag.get(shlok, shlok)
    prasang_tag = name_to_tag.get(prasang, prasang)
    ending_tag = name_to_tag.get(ending, ending)
    
    text = f"""Reminder Weekly Call
Tuesday {tuesday_short}
{time_phrase}

Agenda:

📮Sholka and Jaynaad ({shlok_tag})
📮Prasang ({prasang_tag})
📮Sabha Overview ({HARIBHAI_TAG})
📮Announcements ({HARIBHAI_TAG})
📮Ending Sholka ({ending_tag})

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