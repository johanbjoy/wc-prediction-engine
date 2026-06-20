import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import streamlit as st
from app.components.css import apply_command_center_css
from app.components.utils import load_worldcup_data_v2
from app.components.prediction_card import render_prediction_card

st.set_page_config(page_title="Match History", page_icon="📜", layout="wide")
apply_command_center_css()

st.title("📜 Match History & Evaluation")
st.markdown("Full historical timeline of predictions graded against real-world actual outcomes.")

df = load_worldcup_data_v2()
df_comp = df[~df['is_upcoming']].sort_values('_sort_date', ascending=False)

if len(df_comp) == 0:
    st.info("No historical data available.")
else:
    for idx, row in df_comp.iterrows():
        st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 15px 0;'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            ist_dt = row['_sort_date'].tz_convert('Asia/Kolkata')
            st.markdown(f"""
            <div style="font-family: var(--font-mono); font-size: 0.9rem; color: var(--text-secondary); margin-top: 20px;">
                {ist_dt.strftime('%A, %b %d')}<br>
                <span style="color: var(--accent-cyan);">{ist_dt.strftime('%I:%M %p IST')}</span>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            render_prediction_card(row)
            
        with col3:
            # Display accuracy status explicitly
            acc = row.get('model_accuracy', 0.0)
            if acc == 1.0:
                status_color = "var(--accent-green)"
                status_text = "PERFECT SCORE"
                points = "+3 Pts"
            elif acc >= 0.5:
                status_color = "var(--accent-cyan)"
                status_text = "CORRECT OUTCOME"
                points = "+1 Pt"
            else:
                status_color = "var(--accent-red)"
                status_text = "INCORRECT"
                points = "0 Pts"
                
            st.markdown(f"""
            <div style="text-align: center; margin-top: 15px; padding: 10px; border: 1px solid {status_color}; border-radius: 8px; background: rgba(0,0,0,0.2);">
                <div style="font-family: var(--font-display); color: {status_color}; font-size: 1.1rem; letter-spacing: 1px;">{status_text}</div>
                <div style="font-family: var(--font-mono); color: var(--text-secondary); font-size: 0.9rem; margin-top: 5px;">{points}</div>
            </div>
            """, unsafe_allow_html=True)
