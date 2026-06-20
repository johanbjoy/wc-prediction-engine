import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import numpy as np
import logging
from datetime import datetime
from data.database import get_connection
from models.nexus_model import predict
from core.evaluator import evaluate_all_pending

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
    
    # Reuse a single DB connection for all insertions and updates
    db_conn = get_connection()
    try:
        with db_conn.cursor() as cur:
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
                    
                probs = result.get("blended_probs", result.get("dixon_coles_probs", {}))
                ph = probs.get("p_home_win", 0.33)
                pd = probs.get("p_draw", 0.33)
                pa = probs.get("p_away_win", 0.33)
                # Extract most likely scoreline matching the highest probability outcome
                dc_dict = result.get("dixon_coles_probs", {})
                matrix = dc_dict.get("matrix", None)
                
                if matrix is not None:
                    matrix_arr = np.array(matrix)
                    
                    # 1. Determine the outcome based on aggregated probabilities
                    outcome = "H" if ph > max(pa, pd) else "A" if pa > max(ph, pd) else "D"
                    
                    # 2. Mask the matrix so we only consider scorelines matching the outcome
                    mask = np.zeros_like(matrix_arr, dtype=bool)
                    for i in range(matrix_arr.shape[0]):
                        for j in range(matrix_arr.shape[1]):
                            if outcome == "H" and i > j: mask[i, j] = True
                            elif outcome == "A" and i < j: mask[i, j] = True
                            elif outcome == "D" and i == j: mask[i, j] = True
                            
                    masked_matrix = matrix_arr * mask
                    flat_idx = np.argmax(masked_matrix)
                    pred_h, pred_a = np.unravel_index(flat_idx, masked_matrix.shape)
                    pred_h, pred_a = int(pred_h), int(pred_a)
                else:
                    # Fallback
                    base_h = result.get("nexus_home_xg", 1.0)
                    base_a = result.get("nexus_away_xg", 1.0)
                    pred_h = int(round(base_h))
                    pred_a = int(round(base_a))
                    
                    if pa > ph and pa > pd and pred_a <= pred_h:
                        pred_a = pred_h + 1
                    elif ph > pa and ph > pd and pred_h <= pred_a:
                        pred_h = pred_a + 1
                    elif pd > ph and pd > pa and pred_h != pred_a:
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
                
                cur.execute("""
                    INSERT INTO predictions (fixture_id, model_name, predicted_home_score, predicted_away_score, meta_json)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT(fixture_id, model_name) DO UPDATE SET
                        predicted_home_score = EXCLUDED.predicted_home_score,
                        predicted_away_score = EXCLUDED.predicted_away_score,
                        meta_json = EXCLUDED.meta_json
                """, (fid, "nexus_v2", pred_h, pred_a, meta_json))
                
            db_conn.commit()
            
            logger.info("Evaluating predictions...")
            cur.execute("""
                UPDATE predictions p
                SET points_awarded = CASE
                    WHEN p.predicted_home_score = f.real_home_score AND p.predicted_away_score = f.real_away_score THEN 3
                    WHEN (p.predicted_home_score > p.predicted_away_score AND f.real_home_score > f.real_away_score) THEN 1
                    WHEN (p.predicted_home_score < p.predicted_away_score AND f.real_away_score > f.real_home_score) THEN 1
                    WHEN (p.predicted_home_score = p.predicted_away_score AND f.real_home_score = f.real_away_score) THEN 1
                    ELSE 0 END
                FROM fixtures f
                WHERE p.fixture_id = f.id AND p.model_name = 'nexus_v2' AND f.status IN ('FT', 'AET', 'PEN')
            """)
            db_conn.commit()
    finally:
        db_conn.close()
        
    logger.info("Backfill complete.")

if __name__ == "__main__":
    run_backfill()
