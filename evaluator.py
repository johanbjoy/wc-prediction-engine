"""
evaluator.py — Post-match scoring and leaderboard management.

Scoring rules
-------------
  Exact scoreline match         → 3 points
  Correct outcome (W/D/L) only  → 1 point
  Wrong outcome                 → 0 points

Usage
-----
  from evaluator import evaluate_fixture, evaluate_all_pending

  # Score one match manually after entering real scores:
  evaluate_fixture(1001)

  # Run as a daily cron over all completed fixtures:
  evaluate_all_pending()
"""
import logging
from data.database import get_connection
from data.scraper  import fetch_actual_result

logger = logging.getLogger(__name__)


# ─── OUTCOME HELPERS ───────────────────────────────────────────────────────

def _outcome(home: int, away: int) -> str:
    """Return 'home', 'draw', or 'away'."""
    if   home > away: return "home"
    elif home < away: return "away"
    return "draw"


def _calculate_points(pred_h: int, pred_a: int, real_h: int, real_a: int) -> int:
    """Apply scoring rules; returns 0, 1, or 3."""
    if pred_h == real_h and pred_a == real_a:
        return 3
    if _outcome(pred_h, pred_a) == _outcome(real_h, real_a):
        return 1
    return 0


# ─── LEADERBOARD REBUILD ───────────────────────────────────────────────────

def rebuild_leaderboard() -> None:
    """Recalculate leaderboard from all scored predictions."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT model_name FROM predictions")
            models = [r["model_name"] for r in cur.fetchall()]

            for model_name in models:
                cur.execute("""
                    SELECT 
                        COALESCE(SUM(points_awarded), 0) as total_points,
                        SUM(CASE WHEN points_awarded = 3 THEN 1 ELSE 0 END) as exact_scores,
                        SUM(CASE WHEN points_awarded = 1 THEN 1 ELSE 0 END) as correct_winner,
                        SUM(CASE WHEN points_awarded = 0 THEN 1 ELSE 0 END) as wrong
                    FROM predictions WHERE model_name = %s AND points_awarded IS NOT NULL
                """, (model_name,))
                stats = cur.fetchone()

                total  = stats["total_points"]
                exact  = stats["exact_scores"] or 0
                winner = stats["correct_winner"] or 0
                wrong  = stats["wrong"] or 0

                cur.execute("""
                    INSERT INTO leaderboard (model_name, total_points, exact_scores_count, correct_winner_count, wrong_count)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT(model_name) DO UPDATE SET
                        total_points = EXCLUDED.total_points,
                        exact_scores_count = EXCLUDED.exact_scores_count,
                        correct_winner_count = EXCLUDED.correct_winner_count,
                        wrong_count = EXCLUDED.wrong_count
                """, (model_name, total, exact, winner, wrong))
        
        conn.commit()
        logger.info("Leaderboard rebuilt successfully.")
    finally:
        conn.close()


# ─── FIXTURE EVALUATOR ─────────────────────────────────────────────────────

def evaluate_fixture(fixture_id: int, home_score: int | None = None, away_score: int | None = None) -> int:
    """
    Score all unscored predictions for a specific fixture.
    Optionally accepts real scores to update the fixture table first.
    Returns number of predictions scored.
    """
    conn = get_connection()
    scored_count = 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM fixtures WHERE id=%s", (fixture_id,))
            row = cur.fetchone()
            if not row:
                logger.error(f"Fixture {fixture_id} not found.")
                return 0
            fixture = dict(row)

            # If manual scores provided, lock them in
            if home_score is not None and away_score is not None:
                fixture["real_home_score"] = home_score
                fixture["real_away_score"] = away_score
                fixture["status"] = 'FT'
                cur.execute(
                    "UPDATE fixtures SET real_home_score=%s, real_away_score=%s, status='FT' WHERE id=%s",
                    (home_score, away_score, fixture_id)
                )
                conn.commit()

            if fixture["status"] != 'FT' or fixture["real_home_score"] is None or fixture["real_away_score"] is None:
                logger.warning(f"Fixture {fixture_id} is not FT or missing real scores. Cannot evaluate.")
                return 0

            actual_h = fixture["real_home_score"]
            actual_a = fixture["real_away_score"]

            cur.execute(
                "SELECT id, model_name, predicted_home_score, predicted_away_score "
                "FROM predictions WHERE fixture_id=%s AND points_awarded IS NULL",
                (fixture_id,)
            )
            preds = cur.fetchall()

            for p in preds:
                pid = p["id"]
                pred_h = p["predicted_home_score"]
                pred_a = p["predicted_away_score"]

                logger.info(f"Evaluating {p['model_name']} pred for {fixture_id}: {pred_h}-{pred_a} (Actual: {actual_h}-{actual_a})")

                pts = _calculate_points(pred_h, pred_a, actual_h, actual_a)

                cur.execute(
                    "UPDATE predictions SET points_awarded=%s WHERE id=%s",
                    (pts, pid)
                )
                scored_count += 1

        if scored_count > 0:
            conn.commit()
            logger.info(f"Fixture {fixture_id}: scored {scored_count} predictions.")

    finally:
        conn.close()

    return scored_count

def evaluate_all_pending() -> None:
    """Finds all fixtures with FT real scores but unscored predictions, and scores them."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT f.id
                FROM fixtures f
                JOIN predictions p ON f.id = p.fixture_id
                WHERE p.points_awarded IS NULL
                  AND f.status = 'FT'
                  AND f.real_home_score IS NOT NULL
                  AND f.real_away_score IS NOT NULL
            """)
            fixtures = cur.fetchall()
        
        fids = [f["id"] for f in fixtures]
    finally:
        conn.close()

    total_scored = 0
    for fid in fids:
        total_scored += evaluate_fixture(fid)

import re
from datetime import datetime, timezone, timedelta

def _is_120_mins_past(date_str: str) -> bool:
    if not date_str: return False
    m = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+UTC([+-]\d+)', date_str)
    if m:
        d_str, t_str, offset_str = m.groups()
        try:
            dt = datetime.strptime(f"{d_str} {t_str}", "%Y-%m-%d %H:%M")
            utc_dt = dt - timedelta(hours=int(offset_str))
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= (utc_dt + timedelta(minutes=120))
        except Exception:
            return False
    # Fallback for standard iso dates
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= (dt + timedelta(minutes=120))
    except Exception:
        # Absolute fallback: just check if the date is in the past
        return str(datetime.utcnow().date()) > date_str[:10]

def check_and_evaluate_recent() -> None:
    """Checks the real API for recent match results, updates the DB, and evaluates."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, match_date FROM fixtures WHERE status IN ('NS','TBD')")
            rows = cur.fetchall()
            # Filter matches that have passed the 120 minute threshold
            pending_ids = [r["id"] for r in rows if _is_120_mins_past(r["match_date"])]
    finally:
        conn.close()

    updated = False
    for fid in pending_ids:
        actual = fetch_actual_result(fid)
        if actual and actual["status"] in ("FT", "AET", "PEN"):
            logger.info(f"Found finished match via API for {fid}: {actual['home_score']}-{actual['away_score']}")
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE fixtures SET real_home_score=%s, real_away_score=%s, status='FT' WHERE id=%s",
                        (actual["home_score"], actual["away_score"], fid)
                    )
                conn.commit()
                updated = True
            finally:
                conn.close()
