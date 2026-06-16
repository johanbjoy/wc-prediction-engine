# ⚽ WC 2026 Prediction Engine

A highly scalable, multi-agent predictive syndicate engine for the **2026 FIFA World Cup**.

## 🧠 The Architecture: Modular Multi-Agent System
Unlike flat-file sports predictors, this engine utilizes a fully decoupled, cloud-ready architecture:
- **Data Layer:** Ingests live fixtures, starting XI data, and real-time betting market odds.
- **Model Layer:** A dual-execution predictive ensemble that mathematically blends probabilities.
- **Agent Layer:** Two specialized LLM agents (DeepSeek & Gemini/Grok) that parse tactical data and output deterministic modifiers.
- **Orchestrator:** The central nervous system that runs the pipeline, fetches consensus, calculates edges, and persists final predictions to **Supabase (PostgreSQL)**.

## 📊 The Math: Weighted XGBoost Ensemble
This engine has been fundamentally upgraded from a static zero-inflated Poisson model to a **consensus-driven ensemble**:
1. **Monte Carlo Poisson Simulator:** Runs a 10,000-iteration minute-by-minute simulation using Time-Decay and Urgency scaling.
2. **XGBoost Regression Model:** An ML model trained on a historical dataset of 49,000+ international football fixtures, engineered with dynamic Elo calculations and rolling form metrics.
3. **The Blend:** The orchestrator runs both models dynamically on live data and mathematically blends their expected goals (xG) to reach a highly stable consensus.

## 📈 The Edge: Value Engine & Market Consensus
This project doesn't just predict scores—it operates like a professional quantitative sports syndicate.
- **Market Blending:** Live odds are pulled from The-Odds-API, the bookmaker 'vig' (margin) is stripped out to find the True Implied Probability, and the consensus is blended into the model.
- **Expected Value (EV):** The built-in Value Engine strictly compares our model's probability against the market's true probability.
- **Kelly Criterion:** If positive EV exists, the Value Engine calculates the exact mathematically optimal percentage of the bankroll to wager, safely capped at 25% to prevent risk of ruin.

## 🚀 CI/CD Automation
The entire pipeline runs entirely on autopilot. A **GitHub Action** wakes the engine up every morning at 08:00 UTC, fetches the day's matchups, runs the ML models, queries the LLMs, and stores the final expected value predictions directly into the Supabase cloud.
