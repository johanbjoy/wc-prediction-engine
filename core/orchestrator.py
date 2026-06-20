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

from models.nexus_model import predict as run_nexus

from agents.analyst import build_tactical_prompt, call_llm
from agents.predictor import build_prediction_prompt, call_gemini, call_grok, call_groq, parse_prediction_json

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
                ON CONFLICT (fixture_id, model_name) DO UPDATE SET 
                    predicted_home_score = EXCLUDED.predicted_home_score,
                    predicted_away_score = EXCLUDED.predicted_away_score,
                    meta_json = EXCLUDED.meta_json
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
    model_tag = "nexus_v2"
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

    # --- N.E.X.U.S. V2 EXECUTION ---
    from data.scraper import TEAM_BASELINES
    hb = TEAM_BASELINES.get(home_team, TEAM_BASELINES["Default"])
    ab = TEAM_BASELINES.get(away_team, TEAM_BASELINES["Default"])
    elo_home = hb.get("elo", 1800)
    elo_away = ab.get("elo", 1800)
    
    from data.tournament_form import get_tournament_form
    home_form = get_tournament_form(home_team)["form_modifier"]
    away_form = get_tournament_form(away_team)["form_modifier"]

    try:
        nex_out = run_nexus(home_team, away_team, "World Cup", match_date, elo_home, elo_away, home_form, away_form)
    except Exception as e:
        logger.error(f"N.E.X.U.S. model failed: {e}")
        return None

    if not nex_out:
        logger.error("N.E.X.U.S. returned empty prediction.")
        return None

    blended_home_xg = nex_out["nexus_home_xg"]
    blended_away_xg = nex_out["nexus_away_xg"]
    dc_probs = nex_out["dixon_coles_probs"]
    
    p_home = dc_probs["p_home_win"]
    p_draw = dc_probs["p_draw"]
    p_away = dc_probs["p_away_win"]

    final_pred = {
        "home_score": 0, "away_score": 0, "predicted_winner": "",
        "model_meta": {
            "model": "nexus_v2",
            "blended_xg": {"home": round(blended_home_xg, 3), "away": round(blended_away_xg, 3)},
            "lam_home": round(blended_home_xg, 3),
            "lam_away": round(blended_away_xg, 3),
            "p_home_win": p_home, "p_draw": p_draw, "p_away_win": p_away,
            "rest_home": nex_out["env_context"]["rest_home"],
            "rest_away": nex_out["env_context"]["rest_away"]
        }
    }

    # Removed market consensus blending

    cache_key = f"tactical_{fid}"
    tactical_preview = _cache_get(cache_key)
    if not tactical_preview:
        logger.info("  Agent 1: requesting tactical preview from Groq LLaMA 3.3…")
        from agents.analyst import call_llm, build_tactical_prompt
        from data.scraper import get_team_sentiment
        logger.info("  Fetching sentiment headlines...")
        home_sentiment = get_team_sentiment(home_team)
        away_sentiment = get_team_sentiment(away_team)
        tactical_preview = call_llm(build_tactical_prompt(home_team, away_team, home_players, away_players, home_sentiment, away_sentiment))
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
        if AGENT2_BACKEND == "groq":
            raw = call_groq(prompt)
        elif AGENT2_BACKEND == "grok":
            raw = call_grok(prompt)
        else:
            raw = call_gemini(prompt)
        llm_modifiers = parse_prediction_json(raw)
        logger.info(f"  Agent 2 ({AGENT2_BACKEND}) Modifiers: {llm_modifiers}")

    # Apply LLM modifiers
    if llm_modifiers:
        blended_home_xg *= llm_modifiers.get("home_attack_mod", 1.0) * llm_modifiers.get("away_defense_mod", 1.0)
        blended_away_xg *= llm_modifiers.get("away_attack_mod", 1.0) * llm_modifiers.get("home_defense_mod", 1.0)
        
        from models.dixon_coles import get_dixon_coles_probs
        dc_probs = get_dixon_coles_probs(blended_home_xg, blended_away_xg)
        p_home = dc_probs["p_home_win"]
        p_draw = dc_probs["p_draw"]
        p_away = dc_probs["p_away_win"]
        final_pred["model_meta"].update({
            "lam_home": round(blended_home_xg, 3),
            "lam_away": round(blended_away_xg, 3),
            "p_home_win": p_home, "p_draw": p_draw, "p_away_win": p_away
        })

    probs = nex_out.get("blended_probs", nex_out.get("dixon_coles_probs", {}))
    ph = probs.get("p_home_win", 0.33)
    pd = probs.get("p_draw", 0.33)
    pa = probs.get("p_away_win", 0.33)

    home_score = int(round(blended_home_xg))
    away_score = int(round(blended_away_xg))

    if pa > ph and pa > pd and away_score <= home_score:
        away_score = home_score + 1
    elif ph > pa and ph > pd and home_score <= away_score:
        home_score = away_score + 1
    elif pd > ph and pd > pa and home_score != away_score:
        home_score = max(home_score, away_score)
        away_score = home_score

    if p_home > p_away and p_home > p_draw:
        predicted_winner = home_team
    elif p_away > p_home and p_away > p_draw:
        predicted_winner = away_team
    else:
        predicted_winner = "Draw"

    final_pred["home_score"] = home_score
    final_pred["away_score"] = away_score
    final_pred["predicted_winner"] = predicted_winner

    meta = final_pred["model_meta"]
    
    # Removed value engine EV calculation
    
    logger.info(f"  Final Ensemble → {home_team} {final_pred['home_score']}-{final_pred['away_score']} {away_team}  ({meta['p_home_win']}% / {meta['p_draw']}% / {meta['p_away_win']}%)")

    import json
    _save_prediction(fid, model_tag, final_pred["home_score"], final_pred["away_score"], json.dumps(meta))
    logger.info(f"  ✓ Saved: {home_team} {final_pred['home_score']}-{final_pred['away_score']} {away_team} [{model_tag}]")

    return {"fixture_id": fid, "home_team": home_team, "away_team": away_team, "prediction": final_pred, "poisson_meta": meta, "model_name": model_tag}


def run_all_upcoming(limit=104):
    results = []
    for f in get_upcoming_fixtures(limit):
        result = run_pipeline(fixture_id=f["id"])
        if result:
            results.append(result)
    return results


if __name__ == "__main__":
    from data.database import init_db
    from data.scraper  import fetch_and_store_fixtures
    from core.evaluator import evaluate_all_pending, rebuild_leaderboard, check_and_evaluate_recent
    
    init_db()
    fetch_and_store_fixtures()
    
    # 1. Smart-check live API for any newly finished matches (post-120 mins)
    check_and_evaluate_recent()

    # 2. Grade completed matches and update metrics before predicting new ones
    evaluate_all_pending()
    rebuild_leaderboard()
    
    print("\n" + "─" * 50)
    results = run_all_upcoming(limit=104)
    print("\n" + "─" * 50)
    print("PREDICTIONS")
    for r in results:
        p = r["prediction"]
        print(f"  {r['home_team']:15} {p['home_score']}-{p['away_score']}  {r['away_team']:15}  → {p['predicted_winner']}")
