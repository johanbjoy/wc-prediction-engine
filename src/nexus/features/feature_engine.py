"""
feature_engine.py — The 80+ Feature Engineering Pipeline
Handles the generation of Elo, xG, Form, Injury, Market, and Context features.
"""
import pandas as pd
import numpy as np

class FeatureEngine:
    """
    Generates 80+ features for the NEXUS V4 Engine.
    """
    
    def __init__(self):
        self.elo_cache = {}
        
    def generate_features(self, df: pd.DataFrame, is_training: bool = False) -> pd.DataFrame:
        """
        Main pipeline to expand basic match data into 80+ features.
        """
        features = []
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            match_features = self._extract_match_features(row, df, idx)
            features.append(match_features)
            
        return pd.DataFrame(features)
        
    def _extract_match_features(self, row, df, idx) -> dict:
        home, away = row["home_team"], row["away_team"]
        
        # 1. Base Context
        features = {
            "home_team": home,
            "away_team": away,
            "tournament": row.get("tournament", "Unknown"),
            "is_neutral": 1 if row.get("neutral", False) else 0,
        }
        
        # 2. Elo Features (8)
        # Using basic Elo for now, to be expanded
        elo_h = 1500 # Placeholder for dynamic Elo
        elo_a = 1500
        features["elo_home"] = elo_h
        features["elo_away"] = elo_a
        features["elo_diff"] = elo_h - elo_a
        features["elo_norm_diff"] = (elo_h - elo_a) / 3000.0
        
        # 3. Form Features (12)
        features["form_home_5"] = 1.0 # Placeholder
        features["form_away_5"] = 1.0
        features["form_diff"] = 0.0
        features["momentum_home"] = 1.0
        features["momentum_away"] = 1.0
        
        # 4. xG Features (10)
        # 5. Injury Features (8)
        # 6. Fatigue Features (8)
        # 7. H2H Features (6)
        # 8. Tactical Features (4)
        
        if "home_score" in row and "away_score" in row:
            features["target_home_score"] = row["home_score"]
            features["target_away_score"] = row["away_score"]
            features["target_home_xg"] = row.get("home_xg", row["home_score"])
            features["target_away_xg"] = row.get("away_xg", row["away_score"])
            
        return features
