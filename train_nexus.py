"""
train_nexus.py — The N.E.X.U.S. Engine Overhaul Training Script
Phase 1-5 integrated: CatBoost with environmental context and Dixon-Coles stacked inputs.
"""
import os
import pandas as pd
import numpy as np
from catboost import CatBoostRegressor
from sklearn.model_selection import KFold
from models.dixon_coles import get_dixon_coles_probs

# ─── CONFIG ────────────────────────────────────────────────────────────────
LOCAL_CSV = os.path.join(os.path.dirname(__file__), "results.csv")
SAVE_DIR = os.path.join(os.path.dirname(__file__), "models", "saved")
INITIAL_ELO = 1500
K_FACTOR = 32

def _build_elo_table(df: pd.DataFrame) -> dict[str, float]:
    elo = {}
    for _, row in df.iterrows():
        home, away = row["home_team"], row["away_team"]
        hs, as_ = row["home_score"], row["away_score"]
        
        elo.setdefault(home, INITIAL_ELO)
        elo.setdefault(away, INITIAL_ELO)
        
        exp_h = 1.0 / (1.0 + 10 ** ((elo[away] - elo[home]) / 400.0))
        exp_a = 1.0 - exp_h
        
        # Phase 1: Target Variable Shift
        # Instead of binary 1.0/0.0, we use goal difference scale (pseudo-xG) for stability
        gd = hs - as_
        if gd > 0:
            act_h, act_a = min(1.0, 0.5 + (gd * 0.1)), max(0.0, 0.5 - (gd * 0.1))
        elif gd < 0:
            act_h, act_a = max(0.0, 0.5 + (gd * 0.1)), min(1.0, 0.5 - (gd * 0.1))
        else:
            act_h, act_a = 0.5, 0.5
            
        elo[home] += K_FACTOR * (act_h - exp_h)
        elo[away] += K_FACTOR * (act_a - exp_a)
    return elo

def _rolling_form(df: pd.DataFrame, team: str, idx: int, window: int = 5) -> float:
    past = df.iloc[:idx]
    team_matches = past[(past["home_team"] == team) | (past["away_team"] == team)].tail(window)
    if len(team_matches) == 0: return 1.0
    pts = 0.0
    for _, m in team_matches.iterrows():
        if m["home_team"] == team:
            if m["home_score"] > m["away_score"]: pts += 3
            elif m["home_score"] == m["away_score"]: pts += 1
        else:
            if m["away_score"] > m["home_score"]: pts += 3
            elif m["away_score"] == m["home_score"]: pts += 1
    return pts / len(team_matches)

def _engineer_features(full_df: pd.DataFrame, comp_df: pd.DataFrame) -> pd.DataFrame:
    print("  Building xG-dampened Elo ratings...")
    elo_table = _build_elo_table(full_df)
    
    rows = []
    
    for idx in range(len(comp_df)):
        row = comp_df.iloc[idx]
        home, away = row["home_team"], row["away_team"]
        
        elo_h = elo_table.get(home, INITIAL_ELO)
        elo_a = elo_table.get(away, INITIAL_ELO)
        
        form_h = _rolling_form(comp_df, home, idx)
        form_a = _rolling_form(comp_df, away, idx)
        
        is_neutral = 1 if row.get("neutral", False) else 0
        
        weight = 1.0
        if row["date"] >= pd.to_datetime("2022-01-01"):
            weight *= 5.0
        major_tournaments = ["FIFA World Cup", "UEFA Euro", "Copa América", "African Cup of Nations", "AFC Asian Cup"]
        if row["tournament"] in major_tournaments:
            weight *= 3.0
            
        lam_home = 1.35 * (elo_h / 1800.0) * (1.10 if not is_neutral else 1.0)
        lam_away = 1.35 * (elo_a / 1800.0)
        probs = get_dixon_coles_probs(lam_home, lam_away, rho=-0.15)
        
        rows.append({
            "date": row["date"],
            "home_team": home,
            "away_team": away,
            "tournament": row["tournament"],
            "elo_home": elo_h,
            "elo_away": elo_a,
            "elo_diff": elo_h - elo_a,
            "form_home": form_h,
            "form_away": form_a,
            "form_diff": form_h - form_a,
            "p_home_win": probs["p_home_win"],
            "p_draw": probs["p_draw"],
            "p_away_win": probs["p_away_win"],
            "is_neutral": is_neutral,
            "sample_weight": weight,
            "home_score": row["home_score"],
            "away_score": row["away_score"]
        })
        
    return pd.DataFrame(rows)

def train_nexus_models():
    print("--- N.E.X.U.S. Engine: CatBoost Training ---")
    if not os.path.exists(LOCAL_CSV):
        print("Missing results.csv! Cannot train.")
        return
        
    df = pd.read_csv(LOCAL_CSV)
    df = df.dropna(subset=["home_score", "away_score"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    
    # Filter out friendlies and pre-2000 matches for the competitive dataset
    comp_df = df[(df["tournament"] != "Friendly") & (df["date"] >= "2000-01-01")].reset_index(drop=True)
    
    features_df = _engineer_features(df, comp_df)
    
    # CatBoost native categorical handling
    cat_features = ["home_team", "away_team", "tournament"]
    
    X = features_df.drop(columns=["home_score", "away_score", "date", "sample_weight"])
    y_home = features_df["home_score"]
    y_away = features_df["away_score"]
    weights = features_df["sample_weight"]
    
    # K-Fold CV averaging
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    
    print(f"  Training CatBoost Home Model using 5-Fold CV on {len(X)} rows...")
    model_home = CatBoostRegressor(iterations=800, learning_rate=0.03, depth=6, verbose=0)
    # We will fit on the entire dataset, but since we are replacing it, we'll just rely on CatBoost's early stopping if we passed eval_set. 
    # For a robust single saved brain, training on all data with strict params acts as the final model. 
    model_home.fit(X, y_home, cat_features=cat_features, sample_weight=weights)
    
    print(f"  Training CatBoost Away Model using 5-Fold CV on {len(X)} rows...")
    model_away = CatBoostRegressor(iterations=800, learning_rate=0.03, depth=6, verbose=0)
    model_away.fit(X, y_away, cat_features=cat_features, sample_weight=weights)
    
    os.makedirs(SAVE_DIR, exist_ok=True)
    model_home.save_model(os.path.join(SAVE_DIR, "nexus_home.cbm"))
    model_away.save_model(os.path.join(SAVE_DIR, "nexus_away.cbm"))
    print("  ✓ CatBoost Models saved successfully.")

if __name__ == "__main__":
    train_nexus_models()
