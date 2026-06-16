import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def remove_vig(odds: list[float]) -> list[float]:
    """
    Remove bookmaker margin from decimal odds to find true implied probabilities.
    Example: 2.00, 3.20, 3.80 -> 1/2.00 + 1/3.20 + 1/3.80 = 0.5 + 0.3125 + 0.2631 = 1.0756 (107.56%)
    True Probs: 0.5/1.0756 = 46.4%, 0.3125/1.0756 = 29.0%, 0.2631/1.0756 = 24.4%
    """
    implied = [1.0 / o for o in odds]
    total_implied = sum(implied)
    return [p / total_implied for p in implied]

def get_blended_probabilities(home_team: str, away_team: str, mc_probs: dict, market_weight: float = 0.65) -> dict:
    """
    Fetches market odds, removes vig, and blends with Monte Carlo probabilities.
    mc_probs: dict containing 'p_home_win', 'p_draw', 'p_away_win' as percentages (0-100).
    """
    api_key = os.getenv("ODDS_API_KEY")
    fallback_probs = {
        "p_home_win": mc_probs.get("p_home_win", 0.0),
        "p_draw": mc_probs.get("p_draw", 0.0),
        "p_away_win": mc_probs.get("p_away_win", 0.0)
    }
    
    if not api_key:
        logger.warning("No ODDS_API_KEY found in .env. Using 100% Monte Carlo weights.")
        return fallback_probs
        
    try:
        url = f"https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/?apiKey={api_key}&regions=eu&markets=h2h"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        games = response.json()
        
        # Match teams
        target_game = None
        for game in games:
            # Simple matching: check if names overlap
            ht_api = game['home_team'].lower()
            at_api = game['away_team'].lower()
            if (home_team.lower() in ht_api or ht_api in home_team.lower()) or \
               (away_team.lower() in ht_api or ht_api in away_team.lower()):
                target_game = game
                break
                
        if not target_game or not target_game.get('bookmakers'):
            logger.warning(f"No odds found for {home_team} vs {away_team}. Using 100% Monte Carlo.")
            return fallback_probs
            
        # Extract H2H odds from the first bookmaker
        bookie = target_game['bookmakers'][0]
        h2h_market = next((m for m in bookie['markets'] if m['key'] == 'h2h'), None)
        
        if not h2h_market:
            return fallback_probs
            
        outcomes = h2h_market['outcomes']
        
        # Depending on naming conventions, exact matching might be tricky. We match substring.
        home_odds = None
        away_odds = None
        draw_odds = None
        
        for o in outcomes:
            name = o['name'].lower()
            if name == 'draw':
                draw_odds = o['price']
            elif home_team.lower() in name or name in home_team.lower():
                home_odds = o['price']
            elif away_team.lower() in name or name in away_team.lower():
                away_odds = o['price']
                
        if not all([home_odds, away_odds, draw_odds]):
            logger.warning(f"Missing specific odds outcomes. Found Home: {home_odds}, Away: {away_odds}, Draw: {draw_odds}. Using fallback.")
            return fallback_probs
            
        # Calculate true probabilities (0 to 1)
        true_h, true_d, true_a = remove_vig([home_odds, draw_odds, away_odds])
        
        market_probs = {
            "p_home_win": true_h * 100.0,
            "p_draw": true_d * 100.0,
            "p_away_win": true_a * 100.0
        }
        
        mc_weight = 1.0 - market_weight
        
        blended = {
            "p_home_win": round(market_probs["p_home_win"] * market_weight + mc_probs["p_home_win"] * mc_weight, 1),
            "p_draw": round(market_probs["p_draw"] * market_weight + mc_probs["p_draw"] * mc_weight, 1),
            "p_away_win": round(market_probs["p_away_win"] * market_weight + mc_probs["p_away_win"] * mc_weight, 1)
        }
        
        logger.info(f"Market Consensus Blended! True Market: H:{market_probs['p_home_win']:.1f} D:{market_probs['p_draw']:.1f} A:{market_probs['p_away_win']:.1f}")
        logger.info(f"Final Blend: H:{blended['p_home_win']} D:{blended['p_draw']} A:{blended['p_away_win']}")
        return blended
        
    except Exception as e:
        logger.warning(f"Failed to fetch or process odds: {e}. Using 100% Monte Carlo.")
        return fallback_probs
