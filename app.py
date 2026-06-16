import streamlit as st
import pandas as pd
from data.database import get_recent_predictions, get_leaderboard, get_summary, get_all_fixtures

st.set_page_config(page_title="World Cup Engine", layout="wide")

st.title("🏆 World Cup 2026 Prediction Engine")
st.write("Powered by an XGBoost & Poisson Ensemble Model")
st.markdown("---")

# 1. LIVE MATCH SCOREBOARD
st.subheader("Live Fixtures & Scores")
fixtures = get_all_fixtures()

if fixtures:
    formatted_fixtures = []
    for f in fixtures:
        match = f"{f['home_team']} vs {f['away_team']}"
        if f['real_home_score'] is not None:
            actual = f"{f['real_home_score']} - {f['real_away_score']}"
        else:
            actual = "TBD"
            
        formatted_fixtures.append({
            "Match Date": f['match_date'],
            "Match": match,
            "Score": actual,
            "Status": f['status']
        })
    df_fix = pd.DataFrame(formatted_fixtures)
    st.dataframe(df_fix, use_container_width=True, hide_index=True)
else:
    st.info("No fixtures found in database.")

st.markdown("---")

# 2. SUMMARY METRICS
st.subheader("Engine Accuracy Metrics")
stats = get_summary()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Total Predictions Scored", value=stats["total"])
with col2:
    st.metric(label="Exact Score Hits", value=stats["exact"])
with col3:
    st.metric(label="Exact Score %", value=f"{stats['exact_pct']}%")
with col4:
    st.metric(label="Correct Outcome %", value=f"{stats['acc_pct']}%")

st.markdown("---")

# 3. LEADERBOARD
st.subheader("Model Leaderboard")
leaderboard = get_leaderboard()

if leaderboard:
    # Clean up the raw leaderboard data for display
    formatted_lb = []
    for rank, l in enumerate(leaderboard, 1):
        formatted_lb.append({
            "Rank": f"#{rank}",
            "Model": l['model_name'],
            "Points": l['total_points'] or 0,
            "Exact Scores": l['exact_scores_count'] or 0,
            "Accuracy": f"{round((l['correct_outcomes'] or 0) / (l['scored_preds'] or 1) * 100, 1)}%"
        })
    df_lb = pd.DataFrame(formatted_lb)
    st.dataframe(df_lb, use_container_width=True, hide_index=True)
else:
    st.info("No models scored yet.")

st.markdown("---")

# 4. RECENT PREDICTIONS
st.subheader("Recent Predictions")
predictions = get_recent_predictions()

if predictions:
    # Clean up the raw data into a beautiful, readable format
    formatted_data = []
    for p in predictions:
        match = f"{p['home_team']} vs {p['away_team']}"
        pred = f"{p['predicted_home_score']}-{p['predicted_away_score']}"
        
        if p['real_home_score'] is not None:
            actual = f"{p['real_home_score']}-{p['real_away_score']}"
        else:
            actual = "TBD"
            
        formatted_data.append({
            "Match": match,
            "Prediction": pred,
            "Actual Result": actual,
            "Points": p['points_awarded'] if p['points_awarded'] is not None else "-",
            "Model": p['model_name'],
            "Date": p['match_date']
        })

    df = pd.DataFrame(formatted_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No predictions scored yet.")
