"""
dixon_coles.py — Bivariate Poisson Model with Dixon-Coles Adjustment
Calculates score probabilities adjusting for low-scoring matches.
"""
import numpy as np
from scipy.stats import poisson

def get_dixon_coles_probs(lam_home: float, lam_away: float, rho: float = -0.15, max_goals: int = 10) -> dict:
    h = np.arange(max_goals)
    a = np.arange(max_goals)
    
    # Vectorized Poisson (1 call instead of 100)
    home_probs = poisson.pmf(h, lam_home)
    away_probs = poisson.pmf(a, lam_away)
    
    probs = np.outer(home_probs, away_probs)
    
    # Dixon-Coles low-score adjustment factor
    probs[0, 0] *= (1.0 - lam_home * lam_away * rho)
    probs[0, 1] *= (1.0 + lam_home * rho)
    probs[1, 0] *= (1.0 + lam_away * rho)
    probs[1, 1] *= (1.0 - rho)
    
    probs = np.clip(probs, 0, None)
    probs = probs / np.sum(probs)
    
    return {
        "p_home_win": round(float(np.sum(np.tril(probs, -1))) * 100, 2),
        "p_draw": round(float(np.sum(np.diag(probs))) * 100, 2),
        "p_away_win": round(float(np.sum(np.triu(probs, 1))) * 100, 2),
        "matrix": probs
    }
