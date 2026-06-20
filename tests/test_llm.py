import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
from dotenv import load_dotenv
load_dotenv()

from src.nexus.agents.analyst import build_tactical_prompt, call_openrouter

# Mock players
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

print("Building Prompt...")
prompt = build_tactical_prompt(home_team, away_team, home_players, away_players)

# Re-initialize the key now that dotenv is loaded
import src.nexus.agents.analyst
agents.analyst.OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Test DeepSeek R1
print("\n--- DEEPSEEK R1 PREVIEW ---")
agents.analyst.OPENROUTER_MODEL = "deepseek/deepseek-r1"
print(call_openrouter(prompt))

# Test GPT-4o
print("\n--- GPT-4o PREVIEW ---")
agents.analyst.OPENROUTER_MODEL = "openai/gpt-4o"
print(call_openrouter(prompt))

# Test Claude 3.5 Sonnet
print("\n--- CLAUDE 3.5 SONNET PREVIEW ---")
agents.analyst.OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"
print(call_openrouter(prompt))
