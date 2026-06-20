"""
temporal_fusion.py — Neural Time-Series Component
Implements deep learning for tracking form via PyTorch.
"""
import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

class SimpleNeuralNet(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1)
        )
    def forward(self, x):
        return self.net(x)

class TemporalFusionTransformer:
    def __init__(self, target: str = "home_xg"):
        self.target = target
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.cat_features = ["home_team", "away_team", "tournament"]
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        X_train = X.drop(columns=self.cat_features, errors="ignore").fillna(0).values
        y_train = y.values.reshape(-1, 1)
        
        self.model = SimpleNeuralNet(X_train.shape[1]).to(self.device)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.01)
        criterion = nn.MSELoss()
        
        X_t = torch.FloatTensor(X_train).to(self.device)
        y_t = torch.FloatTensor(y_train).to(self.device)
        
        self.model.train()
        for epoch in range(50):
            optimizer.zero_grad()
            preds = self.model(X_t)
            loss = criterion(preds, y_t)
            loss.backward()
            optimizer.step()
            
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        X_pred = X.drop(columns=self.cat_features, errors="ignore").fillna(0).values
        if self.model is None:
            return np.ones(len(X_pred))
            
        self.model.eval()
        with torch.no_grad():
            X_t = torch.FloatTensor(X_pred).to(self.device)
            preds = self.model(X_t).cpu().numpy()
            
        return np.maximum(0.0, preds.flatten())
        
    def save_model(self, path: str):
        if self.model:
            torch.save(self.model.state_dict(), path)
        
    def load_model(self, path: str):
        if os.path.exists(path):
            # Assumes 15 features (18 total minus 3 dropped cat_features)
            self.model = SimpleNeuralNet(15).to(self.device)
            self.model.load_state_dict(torch.load(path, map_location=self.device))
        return self
