"""
poisson_model.py — Poisson goal-scoring model for World Cup match prediction.

Method
------
  λ_home = home_attack_index × away_defense_index × LEAGUE_AVG × VENUE_FACTOR
  λ_away = away_attack_index × home_defense_index × LEAGUE_AVG

  P(home=i, away=j) = Poisson(λ_home, i) × Poisson(λ_away, j)

The scoreline (i, j) with the highest joint probability is the prediction.
xG from live player data enriches attack λ when available.

World Cup context: neutral venues → VENUE_FACTOR = 1.0 (no home advantage).
"""
import math
import random
from data.scraper import TEAM_BASELINES

LEAGUE_AVG_GOALS = 1.35   # WC historical: ~1.35 goals per team per match
VENUE_FACTOR     = 1.0    # Neutral site
MAX_GOALS        = 8      # Probability matrix ceiling (8×8 grid)

_ATTACKING_POSITIONS = {"ST", "LW", "RW", "CAM", "SS", "CF"}
_MIDFIELD_POSITIONS = {"CM", "CDM", "CAM", "LW", "RW", "LM", "RM"}


# ─── CORE MATH ─────────────────────────────────────────────────────────────

def _poisson_pmf(lam: float, k: int) -> float:
    """P(X = k) for Poisson(λ)."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def _player_xg_lambda(team_name: str, players: list[dict]) -> float | None:
    """
    Estimate team attack λ from live player xG.
    Returns None if data is too sparse to use (all-baseline squads).
    """
    attackers = [
        p for p in players
        if any(pos in (p.get("position") or "") for pos in _ATTACKING_POSITIONS)
    ]
    midfielders = [
        p for p in players
        if any(pos in (p.get("position") or "") for pos in _MIDFIELD_POSITIONS)
    ]
    
    if not attackers and not midfielders:
        return None

    # Forward xG + Midfielder xA
    total_xg = sum(p.get("xG", 0.0) for p in attackers) + sum(p.get("xA", 0.0) for p in midfielders)
    
    if all(p.get("source") == "baseline_fallback" for p in players):
        return None

    base_xg = TEAM_BASELINES.get(team_name, TEAM_BASELINES["Default"])["xG"]
    lam = total_xg * 0.4 + base_xg * 0.6
    return max(0.25, min(lam, 4.0))


def _player_def_lambda(team_name: str, players: list[dict]) -> float | None:
    """
    Estimate defensive modifier from live GK save pct and defender tackles.
    Returns None if data is all baseline.
    """
    gks = [p for p in players if "GK" in (p.get("position") or "")]
    defenders = [p for p in players if any(pos in (p.get("position") or "") for pos in {"CB", "LB", "RB", "LWB", "RWB"})]
    
    if not gks and not defenders:
        return None
    if all(p.get("source") == "baseline_fallback" for p in players):
        return None

    save_pct = sum(p.get("save_pct", 0.0) for p in gks) / max(1, len(gks))
    tackles = sum(p.get("tackles", 0.0) for p in defenders)

    # 75% save pct is average -> boost defense if higher (lower multiplier). 15 tackles is average.
    save_mod = 75.0 / max(50.0, save_pct) if save_pct > 0 else 1.0
    tackles_mod = 15.0 / max(5.0, tackles) if tackles > 0 else 1.0
    
    return (save_mod * 0.6) + (tackles_mod * 0.4)


def _compute_lambdas(
    home_team: str, away_team: str,
    home_players: list[dict], away_players: list[dict],
) -> tuple[float, float]:
    """
    Compute (λ_home, λ_away) using Elo win probability mappings.
    Uses player xG/xA and defensive stats when available.
    """
    hb = TEAM_BASELINES.get(home_team, TEAM_BASELINES["Default"])
    ab = TEAM_BASELINES.get(away_team, TEAM_BASELINES["Default"])

    elo_h = hb.get("elo", 1500)
    elo_a = ab.get("elo", 1500)

    # Calculate Strength of Schedule Elo multiplier (baseline 1800 for WC caliber)
    home_elo_mod = elo_h / 1800.0
    away_elo_mod = elo_a / 1800.0

    # Attack/Defense indices derived from goals + Elo quality adjustment
    home_att = (hb["avg_goals_scored"] / LEAGUE_AVG_GOALS) * home_elo_mod
    home_def = (hb["avg_goals_conceded"] / LEAGUE_AVG_GOALS) / home_elo_mod
    away_att = (ab["avg_goals_scored"] / LEAGUE_AVG_GOALS) * away_elo_mod
    away_def = (ab["avg_goals_conceded"] / LEAGUE_AVG_GOALS) / away_elo_mod

    # Base Poisson lambdas
    lam_home = home_att * away_def * LEAGUE_AVG_GOALS * VENUE_FACTOR
    lam_away = away_att * home_def * LEAGUE_AVG_GOALS

    # Blend in holistic live stats if meaningful data exists
    home_xg_lam = _player_xg_lambda(home_team, home_players)
    away_xg_lam = _player_xg_lambda(away_team, away_players)
    
    home_def_mod = _player_def_lambda(home_team, home_players)
    away_def_mod = _player_def_lambda(away_team, away_players)

    if home_xg_lam is not None:
        lam_home = lam_home * 0.55 + home_xg_lam * 0.45
    if away_xg_lam is not None:
        lam_away = lam_away * 0.55 + away_xg_lam * 0.45
        
    if home_def_mod is not None:
        lam_away *= home_def_mod
    if away_def_mod is not None:
        lam_home *= away_def_mod

    return (
        max(0.2, min(round(lam_home, 4), 4.5)),
        max(0.2, min(round(lam_away, 4), 4.5)),
    )


# ─── PROBABILITY MATRIX ────────────────────────────────────────────────────

def _simulate_match(lam_h: float, lam_a: float, num_simulations: int = 10000, llm_modifiers: dict = None) -> dict:
    if llm_modifiers:
        lam_h *= llm_modifiers.get("home_attack_mod", 1.0) * llm_modifiers.get("away_defense_mod", 1.0)
        lam_a *= llm_modifiers.get("away_attack_mod", 1.0) * llm_modifiers.get("home_defense_mod", 1.0)
        
    base_prob_h_min = lam_h / 90.0
    base_prob_a_min = lam_a / 90.0
    
    outcomes = {}
    
    for _ in range(num_simulations):
        score_h, score_a = 0, 0
        for _ in range(90):
            prob_h = base_prob_h_min
            prob_a = base_prob_a_min
            
            # Game-State Modifiers
            if score_h > score_a:
                prob_h *= 0.85
                prob_a *= (1.20 * 0.90)
            elif score_a > score_h:
                prob_a *= 0.85
                prob_h *= (1.20 * 0.90)
                
            if random.random() < prob_h:
                score_h += 1
            if random.random() < prob_a:
                score_a += 1
                
        score_str = f"{score_h}-{score_a}"
        outcomes[score_str] = outcomes.get(score_str, 0) + 1
        
    # Convert counts to probabilities
    matrix = {k: v / num_simulations for k, v in outcomes.items()}
    
    # Zero-Inflated Poisson (ZIP) correction for defensive matchups
    if lam_h + lam_a < 2.2:
        matrix["0-0"] = matrix.get("0-0", 0.0) + 0.065
        
    total_p = sum(matrix.values())
    matrix = {k: v / total_p for k, v in matrix.items()}
    
    best_prob = -1.0
    best_score = (1, 0)
    p_home_win = p_draw = p_away_win = 0.0
    
    for k, v in matrix.items():
        h, a = map(int, k.split("-"))
        if v > best_prob:
            best_prob = v
            best_score = (h, a)
            
        if h > a: p_home_win += v
        elif h == a: p_draw += v
        else: p_away_win += v
        
        matrix[k] = round(v * 100, 4)
        
    return {
        "lam_home":             round(lam_h, 3),
        "lam_away":             round(lam_a, 3),
        "predicted_home_score": best_score[0],
        "predicted_away_score": best_score[1],
        "best_score_prob_pct":  round(best_prob * 100, 3),
        "p_home_win":           round(p_home_win  * 100, 1),
        "p_draw":               round(p_draw      * 100, 1),
        "p_away_win":           round(p_away_win  * 100, 1),
        "top_scorelines":       _top_n(matrix, 5),
    }


def _top_n(matrix: dict[str, float], n: int) -> list[dict]:
    """Return the N most probable scorelines sorted descending."""
    ranked = sorted(matrix.items(), key=lambda x: x[1], reverse=True)[:n]
    return [{"score": s, "prob_pct": p} for s, p in ranked]


# ─── PUBLIC ENTRY POINT ────────────────────────────────────────────────────

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
        "model_meta": { lam_home, lam_away, confidence, p_home_win, p_draw, p_away_win, ... }
      }
    """
    lam_h, lam_a = _compute_lambdas(home_team, away_team, home_players, away_players)
    result = _simulate_match(lam_h, lam_a, num_simulations=10000, llm_modifiers=llm_modifiers)
    h, a   = result["predicted_home_score"], result["predicted_away_score"]
    winner = home_team if h > a else (away_team if a > h else "Draw")

    return {
        "home_score":      h,
        "away_score":      a,
        "predicted_winner": winner,
        "model_meta": {
            "model":        "poisson_v1",
            "lam_home":     result["lam_home"],
            "lam_away":     result["lam_away"],
            "confidence":   result["best_score_prob_pct"],
            "p_home_win":   result["p_home_win"],
            "p_draw":       result["p_draw"],
            "p_away_win":   result["p_away_win"],
            "top_scorelines": result["top_scorelines"],
        },
    }


if __name__ == "__main__":
    # Quick sanity check without any DB needed
    from scraper import _baseline_squad
    home_p = _baseline_squad("Argentina")
    away_p = _baseline_squad("France")
    result = predict("Argentina", "France", home_p, away_p)
    print(f"Argentina {result['home_score']}-{result['away_score']} France")
    print(f"Winner: {result['predicted_winner']}")
    meta = result["model_meta"]
    print(f"λ_home={meta['lam_home']}  λ_away={meta['lam_away']}  "
          f"confidence={meta['confidence']}%")
    print(f"Probs → Home {meta['p_home_win']}% | Draw {meta['p_draw']}% | Away {meta['p_away_win']}%")
    print("Top scorelines:")
    for s in meta["top_scorelines"]:
        print(f"  {s['score']} → {s['prob_pct']}%")
