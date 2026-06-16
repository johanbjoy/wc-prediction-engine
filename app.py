import streamlit as st
import pandas as pd
from data.database import get_upcoming_predictions, get_completed_predictions, get_leaderboard, get_summary, get_all_fixtures

def render_prediction_cards(predictions):
    if not predictions:
        st.info("No predictions in this category yet.")
        return

    html_cards = "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 20px;'>"
    for p in predictions:
        home, away = p['home_team'], p['away_team']
        pred_h, pred_a = p['predicted_home_score'], p['predicted_away_score']
        real_h = p['real_home_score']
        real_a = p['real_away_score']
        pts = p['points_awarded']
        
        # Format match date string
        raw_date = p.get('match_date', '')
        if hasattr(raw_date, 'strftime'):
            date_str = raw_date.strftime('%b %d, %Y - %H:%M')
        else:
            date_str = str(raw_date)[:16] if raw_date else "TBD"
        
        h_flag = TEAM_FLAGS.get(home, "⚽")
        a_flag = TEAM_FLAGS.get(away, "⚽")

        # Visual pill for the actual result
        if pts == 3:
            pill = f"<span style='background-color:rgba(34,197,94,0.15); color:#22c55e; padding:3px 8px; border-radius:12px; font-size:0.7rem; font-weight:bold;'>✓✓ EXACT ({real_h}-{real_a})</span>"
        elif pts == 1:
            pill = f"<span style='background-color:rgba(234,179,8,0.15); color:#eab308; padding:3px 8px; border-radius:12px; font-size:0.7rem; font-weight:bold;'>✓ WINNER ({real_h}-{real_a})</span>"
        elif pts == 0:
            pill = f"<span style='background-color:rgba(239,68,68,0.15); color:#ef4444; padding:3px 8px; border-radius:12px; font-size:0.7rem; font-weight:bold;'>✗ WRONG ({real_h}-{real_a})</span>"
        else:
            pill = "<span style='background-color:#3c4043; color:#9aa0a6; padding:3px 8px; border-radius:12px; font-size:0.7rem; font-weight:bold;'>PENDING</span>"

        card = f"""<div style="background-color: #202124; border: 1px solid #3c4043; border-radius: 8px; padding: 16px; font-family: Roboto, Arial, sans-serif;">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
        <span style="color: #9aa0a6; font-size: 0.75rem; text-transform: uppercase;">{date_str}</span>
        {pill}
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 1.2rem;">{h_flag}</span>
            <span style="color: #e8eaed; font-size: 1rem;">{home}</span>
        </div>
        <span style="color: #8ab4f8; font-size: 1.2rem; font-weight: bold;">{pred_h}</span>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 1.2rem;">{a_flag}</span>
            <span style="color: #e8eaed; font-size: 1rem;">{away}</span>
        </div>
        <span style="color: #8ab4f8; font-size: 1.2rem; font-weight: bold;">{pred_a}</span>
    </div>
</div>"""
        html_cards += card
        
    html_cards += "</div>"
    st.markdown(html_cards, unsafe_allow_html=True)

st.set_page_config(page_title="World Cup Engine", layout="wide")

st.title("🏆 World Cup 2026 Prediction Engine")
st.write("Powered by an XGBoost & Poisson Ensemble Model")
st.markdown("---")

# Comprehensive Flag Mapper
TEAM_FLAGS = {
    "Belgium": "🇧🇪", "Egypt": "🇪🇬", "Saudi Arabia": "🇸🇦", "Uruguay": "🇺🇾", 
    "Iran": "🇮🇷", "New Zealand": "🇳🇿", "Argentina": "🇦🇷", "Algeria": "🇩🇿",
    "France": "🇫🇷", "Senegal": "🇸🇳", "Portugal": "🇵🇹", "Brazil": "🇧🇷",
    "USA": "🇺🇸", "Mexico": "🇲🇽", "Canada": "🇨🇦", "Spain": "🇪🇸", "Germany": "🇩🇪",
    "Czech Republic": "🇨🇿", "Sweden": "🇸🇪", "Jordan": "🇯🇴", "Uzbekistan": "🇺🇿", 
    "South Korea": "🇰🇷", "Colombia": "🇨🇴", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Cape Verde": "🇨🇻", 
    "South Africa": "🇿🇦", "Ghana": "🇬🇭", "Japan": "🇯🇵", "Ivory Coast": "🇨🇮", 
    "Iraq": "🇮🇶", "Turkey": "🇹🇷", "Switzerland": "🇨🇭", "Ecuador": "🇪🇨", 
    "Norway": "🇳🇴", "Qatar": "🇶🇦", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Netherlands": "🇳🇱", 
    "Paraguay": "🇵🇾", "Austria": "🇦🇹", "Australia": "🇦🇺", "Bosnia & Herzegovina": "🇧🇦", 
    "Panama": "🇵🇦", "Croatia": "🇭🇷", "Tunisia": "🇹🇳", "Morocco": "🇲🇦", 
    "Curaçao": "🇨🇼", "Haiti": "🇭🇹", "DR Congo": "🇨🇩"
}



# 1. COMPLETED PREDICTIONS
st.subheader("Historical & Completed Predictions")
completed = get_completed_predictions()
render_prediction_cards(completed)

st.markdown("---")

# 2. UPCOMING PREDICTIONS
st.subheader("Upcoming Predictions")
upcoming = get_upcoming_predictions()
render_prediction_cards(upcoming)

st.markdown("---")

# 3. SUMMARY METRICS
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

# 4. LEADERBOARD
st.subheader("Model Leaderboard")
leaderboard = get_leaderboard()

if leaderboard:
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
