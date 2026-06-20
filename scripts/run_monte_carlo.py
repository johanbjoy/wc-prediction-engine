import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import os
import random
import time
from collections import defaultdict

from models.nexus_model import predict
from data.database import get_connection

# Projected Top 48 Teams for 2026
TEAMS = [
    "Argentina", "France", "Brazil", "England", "Belgium", "Portugal", "Netherlands", "Spain",
    "Italy", "Croatia", "Uruguay", "USA", "Morocco", "Colombia", "Mexico", "Germany",
    "Japan", "Switzerland", "Denmark", "Senegal", "Iran", "South Korea", "Australia", "Ukraine",
    "Austria", "Sweden", "Poland", "Wales", "Hungary", "Serbia", "Peru", "Scotland",
    "Turkey", "Ecuador", "Chile", "Tunisia", "Algeria", "Egypt", "Nigeria", "Cameroon",
    "Canada", "Mali", "Ivory Coast", "Saudi Arabia", "Qatar", "Panama", "Costa Rica", "New Zealand"
]

def get_elo(team):
    base = 1500
    if team in ["Argentina", "France", "Brazil", "England"]: base = 2000
    elif team in ["Spain", "Portugal", "Germany", "Belgium"]: base = 1900
    elif team in ["Netherlands", "Uruguay", "Croatia", "Italy"]: base = 1850
    return base + random.randint(-50, 50)

# Memory Cache for predictions to avoid repeating expensive ML model loads & DB calls
PREDICTION_CACHE = {}

from models.poisson_model import _compute_lambdas
from models.dixon_coles import get_dixon_coles_probs
import pandas as pd
from catboost import CatBoostRegressor

_CATBOOST_HOME = None
_CATBOOST_AWAY = None

def get_cached_prediction(home, away, stage="Group Stage"):
    global _CATBOOST_HOME, _CATBOOST_AWAY
    key = f"{home}_vs_{away}"
    if key in PREDICTION_CACHE:
        return PREDICTION_CACHE[key]
        
    if _CATBOOST_HOME is None:
        _CATBOOST_HOME = CatBoostRegressor().load_model(os.path.join("data_store", "models", "nexus_home.cbm"))
        _CATBOOST_AWAY = CatBoostRegressor().load_model(os.path.join("data_store", "models", "nexus_away.cbm"))

    elo_h = get_elo(home)
    elo_a = get_elo(away)
    
    # Fast Poisson
    lam_h, lam_a = _compute_lambdas(home, away, [], [])
    poi_probs = get_dixon_coles_probs(lam_h, lam_a)
    
    # Fast CatBoost
    features = pd.DataFrame([{
        "home_team": home, "away_team": away, "tournament": "World Cup 2026",
        "elo_home": elo_h, "elo_away": elo_a, "elo_diff": elo_h - elo_a,
        "form_home": 1.5, "form_away": 1.5, "form_diff": 0,
        "p_home_win": poi_probs["p_home_win"], "p_draw": poi_probs["p_draw"], "p_away_win": poi_probs["p_away_win"],
        "is_neutral": 1, "team_value_ratio": 1.0, "h2h_streak": 0,
        "momentum_decay": 1.0, "weather_factor": 1.0, "coach_tactic": 0
    }])
    
    pred_h = max(0.0, float(_CATBOOST_HOME.predict(features)[0]))
    pred_a = max(0.0, float(_CATBOOST_AWAY.predict(features)[0]))
    
    cat_probs = get_dixon_coles_probs(pred_h, pred_a, rho=-0.15)
    
    # Advanced Blending (RPS Weights)
    W_CAT = 0.65
    W_POI = 0.35
    
    prob_h = (cat_probs["p_home_win"] * W_CAT + poi_probs["p_home_win"] * W_POI) / 100.0
    prob_d = (cat_probs["p_draw"] * W_CAT + poi_probs["p_draw"] * W_POI) / 100.0
    prob_a = (cat_probs["p_away_win"] * W_CAT + poi_probs["p_away_win"] * W_POI) / 100.0
    
    total = prob_h + prob_d + prob_a
    if total == 0:
        prob_h, prob_d, prob_a = 0.33, 0.33, 0.34
    else:
        prob_h, prob_d, prob_a = prob_h/total, prob_d/total, prob_a/total
        
    PREDICTION_CACHE[key] = (prob_h, prob_d, prob_a)
    return prob_h, prob_d, prob_a

