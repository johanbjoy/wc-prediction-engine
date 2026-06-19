import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

from data.database import get_completed_predictions, get_upcoming_predictions, get_summary

# Page config
st.set_page_config(
    page_title="N.E.X.U.S. V2 - World Cup 2026",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# WORLD CUP 2026 THEME COLORS
# ============================================
WC2026_COLORS = {
    'primary': '#E31B23',      # FIFA Red
    'secondary': '#002B5C',    # FIFA Dark Blue
    'accent': '#FFD700',       # Gold (trophy)
    'background': '#F5F5F5',   # Light gray
    'white': '#FFFFFF',
    'green': '#009E60',        # Pitch green
    'dark': '#1A1A1A'
}

# Custom CSS for Premium Dark UI
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@400;600&display=swap');

.stApp {
    background-color: #050505;
    background-image: radial-gradient(#1a1a1a 1px, transparent 1px);
    background-size: 20px 20px;
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
}
.header-text {
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 5rem !important;
    letter-spacing: -2px;
    background: linear-gradient(to bottom right, #ffffff, #94a3b8, #475569);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 0px;
    margin-top: 20px;
    animation: fadeInDown 1s ease-out;
    filter: drop-shadow(0 0 15px rgba(255,255,255,0.1));
}
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
}
.subheader-text {
    font-family: 'Outfit', sans-serif;
    color: #cbd5e1;
    font-size: 1.2rem;
    text-align: center;
    margin-bottom: 30px;
    margin-top: -10px;
    font-weight: 300;
    letter-spacing: 2px;
    text-transform: uppercase;
}
.metric-card {
    background: rgba(10, 10, 10, 0.8);
    backdrop-filter: blur(12px);
    border: 1px solid #333333;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}
.metric-card:hover {
    transform: translateY(-5px);
    border-color: #3b82f6;
    box-shadow: 0 4px 30px rgba(59, 130, 246, 0.2);
}
.match-card {
    background: rgba(15, 15, 15, 0.9);
    border: 1px solid #262626;
    border-radius: 12px;
    padding: 20px;
    margin: 15px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    transition: all 0.3s ease;
}
.match-card:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 20px rgba(59, 130, 246, 0.15);
}
div[data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 2.5rem !important;
    color: #ffffff;
}

/* Premium Web App Styles */
body {
    background: radial-gradient(circle at top right, #0f172a, #000000) !important;
    color: #f8fafc !important;
}
.header-text {
    background: linear-gradient(to right, #3b82f6, #8b5cf6, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shine 5s linear infinite;
    background-size: 200% auto;
}
@keyframes shine {
    to { background-position: 200% center; }
}
.score-card {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 20px 25px;
    margin: 15px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1);
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.score-card:hover {
    border-color: rgba(59, 130, 246, 0.5);
    box-shadow: 0 10px 40px rgba(59, 130, 246, 0.2), inset 0 1px 0 rgba(255,255,255,0.2);
    transform: translateY(-5px) scale(1.02);
}
.score-team {
    font-family: 'Inter', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    color: #f8fafc;
    flex: 1;
    letter-spacing: -0.5px;
}
.score-home { text-align: right; }
.score-away { text-align: left; }
.score-center {
    flex: 0.6;
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
}
.score-center::before {
    content: '';
    position: absolute;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle, rgba(59,130,246,0.1) 0%, transparent 70%);
    z-index: 0;
}
.score-actual {
    font-size: 2.5rem;
    font-weight: 900;
    font-family: 'Outfit', sans-serif;
    color: #ffffff;
    letter-spacing: 4px;
    text-shadow: 0 0 20px rgba(255,255,255,0.3);
    z-index: 1;
}
.badge-exact {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
    box-shadow: 0 0 15px rgba(16, 185, 129, 0.6);
    margin-top: 8px;
    z-index: 1;
    animation: pulseBadge 2s infinite;
}
@keyframes pulseBadge {
    0% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.4); }
    50% { box-shadow: 0 0 20px rgba(16, 185, 129, 0.8); }
    100% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.4); }
}
.badge-correct {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.5);
    color: #93c5fd;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: bold;
    text-transform: uppercase;
    margin-top: 8px;
    z-index: 1;
}
.badge-wrong {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.5);
    color: #fca5a5;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: bold;
    text-transform: uppercase;
    margin-top: 8px;
    z-index: 1;
}
.predicted-sub {
    font-size: 0.85rem;
    color: #94a3b8;
    margin-top: 2px;
    font-weight: 500;
    z-index: 1;
}
/* Bracket Animations */
.bracket-node {
    animation: slideInRight 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
    opacity: 0;
}
@keyframes slideInRight {
    from { opacity: 0; transform: translateX(-30px); }
    to { opacity: 1; transform: translateX(0); }
}
.champ-card {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(180, 83, 9, 0.3));
    border: 2px solid #f59e0b;
    box-shadow: 0 0 30px rgba(245, 158, 11, 0.3);
    animation: goldenPulse 2s infinite;
}
@keyframes goldenPulse {
    0% { box-shadow: 0 0 20px rgba(245, 158, 11, 0.2); }
    50% { box-shadow: 0 0 40px rgba(245, 158, 11, 0.5); }
    100% { box-shadow: 0 0 20px rgba(245, 158, 11, 0.2); }
}
/* Log Console */
.log-console {
    background-color: #050505;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 20px;
    font-family: 'JetBrains Mono', 'Courier New', Courier, monospace;
    font-size: 0.85rem;
    height: 300px;
    overflow-y: auto;
    margin-bottom: 25px;
    box-shadow: inset 0 0 20px rgba(0,0,0,0.8), 0 0 15px rgba(16, 185, 129, 0.1);
    position: relative;
}
.log-console::after {
    content: " ";
    display: block;
    position: absolute;
    top: 0; left: 0; bottom: 0; right: 0;
    background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
    z-index: 2;
    background-size: 100% 2px, 3px 100%;
    pointer-events: none;
}
.log-line {
    margin: 4px 0;
    line-height: 1.5;
    text-shadow: 0 0 5px rgba(255,255,255,0.3);
}
.log-time {
    color: #64748b;
    margin-right: 12px;
}
.log-model {
    color: #3b82f6;
    font-weight: bold;
    margin-right: 12px;
}
.log-warn {
    color: #f59e0b;
}
.log-err {
    color: #ef4444;
}
.blinking-cursor {
    display: inline-block;
    width: 8px;
    height: 15px;
    background-color: #10b981;
    animation: blink 1s step-end infinite;
    vertical-align: middle;
    margin-left: 5px;
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}
@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0; }
    100% { opacity: 1; }
}
</style>
""", unsafe_allow_html=True)

# ============================================
# HEADER SECTION
# ============================================
def get_flag(team):
    flags = {
        "Mexico": "🇲🇽", "Canada": "🇨🇦", "USA": "🇺🇸", "Brazil": "🇧🇷", "Argentina": "🇦🇷",
        "France": "🇫🇷", "Germany": "🇩🇪", "Spain": "🇪🇸", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Portugal": "🇵🇹",
        "Italy": "🇮🇹", "Netherlands": "🇳🇱", "Belgium": "🇧🇪", "Croatia": "🇭🇷", "Uruguay": "🇺🇾",
        "Colombia": "🇨🇴", "Japan": "🇯🇵", "South Korea": "🇰🇷", "Senegal": "🇸🇳", "Morocco": "🇲🇦",
        "Switzerland": "🇨🇭", "Ecuador": "🇪🇨", "Ghana": "🇬🇭", "Cameroon": "🇨🇲", "Iran": "🇮🇷",
        "Saudi Arabia": "🇸🇦", "Australia": "🇦🇺", "Tunisia": "🇹🇳", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "Poland": "🇵🇱",
        "Serbia": "🇷🇸", "Denmark": "🇩🇰", "Costa Rica": "🇨🇷", "Sweden": "🇸🇪", "Peru": "🇵🇪",
        "Chile": "🇨🇱", "Nigeria": "🇳🇬", "Egypt": "🇪🇬", "Ivory Coast": "🇨🇮", "Algeria": "🇩🇿",
        "DR Congo": "🇨🇩", "South Africa": "🇿🇦", "Mali": "🇲🇱", "Bosnia & Herzegovina": "🇧🇦",
        "Czech Republic": "🇨🇿", "Norway": "🇳🇴", "Qatar": "🇶🇦", "Uzbekistan": "🇺🇿",
        "Jordan": "🇯🇴", "New Zealand": "🇳🇿", "Panama": "🇵🇦", "Cape Verde": "🇨🇻", "Curaçao": "🇨🇼",
        "Jamaica": "🇯🇲", "Honduras": "🇭🇳", "El Salvador": "🇸🇻", "Iraq": "🇮🇶"
    }
    return flags.get(team, "🏳️")

st.markdown('<div class="header-text" style="font-size: 5rem; letter-spacing: -2px; margin-top: 20px;">N.E.X.U.S.</div>', unsafe_allow_html=True)
st.markdown('<div class="subheader-text">AI-Powered Football Prediction Engine | CatBoost + Transformer Hybrid</div>', unsafe_allow_html=True)


# ============================================
# LIVE ENGINE CONSOLE
# ============================================
st.markdown("### ⚡ Live Autonomous Engine Status")
log_content = ""
try:
    with open("nexus.log", "r") as f:
        lines = f.readlines()[-20:] # Get last 20 lines
        for line in lines:
            line = line.strip()
            if not line: continue
            time_str = datetime.now().strftime("%H:%M:%S")
            if "WARNING" in line:
                log_content += f'<div class="log-line"><span class="log-time">[{time_str}]</span><span class="log-model">N.E.X.U.S.</span><span class="log-warn">{line}</span></div>'
            elif "ERROR" in line:
                log_content += f'<div class="log-line"><span class="log-time">[{time_str}]</span><span class="log-model">N.E.X.U.S.</span><span class="log-err">{line}</span></div>'
            else:
                log_content += f'<div class="log-line"><span class="log-time">[{time_str}]</span><span class="log-model">N.E.X.U.S.</span><span>{line}</span></div>'
except Exception:
    time_str = datetime.now().strftime("%H:%M:%S")
    log_content = f'<div class="log-line"><span class="log-time">[{time_str}]</span><span class="log-model">N.E.X.U.S.</span><span>SYSTEM INITIALIZED. Awaiting live data stream...</span></div>'

st.markdown(f"""
<div class="log-console" id="logConsole">
    {log_content}
    <div class="log-line"><span class="log-time">[{datetime.now().strftime("%H:%M:%S")}]</span><span class="log-model">SYSTEM</span><span>Watching for pipeline triggers...</span><span class="blinking-cursor"></span></div>
