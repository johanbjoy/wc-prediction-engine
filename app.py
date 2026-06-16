import streamlit as st
from data.database import get_recent_predictions
import pandas as pd

st.set_page_config(page_title="World Cup Engine", layout="wide")

st.title("🏆 World Cup 2026 Prediction Engine")
st.write("Powered by an XGBoost & Poisson Ensemble Model")

# Fetch data from existing Supabase connection
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

# Add a button to manually trigger the orchestrator
st.markdown("---")
st.subheader("Live Pipeline")
if st.button("Run Live Prediction Pipeline"):
    with st.spinner("Running XGBoost Ensemble and querying LLM agents..."):
        import orchestrator
        try:
            orchestrator.run_pipeline()
            st.success("Prediction complete! Database updated.")
            st.rerun() # Refresh the dataframe with the new data
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
