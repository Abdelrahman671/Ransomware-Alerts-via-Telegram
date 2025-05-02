import requests
import sys
import os
from datetime import datetime, timedelta

# Telegram bot token and chat ID
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"  
    }
    resp = requests.post(url, data=payload)
    resp.raise_for_status()
    return resp.status_code

# Middle East country ISO codes
ME_COUNTRIES = {
    "AE": "United Arab Emirates",
    "SA": "Saudi Arabia",
    "EG": "Egypt",
    "IQ": "Iraq",
    "IR": "Iran",
    "JO": "Jordan",
    "KW": "Kuwait",
    "LB": "Lebanon",
    "OM": "Oman",
    "PS": "Palestine",
    "QA": "Qatar",
    "SY": "Syria",
    "YE": "Yemen",
    "BH": "Bahrain",
    "TR": "Turkey",
    "IL": "Israel"
}

def get_victim_data(country_code):
    url = f"https://api.ransomware.live/v2/countryvictims/{country_code}"
    headers = {"Accept": "application/json"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def filter_recent_victims(data):
    now = datetime.utcnow()
    cutoff = now - timedelta(days=7)
    entries = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, list):
                entries.extend(item)
            elif isinstance(item, dict):
                entries.append(item)
    elif isinstance(data, dict):
        entries = [data]

    recent = []
    for v in entries:
        ds = v.get("discovered", "")[:19]
        try:
            d = datetime.strptime(ds, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if d >= cutoff:
            recent.append(v)
    return recent

def build_message(country_name, victims):
    msg = f"📢 *Ransomware Victims in {country_name} (Last 7 Days)*\n*Total:* {len(victims)}\n\n"
    for v in victims:
        company    = v.get("post_title", "Unknown")
        activity   = v.get("activity", "—")
        group      = v.get("group_name", "—")
        discovered = v.get("discovered", "")[:19]
        published  = v.get("published", "")[:19]
        post_url   = v.get("post_url", "").strip()
        website    = v.get("website", "—")
        desc       = v.get("description", "No description")[:200]

        size = "—"
        ei = v.get("extrainfos", {})
        if isinstance(ei, dict):
            size = ei.get("size", "—")
        elif isinstance(ei, list):
            for item in ei:
                if isinstance(item, dict) and "size" in item:
                    size = item["size"]
                    break

        dup_list = v.get("duplicates", [])
        dup_info = f"{len(dup_list)} duplicate(s)" if dup_list else ""

        msg += f"🔸 *{company}* ({activity})\n"
        msg += f"• Ransom Group: `{group}`\n"
        msg += f"• Discovered: `{discovered}`\n"
        if published:
            msg += f"• Published: `{published}`\n"
        if post_url:
            msg += f"• DataLeakSite URL: [Click Here]({post_url})\n"
        if website and website != "—":
            msg += f"• Website: {website}\n"
        if dup_info:
            msg += f"• {dup_info}\n"
        msg += f"• Leak Size: {size}\n"
        msg += f"• Description: {desc}...\n\n"

    if len(msg) > 4000:  # Telegram limit is ~4096 characters
        msg = msg[:3990] + "\n…(truncated)"
    return msg

def main():
    for code, country in ME_COUNTRIES.items():
        try:
            data = get_victim_data(code)
            recent_victims = filter_recent_victims(data)
            if not recent_victims:
                print(f"[{country}] No victims found.")
                continue
            message = build_message(country, recent_victims)
            status = send_telegram_notification(message)
            print(f"[{country}] Telegram message sent! Status code: {status}")
        except Exception as e:
            print(f"[{country}] ERROR: {e}")

if __name__ == "__main__":
    main()
