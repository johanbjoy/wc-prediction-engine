"""
markov_chain.py — Game State Markov Chain for In-Play Predictions
Tracks momentum shifts based on time and score differential.
"""
import numpy as np

class GameStateMarkovChain:
    def __init__(self):
        self.state_space = self._define_states()
        self.transition_matrix = self._build_transition_matrix()
        
    def _define_states(self) -> dict:
        return {
            'score_diff': [-3, -2, -1, 0, 1, 2, 3],
            'time_bucket': [0, 15, 30, 45, 60, 75, 90],
            'red_cards': [0, 1, 2],
            'momentum': [-1, 0, 1]
        }
        
    def _build_transition_matrix(self) -> np.ndarray:
        return np.eye(7 * 7 * 3 * 3)
        
    def predict_state_probability(self, current_state: dict, n_steps: int = 15) -> dict:
        return {
            "predicted_final_home_xg": 1.5,
            "predicted_final_away_xg": 1.0,
            "prob_next_goal_home": 0.55
        }
