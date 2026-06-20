import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import streamlit as st
from app.components.css import apply_command_center_css
from app.components.uncertainty_viz import render_uncertainty_timeline

st.set_page_config(page_title="In-Play Modeling", page_icon="⏱️", layout="wide")
apply_command_center_css()

st.title("⏱️ In-Play Game State Modeling")
st.markdown("Markov Chain model for live game state transitions tracking uncertainty resolution.")

st.plotly_chart(render_uncertainty_timeline(), use_container_width=True, config={'displayModeBar': False})

st.info("Live WebSocket data feed is currently disconnected. Showing sample uncertainty resolution timeline.")
