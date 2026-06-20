import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import json
import pandas as pd
from data.database import get_connection
from models.nexus_model import predict

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("SELECT * FROM fixtures WHERE status = 'FT' ORDER BY match_date DESC LIMIT 50")
    rows = cur.fetchall()
conn.close()

exact_count = 0
correct_count = 0
total = 0

for f in rows:
    home, away = f["home_team"], f["away_team"]
    res = predict(home, away, "Qualifiers", f["match_date"], 1800, 1800, 1.0, 1.0)
    if not res: continue
    
    probs = res.get("blended_probs", res.get("dixon_coles_probs", {}))
    ph = probs.get("p_home_win", 0.33)
    pd = probs.get("p_draw", 0.33)
    pa = probs.get("p_away_win", 0.33)
    
    # Calculate exact scores dynamically from xG (matching backfill logic)
    base_h = res.get("nexus_home_xg", 1.0)
    base_a = res.get("nexus_away_xg", 1.0)
    pred_h = int(round(base_h))
    pred_a = int(round(base_a))
    
    # Ensure predicted outcome matches highest probability
    if pa > ph and pa > pd and pred_a <= pred_h:
        pred_a = pred_h + 1
    elif ph > pa and ph > pd and pred_h <= pred_a:
        pred_h = pred_a + 1
    elif pd > ph and pd > pa and pred_h != pred_a:
        pred_h = max(pred_h, pred_a)
        pred_a = pred_h
        
    pred_out = "D"
    if pred_h > pred_a: pred_out = "H"
    elif pred_a > pred_h: pred_out = "A"
    
    real_h, real_a = f["real_home_score"], f["real_away_score"]
    if real_h is None: continue
    
    real_out = "D"
    if real_h > real_a: real_out = "H"
    elif real_a > real_h: real_out = "A"
    
    if pred_h == real_h and pred_a == real_a:
        exact_count += 1
        correct_count += 1
    elif pred_out == real_out:
        correct_count += 1
    
    total += 1
    if total % 10 == 0:
        print(f"Evaluated {total}/50...")

if total > 0:
    print(f"Total Matches: {total}")
    print(f"Coupled Exact Scores: {exact_count} ({exact_count/total*100:.1f}%)")
    print(f"Coupled Correct Winners: {correct_count} ({correct_count/total*100:.1f}%)")
else:
    print("No matches evaluated.")
