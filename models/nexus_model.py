"""
nexus_model.py — The N.E.X.U.S. Stacked Predictor
Runs Phase 5 Stacked Meta-Learner logic using CatBoost, Dixon-Coles, and Environmental context.
"""
import os
import pandas as pd
from catboost import CatBoostRegressor
from models.poisson_model import predict as get_poisson_baseline
from models.dixon_coles import get_dixon_coles_probs
from data.database import get_connection

# Elite feature imports
from data.weather import get_weather_factor
from data.transfermarkt import get_team_value_ratio
from data.scraper import get_h2h_streak, has_coach_changed_tactics

try:
    from models.transformer_model import TransformerModel
    TRANSFORMER_AVAILABLE = True
except ImportError:
    TRANSFORMER_AVAILABLE = False

def _calculate_rest_days(team: str, current_match_date: str) -> float:
    """Calculates schedule congestion (days since last match)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT match_date FROM fixtures 
                WHERE (home_team = %s OR away_team = %s) 
                AND status IN ('FT', 'AET', 'PEN')
                ORDER BY match_date DESC LIMIT 1
            """, (team, team))
            row = cur.fetchone()
            if not row:
                return 7.0 # Default to 1 week rest if no prior matches
            
            # Simple approximation of rest days using string dates
            try:
                last_date = pd.to_datetime(row["match_date"].split(" UTC")[0])
                curr_date = pd.to_datetime(current_match_date.split(" UTC")[0])
                diff = (curr_date - last_date).days
                return float(max(0, diff))
            except Exception:
                return 7.0
    finally:
        conn.close()

def predict(home_team: str, away_team: str, tournament: str, current_date: str, elo_home: float, elo_away: float, form_h: float, form_a: float) -> dict:
    home_model_path = os.path.join(os.path.dirname(__file__), "saved", "nexus_home.cbm")
    away_model_path = os.path.join(os.path.dirname(__file__), "saved", "nexus_away.cbm")
    
    # 1. Gather baseline Poisson xG
    # We pass empty player lists since poisson_model uses baseline if players are missing
    poi_res = get_poisson_baseline(home_team, away_team, [], [])
    meta = poi_res.get("model_meta", {})
    lam_home = meta.get("lam_home", 1.0)
    lam_away = meta.get("lam_away", 1.0)
    
    # 2. Phase 2: Dixon-Coles Probabilities
    dc_probs = get_dixon_coles_probs(lam_home, lam_away)
    
    # 3. Phase 4: Environmental Features
    rest_home = _calculate_rest_days(home_team, current_date)
    rest_away = _calculate_rest_days(away_team, current_date)
    
    # 4. Phase 5: Stacked CatBoost Prediction (Poisson probabilities mathematically stacked in)
    features = pd.DataFrame([{
        "home_team": home_team,
        "away_team": away_team,
        "tournament": tournament,
        "elo_home": elo_home,
        "elo_away": elo_away,
        "elo_diff": elo_home - elo_away,
        "form_home": form_h,
        "form_away": form_a,
        "form_diff": form_h - form_a,
        "p_home_win": dc_probs["p_home_win"],
        "p_draw": dc_probs["p_draw"],
        "p_away_win": dc_probs["p_away_win"],
        "is_neutral": 1, # Assume World Cup is neutral for most
        "team_value_ratio": get_team_value_ratio(home_team, away_team),
        "h2h_streak": get_h2h_streak(home_team, away_team),
        "momentum_decay": form_h * (1.0 / max(1.0, rest_home)),
        "weather_factor": get_weather_factor("New York"), # Placeholder for WC city
        "coach_tactic": has_coach_changed_tactics(home_team)
    }])
    
    # Try Transformer First (Phase 4)
    pt_home_path = os.path.join(os.path.dirname(__file__), "saved", "nexus_home.pt")
    pt_away_path = os.path.join(os.path.dirname(__file__), "saved", "nexus_away.pt")
    
    if TRANSFORMER_AVAILABLE and os.path.exists(pt_home_path) and os.path.exists(pt_away_path):
        try:
            # We must drop cat features since our custom transformer only takes numerical features
            num_features = features.drop(columns=["home_team", "away_team", "tournament"])
            
            t_home = TransformerModel()
            t_home.load_weights(pt_home_path)
            t_away = TransformerModel()
            t_away.load_weights(pt_away_path)
            
            pred_home = max(0.0, float(t_home.predict(num_features)[0]))
            pred_away = max(0.0, float(t_away.predict(num_features)[0]))
            
            # Phase 7: Apply Dynamic Adaptive Momentum
            from data.database import get_team_momentum
            h_mom = get_team_momentum(home_team)
            a_mom = get_team_momentum(away_team)
            
            # Apply momentum to xG
            pred_home *= h_mom
            pred_away *= a_mom
            
            # Adjust probabilities slightly based on new xG (rough approximation)
            dc_probs["p_home_win"] *= (h_mom / ((h_mom + a_mom)/2))
            dc_probs["p_away_win"] *= (a_mom / ((h_mom + a_mom)/2))
            
            # Normalize
            total = dc_probs["p_home_win"] + dc_probs["p_draw"] + dc_probs["p_away_win"]
            dc_probs["p_home_win"] /= total
            dc_probs["p_draw"] /= total
            dc_probs["p_away_win"] /= total
            
            return {
                "nexus_home_xg": float(pred_home),
                "nexus_away_xg": float(pred_away),
                "dixon_coles_probs": dc_probs,
                "env_context": {"rest_home": rest_home, "rest_away": rest_away},
                "model_used": "pytorch_transformer"
            }
        except Exception as e:
            print(f"Transformer fallback: {e}")

    # Fallback to CatBoost
    try:
        model_home = CatBoostRegressor().load_model(home_model_path)
        model_away = CatBoostRegressor().load_model(away_model_path)
    except Exception as e:
        print(f"Failed to load N.E.X.U.S CatBoost models: {e}")
        return {}
        
    pred_home = max(0.0, float(model_home.predict(features)[0]))
    pred_away = max(0.0, float(model_away.predict(features)[0]))
    
        # Phase 7: Apply Dynamic Adaptive Momentum
        from data.database import get_team_momentum
        h_mom = get_team_momentum(home_team)
        a_mom = get_team_momentum(away_team)
        
        # Apply momentum to xG
        pred_home *= h_mom
        pred_away *= a_mom
        
        # Adjust probabilities slightly based on new xG (rough approximation)
        dc_probs["p_home_win"] *= (h_mom / ((h_mom + a_mom)/2))
        dc_probs["p_away_win"] *= (a_mom / ((h_mom + a_mom)/2))
        
        # Normalize
        total = dc_probs["p_home_win"] + dc_probs["p_draw"] + dc_probs["p_away_win"]
        dc_probs["p_home_win"] /= total
        dc_probs["p_draw"] /= total
        dc_probs["p_away_win"] /= total
        
        return {
            "nexus_home_xg": float(pred_home),
            "nexus_away_xg": float(pred_away),
            "dixon_coles_probs": dc_probs,
            "env_context": {"rest_home": rest_home, "rest_away": rest_away},
            "model_used": "catboost_v2"
        }
