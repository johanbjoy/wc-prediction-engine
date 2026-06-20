"""
tabnet_model.py — Deep Learning for Tabular Data
Implements attention-based deep learning (TabNet) for the NEXUS V2 Engine.
"""
import os
import numpy as np
import pandas as pd
import torch
from pytorch_tabnet.tab_model import TabNetRegressor

class TabNetModel:
    def __init__(self, target: str = "home_xg"):
        self.target = target
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = TabNetRegressor(
            n_d=16, n_a=16, n_steps=4, gamma=1.3,
            n_independent=2, n_shared=2,
            optimizer_fn=torch.optim.Adam,
            optimizer_params=dict(lr=2e-2),
            scheduler_params={"step_size": 10, "gamma": 0.9},
            scheduler_fn=torch.optim.lr_scheduler.StepLR,
            mask_type='entmax',
            device_name=self.device
        )
        self.cat_features = ["home_team", "away_team", "tournament"]
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        X_train = X.drop(columns=self.cat_features, errors="ignore").fillna(0).values
        y_train = y.values.reshape(-1, 1)
        
        self.model.fit(
            X_train=X_train, y_train=y_train,
            eval_set=[(X_train, y_train)],
            eval_name=['train'],
            eval_metric=['rmse'],
            max_epochs=20, patience=5,
            batch_size=1024, virtual_batch_size=128,
            num_workers=0, drop_last=False
        )
        
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        X_pred = X.drop(columns=self.cat_features, errors="ignore").fillna(0).values
        preds = self.model.predict(X_pred)
        return np.maximum(0.0, preds.flatten())
        
    def save_model(self, path: str):
        self.model.save_model(path)
        
    def load_model(self, path: str):
        if os.path.exists(path + ".zip"):
            self.model.load_model(path + ".zip")
        return self
