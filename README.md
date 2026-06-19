# ⚽ WC 2026 Prediction Engine

A highly scalable, multi-agent predictive syndicate engine for the **2026 FIFA World Cup**.

## 🧠 The Architecture: Modular Predictive System
Unlike flat-file sports predictors, this engine utilizes a fully decoupled, dynamic architecture:
- **Data Layer:** Ingests live fixtures, starting XI data, and real-time tournament standings directly from API sources.
- **Ensemble Layer:** A dual-execution predictive engine that mathematically blends machine learning with statistical simulation.
- **Form Tracker:** Dynamically adjusts Elo ratings based on real-time group stage performance and points-per-game to catch underperforming favorites.
- **LLM Meta-Learner (Optional):** Two specialized LLM agents (DeepSeek & Gemini) that parse tactical data and apply deterministic multiplier adjustments to the final expected goals (xG).

## 📊 The Math: 60/40 Blended Ensemble
This engine has been rigorously backtested and upgraded to a highly calibrated **consensus-driven ensemble**:
1. **XGBoost Regression Model (60% Weight):** An ML model trained on a historical dataset of 49,000+ international football fixtures, engineered with dynamic Elo calculations.
2. **Monte Carlo Poisson Simulator (40% Weight):** Runs a 10,000-iteration minute-by-minute simulation using Time-Decay and Urgency scaling.
3. **The Blend & Boost:** The orchestrator runs both models, applies a 1.5x Elo boost to favorites, and then applies a live **Tournament Form** modifier to dampen predictions for historically strong teams that are struggling in the actual tournament.
4. **Conservative Bias:** A strict -0.10 expected goals (xG) rounding bias is applied to prevent blowout over-prediction in low-scoring group stage matches.


## 🚀 Automation & Deployment
The pipeline runs entirely on autopilot. A **GitHub Action** wakes the engine up every morning at 08:00 UTC, fetches the day's matchups, runs the ML models, queries the LLMs (if activated), and stores the final expected value predictions directly into the **Supabase (PostgreSQL)** cloud.
