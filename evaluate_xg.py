import json
import pandas as pd
from data.database import get_connection
from models.nexus_model import predict

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("SELECT * FROM fixtures WHERE status = 'FT'")
    rows = cur.fetchall()
conn.close()

correct = 0
total = 0

for f in rows:
    home, away = f["home_team"], f["away_team"]
    res = predict(home, away, "Qualifiers", f["match_date"], 1800, 1800, 1.0, 1.0)
    if not res: continue
    
    # Use the ML xG as the new lambdas for Dixon-Coles
    from models.dixon_coles import get_dixon_coles_probs
    lam_h = res["nexus_home_xg"]
    lam_a = res["nexus_away_xg"]
    
    # Get ML-driven probabilities
    probs = get_dixon_coles_probs(lam_h, lam_a)
    ph, pd, pa = probs["p_home_win"], probs["p_draw"], probs["p_away_win"]
    
    pred_out = "D"
    if ph > pd and ph > pa: pred_out = "H"
    elif pa > ph and pa > pd: pred_out = "A"
    
    real_h, real_a = f["real_home_score"], f["real_away_score"]
    if real_h is None: continue
    
    real_out = "D"
    if real_h > real_a: real_out = "H"
    elif real_a > real_h: real_out = "A"
    
    if pred_out == real_out:
        correct += 1
    total += 1

print(f"ML-Driven Accuracy: {correct}/{total} ({correct/total*100:.1f}%)")
