"""
tournament_form.py — Live tournament form data from wcup2026.org free API.

Fetches real-time standings and match stats to compute a "tournament form
modifier" that adjusts predictions based on how teams are ACTUALLY performing
in this World Cup vs their pre-tournament Elo expectations.

Key insight: Our 9 wrong predictions are mostly draws/upsets where strong
teams underperformed. Static Elo can't detect this — but live standings can.

Data source: https://wcup2026.org/api/data.php (free, no API key, CORS enabled)
"""
import logging
import requests
from functools import lru_cache

logger = logging.getLogger(__name__)

WCUP_API_BASE = "https://wcup2026.org/api/data.php"


def _fetch_standings() -> dict:
    """Fetch live standings from wcup2026.org. Returns dict keyed by team name."""
    try:
        resp = requests.get(f"{WCUP_API_BASE}?action=standings", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("ok"):
            logger.warning("wcup2026 API returned ok=false for standings")
            return {}
        
        # Flatten all groups into one dict keyed by team name
        teams = {}
        for group_name, rows in data.get("standings", {}).items():
            for row in rows:
                teams[row["team"]] = {
                    "played": row.get("p", 0),
                    "wins": row.get("w", 0),
                    "draws": row.get("d", 0),
                    "losses": row.get("l", 0),
                    "gf": row.get("gf", 0),
                    "ga": row.get("ga", 0),
                    "gd": row.get("gd", 0),
                    "pts": row.get("pts", 0),
                    "group": group_name,
                }
        
        logger.info(f"wcup2026 API: fetched standings for {len(teams)} teams")
        return teams
    except Exception as e:
        logger.warning(f"Failed to fetch wcup2026 standings: {e}")
        return {}


def _fetch_match_stats(match_id: int) -> dict | None:
    """Fetch detailed match stats (shots, possession, saves) for a specific match."""
    try:
        resp = requests.get(f"{WCUP_API_BASE}?action=match&id={match_id}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("ok"):
            return None
            
        match = data.get("match", {})
        stats_list = match.get("stats", [])
        
        # Parse stats into a clean dict
        stats = {}
        for s in stats_list:
            key = s.get("k_en", "").lower().replace(" ", "_")
            if key and s.get("v"):
                stats[key] = s["v"]  # [team1_val, team2_val]
        
        return {
            "team1": match.get("team1"),
            "team2": match.get("team2"),
            "score": match.get("score"),
            "stats": stats,
        }
    except Exception as e:
        logger.warning(f"Failed to fetch match {match_id} stats: {e}")
        return None


def get_tournament_form(team_name: str) -> dict:
    """
    Calculate a tournament form modifier for a team based on live standings.
    
    Returns:
        {
            "form_modifier": float,  # Multiplier for the Elo boost (0.5 = halved, 1.0 = unchanged, 1.5 = boosted)
            "goals_per_game": float, # Actual goals per game in tournament
            "conceded_per_game": float,
            "pts_per_game": float,
            "played": int,
        }
    """
    standings = _fetch_standings()
    
    if not standings or team_name not in standings:
        # No data available — return neutral modifier
        return {"form_modifier": 1.0, "goals_per_game": 0, "conceded_per_game": 0, "pts_per_game": 0, "played": 0}
    
    team = standings[team_name]
    played = team["played"]
    
    if played == 0:
        return {"form_modifier": 1.0, "goals_per_game": 0, "conceded_per_game": 0, "pts_per_game": 0, "played": 0}
    
    # Calculate actual performance metrics
    pts_per_game = team["pts"] / played
    goals_per_game = team["gf"] / played
    conceded_per_game = team["ga"] / played
    
    # Tournament form modifier logic (dampen-only — never boost above 1.0):
    # - A team averaging 3 pts/game (all wins) → unchanged (1.0)
    # - A team averaging 1 pt/game (all draws) → dampened (0.73)
    # - A team averaging 0 pts/game (all losses) → heavily dampened (0.5)
    # Boosting winners was tested and caused score inflation (8-1 instead of 5-1)
    
    # Normalize: 0 pts → 0.5, 1 pt → 0.73, 3 pts → 1.0 (capped)
    form_modifier = 0.5 + (pts_per_game / 3.0) * 0.5
    form_modifier = max(0.5, min(1.0, form_modifier))
    
    # Also factor in goal difference — teams conceding a lot should be dampened
    # If conceding more than 2 per game, dampen further
    if conceded_per_game > 2.0:
        form_modifier *= 0.9
    
    # If scoring 0 per game but expected to be strong, dampen heavily
    if goals_per_game == 0 and played >= 1:
        form_modifier *= 0.8
    
    return {
        "form_modifier": round(form_modifier, 3),
        "goals_per_game": round(goals_per_game, 2),
        "conceded_per_game": round(conceded_per_game, 2),
        "pts_per_game": round(pts_per_game, 2),
        "played": played,
    }


def get_all_tournament_form() -> dict:
    """Get tournament form for all teams at once (single API call)."""
    standings = _fetch_standings()
    result = {}
    
    for team_name, team in standings.items():
        played = team["played"]
        if played == 0:
            result[team_name] = {"form_modifier": 1.0, "played": 0}
            continue
            
        pts_per_game = team["pts"] / played
        goals_per_game = team["gf"] / played
        conceded_per_game = team["ga"] / played
        
        form_modifier = 0.5 + (pts_per_game / 3.0) * 0.5
        form_modifier = max(0.5, min(1.0, form_modifier))
        
        if conceded_per_game > 2.0:
            form_modifier *= 0.9
        if goals_per_game == 0 and played >= 1:
            form_modifier *= 0.8
            
        result[team_name] = {
            "form_modifier": round(form_modifier, 3),
            "goals_per_game": round(goals_per_game, 2),
            "conceded_per_game": round(conceded_per_game, 2),
            "pts_per_game": round(pts_per_game, 2),
            "played": played,
            "gd": team["gd"],
        }
    
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    from data.scraper import TEAM_BASELINES
    
    forms = get_all_tournament_form()
    
    print("=" * 75)
    print(f"  LIVE TOURNAMENT FORM — {len(forms)} teams")
    print("=" * 75)
    print(f"  {'TEAM':<25} {'ELO':>5} {'P':>3} {'PPG':>5} {'GPG':>5} {'CPG':>5} {'GD':>4} {'MODIFIER':>8}")
    print("  " + "─" * 65)
    
    for team, data in sorted(forms.items(), key=lambda x: -x[1].get("form_modifier", 1.0)):
        elo = TEAM_BASELINES.get(team, TEAM_BASELINES.get("Default", {})).get("elo", "?")
        mod = data["form_modifier"]
        marker = "🔥" if mod > 1.0 else ("⚠️" if mod < 0.8 else "  ")
        print(f"  {team:<25} {elo:>5} {data['played']:>3} {data.get('pts_per_game',0):>5.1f} {data.get('goals_per_game',0):>5.1f} {data.get('conceded_per_game',0):>5.1f} {data.get('gd',0):>4} {mod:>7.3f} {marker}")
