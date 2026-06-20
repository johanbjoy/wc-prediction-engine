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
        
    def optimize(self, X: pd.DataFrame, y: pd.Series, n_trials: int = 20):
        """Runs Bayesian Optimization using Optuna to find best hyperparameters."""
        import optuna
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_squared_error
        
        print(f"Running Optuna Optimization for {n_trials} trials...")
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        for col in self.cat_features:
            if col in X_train.columns:
                X_train[col] = X_train[col].astype('category')
                X_val[col] = X_val[col].astype('category')
                
        def objective(trial):
            params = {
                'boosting_type': 'dart',
                'num_leaves': trial.suggest_int('num_leaves', 20, 150),
                'max_depth': trial.suggest_int('max_depth', 4, 15),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
                'n_estimators': trial.suggest_int('n_estimators', 50, 500),
                'min_child_samples': trial.suggest_int('min_child_samples', 10, 100),
                'subsample': trial.suggest_float('subsample', 0.5, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
                'random_state': 42,
                'verbose': -1
            }
            
            model = lgb.LGBMRegressor(**params)
            model.fit(X_train, y_train, categorical_feature=self.cat_features)
            preds = model.predict(X_val)
            return np.sqrt(mean_squared_error(y_val, preds)) # RMSE
            
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction='minimize')
        study.optimize(objective, n_trials=n_trials)
        
        best_params = study.best_params
        best_params['boosting_type'] = 'dart'
        best_params['random_state'] = 42
        self.model = lgb.LGBMRegressor(**best_params)
        print(f"  Best RMSE: {study.best_value:.4f}")
        return self
        
    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: pd.Series = None, optimize: bool = False):
        """Trains the model with native categorical handling."""
        if optimize:
            self.optimize(X, y, n_trials=20)
            
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
                
        if isinstance(self.model, lgb.Booster):
            preds = self.model.predict(X_pred)
        else:
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
        if isinstance(self.model, lgb.Booster):
            self.model.save_model(path)
        else:
            self.model.booster_.save_model(path)
        
    def load_model(self, path: str):
        self.model = lgb.Booster(model_file=path)
        return self
