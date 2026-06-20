# NEXUS V2 — Sovereign Prediction Engine
**The World's Most Advanced Football Prediction System**

*"Beyond ensembles — a self-adaptive, multi-modal prediction intelligence that learns, reasons, and evolves."*

## 🧠 The Architecture: Modular Predictive System
Unlike legacy flat-file sports predictors, this engine utilizes a fully decoupled, dynamic deep stacking architecture designed for the 2026 FIFA World Cup.

- **Data Layer:** Ingests live fixtures, starting XI data, and real-time tournament standings directly from API sources via PostgreSQL.
- **Dynamic Model Selection:** AI neural routing dynamically chooses the optimal model subset per match context (e.g. prioritizing Form models for group stages and Bookmaker metrics for knockout rounds).
- **Deep Stacking Ensemble (Level 3 BMA):** 
  - **LightGBM:** High-speed, histogram-based gradient boosting (replacing CatBoost as the primary ML engine).
  - **PyTorch TabNet:** Attention-based deep learning for tabular data, capable of learning non-linear feature interactions.
  - **Temporal Fusion Transformer (TFT):** Advanced time-series forecasting to capture team momentum and form over time.
- **Causal Inference Engine:** Causal ML to generate counterfactual predictions and isolate true team momentum (ATET) by neutralizing home-field advantage or opponent bias.
- **Bayesian Calibration:** Uses Venn-ABERS and multinomial Dirichlet Calibration to ensure the output probabilities represent true empirical frequencies.

## 📊 The Math: From ML to Exact Scores
This engine does not just predict the winning team—it calculates precise score probabilities using organic probability coupling:
1. **Feature Engineering (80+ Features):** Evaluates Elo differential, opponent-adjusted xG, injury impact scores, team workload/fatigue, and market odds movement.
2. **Deep Stack xG Prediction:** The `DeepStackingEnsemble` mathematically blends LightGBM, TabNet, and TFT predictions to output highly accurate Expected Goals (xG) for both teams.
3. **Dixon-Coles Organic Matrix:** The final xG values are fed into a mathematically robust Dixon-Coles model (with a rho `ρ` correlation factor to prevent draw compression) to output a 2D matrix of every possible exact scoreline.

## 🖥️ Command Center UI
The frontend has been completely refactored into a high-fidelity, multi-page Streamlit dashboard matching the Sovereign Intelligence Command Center spec:
- **1_Dashboard:** Tracks calibration metrics (ECE) and Outcome/Exact Score accuracy in real-time.
- **2_Predictions:** Displays the upcoming prediction timeline using Bayesian Uncertainty Donuts and Confidence Cones.
- **3_Tournament_Sim:** A fully interactive Monte Carlo Simulator running 10,000+ iterations to calculate exact Championship paths.
- **4_Backtesting:** Analyzes the Deep Stack's feature importance through Model Attribution Waterfalls (SHAP-style visualizations).

## 🚀 Deployment
Built for production. The environment includes a decoupled REST API, WebSocket server for in-play state modeling, Redis caching, and a Supabase PostgreSQL datastore.

```bash
# Bring up the full NEXUS ecosystem locally
docker-compose up -d
```
