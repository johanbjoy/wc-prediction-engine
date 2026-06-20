import pandas as pd
from data.database import get_completed_predictions, get_upcoming_predictions

def test_dates():
    comp = get_completed_predictions(limit=5)
    upc = get_upcoming_predictions(limit=5)
    all_rows = comp + upc
    df = pd.DataFrame(all_rows)
    df['_sort_date'] = pd.to_datetime(df['match_date'].astype(str).str.replace(' UTC', ':00', regex=False), utc=True)
    
    for idx, row in df.iterrows():
        raw_date = row['match_date']
        sort_date = row['_sort_date']
        ist_dt = sort_date.tz_convert('Asia/Kolkata')
        formatted = ist_dt.strftime('%b %d, %Y • %I:%M %p IST')
        print(f"RAW: {raw_date} | SORT_DATE (UTC): {sort_date} | IST: {formatted}")

test_dates()
