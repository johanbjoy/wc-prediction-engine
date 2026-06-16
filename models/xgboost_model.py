"""
xgboost_model.py — XGBoost inference engine for World Cup 2026.

Loads pre-trained XGBRegressor models (home_score, away_score) and exposes
the same `predict()` interface as the Monte Carlo Poisson model to maintain
full backward compatibility with orchestrator.py and evaluator.py.
"""
import os
import logging
import numpy as np
from xgboost import XGBRegressor
from data.scraper import TEAM_BASELINES

logger = logging.getLogger(__name__)

# ─── MODEL LOADING ─────────────────────────────────────────────────────────
_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved")
_model_home = None
_model_away = None


def _load_models():
    """Lazy-load the pre-trained XGBoost models on first inference call."""
    global _model_home, _model_away

    if _model_home is not None:
        return

    home_path = os.path.join(_MODELS_DIR, "xgb_home.json")
    away_path = os.path.join(_MODELS_DIR, "xgb_away.json")

    if not os.path.exists(home_path) or not os.path.exists(away_path):
        raise FileNotFoundError(
            f"Pre-trained models not found at {_MODELS_DIR}/. "
            f"Run `python3 train_xgboost.py` first."
        )

    _model_home = XGBRegressor()
    _model_home.load_model(home_path)

    _model_away = XGBRegressor()
    _model_away.load_model(away_path)

    logger.info("XGBoost models loaded from disk.")


# ─── FEATURE EXTRACTION ───────────────────────────────────────────────────

def _extract_features(home_team: str, away_team: str,
                      home_players: list[dict], away_players: list[dict]) -> dict:
    """
    Build the same feature vector used during training.
    Uses TEAM_BASELINES for Elo and form, enriched with live player data.
    """
    hb = TEAM_BASELINES.get(home_team, TEAM_BASELINES["Default"])
    ab = TEAM_BASELINES.get(away_team, TEAM_BASELINES["Default"])

    elo_home = hb.get("elo", 1800)
    elo_away = ab.get("elo", 1800)

    # Use live player form if available, otherwise use baseline
    if home_players:
        form_home = np.mean([p.get("form_metric", hb["form"]) for p in home_players[:11]])
    else:
        form_home = hb["form"]

    if away_players:
        form_away = np.mean([p.get("form_metric", ab["form"]) for p in away_players[:11]])
    else:
        form_away = ab["form"]

    # Normalize form from (0-10 scale) to points-per-game scale (0-3)
    form_home_ppg = (form_home / 10.0) * 3.0
    form_away_ppg = (form_away / 10.0) * 3.0

    return {
        "elo_home": elo_home,
        "elo_away": elo_away,
        "elo_diff": elo_home - elo_away,
        "form_home": form_home_ppg,
        "form_away": form_away_ppg,
        "form_diff": form_home_ppg - form_away_ppg,
        "is_neutral": 1,  # World Cup = always neutral venue
    }


# ─── PUBLIC ENTRY POINT ───────────────────────────────────────────────────

def predict(
    home_team: str, away_team: str,
    home_players: list[dict], away_players: list[dict],
    llm_modifiers: dict = None
) -> dict:
    """
    Public interface matching orchestrator's JSON contract.

    Returns:
      {
        "home_score": int,
        "away_score": int,
        "predicted_winner": str,
        "model_meta": { model, raw_home_xg, raw_away_xg, features_used, ... }
      }
    """
    _load_models()

    features = _extract_features(home_team, away_team, home_players, away_players)

    # Build numpy array in the exact column order used during training
    feature_cols = ["elo_home", "elo_away", "elo_diff", "form_home", "form_away", "form_diff", "is_neutral"]
    X = np.array([[features[c] for c in feature_cols]])

    raw_home_xg = float(_model_home.predict(X)[0])
    raw_away_xg = float(_model_away.predict(X)[0])

    # Apply LLM tactical modifiers (same interface as Poisson model)
    if llm_modifiers:
        raw_home_xg *= llm_modifiers.get("home_attack_mod", 1.0) * llm_modifiers.get("away_defense_mod", 1.0)
        raw_away_xg *= llm_modifiers.get("away_attack_mod", 1.0) * llm_modifiers.get("home_defense_mod", 1.0)

    # Clamp to non-negative and round to nearest integer
    home_score = max(0, round(raw_home_xg))
    away_score = max(0, round(raw_away_xg))

    if home_score > away_score:
        winner = home_team
    elif away_score > home_score:
        winner = away_team
    else:
        winner = "Draw"

    # Estimate win probabilities from the raw xG gap
    # Using a simple logistic approximation based on xG difference
    xg_diff = raw_home_xg - raw_away_xg
    p_home = 1.0 / (1.0 + np.exp(-0.8 * xg_diff)) * 100
    p_away = (1.0 - p_home / 100.0) * 0.72 * 100  # scale to leave room for draw
    p_draw = 100.0 - p_home - p_away

    # Normalize if rounding causes drift
    total = p_home + p_draw + p_away
    p_home = round(p_home / total * 100, 1)
    p_draw = round(p_draw / total * 100, 1)
    p_away = round(100.0 - p_home - p_draw, 1)

    return {
        "home_score": home_score,
        "away_score": away_score,
        "predicted_winner": winner,
        "model_meta": {
            "model": "xgboost_v1",
            "raw_home_xg": round(raw_home_xg, 3),
            "raw_away_xg": round(raw_away_xg, 3),
            "lam_home": round(raw_home_xg, 3),
            "lam_away": round(raw_away_xg, 3),
            "confidence": round(max(p_home, p_draw, p_away), 1),
            "p_home_win": p_home,
            "p_draw": p_draw,
            "p_away_win": p_away,
            "features_used": features,
            "top_scorelines": [
                {"score": f"{home_score}-{away_score}", "prob_pct": round(max(p_home, p_draw, p_away), 1)},
            ],
        },
    }


if __name__ == "__main__":
    from data.scraper import _baseline_squad

    home_p = _baseline_squad("Argentina")
    away_p = _baseline_squad("France")
    result = predict("Argentina", "France", home_p, away_p)
    print(f"Argentina {result['home_score']}-{result['away_score']} France")
    print(f"Winner: {result['predicted_winner']}")
    meta = result["model_meta"]
    print(f"Raw xG: Home={meta['raw_home_xg']}  Away={meta['raw_away_xg']}")
    print(f"Probs → Home {meta['p_home_win']}% | Draw {meta['p_draw']}% | Away {meta['p_away_win']}%")
    print(f"Features: {meta['features_used']}")
