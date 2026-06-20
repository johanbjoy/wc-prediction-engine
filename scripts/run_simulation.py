import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import os
import random
from models.nexus_model import predict

# Projected Top 48 Teams for 2026 (based on current/historical FIFA rankings)
TEAMS = [
    "Argentina", "France", "Brazil", "England", "Belgium", "Portugal", "Netherlands", "Spain",
    "Italy", "Croatia", "Uruguay", "USA", "Morocco", "Colombia", "Mexico", "Germany",
    "Japan", "Switzerland", "Denmark", "Senegal", "Iran", "South Korea", "Australia", "Ukraine",
    "Austria", "Sweden", "Poland", "Wales", "Hungary", "Serbia", "Peru", "Scotland",
    "Turkey", "Ecuador", "Chile", "Tunisia", "Algeria", "Egypt", "Nigeria", "Cameroon",
    "Canada", "Mali", "Ivory Coast", "Saudi Arabia", "Qatar", "Panama", "Costa Rica", "New Zealand"
]

def get_elo(team):
    # Dummy ELO fallback if database lookup isn't used
    base = 1500
    if team in ["Argentina", "France", "Brazil", "England"]: base = 2000
    elif team in ["Spain", "Portugal", "Germany", "Belgium"]: base = 1900
    elif team in ["Netherlands", "Uruguay", "Croatia", "Italy"]: base = 1850
    return base + random.randint(-50, 50)

