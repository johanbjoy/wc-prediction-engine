import os
import pandas as pd
from statsbombpy import sb

def fetch_world_cup_xg():
    print("Fetching World Cup 2022 Matches from StatsBomb...")
    
    # World Cup 2022: competition_id=43, season_id=106
    matches = sb.matches(competition_id=43, season_id=106)
    
    match_ids = matches['match_id'].tolist()
    
    xg_data = []
    
    print(f"Found {len(match_ids)} matches. Fetching event data (this may take a minute)...")
    
    for idx, match_id in enumerate(match_ids):
        events = sb.events(match_id=match_id)
        
        # Filter only shots
        shots = events[events['type'] == 'Shot']
        
        home_team = matches.loc[matches['match_id'] == match_id, 'home_team'].values[0]
        away_team = matches.loc[matches['match_id'] == match_id, 'away_team'].values[0]
        match_date = matches.loc[matches['match_id'] == match_id, 'match_date'].values[0]
        
        # Calculate sum of xG for home and away
        home_xg = shots[shots['team'] == home_team]['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in shots.columns else 0.0
        away_xg = shots[shots['team'] == away_team]['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in shots.columns else 0.0
        
        # StatsBomb team names might differ slightly, but we'll store them for now
        xg_data.append({
            'match_id': match_id,
            'match_date': match_date,
            'home_team': home_team,
            'away_team': away_team,
            'home_xg': round(home_xg, 3),
            'away_xg': round(away_xg, 3)
        })
        
        if (idx + 1) % 10 == 0:
            print(f"Processed {idx + 1}/{len(match_ids)} matches...")
            
    df = pd.DataFrame(xg_data)
    
    os.makedirs('statsbomb_data', exist_ok=True)
    df.to_csv('data_store/statsbomb/xg_data.csv', index=False)
    print("Successfully saved xG data to data_store/statsbomb/xg_data.csv")

if __name__ == "__main__":
    fetch_world_cup_xg()