def sample_match_outcome(home, away, stage):
    """Probabilistically samples an outcome based on blended probabilities."""
    ph, pd, pa = get_cached_prediction(home, away, stage)
    
    r = random.random()
    if r < ph:
        winner = home
        pts_h, pts_a = 3, 0
    elif r < ph + pd:
        winner = "Draw"
        pts_h, pts_a = 1, 1
    else:
        winner = away
        pts_h, pts_a = 0, 3
        
    # If knockout and draw, coin flip penalty shootout
    if stage != "Group Stage" and winner == "Draw":
        winner = home if random.random() > 0.5 else away
        
    return winner, pts_h, pts_a

def run_single_simulation(groups):
    standings = {t: 0 for t in TEAMS} # Just track points for speed
    
    # Group Stage
    for g_name, g_teams in groups.items():
        for i in range(len(g_teams)):
            for j in range(i+1, len(g_teams)):
                h, a = g_teams[i], g_teams[j]
                winner, pts_h, pts_a = sample_match_outcome(h, a, "Group Stage")
                standings[h] += pts_h
                standings[a] += pts_a

    advancing = []
    third_places = []
    
    for g_name, g_teams in groups.items():
        # Sort by points. In ties, use random choice (simulating GD/H2H ties randomly for speed)
        sorted_g = sorted(g_teams, key=lambda t: standings[t] + random.random()*0.1, reverse=True)
        advancing.append(sorted_g[0])
        advancing.append(sorted_g[1])
        third_places.append(sorted_g[2])
        
    third_places = sorted(third_places, key=lambda t: standings[t] + random.random()*0.1, reverse=True)
    advancing.extend(third_places[:8])
    
    random.shuffle(advancing)
    
    # Track stage reached
    stage_reached = {t: "Group Stage" for t in TEAMS}
    for t in advancing:
        stage_reached[t] = "Round of 32"
        
    stages = [
        ("Round of 32", "Round of 16"),
        ("Round of 16", "Quarter Finals"),
        ("Quarter Finals", "Semi Finals"),
        ("Semi Finals", "Final"),
        ("Final", "Champion")
    ]
    
    current_teams = advancing
    
    for current_stage_name, next_stage_name in stages:
        next_teams = []
        for i in range(0, len(current_teams), 2):
            h, a = current_teams[i], current_teams[i+1]
            winner, _, _ = sample_match_outcome(h, a, current_stage_name)
            next_teams.append(winner)
            stage_reached[winner] = next_stage_name
            
        current_teams = next_teams
        if len(current_teams) == 1:
            break
            
    return stage_reached, current_teams[0]

def run_monte_carlo(iterations=1000):
    print(f"Running Monte Carlo Tournament Simulation ({iterations} iterations)...")
    
    # Fixed groups for the simulation so teams face the same initial paths
    random.seed(42) # Deterministic group draw for consistency
    shuffled_teams = TEAMS.copy()
    random.shuffle(shuffled_teams)
    groups = {f"Group {chr(65+i)}": shuffled_teams[i*4:(i+1)*4] for i in range(12)}
    
    results = {
        t: {
            "Champion": 0,
            "Final": 0,
            "Semi Finals": 0,
            "Quarter Finals": 0,
            "Round of 16": 0,
            "Round of 32": 0,
            "Group Stage": 0
        } for t in TEAMS
    }
    
    # Pre-warm cache for all group matches to show progress bar properly
    print("Pre-warming ML Prediction Cache...")
    for g_teams in groups.values():
        for i in range(len(g_teams)):
            for j in range(i+1, len(g_teams)):
                get_cached_prediction(g_teams[i], g_teams[j], "Group Stage")
                
    start_time = time.time()
    for i in range(iterations):
        if i % 100 == 0:
            print(f"Iteration {i}/{iterations}...")
        # Re-seed with none so simulations are random
        random.seed(None)
        stage_reached, champion = run_single_simulation(groups)
        
        for t, stage in stage_reached.items():
            results[t][stage] += 1
            
    print(f"Completed in {time.time() - start_time:.2f} seconds.")
    
    # Calculate probabilities
    mc_data = []
    for t in TEAMS:
        mc_data.append({
            "team": t,
            "win_prob": results[t]["Champion"] / iterations,
            "final_prob": (results[t]["Champion"] + results[t]["Final"]) / iterations,
            "semi_prob": (results[t]["Champion"] + results[t]["Final"] + results[t]["Semi Finals"]) / iterations,
            "knockout_prob": 1.0 - (results[t]["Group Stage"] / iterations)
        })
        
    mc_data = sorted(mc_data, key=lambda x: x["win_prob"], reverse=True)
    
    with open("data_store/databases/monte_carlo_results.json", "w") as f:
        json.dump({"iterations": iterations, "data": mc_data}, f, indent=4)
        
    print("Saved Monte Carlo results to data_store/databases/monte_carlo_results.json")

if __name__ == "__main__":
    run_monte_carlo(1000)
