"""
train_xgboost.py — XGBoost training pipeline for World Cup 2026.

Ingests historical international football results, engineers Elo-based
features, and trains two XGBRegressor models (home_score, away_score).

Usage:
    python3 train_xgboost.py

Outputs:
    models/saved/xgb_home.json
    models/saved/xgb_away.json
"""
import os
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

# ─── CONFIG ────────────────────────────────────────────────────────────────
DATA_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
LOCAL_CSV = os.path.join(os.path.dirname(__file__), "results.csv")
SAVE_DIR = os.path.join(os.path.dirname(__file__), "models", "saved")
INITIAL_ELO = 1500
K_FACTOR = 32


# ─── ELO CALCULATOR ───────────────────────────────────────────────────────

def _build_elo_table(df: pd.DataFrame) -> dict[str, float]:
    """Walk through every match chronologically and compute live Elo ratings."""
    elo = {}

    for _, row in df.iterrows():
        home, away = row["home_team"], row["away_team"]
        hs, as_ = row["home_score"], row["away_score"]

        elo.setdefault(home, INITIAL_ELO)
        elo.setdefault(away, INITIAL_ELO)

        # Expected scores
        exp_h = 1.0 / (1.0 + 10 ** ((elo[away] - elo[home]) / 400.0))
        exp_a = 1.0 - exp_h

        # Actual scores
        if hs > as_:
            act_h, act_a = 1.0, 0.0
        elif hs < as_:
            act_h, act_a = 0.0, 1.0
        else:
            act_h, act_a = 0.5, 0.5

        elo[home] += K_FACTOR * (act_h - exp_h)
        elo[away] += K_FACTOR * (act_a - exp_a)

    return elo


# ─── FEATURE ENGINEERING ──────────────────────────────────────────────────

def _rolling_form(df: pd.DataFrame, team: str, idx: int, window: int = 10) -> float:
    """Calculate points-per-game over the last `window` matches for `team`."""
    past = df.iloc[:idx]
    team_matches = past[(past["home_team"] == team) | (past["away_team"] == team)].tail(window)

    if len(team_matches) == 0:
        return 1.0  # neutral

    pts = 0.0
    for _, m in team_matches.iterrows():
        if m["home_team"] == team:
            if m["home_score"] > m["away_score"]:
                pts += 3
            elif m["home_score"] == m["away_score"]:
                pts += 1
        else:
            if m["away_score"] > m["home_score"]:
                pts += 3
            elif m["away_score"] == m["home_score"]:
                pts += 1

    return pts / len(team_matches)


def _engineer_features(full_df: pd.DataFrame, comp_df: pd.DataFrame) -> pd.DataFrame:
    """Build the full feature matrix. Elo from full history, features from competitive matches."""
    print("  Building Elo ratings from full history...")
    elo_table = _build_elo_table(full_df)

    print("  Engineering features from competitive matches...")
    rows = []
    # Use last 40% of competitive dataset (more recent = more relevant)
    start_idx = int(len(comp_df) * 0.6)

    for idx in range(start_idx, len(comp_df)):
        row = comp_df.iloc[idx]
        home, away = row["home_team"], row["away_team"]

        elo_h = elo_table.get(home, INITIAL_ELO)
        elo_a = elo_table.get(away, INITIAL_ELO)

        form_h = _rolling_form(comp_df, home, idx)
        form_a = _rolling_form(comp_df, away, idx)

        is_neutral = 1 if row.get("neutral", False) else 0

        rows.append({
            "elo_home": elo_h,
            "elo_away": elo_a,
            "elo_diff": elo_h - elo_a,
            "form_home": form_h,
            "form_away": form_a,
            "form_diff": form_h - form_a,
            "is_neutral": is_neutral,
            "home_score": row["home_score"],
            "away_score": row["away_score"],
        })

    return pd.DataFrame(rows)


# ─── TRAINING ──────────────────────────────────────────────────────────────