</div>
<script>
    var consoleDiv = document.getElementById("logConsole");
    consoleDiv.scrollTop = consoleDiv.scrollHeight;
</script>
""", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ============================================
# LOAD REAL DATA
# ============================================
@st.cache_data(ttl=300)
def load_worldcup_data():
    """Load actual prediction data from our Postgres DB"""
    comp = get_completed_predictions()
    upc = get_upcoming_predictions(limit=50)
    
    # Process rows into a unified DataFrame
    all_rows = []
    
    for row in comp + upc:
        # Parse probabilities
        probs = {}
        if isinstance(row.get("meta_json"), str):
            try:
                meta = json.loads(row["meta_json"])
                if "probabilities" in meta:
                    probs = meta["probabilities"]
                elif "dixon_coles_probs" in meta:
                    probs = meta["dixon_coles_probs"]
            except:
                pass
        elif isinstance(row.get("meta_json"), dict):
            meta = row["meta_json"]
            if "probabilities" in meta:
                probs = meta["probabilities"]
            elif "dixon_coles_probs" in meta:
                probs = meta["dixon_coles_probs"]
            
        h_prob = probs.get("p_home_win", 0.0)
        d_prob = probs.get("p_draw", 0.0)
        a_prob = probs.get("p_away_win", 0.0)
        
        # Predicted outcome letter
        pred_out = 'D'
        if h_prob > d_prob and h_prob > a_prob: pred_out = 'H'
        elif a_prob > h_prob and a_prob > d_prob: pred_out = 'A'
            
        # Parse actual results
        actual_out = None
        actual_score = None
        h_score = row.get("real_home_score")
        a_score = row.get("real_away_score")
        if h_score is not None and a_score is not None:
            actual_score = f"{h_score}-{a_score}"
            if h_score > a_score: actual_out = 'H'
            elif a_score > h_score: actual_out = 'A'
            else: actual_out = 'D'
            
        # Try to parse match date
        try:
            m_date = pd.to_datetime(row.get("match_date", ""))
        except:
            m_date = pd.to_datetime("2026-06-01 15:00:00")
            
        is_upcoming = actual_out is None
        
        # Process model accuracy if historical
        model_acc = 0.0
        if not is_upcoming and row.get("points_awarded") is not None:
            pts = row.get("points_awarded")
            if pts == 3: model_acc = 1.0 # Exact score
            elif pts == 1: model_acc = 0.5 # Correct result
            else: model_acc = 0.0
        
        all_rows.append({
            'match_id': row.get("fixture_id", 0),
            'match_date': m_date,
            'home_team': row.get("home_team"),
            'away_team': row.get("away_team"),
            'stage': 'Qualifiers' if 'Q' in row.get("home_team", "") else 'Group Stage',
            'home_elo': 1800 + (h_prob * 200), # Approximation since not stored
            'away_elo': 1800 + (a_prob * 200),
            'home_xg': h_prob * 2.5, # Approximation
            'away_xg': a_prob * 2.5,
            'home_win_prob': h_prob,
            'draw_prob': d_prob,
            'away_win_prob': a_prob,
            'predicted_result': pred_out,
            'pred_h_score': row.get("predicted_home_score"),
            'pred_a_score': row.get("predicted_away_score"),
            'actual_result': actual_out,
            'actual_score': actual_score,
            'model_accuracy': model_acc if not is_upcoming else 0.0,
            'is_upcoming': is_upcoming
        })
        
    df = pd.DataFrame(all_rows)
    if len(df) > 0:
        df['match_date'] = pd.to_datetime(df['match_date'], utc=True).dt.tz_convert('Asia/Kolkata')
    
    # Ensure there's data even if DB is empty
    if len(df) == 0:
        return pd.DataFrame(columns=[
            'match_id', 'match_date', 'home_team', 'away_team', 'stage', 
            'home_elo', 'away_elo', 'home_xg', 'away_xg', 'home_win_prob', 
            'draw_prob', 'away_win_prob', 'predicted_result', 'actual_result', 
            'actual_score', 'model_accuracy', 'is_upcoming'
        ])
    return df

df = load_worldcup_data()

# Filter data
if len(df) > 0:
    # Remove confidence filter since sidebar is removed. Show all.
    filtered_df = df
else:
    filtered_df = df

# ============================================
# KEY METRICS ROW
# ============================================
st.header("📊 Model Performance Metrics")

if len(filtered_df) > 0:
    # Calculate metrics
    total_matches = len(filtered_df)
    historical_matches = len(filtered_df[~filtered_df['is_upcoming']])
    upcoming_matches = len(filtered_df[filtered_df['is_upcoming']])
    
    correct_predictions = len(filtered_df[
        (~filtered_df['is_upcoming']) & 
        (filtered_df['predicted_result'] == filtered_df['actual_result'])
    ])
    
    accuracy = correct_predictions / historical_matches if historical_matches > 0 else 0.0

    # Real DB summary
    db_summary = get_summary()
    if db_summary.get("total", 0) > 0:
        accuracy = db_summary["acc_pct"] / 100.0
        correct_predictions = db_summary["correct"]
        historical_matches = db_summary["total"]
else:
    total_matches = 0
    historical_matches = 0
    upcoming_matches = 0
    accuracy = 0.0
    correct_predictions = 0

# Metrics row via HTML for CSS class injection
wrong_predictions = historical_matches - correct_predictions

st.markdown(f"""
<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;">
    <div class="metric-card">
        <div style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 5px;">🏆 Total Completed Matches</div>
        <div style="font-size: 2.5rem; font-weight: 800; font-family: 'Outfit'; color: #f8fafc;">{historical_matches}</div>
        <div style="color: #3b82f6; font-size: 0.8rem; margin-top: 5px;">+{upcoming_matches} upcoming</div>
    </div>
    <div class="metric-card">
        <div style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 5px;">🎯 Current Accuracy</div>
        <div style="font-size: 2.5rem; font-weight: 800; font-family: 'Outfit'; color: #f8fafc;">{accuracy:.1%}</div>
        <div style="color: #10b981; font-size: 0.8rem; margin-top: 5px;">Adaptive Momentum Active</div>
    </div>
    <div class="metric-card">
        <div style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 5px;">✅ Correct Predictions</div>
        <div style="font-size: 2.5rem; font-weight: 800; font-family: 'Outfit'; color: #10b981;">{correct_predictions}</div>
        <div style="color: #8b5cf6; font-size: 0.8rem; margin-top: 5px;">Predicted exact outcome</div>
    </div>
    <div class="metric-card">
        <div style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 5px;">❌ Incorrect Predictions</div>
        <div style="font-size: 2.5rem; font-weight: 800; font-family: 'Outfit'; color: #ef4444;">{wrong_predictions}</div>
        <div style="color: #f59e0b; font-size: 0.8rem; margin-top: 5px;">Upsets & Draws</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

