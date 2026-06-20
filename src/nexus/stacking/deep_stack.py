"""
deep_stack.py — 3-Level Deep Stacking Ensemble
Combines Level 1 base models using Level 2 meta-learners and Level 3 BMA.
"""
import numpy as np
import pandas as pd

class StackingMetaLearner:
    """
    Level 2: Specialized meta-learner per outcome (Home/Draw/Away)
    """
    def __init__(self, task: str):
        self.task = task
        # Placeholder for actual meta-learner (e.g. Ridge Regression)
        
    def fit(self, base_preds: dict, y_true: np.ndarray):
        pass
        
    def predict(self, base_preds: dict) -> np.ndarray:
        # Simplistic average for now
        values = list(base_preds.values())
        return np.mean(values, axis=0) if values else np.zeros(1)


class BayesianModelAveraging:
    """
    Level 3: Super-ensemble with Bayesian Model Averaging
    """
    def combine(self, meta_home: np.ndarray, meta_draw: np.ndarray, meta_away: np.ndarray, match_context: dict):
        """Returns final probabilities and uncertainty."""
        # Simple normalization
        total = meta_home + meta_draw + meta_away
        if np.any(total == 0):
            return {"p_home_win": 0.33, "p_draw": 0.34, "p_away_win": 0.33}, 0.1
            
        probs = {
            "p_home_win": meta_home[0] / total[0],
            "p_draw": meta_draw[0] / total[0],
            "p_away_win": meta_away[0] / total[0]
        }
        uncertainty = 0.05 # Placeholder for epistemic uncertainty
        return probs, uncertainty


class DeepStackingEnsemble:
    """
    3-Level hierarchical stacking with uncertainty quantification
    """
    def __init__(self):
        # Level 1 Base Models
        self.base_models = [
            'dixon_coles', 
            'poisson_regression',
            'lightgbm', 
            'tabnet', 
            'temporal_fusion'
        ]
        
        # Dynamic Router
        from src.nexus.stacking.model_selector import DynamicModelSelector
        self.model_selector = DynamicModelSelector()
        
        # Level 2 Meta-Learners
        self.meta_home = StackingMetaLearner(task='home_win')
        self.meta_draw = StackingMetaLearner(task='draw')
        self.meta_away = StackingMetaLearner(task='away_win')
        
        # Level 3 BMA
        self.super_ensemble = BayesianModelAveraging()
        
    def should_include(self, model: str, context: dict) -> bool:
        """Dynamic router logic."""
        selected, _ = self.model_selector.select_models(context)
        return model in selected
        
    def fit(self, X: pd.DataFrame, y_home: pd.Series, y_away: pd.Series):
        """Train all base models and meta learners."""
        print("Training Deep Stacking Ensemble...")
        from src.nexus.models.lightgbm_model import LightGBMModel
        from src.nexus.models.tabnet_model import TabNetModel
        from src.nexus.models.temporal_fusion import TemporalFusionTransformer
        
        print("  Training LightGBM Models (with Optuna)...")
        self.lgb_home = LightGBMModel(target="home_xg")
        self.lgb_home.fit(X, y_home, optimize=True)
        self.lgb_away = LightGBMModel(target="away_xg")
        self.lgb_away.fit(X, y_away, optimize=True)
        
        print("  Training TabNet Models...")
        self.tabnet_home = TabNetModel(target="home_xg")
        self.tabnet_home.fit(X, y_home)
        self.tabnet_away = TabNetModel(target="away_xg")
        self.tabnet_away.fit(X, y_away)
        
        print("  Training Temporal Fusion Models...")
        self.tft_home = TemporalFusionTransformer(target="home_xg")
        self.tft_home.fit(X, y_home)
        self.tft_away = TemporalFusionTransformer(target="away_xg")
        self.tft_away.fit(X, y_away)
        
        print("  ✓ Level 1 Base Models trained.")
        
    def save_models(self, path: str):
        import os
        print(f"Saving deep stack models to {path}...")
        if hasattr(self, 'lgb_home'):
            self.lgb_home.save_model(os.path.join(path, "lgb_home.txt"))
            self.lgb_away.save_model(os.path.join(path, "lgb_away.txt"))
            self.tabnet_home.save_model(os.path.join(path, "tabnet_home"))
            self.tabnet_away.save_model(os.path.join(path, "tabnet_away"))
            self.tft_home.save_model(os.path.join(path, "tft_home.pt"))
            self.tft_away.save_model(os.path.join(path, "tft_away.pt"))
        
    def load_models(self, path: str):
        import os
        from src.nexus.models.lightgbm_model import LightGBMModel
        from src.nexus.models.tabnet_model import TabNetModel
        from src.nexus.models.temporal_fusion import TemporalFusionTransformer
        
        self.lgb_home = LightGBMModel(target="home_xg").load_model(os.path.join(path, "lgb_home.txt"))
        self.lgb_away = LightGBMModel(target="away_xg").load_model(os.path.join(path, "lgb_away.txt"))
        
        self.tabnet_home = TabNetModel(target="home_xg").load_model(os.path.join(path, "tabnet_home"))
        self.tabnet_away = TabNetModel(target="away_xg").load_model(os.path.join(path, "tabnet_away"))
        
        self.tft_home = TemporalFusionTransformer(target="home_xg").load_model(os.path.join(path, "tft_home.pt"))
        self.tft_away = TemporalFusionTransformer(target="away_xg").load_model(os.path.join(path, "tft_away.pt"))
        return self
        
    def predict(self, features: pd.DataFrame, match_context: dict) -> dict:
        """Execute the deep stack."""
        base_preds = {}
        
        # Determine active models for this match context
        active_models, weights = self.model_selector.select_models(match_context)
        
        # Base Model Predictions
        if hasattr(self, 'lgb_home'):
            pred_h = self.lgb_home.predict(features)[0]
            pred_a = self.lgb_away.predict(features)[0]
            base_preds['lightgbm'] = np.array([pred_h, pred_a])
            
            tab_h = self.tabnet_home.predict(features)[0]
            tab_a = self.tabnet_away.predict(features)[0]
            base_preds['tabnet'] = np.array([tab_h, tab_a])
            
            tft_h = self.tft_home.predict(features)[0]
            tft_a = self.tft_away.predict(features)[0]
            base_preds['temporal_fusion'] = np.array([tft_h, tft_a])
        else:
            base_preds['lightgbm'] = np.array([1.0, 1.0])
            base_preds['tabnet'] = np.array([1.0, 1.0])
            base_preds['temporal_fusion'] = np.array([1.0, 1.0])
            
        # Bayesian Model Averaging (Simple weighted ensemble)
        valid_models = [m for m in active_models if m in base_preds]
        valid_weights = [weights[active_models.index(m)] for m in valid_models]
        if sum(valid_weights) > 0:
            norm_valid_weights = [w / sum(valid_weights) for w in valid_weights]
        else:
            norm_valid_weights = [1.0 / len(valid_models)] * len(valid_models)
            
        final_h = sum(base_preds[m][0] * w for m, w in zip(valid_models, norm_valid_weights))
        final_a = sum(base_preds[m][1] * w for m, w in zip(valid_models, norm_valid_weights))
        
        # Fallback if no models active
        if final_h == 0 and final_a == 0:
            final_h, final_a = 1.0, 1.0
            
        return {
            'probabilities': {
                'p_home_win': final_h / 3.0, # Dummy conversion for pipeline
                'p_draw': 1.0 / 3.0,
                'p_away_win': final_a / 3.0
            },
            'raw_xg': (final_h, final_a),
            'uncertainty': 0.1
        }
