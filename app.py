import streamlit as st
import pandas as pd
import json, re
from datetime import datetime, timedelta
from data.database import get_upcoming_predictions, get_completed_predictions, get_leaderboard, get_summary, get_all_fixtures

# ─── PAGE CONFIG ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WC 2026 Prediction Engine",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── COMPREHENSIVE FLAG MAPPER ─────────────────────────────────────────────
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


# ─── GLOBAL CSS INJECTION ──────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* Global overrides */
    .stApp { background: linear-gradient(135deg, #0a0e1a 0%, #111827 40%, #0f172a 100%); }
    .stApp header { background: transparent !important; }
    .stMarkdown, .stApp, p, span, label { font-family: 'Inter', sans-serif !important; }
    h1, h2, h3 { font-family: 'Inter', sans-serif !important; }

    /* Hide Streamlit chrome */
    #MainMenu, footer, .stDeployButton { display: none !important; }

    /* Section headers */
    .section-header {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 1.4rem;
        color: #e2e8f0;
        margin-bottom: 20px;
        padding-left: 12px;
        border-left: 3px solid #6366f1;
        letter-spacing: -0.02em;
    }

    /* Metric card styling */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(139,92,246,0.06) 100%);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 12px;
        padding: 16px 20px;
        backdrop-filter: blur(12px);
    }
    [data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #e2e8f0 !important;
        font-weight: 800 !important;
        font-size: 1.8rem !important;
    }

    /* Dataframe overrides */
    .stDataFrame { border-radius: 12px; overflow: hidden; }

    /* Card grid */
    .prediction-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(370px, 1fr));
        gap: 20px;
        margin-bottom: 28px;
    }

    /* Prediction card */
    .pred-card {
        background: linear-gradient(145deg, rgba(30,41,59,0.85) 0%, rgba(15,23,42,0.95) 100%);
        border: 1px solid rgba(99,102,241,0.15);
        border-radius: 16px;
        padding: 20px 22px;
        font-family: 'Inter', sans-serif;
        backdrop-filter: blur(20px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .pred-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #6366f1, #a78bfa, #6366f1);
        opacity: 0.6;
    }
    .pred-card:hover {
        border-color: rgba(99,102,241,0.4);
        transform: translateY(-3px);
        box-shadow: 0 12px 40px rgba(99,102,241,0.12);
    }

    /* Card header */
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }
    .card-date {
        color: #64748b;
        font-size: 0.72rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* Result badges */
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.65rem; font-weight: 700; letter-spacing: 0.04em; }
    .badge-exact { background: rgba(16,185,129,0.12); color: #34d399; border: 1px solid rgba(16,185,129,0.25); }
    .badge-winner { background: rgba(245,158,11,0.12); color: #fbbf24; border: 1px solid rgba(245,158,11,0.25); }
    .badge-wrong { background: rgba(239,68,68,0.1); color: #f87171; border: 1px solid rgba(239,68,68,0.2); }
    .badge-pending { background: rgba(99,102,241,0.1); color: #818cf8; border: 1px solid rgba(99,102,241,0.2); }

    /* Team rows */
    .team-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
    }
    .team-info { display: flex; align-items: center; gap: 12px; }
    .team-flag { font-size: 1.5rem; }
    .team-name { color: #e2e8f0; font-size: 0.95rem; font-weight: 500; }
    .team-score {
        font-size: 1.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #818cf8, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* VS divider */
    .vs-divider {
        text-align: center;
        color: #475569;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        padding: 2px 0;
    }

    /* Probability bar */
    .prob-container {
        margin-top: 14px;
        padding-top: 14px;
        border-top: 1px solid rgba(99,102,241,0.1);
    }
    .prob-labels {
        display: flex;
        justify-content: space-between;
        margin-bottom: 6px;
    }
    .prob-label {
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .prob-home { color: #818cf8; }
    .prob-draw { color: #64748b; }
    .prob-away { color: #f472b6; }
    .prob-bar {
        display: flex;
        height: 6px;
        border-radius: 6px;
        overflow: hidden;
        background: rgba(30,41,59,0.6);
    }
    .prob-seg-home {
        background: linear-gradient(90deg, #6366f1, #818cf8);
        border-radius: 6px 0 0 6px;
        transition: width 0.8s ease;
    }
    .prob-seg-draw {
        background: linear-gradient(90deg, #475569, #64748b);
        transition: width 0.8s ease;
    }
    .prob-seg-away {
        background: linear-gradient(90deg, #ec4899, #f472b6);
        border-radius: 0 6px 6px 0;
        transition: width 0.8s ease;
    }

    /* xG badges */
    .xg-row {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin-top: 10px;
    }
    .xg-badge {
        font-size: 0.62rem;
        color: #64748b;
        font-weight: 500;
        letter-spacing: 0.04em;
    }
    .xg-val { color: #94a3b8; font-weight: 700; }

    /* Hero header */
    .hero {
        text-align: center;
        padding: 24px 0 8px;
    }
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.2rem;
        font-weight: 900;
        letter-spacing: -0.04em;
        background: linear-gradient(135deg, #e2e8f0 0%, #818cf8 50%, #a78bfa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 4px;
    }
    .hero-sub {
        color: #64748b;
        font-size: 0.85rem;
        font-weight: 400;
        letter-spacing: 0.02em;
    }
    .hero-sub span {
        color: #818cf8;
        font-weight: 600;
    }

    /* Divider */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99,102,241,0.25), transparent);
        margin: 28px 0;
    }

    /* Animated pulse for live indicator */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-6px); }
    }
    .live-dot {
        display: inline-block;
        width: 8px; height: 8px;
        background: #22c55e;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 2s ease-in-out infinite;
        box-shadow: 0 0 8px rgba(34,197,94,0.5);
    }
    .hero-icon {
        font-size: 3rem;
        display: block;
        margin-bottom: 8px;
        animation: float 3s ease-in-out infinite;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(99,102,241,0.1);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.7rem;
        color: #818cf8;
        font-weight: 600;
        margin-top: 12px;
        letter-spacing: 0.04em;
    }

    /* Footer watermark */
    .footer {
        text-align: center;
        padding: 40px 0 20px;
        font-family: 'Inter', sans-serif;
    }
    .footer-line {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99,102,241,0.15), transparent);
        margin-bottom: 24px;
    }
    .footer-credit {
        color: #475569;
        font-size: 0.75rem;
        font-weight: 400;
        letter-spacing: 0.02em;
    }
    .footer-credit a {
        color: #818cf8;
        text-decoration: none;
        font-weight: 600;
        transition: color 0.2s;
    }
    .footer-credit a:hover {
        color: #a78bfa;
    }
    .footer-name {
        color: #94a3b8;
        font-weight: 700;
        font-size: 0.8rem;
        margin-bottom: 6px;
    }
    .footer-gh {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-top: 8px;
        color: #64748b;
        font-size: 0.7rem;
        text-decoration: none;
        border: 1px solid rgba(100,116,139,0.2);
        padding: 5px 14px;
        border-radius: 20px;
        transition: all 0.3s;
    }
    .footer-gh:hover {
        color: #e2e8f0;
        border-color: rgba(99,102,241,0.4);
        background: rgba(99,102,241,0.08);
    }
</style>
""", unsafe_allow_html=True)


# ─── HELPER: CONVERT TO IST ────────────────────────────────────────────────
def _to_ist(raw_date: str) -> str:
    if not raw_date:
        return "TBD"
    date_str = str(raw_date)
    m = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+UTC([+-]\d+)', date_str)
    if m:
        d_str, t_str, offset_str = m.groups()
        try:
            dt = datetime.strptime(f"{d_str} {t_str}", "%Y-%m-%d %H:%M")
            utc_dt = dt - timedelta(hours=int(offset_str))
            ist_dt = utc_dt + timedelta(hours=5, minutes=30)
            return ist_dt.strftime("%b %d, %Y · %I:%M %p IST")
        except Exception:
            pass
    # Fallback: just the date string
    return date_str


# ─── HELPER: BUILD A SINGLE PREDICTION CARD ────────────────────────────────
def _build_card(p: dict) -> str:
    home, away = p['home_team'], p['away_team']
    pred_h, pred_a = p['predicted_home_score'], p['predicted_away_score']
    real_h, real_a = p['real_home_score'], p['real_away_score']
    pts = p['points_awarded']

    date_str = _to_ist(p.get('match_date', ''))
    h_flag = TEAM_FLAGS.get(home, "⚽")
    a_flag = TEAM_FLAGS.get(away, "⚽")

    # Result badge
    if pts == 3:
        badge = f'<span class="badge badge-exact">✓✓ EXACT SCORE ({real_h}–{real_a})</span>'
    elif pts == 1:
        badge = f'<span class="badge badge-winner">✓ OUTCOME ({real_h}–{real_a})</span>'
    elif pts == 0:
        badge = f'<span class="badge badge-wrong">✗ WRONG ({real_h}–{real_a})</span>'
    else:
        badge = '<span class="badge badge-pending">⏳ PENDING</span>'

    # Parse meta_json for probability bars
    meta = {}
    raw_meta = p.get('meta_json')
    if raw_meta:
        try:
            meta = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
        except Exception:
            pass

    p_home = meta.get('p_home_win', 0)
    p_draw = meta.get('p_draw', 0)
    p_away = meta.get('p_away_win', 0)
    blended = meta.get('blended_xg', {})
    xg_home = blended.get('home', 0)
    xg_away = blended.get('away', 0)

    # Build probability section (only if data available)
    prob_html = ""
    if p_home > 0 or p_draw > 0 or p_away > 0:
        prob_html = f"""
        <div class="prob-container">
            <div class="prob-labels">
                <span class="prob-label prob-home">{home[:3].upper()} {p_home}%</span>
                <span class="prob-label prob-draw">DRAW {p_draw}%</span>
                <span class="prob-label prob-away">{away[:3].upper()} {p_away}%</span>
            </div>
            <div class="prob-bar">
                <div class="prob-seg-home" style="width:{p_home}%"></div>
                <div class="prob-seg-draw" style="width:{p_draw}%"></div>
                <div class="prob-seg-away" style="width:{p_away}%"></div>
            </div>
        </div>"""

    # xG badges
    xg_html = ""
    if xg_home > 0 or xg_away > 0:
        xg_html = f"""
        <div class="xg-row">
            <span class="xg-badge">xG {home[:3].upper()}: <span class="xg-val">{xg_home:.2f}</span></span>
            <span class="xg-badge">xG {away[:3].upper()}: <span class="xg-val">{xg_away:.2f}</span></span>
        </div>"""

    return f"""
    <div class="pred-card">
        <div class="card-header">
            <span class="card-date">{date_str}</span>
            {badge}
        </div>
        <div class="team-row">
            <div class="team-info">
                <span class="team-flag">{h_flag}</span>
                <span class="team-name">{home}</span>
            </div>
            <span class="team-score">{pred_h}</span>
        </div>
        <div class="vs-divider">VS</div>
        <div class="team-row">
            <div class="team-info">
                <span class="team-flag">{a_flag}</span>
                <span class="team-name">{away}</span>
            </div>
            <span class="team-score">{pred_a}</span>
        </div>
        {prob_html}
        {xg_html}
    </div>"""


def render_prediction_cards(predictions):
    if not predictions:
        st.markdown("""
        <div style="text-align:center; color:#475569; padding:40px; font-family:'Inter',sans-serif;">
            <div style="font-size:2.5rem; margin-bottom:8px;">🔮</div>
            <div style="font-size:0.9rem; font-weight:500;">No predictions in this category yet</div>
            <div style="font-size:0.75rem; color:#334155; margin-top:4px;">The engine will populate this section automatically</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Render cards in a 2-column Streamlit grid, one st.markdown per card
    cols = st.columns(2)
    for i, p in enumerate(predictions):
        with cols[i % 2]:
            st.markdown(_build_card(p), unsafe_allow_html=True)


# ─── HERO HEADER ───────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <span class="hero-icon">&#9917;</span>
    <div class="hero-title">World Cup 2026 Prediction Engine</div>
    <div class="hero-sub">Powered by <span>XGBoost</span> &middot; Elo Heuristic &middot; Real-Time Market Odds Blending</div>
    <div class="hero-badge"><span class="live-dot"></span>AUTONOMOUS &middot; HOURLY UPDATES</div>
</div>
<div class="divider"></div>
""", unsafe_allow_html=True)


# ─── SECTION 1: HISTORICAL & COMPLETED ─────────────────────────────────────
st.markdown('<div class="section-header">📊 Historical & Completed Predictions</div>', unsafe_allow_html=True)
completed = get_completed_predictions()
render_prediction_cards(completed)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# ─── SECTION 2: UPCOMING PREDICTIONS ───────────────────────────────────────
st.markdown('<div class="section-header">🔮 Upcoming Predictions</div>', unsafe_allow_html=True)
upcoming = get_upcoming_predictions()
render_prediction_cards(upcoming)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# ─── SECTION 3: ENGINE ACCURACY METRICS ────────────────────────────────────
st.markdown('<div class="section-header">🎯 Engine Accuracy Metrics</div>', unsafe_allow_html=True)
stats = get_summary()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Total Scored", value=stats["total"])
with col2:
    st.metric(label="Exact Scores", value=stats["exact"])
with col3:
    st.metric(label="Exact Score %", value=f"{stats['exact_pct']}%")
with col4:
    st.metric(label="Outcome Accuracy", value=f"{stats['acc_pct']}%")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# ─── SECTION 4: MODEL LEADERBOARD ──────────────────────────────────────────
st.markdown('<div class="section-header">🏅 Model Leaderboard</div>', unsafe_allow_html=True)
leaderboard = get_leaderboard()

if leaderboard:
    formatted_lb = []
    for rank, l in enumerate(leaderboard, 1):
        scored = l.get('scored_preds') or 1
        correct = l.get('correct_outcomes') or 0
        formatted_lb.append({
            "Rank": f"#{rank}",
            "Model": l['model_name'],
            "Points": l['total_points'] or 0,
            "Exact Scores": l['exact_scores_count'] or 0,
            "Accuracy": f"{round(correct / scored * 100, 1)}%"
        })
    df_lb = pd.DataFrame(formatted_lb)
    st.dataframe(df_lb, use_container_width=True, hide_index=True)
else:
    st.info("No models scored yet.")

# ─── FOOTER / WATERMARK ────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    <div class="footer-line"></div>
    <div class="footer-name">Built by Johan B Joy</div>
    <div class="footer-credit">AI-Powered Autonomous Prediction Engine &middot; FIFA World Cup 2026&trade;</div>
    <a class="footer-gh" href="https://github.com/johanbjoy/wc-prediction-engine" target="_blank">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
        View on GitHub
    </a>
</div>
""", unsafe_allow_html=True)