def train():
    # 1. Load data
    if os.path.exists(LOCAL_CSV):
        print(f"  Loading local CSV: {LOCAL_CSV}")
        df = pd.read_csv(LOCAL_CSV)
    else:
        print(f"  Downloading results.csv from GitHub...")
        df = pd.read_csv(DATA_URL)
        df.to_csv(LOCAL_CSV, index=False)
        print(f"  Saved to {LOCAL_CSV}")

    df = df.sort_values("date").reset_index(drop=True)
    df = df.dropna(subset=["home_score", "away_score"])
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    print(f"  Total historical matches: {len(df)}")

    # 2. Build Elo from ALL matches (full signal), but train on competitive only
    COMPETITIVE_TOURNAMENTS = [
        "FIFA World Cup", "FIFA World Cup qualification",
        "Copa América", "UEFA Euro", "UEFA Euro qualification",
        "African Cup of Nations", "African Cup of Nations qualification",
        "AFC Asian Cup", "AFC Asian Cup qualification",
        "Gold Cup", "UEFA Nations League", "CONCACAF Nations League",
        "Confederations Cup",
    ]
    comp_df = df[df["tournament"].isin(COMPETITIVE_TOURNAMENTS)].reset_index(drop=True)
    print(f"  Competitive matches (training subset): {len(comp_df)}")

    # 3. Feature engineering (Elo from full history, features from competitive)
    features_df = _engineer_features(df, comp_df)
    print(f"  Feature matrix: {features_df.shape[0]} rows × {features_df.shape[1]} cols")

    feature_cols = ["elo_home", "elo_away", "elo_diff", "form_home", "form_away", "form_diff", "is_neutral"]
    X = features_df[feature_cols]
    y_home = features_df["home_score"]
    y_away = features_df["away_score"]

    # 3. Train/test split
    X_train, X_test, yh_train, yh_test, ya_train, ya_test = train_test_split(
        X, y_home, y_away, test_size=0.15, random_state=42
    )
    print(f"  Train: {len(X_train)} | Test: {len(X_test)}")

    # 4. Train home goals model
    print("\n  Training XGBRegressor for HOME goals...")
    model_home = XGBRegressor(
        n_estimators=500,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        verbosity=0,
    )
    model_home.fit(X_train, yh_train, eval_set=[(X_test, yh_test)], verbose=False)
    pred_h = model_home.predict(X_test)
    mae_h = mean_absolute_error(yh_test, pred_h)
    print(f"  Home MAE: {mae_h:.4f}")

    # 5. Train away goals model
    print("  Training XGBRegressor for AWAY goals...")
    model_away = XGBRegressor(
        n_estimators=500,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        verbosity=0,
    )
    model_away.fit(X_train, ya_train, eval_set=[(X_test, ya_test)], verbose=False)
    pred_a = model_away.predict(X_test)
    mae_a = mean_absolute_error(ya_test, pred_a)
    print(f"  Away MAE: {mae_a:.4f}")

    # 6. Save models
    os.makedirs(SAVE_DIR, exist_ok=True)
    home_path = os.path.join(SAVE_DIR, "xgb_home.json")
    away_path = os.path.join(SAVE_DIR, "xgb_away.json")
    model_home.save_model(home_path)
    model_away.save_model(away_path)
    print(f"\n  ✓ Saved: {home_path}")
    print(f"  ✓ Saved: {away_path}")

    # 7. Feature importance
    print("\n  Feature Importance (Home Model):")
    for feat, imp in sorted(zip(feature_cols, model_home.feature_importances_), key=lambda x: -x[1]):
        print(f"    {feat:20s}  {imp:.4f}")

    print(f"\n  Done! Models are ready for inference in models/xgboost_model.py")


if __name__ == "__main__":
    print("=" * 70)
    print("  XGBoost Training Pipeline — World Cup 2026")
    print("=" * 70)
    train()
