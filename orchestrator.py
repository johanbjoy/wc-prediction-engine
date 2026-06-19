"""
orchestrator.py — Main pipeline controller.

Pipeline per fixture
--------------------
1. Pull fixture from SQLite
2. Fetch starting XI (scraper → baseline fallback)
3. Cache guard: return immediately if prediction already exists
4. Agent 1 (OpenRouter / DeepSeek R1 Free): tactical analysis, cached per fixture
5. Agent 2: Poisson model (always) + optional LLM override (Gemini / Grok)
6. Save prediction to SQLite

Env vars
--------
  OPENROUTER_API_KEY   — Agent 1
  GEMINI_API_KEY       — Agent 2 LLM (optional)
  GROK_API_KEY         — Agent 2 LLM alternative (optional)
  AGENT2_BACKEND       — "poisson" (default) | "gemini" | "grok"

Set AGENT2_BACKEND=poisson for zero LLM API cost on Agent 2.
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

from data.database import get_connection
from data.scraper import get_starting_xi, get_upcoming_fixtures
from data.odds_blender import get_blended_probabilities

from models.poisson_model import predict as run_poisson
from models.xgboost_model import predict as run_xgboost
from models.value_engine import calculate_edge

from agents.analyst import build_tactical_prompt, call_openrouter
from agents.predictor import build_prediction_prompt, call_gemini, call_grok, parse_prediction_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

AGENT2_BACKEND = os.getenv("AGENT2_BACKEND", "poisson")

def get_dynamic_weights() -> dict:
    # Set default weights to fall back on if criteria are not met
    # Backtested: 60X/40P blend scores +2pts over pure XGBoost across 24 matches
    weights = {"xgboost": 0.6, "poisson": 0.4}
    
    # Establish a connection to the PostgreSQL database
    conn = get_connection()
    
    try:
        # Create a cursor to execute the query
        with conn.cursor() as cur:
            # Query the database for average points per model component (xgboost vs poisson)
            cur.execute("""
                SELECT
                    CASE
                        WHEN model_name LIKE '%%xgboost%%' THEN 'xgboost'
                        WHEN model_name LIKE '%%poisson%%' THEN 'poisson'
                    END AS model_type,
                    COUNT(points_awarded) AS match_count,
                    AVG(points_awarded) AS avg_points
                FROM predictions
                WHERE points_awarded IS NOT NULL
                  AND (model_name LIKE '%%xgboost%%' OR model_name LIKE '%%poisson%%')
                GROUP BY model_type
            """)
            
            # Fetch all the aggregated results from the query
            rows = cur.fetchall()
            
            # Create a dictionary keyed by the clean model_type alias
            stats = {row["model_type"]: {"count": row["match_count"], "avg": float(row["avg_points"])} for row in rows}
            
            # Check if both models have at least 3 graded matches to safely proceed with dynamic weighting
            if stats.get("xgboost", {}).get("count", 0) >= 3 and stats.get("poisson", {}).get("count", 0) >= 3:
                
                # Extract the calculated average points for both models
                xgb_avg = stats["xgboost"]["avg"]
                poi_avg = stats["poisson"]["avg"]
                
                # Calculate the combined average sum to use for mathematical normalization
                total_avg = xgb_avg + poi_avg
                
                # Prevent division by zero in the rare event both models average exactly 0 points
                if total_avg > 0:
                    
                    # Normalize the weights so they dynamically sum to exactly 1.0
                    weights["xgboost"] = round(xgb_avg / total_avg, 3)
                    weights["poisson"] = round(poi_avg / total_avg, 3)
    finally:
        # Ensure the database connection is securely closed regardless of success or failure
        conn.close()
        
    # Return the final dynamically calculated or default fallback weights
    return weights

def _cache_get(key: str) -> str | None:
    """Retrieve Agent 1's tactical summary from database cache."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM cache WHERE key=%s", (key,))
            row = cur.fetchone()
            return row["value"] if row else None
    finally:
        conn.close()