if len(filtered_df) == 0:
    st.warning("No data found matching current filters.")
    st.stop()

# ============================================
# TABS: HISTORY, UPCOMING, SIMULATION
# ============================================
tab1, tab2, tab3 = st.tabs(["📜 Prediction History", "📅 Upcoming Matches", "🏆 Projected Bracket"])

# ============================================
# TAB 1: PREDICTION HISTORY
# ============================================
with tab1:
    st.subheader("📜 Historical Prediction Performance")
    
    # Filter historical matches only
    historical_df = filtered_df[~filtered_df['is_upcoming']]
    
    st.markdown("### 📊 Detailed Match History")
    
    if len(historical_df) > 0:
        history_cols = ['match_date', 'home_team', 'away_team', 'stage', 
                       'home_win_prob', 'predicted_result', 'actual_result', 
                       'actual_score', 'pred_h_score', 'pred_a_score', 'model_accuracy']
        
        history_df_display = historical_df[history_cols].copy()
        # Format date WITH TIME in IST
        history_df_display['match_date'] = history_df_display['match_date'].dt.strftime('%B %d, %Y at %I:%M %p IST')
        
        cards_html = "<div>"
        for _, row in history_df_display.iterrows():
            date = row['match_date']
            home = row['home_team']
            away = row['away_team']
            pred = row['predicted_result']
            actual = row['actual_result']
            act_score_str = row['actual_score']
            pred_h = row['pred_h_score']
            pred_a = row['pred_a_score']
            acc = row['model_accuracy']
            
            # Flags
            home_flag = get_flag(home)
            away_flag = get_flag(away)
            
            # Formatted predicted string
            if pd.notna(pred_h) and pd.notna(pred_a):
                pred_str = f"Predicted: {int(pred_h)}-{int(pred_a)}"
            else:
                pred_str = f"Predicted: {pred}"
            
            # Exact score check logic using model_accuracy (1.0 = exact, 0.5 = correct outcome)
            if acc == 1.0:
                badge = '<div class="badge-exact">🎯 Exact Score</div>'
            elif acc > 0.0 or pred == actual:
                badge = '<div class="badge-correct">✅ Correct Winner</div>'
            else:
                badge = '<div class="badge-wrong">❌ Incorrect</div>'
                
            cards_html += f"""
<div class="score-card">
    <div class="score-team score-home">{home_flag} {home}</div>
    <div class="score-center">
        <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 5px;">{date}</div>
        <div class="score-actual">{act_score_str}</div>
        <div class="predicted-sub">{pred_str}</div>
        {badge}
    </div>
    <div class="score-team score-away">{away} {away_flag}</div>
</div>
"""
        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

