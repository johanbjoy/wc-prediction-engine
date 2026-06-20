import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
from dotenv import load_dotenv
load_dotenv()
from src.nexus.agents.analyst import build_tactical_prompt, call_llm

home_team = "Argentina"
away_team = "Brazil"

home_players = [
    {"player_name": "L. Messi", "position": "F", "rating": 9.0, "goals": 3, "xG": 2.5, "form_metric": 8.5},
    {"player_name": "E. Fernandez", "position": "M", "rating": 7.5, "goals": 0, "xG": 0.2, "form_metric": 7.0}
]
away_players = [
    {"player_name": "Vinicius Jr", "position": "F", "rating": 8.8, "goals": 2, "xG": 2.1, "form_metric": 8.2},
    {"player_name": "Casemiro", "position": "M", "rating": 7.2, "goals": 0, "xG": 0.1, "form_metric": 6.5}
]

prompt = build_tactical_prompt(home_team, away_team, home_players, away_players)
print("Testing LLaMA 3.3 70B via Groq API...")
res = call_llm(prompt)
print("\n--- OUTPUT ---")
print(res)
