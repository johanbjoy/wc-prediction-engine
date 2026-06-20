import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import os
from app.components.css import apply_command_center_css
from app.components.utils import get_flag

st.set_page_config(page_title="Tournament Simulation", page_icon="🏆", layout="wide")
apply_command_center_css()

st.title("🏆 Monte Carlo Tournament Simulation")
st.markdown("Pre-calculated results from 10,000+ simulation iterations of the 2026 World Cup Bracket.")

# Path to the pre-calculated results
RESULTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data_store", "databases", "monte_carlo_results.json"))

if not os.path.exists(RESULTS_PATH):
    st.error("No Monte Carlo simulation results found. Please run the backend script `scripts/run_monte_carlo.py` to generate the data.")
else:
    try:
        with open(RESULTS_PATH, "r") as f:
            sim_data = json.load(f)
            
        iterations = sim_data.get("iterations", 10000)
        df = pd.DataFrame(sim_data.get("data", []))
        
        st.markdown(f'<div class="subheader-text" style="text-align: left; margin-bottom: 20px;">Iterations Run: {iterations:,}</div>', unsafe_allow_html=True)

        if not df.empty:
            # Sort by win prob
            df = df.sort_values(by='win_prob', ascending=False).reset_index(drop=True)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("Top Title Contenders")
                
                # Plotly Bar Chart
                top_10 = df.head(10)
                flags = [get_flag(team) for team in top_10['team']]
                labels = [f"{flag} {team}" for flag, team in zip(flags, top_10['team'])]
                
                fig = go.Figure(go.Bar(
                    x=top_10['win_prob'] * 100,
                    y=labels,
                    orientation='h',
                    marker=dict(color='#f59e0b', line=dict(width=1, color='rgba(255,255,255,0.2)')),
                    text=[f"{w*100:.1f}%" for w in top_10['win_prob']],
                    textposition='inside'
                ))
                
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f9fafb', family='Inter'),
                    xaxis=dict(showgrid=False, title="Championship Probability (%)"),
                    yaxis=dict(showgrid=False, autorange="reversed"),
                    margin=dict(l=0, r=0, t=30, b=0),
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
            with col2:
                st.subheader("Full Simulation Leaderboard")
                
                # Format dataframe for display
                display_df = df.copy()
                display_df['team'] = display_df['team'].apply(lambda t: f"{get_flag(t)} {t}")
                display_df['win_prob'] = (display_df['win_prob'] * 100).map("{:.1f}%".format)
                display_df['final_prob'] = (display_df['final_prob'] * 100).map("{:.1f}%".format)
                display_df['semi_prob'] = (display_df['semi_prob'] * 100).map("{:.1f}%".format)
                display_df['knockout_prob'] = (display_df['knockout_prob'] * 100).map("{:.1f}%".format)
                
                display_df.columns = ["Team", "Win WC", "Reach Final", "Reach Semi", "Reach Knockouts"]
                
                st.dataframe(
                    display_df, 
                    use_container_width=True, 
                    hide_index=True,
                    height=400
                )

    except Exception as e:
        st.error(f"Error parsing simulation results: {e}")
