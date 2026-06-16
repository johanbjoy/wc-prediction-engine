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
    html_cards = "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 20px;'>"
    
    # Simple flag mapper for aesthetics
    flags = {
        "Belgium": "🇧🇪", "Egypt": "🇪🇬", "Saudi Arabia": "🇸🇦", "Uruguay": "🇺🇾", 
        "Iran": "🇮🇷", "New Zealand": "🇳🇿", "Argentina": "🇦🇷", "Algeria": "🇩🇿",
        "France": "🇫🇷", "Senegal": "🇸🇳", "Portugal": "🇵🇹", "Brazil": "🇧🇷",
        "USA": "🇺🇸", "Mexico": "🇲🇽", "Canada": "🇨🇦", "Spain": "🇪🇸", "Germany": "🇩🇪"
    }

    for f in fixtures:
        home, away = f['home_team'], f['away_team']
        h_score = f['real_home_score'] if f['real_home_score'] is not None else ""
        a_score = f['real_away_score'] if f['real_away_score'] is not None else ""
        status = f['status'] if f['status'] else "Upcoming"
        if status == "FT": status = "FT<br><span style='font-size:0.75rem; color:#8ab4f8;'>Today</span>"
        
        h_flag = flags.get(home, "⚽")
        a_flag = flags.get(away, "⚽")

        card = f"""
        <div style="background-color: #202124; border: 1px solid #3c4043; border-radius: 8px; padding: 16px; font-family: Roboto, Arial, sans-serif;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <span style="color: #9aa0a6; font-size: 0.85rem;">World Cup 2026</span>
                <span style="color: #9aa0a6; font-size: 0.85rem; text-align: right;">{status}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.2rem;">{h_flag}</span>
                    <span style="color: #e8eaed; font-size: 1rem;">{home}</span>
                </div>
                <span style="color: #e8eaed; font-size: 1.1rem; font-weight: 500;">{h_score}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.2rem;">{a_flag}</span>
                    <span style="color: #e8eaed; font-size: 1rem;">{away}</span>
                </div>
                <span style="color: #e8eaed; font-size: 1.1rem; font-weight: 500;">{a_score}</span>
            </div>
        </div>
        """
        html_cards += card
        
    html_cards += "</div>"
    st.markdown(html_cards, unsafe_allow_html=True)
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
