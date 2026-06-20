import streamlit as st
from app.components.css import apply_command_center_css
from app.components.utils import load_worldcup_data
from app.components.prediction_card import render_prediction_card
from app.components.uncertainty_viz import render_probability_donut

st.set_page_config(page_title="Match Predictions", page_icon="🎯", layout="wide")
apply_command_center_css()

st.title("🎯 Upcoming Match Predictions")
st.markdown("Deep Stack ensemble predictions powered by LightGBM, TabNet, and TFT.")

df = load_worldcup_data()
df_upcoming = df[df['is_upcoming']].sort_values('match_date')

if len(df_upcoming) == 0:
    st.info("No upcoming matches currently scheduled.")
else:
    for idx, row in df_upcoming.iterrows():
        st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])
        
        with col1:
            render_prediction_card(row)
            
            # Show raw xG
            st.markdown(f"""
            <div style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-secondary); margin-top: 10px;">
                Expected Goals (xG): <span style="color: var(--text-primary)">{row['home_team']} {row.get('raw_xg_home', 0.0):.2f}</span> — 
                <span style="color: var(--text-primary)">{row['away_team']} {row.get('raw_xg_away', 0.0):.2f}</span>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.plotly_chart(render_probability_donut(row), use_container_width=True, config={'displayModeBar': False})
