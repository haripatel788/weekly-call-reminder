import requests
from datetime import datetime, timedelta

BOT_TOKEN = "8233661802:AAEZm7QPsWVzTFlozY_WY-LHYOMVuLnt5Gw"
CHAT_ID = -1003681456243  # replace with your group chat id

def get_tuesday_date():
    today = datetime.now()
    days_until_tuesday = (1 - today.weekday()) % 7
    tuesday = today + timedelta(days=days_until_tuesday)
    return tuesday.strftime("%B %d, %Y")

def send_message(text):
    url = f"https://api.telegram.org/bot<BOT_TOKEN>/sendMessage".replace("<BOT_TOKEN>", BOT_TOKEN)
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    r = requests.post(url, data=payload)
    r.raise_for_status()

def monday_message():
    tuesday_date = get_tuesday_date()
    message = f"""<b>Reminder Weekly Call</b>

<b>Tuesday {tuesday_date}</b>
Tomorrow @ <b>9:00 PM</b>

<b>Agenda:</b>
📮 Sholka and Jaynaad
📮 Prasang
📮 Sabha Overview
📮 Announcements
📮 Ending Sholka

<b>Link:</b>
https://drexel.zoom.us/j/89041757596
"""
    send_message(message)

def tuesday_message():
    tuesday_date = get_tuesday_date()
    message = f"""<b>Reminder Weekly Call</b>

<b>Tuesday {tuesday_date}</b>
<b>Today @ 9:00 PM</b>

<b>Agenda:</b>
📮 Sholka and Jaynaad
📮 Prasang
📮 Sabha Overview
📮 Announcements
📮 Ending Sholka

<b>Link:</b>
https://drexel.zoom.us/j/89041757596
"""
    send_message(message)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 weekly_call_bot.py monday|tuesday")
        raise SystemExit(1)

    if sys.argv[1] == "monday":
        monday_message()
    elif sys.argv[1] == "tuesday":
        tuesday_message()
    else:
        print("Invalid arg. Use monday or tuesday.")

