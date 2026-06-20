import pandas as pd
import json
import streamlit as st
from data.database import get_completed_predictions, get_upcoming_predictions

def get_flag(team):
    flags = {
        "Mexico": "🇲🇽", "Canada": "🇨🇦", "USA": "🇺🇸", "United States": "🇺🇸", "Brazil": "🇧🇷", "Argentina": "🇦🇷",
        "France": "🇫🇷", "Germany": "🇩🇪", "Spain": "🇪🇸", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Portugal": "🇵🇹",
        "Italy": "🇮🇹", "Netherlands": "🇳🇱", "Belgium": "🇧🇪", "Croatia": "🇭🇷", "Uruguay": "🇺🇾",
        "Colombia": "🇨🇴", "Japan": "🇯🇵", "South Korea": "🇰🇷", "Korea Republic": "🇰🇷", "Senegal": "🇸🇳", "Morocco": "🇲🇦",
        "Switzerland": "🇨🇭", "Ecuador": "🇪🇨", "Ghana": "🇬🇭", "Cameroon": "🇨🇲", "Iran": "🇮🇷", "IR Iran": "🇮🇷",
        "Saudi Arabia": "🇸🇦", "Australia": "🇦🇺", "Tunisia": "🇹🇳", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "Poland": "🇵🇱",
        "Serbia": "🇷🇸", "Denmark": "🇩🇰", "Costa Rica": "🇨🇷", "Sweden": "🇸🇪", "Peru": "🇵🇪",
        "Chile": "🇨🇱", "Nigeria": "🇳🇬", "Egypt": "🇪🇬", "Ivory Coast": "🇨🇮", "Côte d'Ivoire": "🇨🇮", "Algeria": "🇩🇿",
        "DR Congo": "🇨🇩", "Democratic Republic of the Congo": "🇨🇩", "South Africa": "🇿🇦", "Mali": "🇲🇱", 
        "Bosnia & Herzegovina": "🇧🇦", "Bosnia and Herzegovina": "🇧🇦",
        "Czech Republic": "🇨🇿", "Norway": "🇳🇴", "Qatar": "🇶🇦", "Uzbekistan": "🇺🇿",
        "Jordan": "🇯🇴", "New Zealand": "🇳🇿", "Panama": "🇵🇦", "Cape Verde": "🇨🇻", "Curaçao": "🇨🇼",
        "Jamaica": "🇯🇲", "Honduras": "🇭🇳", "El Salvador": "🇸🇻", "Iraq": "🇮🇶",
        "Paraguay": "🇵🇾", "Venezuela": "🇻🇪", "Bolivia": "🇧🇴", "Turkey": "🇹🇷", "Türkiye": "🇹🇷", "Ukraine": "🇺🇦",
        "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Oman": "🇴🇲", "UAE": "🇦🇪", "United Arab Emirates": "🇦🇪", "Bahrain": "🇧🇭", "China": "🇨🇳", "China PR": "🇨🇳",
        "Syria": "🇸🇾", "Thailand": "🇹🇭", "Vietnam": "🇻🇳", "North Korea": "🇰🇵", "Lebanon": "🇱🇧",
        "Palestine": "🇵🇸", "India": "🇮🇳", "Tajikistan": "🇹🇯", "Kyrgyzstan": "🇰🇬", "Kuwait": "🇰🇼",
        "Indonesia": "🇮🇩", "Malaysia": "🇲🇾", "Angola": "🇦🇴", "Burkina Faso": "🇧🇫", "Equatorial Guinea": "🇬🇶",
        "Gabon": "🇬🇦", "Guinea": "🇬🇳", "Zambia": "🇿🇲", "Uganda": "🇺🇬", "Kenya": "🇰🇪",
        "Iceland": "🇮🇸", "Ireland": "🇮🇪", "Republic of Ireland": "🇮🇪", "Northern Ireland": "🇬🇧", "Austria": "🇦🇹", "Hungary": "🇭🇺",
        "Slovakia": "🇸🇰", "Slovenia": "🇸🇮", "Romania": "🇷🇴", "Bulgaria": "🇧🇬", "Greece": "🇬🇷",
        "Finland": "🇫🇮", "Albania": "🇦🇱", "Georgia": "🇬🇪", "Armenia": "🇦🇲", "Israel": "🇮🇱",
        "Guatemala": "🇬🇹", "Trinidad and Tobago": "🇹🇹", "Haiti": "🇭🇹", "North Macedonia": "🇲🇰", "Macedonia": "🇲🇰" 
    }
    return flags.get(team, "🏳️")

