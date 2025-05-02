import requests
import sys
import json
import os
from datetime import datetime, timedelta

# Telegram bot token and chat ID
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Path to the local cache file to store alerted victims
cache_file = "victim_cache.json"

def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"  # You can also use "HTML"
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

def load_victim_cache():
    """Load previously alerted victims from the cache file."""
    try:
        with open(cache_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_victim_cache(cache):
    """Save the updated list of alerted victims to the cache file."""
    with open(cache_file, "w") as f:
        json.dump(cache, f)

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
    msg = f"\U0001F4E2 *New Ransomware Victims in {country_name}*\n*Total:* {len(victims)}\n\n"
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
    victim_cache = load_victim_cache()

    for code, country in ME_COUNTRIES.items():
        try:
            data = get_victim_data(code)
            recent_victims = filter_recent_victims(data)
            if not recent_victims:
                print(f"[{country}] No new victims.")
                continue

            new_victims = []
            for victim in recent_victims:
                victim_id = victim.get("id")
                if victim_id not in victim_cache.get(country, []):
                    new_victims.append(victim)
                    if country not in victim_cache:
                        victim_cache[country] = []
                    victim_cache[country].append(victim_id)

            if new_victims:
                message = build_message(country, new_victims)
                status = send_telegram_notification(message)
                print(f"[{country}] Telegram message sent! Status code: {status}")
            else:
                print(f"[{country}] No new victims.")
            
            save_victim_cache(victim_cache)

        except Exception as e:
            print(f"[{country}] ERROR: {e}")

if __name__ == "__main__":
    main()
