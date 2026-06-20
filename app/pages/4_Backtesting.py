import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import streamlit as st
import pandas as pd
from app.components.css import apply_command_center_css
from app.components.utils import load_worldcup_data
from app.components.model_weights import render_model_attribution, render_dynamic_routing

st.set_page_config(page_title="Model Backtesting", page_icon="📈", layout="wide")
apply_command_center_css()

st.title("📈 Model Backtesting & Attribution")
st.markdown("Analyze historical model performance and see exactly how the Deep Stacking engine weighs features.")

col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(render_model_attribution(), use_container_width=True, config={'displayModeBar': False})
with col_b:
    st.plotly_chart(render_dynamic_routing(), use_container_width=True, config={'displayModeBar': False})

st.markdown("### Historical Log Console")
df = load_worldcup_data()
df_comp = df[~df['is_upcoming']].sort_values('match_date', ascending=False)

if len(df_comp) == 0:
    st.info("No historical data available.")
else:
    for idx, row in df_comp.head(10).iterrows():
        st.markdown(f"""
        <div class="score-card" style="padding: 10px; margin-bottom: 5px; opacity: 0.9;">
            <div style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-secondary); width: 150px;">{row['match_date'].strftime('%Y-%m-%d')}</div>
            <div style="flex: 1; font-weight: 600;">{row['home_team']} vs {row['away_team']}</div>
            <div style="font-family: var(--font-display); font-size: 1.2rem; margin-right: 20px;">{row.get('actual_score', '?')}</div>
            <div style="width: 150px; text-align: right;">
                {'<span style="color: var(--accent-green)">Exact</span>' if row.get('model_accuracy') == 1.0 else ('<span style="color: var(--accent-cyan)">Correct</span>' if row.get('model_accuracy') == 0.5 else '<span style="color: var(--accent-red)">Wrong</span>')}
            </div>
        </div>
        """, unsafe_allow_html=True)