def get_real_match_result(home, away):
    from data.database import get_connection
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT real_home_score, real_away_score 
                FROM fixtures 
                WHERE home_team = %s AND away_team = %s AND status = 'FT'
                ORDER BY match_date DESC LIMIT 1
            """, (home, away))
            row = cur.fetchone()
            if row and row["real_home_score"] is not None:
                return row["real_home_score"], row["real_away_score"]
    finally:
        conn.close()
    return None

def simulate_match(home, away, stage="Group Stage"):
    """Uses N.E.X.U.S. to predict the match outcome."""
    
    # Phase 7: Check if match actually happened in real life
    real_res = get_real_match_result(home, away)
    if real_res:
        rh, ra = real_res
        winner = home if rh > ra else away
        if rh == ra and stage != "Group Stage":
            winner = home if random.random() > 0.5 else away # PK shootout random
        
        return {
            "winner": winner,
            "home_score": rh,
            "away_score": ra,
            "home_prob": 1.0 if winner == home else 0.0,
            "away_prob": 1.0 if winner == away else 0.0,
            "draw_prob": 1.0 if rh == ra else 0.0,
            "is_real": True
        }
        
    elo_h = get_elo(home)
    elo_a = get_elo(away)
    
    res = predict(home, away, "World Cup 2026", "2026-06-15", elo_h, elo_a, 1.0, 1.0)
    
    if not res:
        # Fallback if model fails
        return {"winner": home, "home_score": 1, "away_score": 0, "home_prob": 0.5, "away_prob": 0.5, "draw_prob": 0.0}
        
    probs = res.get("dixon_coles_probs", {})
    ph = probs.get("p_home_win", 0.33)
    pd = probs.get("p_draw", 0.33)
    pa = probs.get("p_away_win", 0.33)
    
    # Deterministic outcome for the bracket
    if stage == "Group Stage":
        if ph > pa and ph > pd:
            return {"winner": home, "home_score": 2, "away_score": 1, "home_prob": ph, "away_prob": pa, "draw_prob": pd}
        elif pa > ph and pa > pd:
            return {"winner": away, "home_score": 1, "away_score": 2, "home_prob": ph, "away_prob": pa, "draw_prob": pd}
        else:
            return {"winner": "Draw", "home_score": 1, "away_score": 1, "home_prob": ph, "away_prob": pa, "draw_prob": pd}
    else:
        # Knockouts can't be drawn, allocate to higher probability
        if ph >= pa:
            return {"winner": home, "home_score": 2, "away_score": 1, "home_prob": ph, "away_prob": pa, "draw_prob": pd}
        else:
            return {"winner": away, "home_score": 1, "away_score": 2, "home_prob": ph, "away_prob": pa, "draw_prob": pd}

def write_log(msg):
    with open("nexus.log", "a") as f:
        f.write(msg + "\n")
    print(msg)

def simulate_tournament():
    write_log("Starting Full Tournament Bracket Simulation...")
    random.shuffle(TEAMS)
    
    # 12 Groups of 4
    groups = {f"Group {chr(65+i)}": TEAMS[i*4:(i+1)*4] for i in range(12)}
    
    bracket_data = {"groups": groups, "matches": []}
    standings = {t: {"pts": 0, "gf": 0, "ga": 0} for t in TEAMS}
    
    write_log("Simulating Group Stage...")
    # Group Stage Matches
    for g_name, g_teams in groups.items():
        for i in range(len(g_teams)):
            for j in range(i+1, len(g_teams)):
                h, a = g_teams[i], g_teams[j]
                m = simulate_match(h, a, "Group Stage")
                bracket_data["matches"].append({
                    "stage": "Group Stage",
                    "group": g_name,
                    "home": h, "away": a,
                    "winner": m["winner"],
                    "home_score": m["home_score"], "away_score": m["away_score"],
                    "home_prob": m["home_prob"], "away_prob": m["away_prob"], "draw_prob": m["draw_prob"]
                })
                
                standings[h]["gf"] += m["home_score"]
                standings[h]["ga"] += m["away_score"]
                standings[a]["gf"] += m["away_score"]
                standings[a]["ga"] += m["home_score"]
                
                if m["winner"] == h:
                    standings[h]["pts"] += 3
                elif m["winner"] == a:
                    standings[a]["pts"] += 3
                else:
                    standings[h]["pts"] += 1
                    standings[a]["pts"] += 1

    # Determine advancing teams: Top 2 from each group (24) + 8 best 3rd place (8) = 32
    advancing = []
    third_places = []
    
    for g_name, g_teams in groups.items():
        sorted_g = sorted(g_teams, key=lambda t: (standings[t]["pts"], standings[t]["gf"] - standings[t]["ga"]), reverse=True)
        advancing.append(sorted_g[0])
        advancing.append(sorted_g[1])
        third_places.append(sorted_g[2])
        
    third_places = sorted(third_places, key=lambda t: (standings[t]["pts"], standings[t]["gf"] - standings[t]["ga"]), reverse=True)
    advancing.extend(third_places[:8])
    
    write_log(f"Knockout Stage Teams: {len(advancing)}")
    
    # Shuffle for Ro32
    random.shuffle(advancing)
    
    stages = ["Round of 32", "Round of 16", "Quarter Finals", "Semi Finals", "Final"]
    current_teams = advancing
    
    for stage in stages:
        write_log(f"Simulating {stage}...")
        next_teams = []
        for i in range(0, len(current_teams), 2):
            h, a = current_teams[i], current_teams[i+1]
            m = simulate_match(h, a, stage)
            bracket_data["matches"].append({
                "stage": stage,
                "home": h, "away": a,
                "winner": m["winner"],
                "home_score": m["home_score"], "away_score": m["away_score"],
                "home_prob": m["home_prob"], "away_prob": m["away_prob"]
            })
            next_teams.append(m["winner"])
            
        current_teams = next_teams
        if len(current_teams) == 1:
            bracket_data["champion"] = current_teams[0]
            write_log(f"🏆 CHAMPION: {current_teams[0]}")
            break
            
    with open("data_store/databases/tournament_bracket.json", "w") as f:
        json.dump(bracket_data, f, indent=4)
    write_log("Saved to data_store/databases/tournament_bracket.json")

if __name__ == "__main__":
    simulate_tournament()
