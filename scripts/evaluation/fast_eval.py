import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# MOCK ALL DB AND API CALLS FIRST
import src.nexus.data.database as db
db.get_team_players = lambda t: []
db.get_team_momentum = lambda t: 1.0

import src.nexus.models.nexus_model as nexus_model
nexus_model._calculate_rest_days = lambda team, d: 5
nexus_model.get_team_value_ratio = lambda h, a: 1.0
nexus_model.get_h2h_streak = lambda h, a: 0
nexus_model.has_coach_changed_tactics = lambda t: 0
nexus_model.get_team_momentum = lambda t: 1.0

import src.nexus.data.scraper as scraper
scraper.fetch_live_odds = lambda h, a: (3.0, 3.0, 3.0)
scraper.fetch_weather_modifier = lambda x: 1.0

from src.nexus.models.nexus_model import predict
from src.nexus.data.database import get_connection

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("SELECT * FROM fixtures WHERE status = 'FT' ORDER BY match_date DESC LIMIT 50")
    rows = cur.fetchall()
conn.close()

exact_count, correct_count, total = 0, 0, 0

print("Starting Fast Evaluation...")
for f in rows:
    home, away = f["home_team"], f["away_team"]
    res = predict(home, away, "Qualifiers", f["match_date"], 1800, 1800, 1.0, 1.0)
    if not res: continue
    
    probs = res.get("blended_probs", res.get("dixon_coles_probs", {}))
    ph, pd, pa = probs.get("p_home_win", 0.33), probs.get("p_draw", 0.33), probs.get("p_away_win", 0.33)
    
    base_h = res.get("nexus_home_xg", 1.0)
    base_a = res.get("nexus_away_xg", 1.0)
    pred_h = int(round(base_h))
    pred_a = int(round(base_a))
    
    if pa > ph and pa > pd and pred_a <= pred_h: pred_a = pred_h + 1
    elif ph > pa and ph > pd and pred_h <= pred_a: pred_h = pred_a + 1
    elif pd > ph and pd > pa and pred_h != pred_a:
        pred_h = max(pred_h, pred_a)
        pred_a = pred_h
        
    pred_out = "H" if pred_h > pred_a else ("A" if pred_a > pred_h else "D")
    
    real_h, real_a = f["real_home_score"], f["real_away_score"]
    if real_h is None: continue
    real_out = "H" if real_h > real_a else ("A" if real_a > real_h else "D")
    
    if pred_h == real_h and pred_a == real_a:
        exact_count += 1
        correct_count += 1
    elif pred_out == real_out:
        correct_count += 1
    
    total += 1
    if total % 10 == 0: print(f"Evaluated {total}/50...")

print(f"Total Matches: {total}")
print(f"Coupled Exact Scores: {exact_count} ({exact_count/total*100:.1f}%)")
print(f"Coupled Correct Winners: {correct_count} ({correct_count/total*100:.1f}%)")
