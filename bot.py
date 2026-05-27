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
# "full" (default) runs the picker + posts agenda; "short" posts only the 15-min nudge.
REMINDER_MODE = os.environ.get("REMINDER_MODE", "full").strip().lower()

# Matches your exact sheet name
SHEET_NAME = "Weekly Call Tracker"

# Column headers as they appear in the Tracker tab. Keep these aligned with the sheet.
COL_WEEK_OF = "Date of Call"
COL_SHLOK = "Shlok + Jaynaad"
COL_PRASANG = "Prasang"
COL_ENDING_SHLOK = "Ending Shlok"
ROLE_COLUMNS = [COL_SHLOK, COL_PRASANG, COL_ENDING_SHLOK]

TZ = ZoneInfo("America/New_York")
HARIBHAI_NAME = "Haribhai"
HARIBHAI_TAG = "@haripatel788"
TEAMS_LINK = "https://teams.microsoft.com/meet/21298270215852?p=wPQ3hDZ6bGsQt2djIf"

def get_next_tuesday(dt):
    days_until_tuesday = (1 - dt.weekday()) % 7
    return dt + timedelta(days=days_until_tuesday)

def connect_to_sheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
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
    
    if records and str(records[-1].get(COL_WEEK_OF)) == tuesday_str:
        return (
            records[-1].get(COL_SHLOK, ""),
            records[-1].get(COL_PRASANG, ""),
            records[-1].get(COL_ENDING_SHLOK, ""),
            tuesday.strftime("%b %d"),
            name_to_tag,
        )

    # Detailed frequencies tracking ALL names (even those on vacation)
    detailed_freqs = {
        name: {COL_SHLOK: 0, COL_PRASANG: 0, COL_ENDING_SHLOK: 0, "Total": 0}
        for name in all_names
    }

    for row in records:
        for role in ROLE_COLUMNS:
            person = row.get(role)
            if person in detailed_freqs:
                detailed_freqs[person][role] += 1
                detailed_freqs[person]["Total"] += 1

    last_week_names = []
    if records:
        last_week_names = [records[-1].get(col) for col in ROLE_COLUMNS]
        last_week_names = [n for n in last_week_names if n]

    if len(eligible_pool) < 3:
        raise SystemExit(
            "Need at least 3 roster members not on vacation to assign Shlok, Prasang, and Ending Shlok."
        )

    # Prefer people who were not on duty last week; if that pool is too small, use full eligible pool
    cooldown_pool = [n for n in eligible_pool if n not in last_week_names]
    available_names = list(cooldown_pool)
    if len(available_names) < 3:
        print(
            "Notice: fewer than 3 eligible members outside last week's trio; "
            "using the full eligible roster for this week's picks.",
            flush=True,
        )
        available_names = list(eligible_pool)

    random.shuffle(available_names)
    available_names.sort(key=lambda x: detailed_freqs[x]["Total"])

    picks = available_names[:3]
    random.shuffle(picks)
    shlok, prasang, ending = picks[0], picks[1], picks[2]
    
    detailed_freqs[shlok][COL_SHLOK] += 1
    detailed_freqs[shlok]["Total"] += 1
    detailed_freqs[prasang][COL_PRASANG] += 1
    detailed_freqs[prasang]["Total"] += 1
    detailed_freqs[ending][COL_ENDING_SHLOK] += 1
    detailed_freqs[ending]["Total"] += 1
    
    # Save standard data to logs (Uses REAL names, not tags)
    generated_on = now.strftime("%b %d, %Y %I:%M %p")
    pool_size = len(cooldown_pool)
    cooldown_str = ", ".join(last_week_names) if last_week_names else "None"
    
    new_row = [
        tuesday_str, generated_on, shlok, prasang, ending,
        HARIBHAI_NAME, pool_size, cooldown_str, "", ""
    ]
    main_sheet.append_row(new_row)
    
    # Rebuild Frequency Tracker
    freq_data = [["Name", COL_SHLOK, COL_PRASANG, COL_ENDING_SHLOK, "Total"]]
    sorted_names = sorted(all_names, key=lambda x: detailed_freqs[x]["Total"], reverse=True)

    for name in sorted_names:
        freq_data.append([
            name,
            detailed_freqs[name][COL_SHLOK],
            detailed_freqs[name][COL_PRASANG],
            detailed_freqs[name][COL_ENDING_SHLOK],
            detailed_freqs[name]["Total"],
        ])
        
    freq_sheet.clear() 
    freq_sheet.append_rows(freq_data) 
    
    return shlok, prasang, ending, tuesday.strftime("%b %d"), name_to_tag

def get_time_phrase():
    """Copy reflects minutes until this week's call (Tue 9:30 PM America/New_York)."""
    now = datetime.now(TZ)
    if now.weekday() == 0:
        return "Tomorrow @ 9:30 PM ET"
    if now.weekday() == 1:
        call_start = now.replace(hour=21, minute=30, second=0, microsecond=0)
        if now >= call_start:
            return "Tonight @ 9:30 PM ET (call time has started)"
        delta = call_start - now
        mins = max(1, int(delta.total_seconds() // 60))
        if mins < 60:
            return f"Tonight @ 9:30 PM ET (Starts in {mins} minute{'s' if mins != 1 else ''}!)"
        hours, rem = divmod(mins, 60)
        if rem == 0:
            return f"Tonight @ 9:30 PM ET (Starts in about {hours} hour{'s' if hours != 1 else ''}!)"
        return f"Tonight @ 9:30 PM ET (Starts in about {hours}h {rem}m!)"
    return "Upcoming Tuesday @ 9:30 PM ET"

def require_config(mode="full"):
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not CHAT_ID:
        missing.append("CHAT_ID")
    if mode == "full" and not GCP_CREDENTIALS_JSON:
        missing.append("GCP_CREDENTIALS")
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

    try:
        int(CHAT_ID)
    except ValueError:
        raise SystemExit("CHAT_ID must be an integer (e.g. -1001234567890).")
    if THREAD_ID:
        try:
            int(THREAD_ID)
        except ValueError:
            raise SystemExit("THREAD_ID must be an integer when set; unset it for non-forum chats.")


def post_to_telegram(text):
    """POST a plain-text message to the configured Telegram chat/thread."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": int(CHAT_ID), "text": text}
    if THREAD_ID:
        payload["message_thread_id"] = int(THREAD_ID)
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise SystemExit(f"Telegram API returned error: {body.get('description', body)}")


def send_short_reminder():
    text = f"""Reminder: weekly call starts in 15 minutes.

{TEAMS_LINK}"""
    post_to_telegram(text)
    print("Short reminder sent.")


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
{TEAMS_LINK}"""

    post_to_telegram(text)
    print(f"Message sent successfully: {time_phrase}")

if __name__ == "__main__":
    if REMINDER_MODE not in {"full", "short"}:
        raise SystemExit(f"Unknown REMINDER_MODE: {REMINDER_MODE!r} (expected 'full' or 'short').")
    require_config(REMINDER_MODE)
    if REMINDER_MODE == "short":
        send_short_reminder()
    else:
        send_message()