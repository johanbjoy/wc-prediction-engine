import streamlit as st
import pandas as pd
from .utils import get_flag

def render_prediction_card(row):
    ist_dt = row['_sort_date'].tz_convert('Asia/Kolkata')
    date = ist_dt.strftime('%b %d, %Y • %I:%M %p IST')
    home = row['home_team']
    away = row['away_team']
    pred_h = row['pred_h_score']
    pred_a = row['pred_a_score']
    pred = row['predicted_result']
    actual = row.get('actual_result')
    act_score_str = row.get('actual_score')
    acc = row.get('model_accuracy', 0.0)
    is_upc = row.get('is_upcoming', False)
    
    home_flag = get_flag(home)
    away_flag = get_flag(away)
    
    if pd.notna(pred_h) and pd.notna(pred_a):
        pred_str = f"Predicted: {int(pred_h)}-{int(pred_a)}"
    else:
        pred_str = f"Predicted: {pred}"
        
    badge = ""
    if not is_upc:
        if acc == 1.0:
            badge = '<div class="badge badge-exact">🎯 Exact Score</div>'
        elif acc > 0.0 or pred == actual:
            badge = '<div class="badge badge-correct">✅ Correct Winner</div>'
        else:
            badge = '<div class="badge badge-wrong">❌ Incorrect</div>'
    else:
        if row['home_win_prob'] > row['away_win_prob'] and row['home_win_prob'] > row['draw_prob']:
            badge = f'<div class="badge" style="color: var(--accent-cyan)">Favored: {home} ({row["home_win_prob"]:.1%})</div>'
        elif row['away_win_prob'] > row['home_win_prob'] and row['away_win_prob'] > row['draw_prob']:
            badge = f'<div class="badge" style="color: var(--accent-green)">Favored: {away} ({row["away_win_prob"]:.1%})</div>'
        else:
            badge = f'<div class="badge" style="color: var(--accent-amber)">Favored: Draw ({row["draw_prob"]:.1%})</div>'

    html = f"""
    <div class="score-card">
        <div class="score-team score-home">{home_flag} {home}</div>
        <div class="score-center">
            <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 5px; font-family: var(--font-mono);">{date}</div>
            <div class="score-actual">{act_score_str if not is_upc else pred_str.replace('Predicted: ', '')}</div>
            <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 2px;">{pred_str if not is_upc else "Expected"}</div>
            {badge}
        </div>
        <div class="score-team score-away">{away} {away_flag}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
