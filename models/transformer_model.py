import os
import torch
import torch.nn as nn
import numpy as np

class NexusTransformer(nn.Module):
    """
    State-of-the-art Temporal Transformer for football match prediction.
    Takes the 15 elite features and outputs the Expected Goals (xG).
    """
    def __init__(self, input_dim=15, d_model=256, n_heads=8, num_layers=6, dropout=0.1):
        super(NexusTransformer, self).__init__()
        
        # 1. Feature Projection
        self.input_projection = nn.Linear(input_dim, d_model)
        
        # 2. Transformer Encoder Layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, 
            nhead=n_heads, 
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # 3. Regression Head (Predicts xG)
        self.regression_head = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 1)
        )
        
    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_dim)
        # Since we use single-match static features right now, sequence_length = 1
        if x.dim() == 2:
            x = x.unsqueeze(1) # Add sequence dimension -> (batch, 1, input_dim)
            
        projected = self.input_projection(x)
        encoded = self.transformer(projected)
        
        # Pooling (take the last sequence element)
        pooled = encoded[:, -1, :] 
        
        # Output xG
        out = self.regression_head(pooled)
        return out.squeeze(-1) # shape: (batch_size,)

class TransformerModel:
    """
    Wrapper class to provide a scikit-learn/CatBoost-like API for the orchestrator.
    """
    def __init__(self, input_dim=15, d_model=256, n_heads=8, num_layers=6, dropout=0.1):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = NexusTransformer(input_dim, d_model, n_heads, num_layers, dropout).to(self.device)
        self.model.eval() # Inference mode by default
        
    def predict(self, features_df):
        """
        Takes a pandas DataFrame of shape (N, 15) and returns predicted xG array.
        """
        # Ensure numerical casting
        x_np = features_df.to_numpy(dtype=np.float32)
        x_tensor = torch.tensor(x_np, dtype=torch.float32).to(self.device)
        
        with torch.no_grad():
            preds = self.model(x_tensor)
            
        # xG cannot be negative
        preds_np = preds.cpu().numpy()
        return np.maximum(0.0, preds_np)
        
    def load_weights(self, path: str):
        """Loads trained PyTorch weights."""
        if os.path.exists(path):
            self.model.load_state_dict(torch.load(path, map_location=self.device, weights_only=True))
            self.model.eval()
        else:
            print(f"Warning: No weights found at {path}. Using untrained initialization.")

    def fit(self, features_df, labels_series, epochs=50, batch_size=32, lr=1e-3):
        """
        Trains the Transformer model using PyTorch Adam optimizer.
        """
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = nn.MSELoss()
        
        x_np = features_df.to_numpy(dtype=np.float32)
        y_np = labels_series.to_numpy(dtype=np.float32)
        
        dataset = torch.utils.data.TensorDataset(
            torch.tensor(x_np, dtype=torch.float32), 
            torch.tensor(y_np, dtype=torch.float32)
        )
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        for epoch in range(epochs):
            total_loss = 0.0
            for batch_x, batch_y in loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                
                optimizer.zero_grad()
                preds = self.model(batch_x)
                loss = criterion(preds, batch_y)
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
                
        self.model.eval()
        
    def save_model(self, path: str):
        """Saves the PyTorch weights."""
        torch.save(self.model.state_dict(), path)