@st.cache_data(ttl=300)
def load_worldcup_data():
    comp = get_completed_predictions(limit=1000)
    upc = get_upcoming_predictions(limit=50)
    
    all_rows = []
    
    for row in comp + upc:
        probs = {}
        if isinstance(row.get("meta_json"), str):
            try:
                meta = json.loads(row["meta_json"])
                if "blended_probs" in meta:
                    probs = meta["blended_probs"]
                elif "probabilities" in meta:
                    probs = meta["probabilities"]
                elif "dixon_coles_probs" in meta:
                    probs = meta["dixon_coles_probs"]
            except:
                pass
        elif isinstance(row.get("meta_json"), dict):
            meta = row["meta_json"]
            if "blended_probs" in meta:
                probs = meta["blended_probs"]
            elif "probabilities" in meta:
                probs = meta["probabilities"]
            elif "dixon_coles_probs" in meta:
                probs = meta["dixon_coles_probs"]
            
        h_prob = probs.get("p_home_win", 0.0)
        d_prob = probs.get("p_draw", 0.0)
        a_prob = probs.get("p_away_win", 0.0)
        
        pred_out = 'D'
        if h_prob > d_prob and h_prob > a_prob: pred_out = 'H'
        elif a_prob > h_prob and a_prob > d_prob: pred_out = 'A'
            
        actual_out = None
        actual_score = None
        h_score = row.get("real_home_score")
        a_score = row.get("real_away_score")
        if h_score is not None and a_score is not None:
            actual_score = f"{h_score}-{a_score}"
            if h_score > a_score: actual_out = 'H'
            elif a_score > h_score: actual_out = 'A'
            else: actual_out = 'D'
            
        try:
            m_date = pd.to_datetime(row.get("match_date", ""))
        except:
            m_date = pd.to_datetime("2026-06-01 15:00:00")
            
        is_upcoming = actual_out is None
        
        model_acc = 0.0
        if not is_upcoming and row.get("points_awarded") is not None:
            pts = row.get("points_awarded")
            if pts == 3: model_acc = 1.0 
            elif pts == 1: model_acc = 0.5 
            else: model_acc = 0.0
            
        meta_data = row.get("meta_json", {})
        if isinstance(meta_data, str):
            try: meta_data = json.loads(meta_data)
            except: meta_data = {}
        
        all_rows.append({
            'match_id': row.get("fixture_id", 0),
            'match_date': m_date,
            'home_team': row.get("home_team"),
            'away_team': row.get("away_team"),
            'stage': 'Qualifiers' if 'Q' in row.get("home_team", "") else 'Group Stage',
            'home_win_prob': h_prob,
            'draw_prob': d_prob,
            'away_win_prob': a_prob,
            'predicted_result': pred_out,
            'pred_h_score': row.get("predicted_home_score"),
            'pred_a_score': row.get("predicted_away_score"),
            'actual_result': actual_out,
            'actual_score': actual_score,
            'model_accuracy': model_acc if not is_upcoming else 0.0,
            'is_upcoming': is_upcoming,
            'raw_xg_home': meta_data.get("nexus_home_xg", 1.0),
            'raw_xg_away': meta_data.get("nexus_away_xg", 1.0)
        })
        
    df = pd.DataFrame(all_rows)
    if len(df) > 0:
        df['match_date'] = pd.to_datetime(df['match_date'], utc=True).dt.tz_convert('Asia/Kolkata')
    else:
        return pd.DataFrame(columns=[
            'match_id', 'match_date', 'home_team', 'away_team', 'stage', 
            'home_win_prob', 'draw_prob', 'away_win_prob', 'predicted_result', 'actual_result', 
            'actual_score', 'model_accuracy', 'is_upcoming', 'raw_xg_home', 'raw_xg_away'
        ])
    return df
