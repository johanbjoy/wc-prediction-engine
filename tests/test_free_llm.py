import os
from dotenv import load_dotenv
load_dotenv()
from agents.analyst import build_tactical_prompt, call_openrouter
import agents.analyst

home_team = "Argentina"
away_team = "Brazil"
home_players = [{"player_name": "L. Messi", "position": "F", "rating": 9.0, "goals": 3, "xG": 2.5, "form_metric": 8.5}]
away_players = [{"player_name": "Vinicius Jr", "position": "F", "rating": 8.8, "goals": 2, "xG": 2.1, "form_metric": 8.2}]

prompt = build_tactical_prompt(home_team, away_team, home_players, away_players)
agents.analyst.OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")

models = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "deepseek/deepseek-r1:free"
]

for model in models:
    print(f"Testing {model}...")
    agents.analyst.OPENROUTER_MODEL = model
    res = call_openrouter(prompt)
    if res:
        print(f"SUCCESS: {res[:50]}...")
    else:
        print("FAILED")
