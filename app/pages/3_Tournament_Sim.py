import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import streamlit as st
from app.components.css import apply_command_center_css

st.set_page_config(page_title="Tournament Simulation", page_icon="🏆", layout="wide")
apply_command_center_css()

st.title("🏆 Tournament Simulation (V2)")
st.markdown("Advanced Monte Carlo Simulation with full bracket paths and group interdependency (50,000+ iterations).")

st.info("The Bracket Visualization module is currently generating the 50,000 simulations. Please check back soon.")

# Placeholder for the Animated Bracket Visualization from the spec
st.markdown("""
<div style="text-align: center; margin-top: 50px;">
    <h3 style="color: var(--accent-amber);">Generating Paths...</h3>
    <div style="width: 50px; height: 50px; border: 5px solid var(--accent-amber); border-top: 5px solid transparent; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto;"></div>
    <style>@keyframes spin { 100% { transform: rotate(360deg); } }</style>
</div>
""", unsafe_allow_html=True)
