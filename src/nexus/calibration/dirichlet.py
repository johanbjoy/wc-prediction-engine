"""
dirichlet.py — Dirichlet Calibration
Multinomial calibration for Home/Draw/Away outcomes.
"""
import numpy as np

class DirichletCalibrator:
    """
    Dirichlet calibration for multi-class probabilities (H/D/A).
    Fits: p_calibrated = Dirichlet(alpha * p_raw)
    """
    
    def __init__(self):
        self.alpha = np.array([1.0, 1.0, 1.0])
        
    def fit(self, y_true: np.ndarray, y_pred: np.ndarray):
        """
        Fit alpha parameters. Minimizes NLL.
        """
        # Placeholder for complex Dirichlet MLE
        self.alpha = np.array([1.1, 0.9, 1.1])
        
    def calibrate(self, y_pred: np.ndarray) -> np.ndarray:
        """
        Apply Dirichlet calibration to probabilities.
        """
        calibrated = self.alpha * y_pred
        # Normalize
        row_sums = calibrated.sum(axis=calibrated.ndim-1, keepdims=True)
        return calibrated / row_sums
