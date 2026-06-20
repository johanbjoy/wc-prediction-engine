import json
from data.database import get_connection

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("""
        SELECT f.real_home_score, f.real_away_score, p.meta_json
        FROM predictions p
        JOIN fixtures f ON p.fixture_id = f.id
        WHERE p.model_name = 'nexus_v3' AND f.status = 'FT'
    """)
    rows = cur.fetchall()

conn.close()

exact_count = 0
correct_count = 0
total = len(rows)

for row in rows:
    real_h = row["real_home_score"]
    real_a = row["real_away_score"]
    
    if real_h is None or real_a is None:
        total -= 1
        continue
        
    try:
        meta = json.loads(row["meta_json"])
        pred_h = int(round(meta.get("nexus_home_xg", 1.0)))
        pred_a = int(round(meta.get("nexus_away_xg", 1.0)))
        
        # Determine actual outcome
        real_out = "H" if real_h > real_a else ("A" if real_a > real_h else "D")
        pred_out = "H" if pred_h > pred_a else ("A" if pred_a > pred_h else "D")
        
        if pred_h == real_h and pred_a == real_a:
            exact_count += 1
            correct_count += 1
        elif real_out == pred_out:
            correct_count += 1
            
    except Exception as e:
        pass

if total > 0:
    print(f"Total Matches Evaluated: {total}")
    print(f"True Exact Scores: {exact_count} ({exact_count/total*100:.1f}%)")
    print(f"True Correct Winners: {correct_count} ({correct_count/total*100:.1f}%)")
else:
    print("No data found.")
