"""
causal_engine.py — Causal Inference Engine for NEXUS V2
Estimates Average Treatment Effect on Treated (ATET) for counterfactual events.
"""
import pandas as pd
import numpy as np

class CausalInferenceEngine:
    def __init__(self):
        pass
        
    def estimate_home_advantage_causal(self, df: pd.DataFrame) -> float:
        """
        Uses simplified Propensity Score Matching (PSM) to isolate the causal
        effect of playing at home (Treatment) on expected goals (Outcome).
        Controls for team strength (Elo).
        """
        if len(df) < 100:
            return 0.35 # Fallback
            
        # Treatment: is_home (1 if home, 0 if away/neutral)
        # Outcome: goals_scored
        # Confounders: elo_diff
        
        # We simulate the ATET by binning Elo differences (propensity proxy)
        # and comparing home goals vs away goals within the exact same Elo bins.
        
        home_stats = pd.DataFrame({
            'goals': df['home_score'],
            'elo_diff': df['elo_home'] - df['elo_away'],
            'is_home': 1
        })
        
        away_stats = pd.DataFrame({
            'goals': df['away_score'],
            'elo_diff': df['elo_away'] - df['elo_home'],
            'is_home': 0
        })
        
        combined = pd.concat([home_stats, away_stats]).dropna()
        combined['elo_bin'] = pd.qcut(combined['elo_diff'], q=10, duplicates='drop')
        
        # Calculate Average Treatment Effect within each bin
        bin_effects = []
        for name, group in combined.groupby('elo_bin', observed=False):
            home_goals = group[group['is_home'] == 1]['goals'].mean()
            away_goals = group[group['is_home'] == 0]['goals'].mean()
            if not np.isnan(home_goals) and not np.isnan(away_goals):
                bin_effects.append(home_goals - away_goals)
                
        # ATET is the average of bin effects
        if len(bin_effects) > 0:
            atet = np.mean(bin_effects)
            return float(atet)
            
        return 0.35
        
    def estimate_injury_impact(self, team: str, missing_player: str, opponent: str) -> float:
        """Placeholder for player-level causal graph"""
        return -0.25
        
    def calculate_uplift(self, team: str, tactical_change: str) -> float:
        """Placeholder for Uplift Modeling"""
        return 0.1
