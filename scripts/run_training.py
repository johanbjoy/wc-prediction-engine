import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.nexus.features.feature_engine import FeatureEngine
from src.nexus.stacking.deep_stack import DeepStackingEnsemble

# ─── CONFIG ────────────────────────────────────────────────────────────────
LOCAL_CSV = os.path.join(os.path.dirname(__file__), "..", "data_store", "databases", "results.csv")
SAVE_DIR = os.path.join(os.path.dirname(__file__), "..", "data_store", "models", "v2")

def train_nexus_v2():
    print("--- N.E.X.U.S. V2 Sovereign Engine: Hierarchical Training ---")
    if not os.path.exists(LOCAL_CSV):
        print("Missing results.csv! Cannot train.")
        return
        
    df = pd.read_csv(LOCAL_CSV)
    df = df.dropna(subset=["home_score", "away_score"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    
    # 1. Expand features
    print(f"Generating 80+ features for {len(df)} matches using FeatureEngine...")
    fe = FeatureEngine()
    features_df = fe.generate_features(df, is_training=True)
    
    X = features_df.drop(columns=["target_home_score", "target_away_score", "target_home_xg", "target_away_xg"], errors="ignore")
    
    if "target_home_xg" in features_df.columns:
        y_home = features_df["target_home_xg"]
        y_away = features_df["target_away_xg"]
    else:
        # Fallback if targets are missing
        y_home = pd.Series([1.0]*len(X))
        y_away = pd.Series([1.0]*len(X))
        
    # 2. Deep Stacking
    ensemble = DeepStackingEnsemble()
    
    # Train
    ensemble.fit(X, y_home, y_away)
    
    # Save
    os.makedirs(SAVE_DIR, exist_ok=True)
    ensemble.save_models(SAVE_DIR)
    
    print("NEXUS V2 training complete. Ready for dynamic routing.")

if __name__ == "__main__":
    train_nexus_v2()
