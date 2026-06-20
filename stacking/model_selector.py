"""
model_selector.py — Dynamic Context-Aware Router
Decides which models to activate for a specific match given the environmental context.
"""
import numpy as np

class DynamicModelSelector:
    """
    Context-aware model selection that chooses optimal model subset
    based on match characteristics.
    """
    
    def __init__(self):
        self.available_models = [
            'lightgbm', 'tabnet', 'temporal_fusion', 'dixon_coles', 'poisson_regression'
        ]
        self.selection_threshold = 0.3
        
    def select_models(self, match_context: dict) -> tuple[list[str], list[float]]:
        """
        Returns subset of models best suited for this match and their weights.
        """
        is_knockout = match_context.get("is_knockout", False)
        
        if is_knockout:
            weights = [0.8, 0.7, 0.6, 0.4, 0.2]
        else:
            weights = [0.6, 0.6, 0.6, 0.5, 0.5]
            
        selected = [m for m, w in zip(self.available_models, weights) if w > self.selection_threshold]
        active_weights = [w for w in weights if w > self.selection_threshold]
        
        s = sum(active_weights)
        norm_weights = [w / s for w in active_weights]
        
        return selected, norm_weights
