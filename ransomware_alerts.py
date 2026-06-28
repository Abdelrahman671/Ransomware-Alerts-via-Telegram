import requests
import sys
import json
import os
import time
from datetime import datetime, timedelta, timezone

# Telegram bot token and chat ID

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")


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
    "YEM": "Yemen",
    "BH": "Bahrain",
    "TR": "Turkey",
    "IL": "Israel"
}

def get_victim_data(country_code, max_retries=3):
    url = f"https://api.ransomware.live/v2/countryvictims/{country_code}"
    headers = {"Accept": "application/json"}

    for attempt in range(max_retries):
        resp = requests.get(url, headers=headers)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            print(f"[{country_code}] Rate limited. Waiting {retry_after}s "
                  f"({attempt + 1}/{max_retries})")
            time.sleep(retry_after)
            continue

        resp.raise_for_status()
        return resp.json()

    print(f"[{country_code}] Skipping after {max_retries} rate-limit retries.")
    return None

from datetime import datetime, timedelta, UTC

def filter_recent_victims(data):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)  # last day

    recent = []

    for victim in data:
        ds = victim.get("discovered")

        if not ds:
            continue

        try:
            # Handles:
            # 2026-06-17T18:24:19.153580+00:00
            d = datetime.fromisoformat(ds)
        except Exception:
            continue

        if d >= cutoff:
            recent.append(victim)

    return recent

def build_message(country_name, victims):
    msg = f"📢 *Ransomware Victims in {country_name} (Last 1 Days)*\n*Total:* {len(victims)}\n\n"
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


# old

""""def main():
    for code, country in ME_COUNTRIES.items():

        time.sleep(2)

        try:
            data = get_victim_data(code)

            if data is None:
                continue

            recent_victims = filter_recent_victims(data)
            if not recent_victims:
                print(f"[{country}] No victims found.")
                continue
            message = build_message(country, recent_victims)

            print(f"API returned: {len(data)}")
            print(f"After filtering: {len(recent_victims)}")

            status = send_telegram_notification(message)
            print(f"[{country}] Telegram message sent! Status code: {status}")
        except Exception as e:
            print(f"[{country}] ERROR: {e}")"""


# new tests

def main():
    for code, country in ME_COUNTRIES.items():
        try:
            data = get_victim_data(code)

            if not data:
                print(f"[{country}] API returned no data.")
                continue

            recent_victims = filter_recent_victims(data)

            print(f"[{country}] API returned {len(data)} victims, "
                  f"{len(recent_victims)} in the last 30 days.")

            if not recent_victims:
                continue

            message = build_message(country, recent_victims)

            status = send_telegram_notification(message)

            print(f"[{country}] Telegram sent successfully ({status}).")

        except Exception as e:
            print(f"[{country}] ERROR: {e}")

        # Optional: be nice to the API
        time.sleep(2)

# test for a country only

"""def main():
    data = get_victim_data("EG")   # or EG, TR, etc.

    print(type(data))

    if isinstance(data, list):
        print(f"Items returned: {len(data)}")
        if data:
            print(json.dumps(data[0], indent=2))
    else:
        print(json.dumps(data, indent=2))"""

if __name__ == "__main__":
    main()
