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

def _save_prediction(fixture_id: int, model_name: str, home: int, away: int) -> None:
    """Store prediction result."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predictions (fixture_id, model_name, predicted_home_score, predicted_away_score) 
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (fixture_id, model_name) DO NOTHING
                """,
                (fixture_id, model_name, home, away)
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

    # --- ENSEMBLE EXECUTION ---
    POISSON_WEIGHT = 0.70
    XGB_WEIGHT = 0.30

    try:
        poisson_result = run_poisson(home_team, away_team, home_players, away_players)
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

    blended_home_xg = (p_xg_home * POISSON_WEIGHT) + (x_xg_home * XGB_WEIGHT)
    blended_away_xg = (p_xg_away * POISSON_WEIGHT) + (x_xg_away * XGB_WEIGHT)

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

    home_score = max(0, int(round(blended_home_xg)))
    away_score = max(0, int(round(blended_away_xg)))

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

    _save_prediction(fid, model_tag, final_pred["home_score"], final_pred["away_score"])
    logger.info(f"  ✓ Saved: {home_team} {final_pred['home_score']}-{final_pred['away_score']} {away_team} [{model_tag}]")

    return {"fixture_id": fid, "home_team": home_team, "away_team": away_team, "prediction": final_pred, "poisson_meta": meta, "model_name": model_tag}


def run_all_upcoming(limit=5):
    results = []
    for f in get_upcoming_fixtures(limit):
        result = run_pipeline(fixture_id=f["id"])
        if result:
            results.append(result)
    return results


if __name__ == "__main__":
    from data.database import init_db
    from data.scraper  import fetch_and_store_fixtures
    init_db()
    fetch_and_store_fixtures()
    print("\n" + "─" * 50)
    results = run_all_upcoming(limit=5)
    print("\n" + "─" * 50)
    print("PREDICTIONS")
    for r in results:
        p = r["prediction"]
        print(f"  {r['home_team']:15} {p['home_score']}-{p['away_score']}  {r['away_team']:15}  → {p['predicted_winner']}")