def _cache_set(key: str, value: str) -> None:
    """Store Agent 1's tactical summary in database cache."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO cache (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (key, value))
        conn.commit()
    finally:
        conn.close()

def _prediction_exists(fixture_id: int, model_name: str) -> dict | None:
    """Check if we already predicted this match."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT predicted_home_score, predicted_away_score FROM predictions WHERE fixture_id=%s AND model_name=%s",
                (fixture_id, model_name)
            )
            row = cur.fetchone()
            if row:
                return {"home_score": row["predicted_home_score"], "away_score": row["predicted_away_score"]}
            return None
    finally:
        conn.close()

def _save_prediction(fixture_id: int, model_name: str, home: int, away: int, meta_json: str = None) -> None:
    """Store prediction result with analytical metadata."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predictions (fixture_id, model_name, predicted_home_score, predicted_away_score, meta_json) 
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (fixture_id, model_name) DO UPDATE SET meta_json = EXCLUDED.meta_json
                """,
                (fixture_id, model_name, home, away, meta_json)
            )
        conn.commit()
    finally:
        conn.close()


def _fetch_fixture(fixture_id: int | None) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if fixture_id:
                cur.execute("SELECT * FROM fixtures WHERE id=%s", (fixture_id,))
            else:
                cur.execute("SELECT * FROM fixtures WHERE status IN ('NS','TBD') ORDER BY match_date ASC LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def run_pipeline(fixture_id=None):
    fixture = _fetch_fixture(fixture_id)
    if not fixture:
        logger.error("No fixture found.")
        return None

    home_team, away_team, fid = fixture["home_team"], fixture["away_team"], fixture["id"]
    model_tag = f"ensemble+{AGENT2_BACKEND}+deepseek-r1"
    logger.info(f"▶ {home_team} vs {away_team} (fixture {fid})")

    existing = _prediction_exists(fid, model_tag)
    if existing:
        logger.info(f"  Cache hit — skipping all API calls for fixture {fid}.")
        return {"fixture_id": fid, "home_team": home_team, "away_team": away_team, "prediction": {**existing, "predicted_winner": "cached"}, "source": "cache"}

    match_date = fixture.get("match_date", "")
    home_players = get_starting_xi(home_team, fid, match_date)
    away_players = get_starting_xi(away_team, fid, match_date)
    logger.info(f"  Players: {len(home_players)} {home_team} | {len(away_players)} {away_team}")


    # Determine if match is in the knockout stage (Extra Time / Penalties enabled)
    # The group stage ends June 27. Knockouts begin June 28.
    is_knockout = False
    if match_date and match_date[:10] >= "2026-06-28":
        is_knockout = True

    # --- ENSEMBLE EXECUTION ---

    try:
        poisson_result = run_poisson(home_team, away_team, home_players, away_players, is_knockout=is_knockout)
    except Exception as e:
        logger.error(f"Poisson model failed: {e}")
        poisson_result = None

    try:
        xgb_result = run_xgboost(home_team, away_team, home_players, away_players)
    except Exception as e:
        logger.error(f"XGBoost model failed: {e}")
        xgb_result = None

    if not poisson_result and not xgb_result:
        logger.error("Both models failed. Aborting prediction.")
        return None

    # Handle fallbacks
    if poisson_result and not xgb_result:
        logger.warning("Falling back to 100% Poisson.")
        p_xg_home = poisson_result["model_meta"]["lam_home"]
        p_xg_away = poisson_result["model_meta"]["lam_away"]
        x_xg_home = p_xg_home
        x_xg_away = p_xg_away
    elif xgb_result and not poisson_result:
        logger.warning("Falling back to 100% XGBoost.")
        x_xg_home = xgb_result["model_meta"]["raw_home_xg"]
        x_xg_away = xgb_result["model_meta"]["raw_away_xg"]
        p_xg_home = x_xg_home
        p_xg_away = x_xg_away
    else:
        p_xg_home = poisson_result["model_meta"]["lam_home"]
        p_xg_away = poisson_result["model_meta"]["lam_away"]
        x_xg_home = xgb_result["model_meta"]["raw_home_xg"]
        x_xg_away = xgb_result["model_meta"]["raw_away_xg"]

    # Shifted to dynamic weighting based on actual model performance
    weights = get_dynamic_weights()
    XGB_WEIGHT = weights["xgboost"]
    POISSON_WEIGHT = weights["poisson"]
    
    logger.info(f"  Dynamic Weights Appied: XGBoost ({XGB_WEIGHT}) | Poisson ({POISSON_WEIGHT})")

    blended_home_xg = (p_xg_home * POISSON_WEIGHT) + (x_xg_home * XGB_WEIGHT)
    blended_away_xg = (p_xg_away * POISSON_WEIGHT) + (x_xg_away * XGB_WEIGHT)

    # Apply Elo Differential Boost (Backtested: 1.5x optimal across 24 matches)
    from data.scraper import TEAM_BASELINES
    hb = TEAM_BASELINES.get(home_team, TEAM_BASELINES["Default"])
    ab = TEAM_BASELINES.get(away_team, TEAM_BASELINES["Default"])
    elo_diff = (hb.get("elo", 1800) - ab.get("elo", 1800)) / 100.0
    
    # Apply live tournament form modifier from wcup2026.org free API
    # Dampens Elo boost for underperforming favorites, boosts overperformers
    from data.tournament_form import get_tournament_form
    home_form = get_tournament_form(home_team)
    away_form = get_tournament_form(away_team)
    
    home_form_mod = home_form["form_modifier"]
    away_form_mod = away_form["form_modifier"]
    
    if home_form["played"] > 0 or away_form["played"] > 0:
        logger.info(f"  Tournament Form: {home_team} ({home_form_mod}) | {away_team} ({away_form_mod})")
    
    ELO_BOOST_MULT = 1.5  # Backtested optimal: stronger Elo signal improves exact scores
    if elo_diff > 0:
        # Home team is the Elo favorite — scale boost by home team's form
        blended_home_xg += elo_diff * ELO_BOOST_MULT * home_form_mod
    else:
        # Away team is the Elo favorite — scale boost by away team's form
        blended_away_xg += abs(elo_diff) * ELO_BOOST_MULT * away_form_mod

    # Estimate base probabilities for Agent 2 and Value Engine
    import numpy as np
    xg_diff = blended_home_xg - blended_away_xg
    p_home = 1.0 / (1.0 + np.exp(-0.8 * xg_diff)) * 100
    p_away = (1.0 - p_home / 100.0) * 0.72 * 100
    p_draw = 100.0 - p_home - p_away

    # Normalize
    total = p_home + p_draw + p_away
    p_home = round(p_home / total * 100, 1)
    p_draw = round(p_draw / total * 100, 1)
    p_away = round(100.0 - p_home - p_draw, 1)

    # Pack into initial schema
    final_pred = {
        "home_score": 0, "away_score": 0, "predicted_winner": "",
        "model_meta": {
            "model": "ensemble_50_50",
            "poisson_xg": {"home": round(p_xg_home, 3), "away": round(p_xg_away, 3)},
            "xgb_xg": {"home": round(x_xg_home, 3), "away": round(x_xg_away, 3)},
            "blended_xg": {"home": round(blended_home_xg, 3), "away": round(blended_away_xg, 3)},
            "lam_home": round(blended_home_xg, 3),
            "lam_away": round(blended_away_xg, 3),
            "p_home_win": p_home, "p_draw": p_draw, "p_away_win": p_away
        }
    }

    # Blending with market consensus
    blended_probs = get_blended_probabilities(
        home_team, away_team, 
        final_pred["model_meta"]
    )
    final_pred["model_meta"].update({
        "p_home_win": blended_probs["p_home_win"],
        "p_draw": blended_probs["p_draw"],
        "p_away_win": blended_probs["p_away_win"]
    })

    cache_key = f"tactical_{fid}"
    tactical_preview = _cache_get(cache_key)
    if not tactical_preview:
        logger.info("  Agent 1: requesting tactical preview from DeepSeek R1…")
        tactical_preview = call_openrouter(build_tactical_prompt(home_team, away_team, home_players, away_players))
        if tactical_preview:
            _cache_set(cache_key, tactical_preview)
            logger.info("  Agent 1: preview received and cached.")
        else:
            tactical_preview = f"No preview available. {home_team} vs {away_team}."
            logger.warning("  Agent 1 unavailable — using placeholder.")
    else:
        logger.info("  Agent 1: loaded from cache.")

    llm_modifiers = None
    if AGENT2_BACKEND != "poisson":
        prompt = build_prediction_prompt(home_team, away_team, home_players, away_players, tactical_preview, final_pred)
        raw = call_gemini(prompt) if AGENT2_BACKEND == "gemini" else call_grok(prompt)
        llm_modifiers = parse_prediction_json(raw)
        logger.info(f"  Agent 2 ({AGENT2_BACKEND}) Modifiers: {llm_modifiers}")

    # Apply LLM modifiers
    if llm_modifiers:
        blended_home_xg *= llm_modifiers.get("home_attack_mod", 1.0) * llm_modifiers.get("away_defense_mod", 1.0)
        blended_away_xg *= llm_modifiers.get("away_attack_mod", 1.0) * llm_modifiers.get("home_defense_mod", 1.0)

    # Conservative rounding bias: -0.10 rounds down borderline xG, better matching real WC scorelines
    ROUND_BIAS = -0.10  # Backtested: avoids over-predicting goals in tight matches
    home_score = max(0, int(np.floor(blended_home_xg + 0.5 + ROUND_BIAS)))
    away_score = max(0, int(np.floor(blended_away_xg + 0.5 + ROUND_BIAS)))

    if home_score > away_score:
        predicted_winner = home_team
    elif away_score > home_score:
        predicted_winner = away_team
    else:
        predicted_winner = "Draw"

    final_pred["home_score"] = home_score
    final_pred["away_score"] = away_score
    final_pred["predicted_winner"] = predicted_winner

    meta = final_pred["model_meta"]
    
    # Value Engine Edge Calculation
    edge_calc = calculate_edge(meta['p_home_win'], blended_probs['p_home_win'])
    logger.info(f"  Value Engine: EV {edge_calc['ev']} | Kelly {edge_calc['kelly_pct']}% | Edge {edge_calc['edge']}%")
    
    logger.info(f"  Final Ensemble → {home_team} {final_pred['home_score']}-{final_pred['away_score']} {away_team}  ({meta['p_home_win']}% / {meta['p_draw']}% / {meta['p_away_win']}%)")

    import json
    _save_prediction(fid, model_tag, final_pred["home_score"], final_pred["away_score"], json.dumps(meta))
    logger.info(f"  ✓ Saved: {home_team} {final_pred['home_score']}-{final_pred['away_score']} {away_team} [{model_tag}]")

    # Save individual model predictions for dynamic weight grading
    if xgb_result:
        xgb_h = max(0, int(round(x_xg_home)))
        xgb_a = max(0, int(round(x_xg_away)))
        _save_prediction(fid, "xgboost", xgb_h, xgb_a)
        logger.info(f"  ✓ Saved individual: {home_team} {xgb_h}-{xgb_a} {away_team} [xgboost]")

    if poisson_result:
        poi_h = max(0, int(round(p_xg_home)))
        poi_a = max(0, int(round(p_xg_away)))
        _save_prediction(fid, "poisson", poi_h, poi_a)
        logger.info(f"  ✓ Saved individual: {home_team} {poi_h}-{poi_a} {away_team} [poisson]")

    return {"fixture_id": fid, "home_team": home_team, "away_team": away_team, "prediction": final_pred, "poisson_meta": meta, "model_name": model_tag}


def run_all_upcoming(limit=4):
    results = []
    for f in get_upcoming_fixtures(limit):
        result = run_pipeline(fixture_id=f["id"])
        if result:
            results.append(result)
    return results


if __name__ == "__main__":
    from data.database import init_db
    from data.scraper  import fetch_and_store_fixtures
    from evaluator     import evaluate_all_pending, rebuild_leaderboard, check_and_evaluate_recent
    
    init_db()
    fetch_and_store_fixtures()
    
    # 1. Smart-check live API for any newly finished matches (post-120 mins)
    check_and_evaluate_recent()

    # 2. Grade completed matches and update metrics before predicting new ones
    evaluate_all_pending()
    rebuild_leaderboard()
    
    print("\n" + "─" * 50)
    results = run_all_upcoming(limit=4)
    print("\n" + "─" * 50)
    print("PREDICTIONS")
    for r in results:
        p = r["prediction"]
        print(f"  {r['home_team']:15} {p['home_score']}-{p['away_score']}  {r['away_team']:15}  → {p['predicted_winner']}")
