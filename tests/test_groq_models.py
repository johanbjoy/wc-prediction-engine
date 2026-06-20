import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
import requests
from dotenv import load_dotenv
load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY", "")

# We'll use a mocked sentiment prompt for Argentina vs Brazil
prompt = """You are a World Cup tactical analyst. Write a concise tactical preview (max 180 words).

MATCH: Argentina vs Brazil

SQUAD DATA:
Argentina:
  L. Messi [F] rating=9.0 goals=3 xG=2.50 form=8.5
  E. Fernandez [M] rating=7.5 goals=0 xG=0.20 form=7.0

Brazil:
  Vinicius Jr [F] rating=8.8 goals=2 xG=2.10 form=8.2
  Casemiro [M] rating=7.2 goals=0 xG=0.10 form=6.5

PUBLIC SENTIMENT & NEWS:
Argentina Headlines: ['Lionel Messi hints at retirement after the tournament', 'Argentina fans erupt in massive celebration']
Brazil Headlines: ['Brazil coach under massive pressure after poor defensive showing', 'Neymar seen limping in practice']

Cover: key player matchups, attacking vs defensive strengths, public morale/pressure based on headlines, predicted tempo.
No score prediction. Pure tactical analysis."""

models = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it"
]

for model in models:
    print(f"\n======================================")
    print(f"TESTING MODEL: {model}")
    print(f"======================================")
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={
            "Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json",
        }, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, timeout=15)
        
        if r.status_code == 200:
            print(r.json()["choices"][0]["message"]["content"])
        else:
            print(f"FAILED: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"ERROR: {e}")
