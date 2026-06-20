import pandas as pd

def parse_match_date(date_str):
    try:
        if 'UTC' in date_str:
            parts = date_str.split(' UTC')
            base_time = pd.to_datetime(parts[0])
            offset_str = parts[1] # e.g. "-5" or "+2" or ""
            if offset_str:
                offset_hours = int(offset_str)
                utc_time = base_time - pd.Timedelta(hours=offset_hours)
            else:
                utc_time = base_time
            return utc_time.tz_localize('UTC')
        else:
            return pd.to_datetime(date_str, utc=True)
    except Exception:
        return pd.NaT

tests = [
    "2026-06-20 12:00 UTC-5",
    "2026-06-19 20:30 UTC-4",
    "2026-06-19 20:00 UTC-7",
    "2026-06-11 13:00 UTC-6",
    "2026-06-19 20:30"
]

for t in tests:
    utc_dt = parse_match_date(t)
    ist_dt = utc_dt.tz_convert('Asia/Kolkata')
    print(f"RAW: {t} | UTC: {utc_dt} | IST: {ist_dt.strftime('%b %d, %Y • %I:%M %p')}")
