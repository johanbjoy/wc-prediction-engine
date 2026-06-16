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
    df = pd.DataFrame(predictions)
    st.dataframe(df, use_container_width=True)
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