# ============================================
# TAB 2: UPCOMING MATCHES
# ============================================
with tab2:
    st.subheader("📅 Upcoming World Cup Matches")
    
    upcoming_df = filtered_df[filtered_df['is_upcoming']].sort_values('match_date')
    
    if len(upcoming_df) == 0:
        st.info("No upcoming matches are scheduled at this time. Awaiting API sync.")
    else:
        st.markdown("### ⚡ Live Autonomous Predictions")
        
        upcoming_cols = ['match_date', 'home_team', 'away_team', 'stage',
                        'home_win_prob', 'draw_prob', 'away_win_prob',
                        'pred_h_score', 'pred_a_score']
        
        upcoming_df_display = upcoming_df[upcoming_cols].copy()
        upcoming_df_display['match_date'] = upcoming_df_display['match_date'].dt.strftime('%B %d, %Y at %I:%M %p IST')
        
        cards_html = "<div>"
        for _, row in upcoming_df_display.iterrows():
            date = row['match_date']
            home = row['home_team']
            away = row['away_team']
            pred_h = row['pred_h_score']
            pred_a = row['pred_a_score']
            
            home_flag = get_flag(home)
            away_flag = get_flag(away)
            
            # Formatted predicted string
            if pd.notna(pred_h) and pd.notna(pred_a):
                pred_str = f"{int(pred_h)} - {int(pred_a)}"
            else:
                pred_str = "TBD"
            
            # Subtext logic
            if row['home_win_prob'] > row['away_win_prob'] and row['home_win_prob'] > row['draw_prob']:
                sub_str = f"Favored: {home} ({row['home_win_prob']:.1%})"
                color = "#3b82f6"
            elif row['away_win_prob'] > row['home_win_prob'] and row['away_win_prob'] > row['draw_prob']:
                sub_str = f"Favored: {away} ({row['away_win_prob']:.1%})"
                color = "#10b981"
            else:
                sub_str = f"Favored: Draw ({row['draw_prob']:.1%})"
                color = "#f59e0b"

            cards_html += f"""
<div class="score-card" style="border-color: rgba(59, 130, 246, 0.3);">
    <div class="score-team score-home">{home_flag} {home}</div>
    <div class="score-center">
        <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 5px;">{date}</div>
        <div class="score-actual" style="font-size: 1.8rem; color: #3b82f6; letter-spacing: 2px;">{pred_str}</div>
        <div class="predicted-sub" style="color: {color}; font-weight: bold; margin-top: 5px;">{sub_str}</div>
    </div>
    <div class="score-team score-away">{away} {away_flag}</div>
</div>
"""
        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)


