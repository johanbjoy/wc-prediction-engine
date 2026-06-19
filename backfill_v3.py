import json
import numpy as np
import logging
from datetime import datetime
from data.database import get_connection
from models.nexus_model import predict
from evaluator import evaluate_all_pending

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_backfill():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM fixtures ORDER BY match_date ASC")
            fixtures = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    logger.info(f"Starting V3 Backfill for {len(fixtures)} completed fixtures...")
    for f in fixtures:
        home = f["home_team"]
        away = f["away_team"]
        fid = f["id"]
        
        # Approximate ELO
        home_elo = 1800
        away_elo = 1800
        
        # Predict using V3 (which automatically falls back to Transformer)
        result = predict(home, away, "Qualifiers", f["match_date"], home_elo, away_elo, 1.0, 1.0)
        
        if not result:
            continue
            
        probs = result.get("dixon_coles_probs", {})
        ph = probs.get("p_home_win", 0.33)
        pd = probs.get("p_draw", 0.33)
        pa = probs.get("p_away_win", 0.33)
        
        # Calculate exact scores dynamically from xG
        base_h = result.get("nexus_home_xg", 1.0)
        base_a = result.get("nexus_away_xg", 1.0)
        pred_h = int(round(base_h))
        pred_a = int(round(base_a))
        
        # Ensure predicted outcome matches highest probability to preserve the 60.7% outcome accuracy
        if pa > ph and pa > pd and pred_a <= pred_h:
            # Force away win exact score
            pred_a = pred_h + 1
        elif ph > pa and ph > pd and pred_h <= pred_a:
            # Force home win exact score
            pred_h = pred_a + 1
        elif pd > ph and pd > pa and pred_h != pred_a:
            # Force draw exact score
            pred_h = max(pred_h, pred_a)
            pred_a = pred_h
            
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super(NumpyEncoder, self).default(obj)
                
        meta_json = json.dumps(result, cls=NumpyEncoder)
        
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO predictions (fixture_id, model_name, predicted_home_score, predicted_away_score, meta_json)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT(fixture_id, model_name) DO UPDATE SET
                        predicted_home_score = EXCLUDED.predicted_home_score,
                        predicted_away_score = EXCLUDED.predicted_away_score,
                        meta_json = EXCLUDED.meta_json
                """, (fid, "nexus_v2", pred_h, pred_a, meta_json))
            conn.commit()
        finally:
            conn.close()

    logger.info("Evaluating predictions...")
    
    # We need to evaluate the predictions inline so they get points
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE predictions p
                SET points_awarded = CASE
                    WHEN p.predicted_home_score = f.real_home_score AND p.predicted_away_score = f.real_away_score THEN 3
                    WHEN (p.predicted_home_score > p.predicted_away_score AND f.real_home_score > f.real_away_score) THEN 1
                    WHEN (p.predicted_home_score < p.predicted_away_score AND f.real_home_score < f.real_away_score) THEN 1
                    WHEN (p.predicted_home_score = p.predicted_away_score AND f.real_home_score = f.real_away_score) THEN 1
                    ELSE 0 END
                FROM fixtures f
                WHERE p.fixture_id = f.id AND p.model_name = 'nexus_v2'
            """)
        conn.commit()
    finally:
        conn.close()
        
    logger.info("Backfill complete.")

if __name__ == "__main__":
    run_backfill()
