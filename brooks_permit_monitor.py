import requests
from datetime import datetime, date, timedelta
import json
import os

API = "https://www.recreation.gov/api/permits/249991/availability/month"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.recreation.gov/permits/249991",
}

# ===== USER CONFIG =====
START_DATE = date(2026, 6, 1)
END_DATE   = date(2026, 7, 22)
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "seen_dates.json"
# =======================

def month_start(d):
    return date(d.year, d.month, 1)

def daterange(d1, d2):
    cur = d1
    while cur <= d2:
        yield cur
        cur += timedelta(days=1)

def fetch_month(start_month):
    params = {
        "start_date": start_month.strftime("%Y-%m-01T00:00:00.000Z"),
        "commercial_acct": "false",
        "is_lottery": "false",
    }
    r = requests.get(API, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def extract_available_dates(payload):
    out = set()
    availability = payload.get("payload", {}).get("availability", {})
    for division in availability.values():
        date_map = division.get("date_availability", {})
        for k, v in date_map.items():
            try:
                d = datetime.strptime(k[:10], "%Y-%m-%d").date()
            except Exception:
                continue
            if v.get("remaining", 0) > 0:
                out.add(d)
    return out

def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(seen), f)

def notify(dates):
    msg = "**Brooks Permit Available**\n" + "\n".join(str(d) for d in dates)
    requests.post(WEBHOOK_URL, json={"content": msg}, timeout=10)

def main():
    months = {month_start(START_DATE), month_start(END_DATE)}
    available = set()

    for m in months:
        data = fetch_month(m)
        available |= extract_available_dates(data)

    hits = [d for d in daterange(START_DATE, END_DATE) if d in available]

    seen = load_seen()
    new_hits = [str(d) for d in hits if str(d) not in seen]

    if new_hits:
        notify(new_hits)
        for d in new_hits:
            seen.add(d)
        save_seen(seen)

if __name__ == "__main__":
    main()
