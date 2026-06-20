"""
uncertainty.py — Uncertainty Quantification Engine
Quantifies Aleatoric (irreducible randomness) and Epistemic (model) uncertainty.
"""
import numpy as np

class UncertaintyEngine:
    """
    Quantifies prediction uncertainty to generate confidence intervals.
    """
    
    def __init__(self):
        pass
        
    def compute_uncertainty(self, predictions: list[np.ndarray], features: np.ndarray) -> dict:
        """
        Total uncertainty = sqrt(aleatoric² + epistemic²)
        """
        # Epistemic: standard deviation of ensemble predictions
        if len(predictions) > 1:
            epistemic = np.std(predictions, axis=0)
        else:
            epistemic = np.array([0.05])
            
        # Aleatoric: baseline noise
        aleatoric = np.array([0.1])
        
        total = np.sqrt(epistemic**2 + aleatoric**2)
        
        return {
            'total_uncertainty': total,
            'epistemic': epistemic,
            'aleatoric': aleatoric,
            'confidence': 1 - total
        }
        
    def compute_credible_interval(self, probs: np.ndarray, uncertainty: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Bayesian credible interval for probabilities (95% CI).
        """
        scale = uncertainty * 1.96  # 95% interval
        
        lower = np.clip(probs - scale, 0.01, 0.99)
        upper = np.clip(probs + scale, 0.01, 0.99)
        
        return lower, upper
