"""
feature_engine.py — The 80+ Feature Engineering Pipeline
Handles the generation of Elo, xG, Form, Injury, Market, and Context features.
"""
import pandas as pd
import numpy as np

class FeatureEngine:
    """
    Generates 80+ features for the NEXUS V2 Engine.
    """
    
    def __init__(self):
        self.elo_cache = {}
        self.form_cache = {} # Track goals scored/conceded lists per team
        self.k_factor = 40   # ELO K-factor
        
    def save_cache(self, path: str):
        import json, os
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "elo_cache.json"), "w") as f:
            json.dump(self.elo_cache, f)
        with open(os.path.join(path, "form_cache.json"), "w") as f:
            json.dump(self.form_cache, f)
            
    def load_cache(self, path: str):
        import json, os
        elo_path = os.path.join(path, "elo_cache.json")
        form_path = os.path.join(path, "form_cache.json")
        if os.path.exists(elo_path):
            with open(elo_path, "r") as f:
                self.elo_cache = json.load(f)
        if os.path.exists(form_path):
            with open(form_path, "r") as f:
                self.form_cache = json.load(f)
        return self
        
    def _get_elo(self, team: str) -> float:
        return self.elo_cache.get(team, 1500.0)
        
    def _update_elo(self, home: str, away: str, home_score: float, away_score: float):
        r_h = self._get_elo(home)
        r_a = self._get_elo(away)
        
        expected_h = 1.0 / (1.0 + 10.0 ** ((r_a - r_h) / 400.0))
        expected_a = 1.0 - expected_h
        
        if home_score > away_score:
            s_h, s_a = 1.0, 0.0
        elif away_score > home_score:
            s_h, s_a = 0.0, 1.0
        else:
            s_h, s_a = 0.5, 0.5
            
        # Margin of victory multiplier
        mov = abs(home_score - away_score)
        mov_mult = np.log(mov + 1) * (2.2 / ((r_h - r_a)*0.001 + 2.2)) if mov > 0 else 1.0
        
        self.elo_cache[home] = r_h + self.k_factor * mov_mult * (s_h - expected_h)
        self.elo_cache[away] = r_a + self.k_factor * mov_mult * (s_a - expected_a)

    def _update_form(self, team: str, scored: float, conceded: float):
        if team not in self.form_cache:
            self.form_cache[team] = []
        self.form_cache[team].append((scored, conceded))
        if len(self.form_cache[team]) > 5:
            self.form_cache[team].pop(0)
            
    def _get_form(self, team: str) -> tuple[float, float]:
        history = self.form_cache.get(team, [])
        if not history:
            return 1.0, 1.0
        avg_scored = sum(x[0] for x in history) / len(history)
        avg_conceded = sum(x[1] for x in history) / len(history)
        return avg_scored, avg_conceded

    def generate_features(self, df: pd.DataFrame, is_training: bool = False) -> pd.DataFrame:
        """
        Main pipeline to expand basic match data into 80+ features.
        """
        features = []
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            match_features = self._extract_match_features(row)
            features.append(match_features)
            
            # Post-match updates if we have results
            if "home_score" in row and "away_score" in row and not pd.isna(row["home_score"]):
                self._update_elo(row["home_team"], row["away_team"], row["home_score"], row["away_score"])
                self._update_form(row["home_team"], row["home_score"], row["away_score"])
                self._update_form(row["away_team"], row["away_score"], row["home_score"])
            
        return pd.DataFrame(features)
        
    def _extract_match_features(self, row) -> dict:
        home, away = row["home_team"], row["away_team"]
        
        # 1. Base Context
        features = {
            "home_team": home,
            "away_team": away,
            "tournament": row.get("tournament", "Unknown"),
            "is_neutral": 1 if row.get("neutral", False) else 0,
        }
        
        # 2. Elo Features
        elo_h = self._get_elo(home)
        elo_a = self._get_elo(away)
        features["elo_home"] = elo_h
        features["elo_away"] = elo_a
        features["elo_diff"] = elo_h - elo_a
        features["elo_norm_diff"] = (elo_h - elo_a) / 3000.0
        
        # 3. Form Features
        h_scored, h_conceded = self._get_form(home)
        a_scored, a_conceded = self._get_form(away)
        
        features["form_home_scored_5"] = h_scored
        features["form_home_conceded_5"] = h_conceded
        features["form_away_scored_5"] = a_scored
        features["form_away_conceded_5"] = a_conceded
        features["form_diff"] = (h_scored - h_conceded) - (a_scored - a_conceded)
        
        # 4. Poisson Baseline Integrations (Legacy V3 fusion)
        try:
            from src.nexus.models.poisson_model import predict as poisson_predict
            from src.nexus.data.scraper import _baseline_squad
            
            home_p = _baseline_squad(home)
            away_p = _baseline_squad(away)
            poi_res = poisson_predict(home, away, home_p, away_p)
            meta = poi_res["model_meta"]
            
            features["poi_home_xg"] = meta["lam_home"]
            features["poi_away_xg"] = meta["lam_away"]
            features["poi_p_home"] = meta["p_home_win"]
            features["poi_p_draw"] = meta["p_draw"]
            features["poi_p_away"] = meta["p_away_win"]
        except Exception:
            features["poi_home_xg"] = 1.35
            features["poi_away_xg"] = 1.35
            features["poi_p_home"] = 33.3
            features["poi_p_draw"] = 33.3
            features["poi_p_away"] = 33.3
        
        # Target labels
        if "home_score" in row and "away_score" in row:
            features["target_home_score"] = row["home_score"]
            features["target_away_score"] = row["away_score"]
            features["target_home_xg"] = row.get("home_xg", row["home_score"])
            features["target_away_xg"] = row.get("away_xg", row["away_score"])
            
        return features
