import os
import requests
import logging

logger = logging.getLogger(__name__)

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

def _fmt_squad(team: str, players: list[dict]) -> str:
    lines = [f"  {p['player_name']} [{p.get('position','?')}] rating={p['rating']:.1f} goals={p['goals']} xG={p['xG']:.2f} form={p['form_metric']:.1f}" for p in players[:11]]
    return f"{team}:\n" + "\n".join(lines)

def build_tactical_prompt(home_team, away_team, home_players, away_players):
    return f"""You are a World Cup tactical analyst. Write a concise tactical preview (max 180 words).

MATCH: {home_team} vs {away_team}

SQUAD DATA:
{_fmt_squad(home_team, home_players)}

{_fmt_squad(away_team, away_players)}

Cover: key player matchups, attacking vs defensive strengths, predicted tempo.
No score prediction. Pure tactical analysis."""

def call_llm(prompt: str) -> str | None:
    if not GROQ_KEY:
        logger.warning("GROQ_API_KEY not set — Agent 1 skipped.")
        return None
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={
            "Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json",
        }, json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}]}, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        return None