# ============================================
# TAB 3: SIMULATION BRACKET
# ============================================
with tab3:
    st.subheader("🏆 N.E.X.U.S. V2 Simulated Tournament Bracket")
    st.markdown("This tab displays a full 100% autonomous simulation of the 2026 World Cup from the projected 48 qualified teams down to the final champion, predicted by the **PyTorch Transformer**.")
    
    import os
    bracket_file = "tournament_bracket.json"
    if os.path.exists(bracket_file):
        with open(bracket_file, "r") as f:
            bracket_data = json.load(f)
            
        champ = bracket_data.get("champion", "TBD")
        champ_flag = get_flag(champ)
        st.markdown(f"""
        <div class="champ-card" style="padding: 30px; border-radius: 20px; text-align: center; margin: 20px 0;">
            <h2 style="color: #f59e0b; margin-bottom: 5px; font-family: 'Inter';">WORLD CHAMPION 2026</h2>
            <h1 style="color: #f8fafc; font-size: 3.5rem; margin: 0; text-transform: uppercase; font-family: 'Outfit';">{champ_flag} 🏆 {champ} 🏆 {champ_flag}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🌳 Knockout Stages")
        
        # Group matches by stage
        stages = ["Final", "Semi Finals", "Quarter Finals", "Round of 16", "Round of 32"]
        
        delay = 0.2
        for stage in stages:
            stage_matches = [m for m in bracket_data.get("matches", []) if m["stage"] == stage]
            if not stage_matches: continue
            
            st.markdown(f"<h4 style='color: #3b82f6; margin-top: 30px;'>{stage}</h4>", unsafe_allow_html=True)
            
            # Using custom HTML grid for bracket nodes instead of st.columns for better animation control
            bracket_html = f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">'
            
            for match in stage_matches:
                home = match['home']
                away = match['away']
                hs = match['home_score']
                _as = match['away_score']
                winner = match['winner']
                
                home_flag = get_flag(home)
                away_flag = get_flag(away)
                
                home_color = "#10b981" if winner == home else "#64748b"
                away_color = "#10b981" if winner == away else "#64748b"
                
                conf = max(match['home_prob'], match['away_prob'])
                
                bracket_html += f"""
<div class="bracket-node" style="animation-delay: {delay}s; background: rgba(15,15,15,0.8); border: 1px solid #262626; border-radius: 10px; padding: 12px; position: relative; overflow: hidden;">
    <div style="position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: {'#10b981' if hs > _as else '#3b82f6'};"></div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-weight: bold; color: {home_color}; font-family: 'Inter';">{home_flag} {home}</span>
        <span style="font-weight: 900; font-size: 1.2rem; color: #f8fafc; font-family: 'Outfit';">{hs}</span>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-weight: bold; color: {away_color}; font-family: 'Inter';">{away_flag} {away}</span>
        <span style="font-weight: 900; font-size: 1.2rem; color: #f8fafc; font-family: 'Outfit';">{_as}</span>
    </div>
    <div style="text-align: right; margin-top: 8px; font-size: 0.7rem; color: #475569;">
        N.E.X.U.S. Confidence: {conf:.1%}
    </div>
</div>
"""
                delay += 0.1
            
            bracket_html += "</div>"
            st.markdown(bracket_html, unsafe_allow_html=True)
                    
    else:
        st.info("The Tournament Simulation is currently compiling. Please check back in a few minutes when the backfill is complete.")

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; color: {WC2026_COLORS['secondary']};">
        <p>🏆 N.E.X.U.S. V2 - World Cup 2026 Prediction Engine</p>
        <p>Built with PyTorch Transformers + DeepSeek-R1 + Groq (Llama-3) | Math Baseline: 65.0%</p>
        <p>Data sourced from API-Football & StatsBomb | Real-time updates every 30 minutes</p>
    </div>
    """,
    unsafe_allow_html=True
)
