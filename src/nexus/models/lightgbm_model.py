"""
lightgbm_model.py — LightGBM with DART (Dropouts meet Multiple Additive Regression Trees)
The primary tabular ML model for NEXUS V2, replacing CatBoost for superior accuracy and speed.
"""
import os
import numpy as np
import lightgbm as lgb
import pandas as pd

class LightGBMModel:
    """
    LightGBM with DART
    
    Hyperparameters:
    - num_leaves: 63
    - max_depth: 8
    - learning_rate: 0.05
    - n_estimators: 200
    """
    
    def __init__(self, target: str = "home_xg"):
        self.target = target
        self.model = lgb.LGBMRegressor(
            boosting_type='dart',
            num_leaves=63,
            max_depth=8,
            learning_rate=0.05,
            n_estimators=200,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42
        )
        self.cat_features = ["home_team", "away_team", "tournament"]
        
    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: pd.Series = None):
        """Trains the model with native categorical handling."""
        # Convert categoricals to 'category' dtype for LightGBM
        X_train = X.copy()
        for col in self.cat_features:
            if col in X_train.columns:
                X_train[col] = X_train[col].astype('category')
                
        self.model.fit(
            X_train, 
            y, 
            sample_weight=sample_weight,
            categorical_feature=self.cat_features
        )
        
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predicts outcomes ensuring no negative values."""
        X_pred = X.copy()
        for col in self.cat_features:
            if col in X_pred.columns:
                X_pred[col] = X_pred[col].astype('category')
                
        preds = self.model.predict(X_pred)
        return np.maximum(0.0, preds)
        
    def get_shap_values(self, X: pd.DataFrame):
        """Calculates SHAP values for feature interpretability."""
        import shap
        X_pred = X.copy()
        for col in self.cat_features:
            if col in X_pred.columns:
                X_pred[col] = X_pred[col].astype('category')
                
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(X_pred)
        return shap_values, explainer
        
    def save_model(self, path: str):
        self.model.booster_.save_model(path)
        
    def load_model(self, path: str):
        self.model = lgb.Booster(model_file=path)
        return self
