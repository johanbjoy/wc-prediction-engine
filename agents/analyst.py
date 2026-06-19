import os
import requests
import logging

logger = logging.getLogger(__name__)

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "deepseek/deepseek-r1"

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

def call_openrouter(prompt: str) -> str | None:
    if not OPENROUTER_KEY:
        logger.warning("OPENROUTER_API_KEY not set — Agent 1 skipped.")
        return None
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json",
            "HTTP-Referer": "https://wc2026-predictor.local", "X-Title": "WC2026 Predictor",
        }, json={"model": OPENROUTER_MODEL, "messages": [{"role": "user", "content": prompt}]}, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"OpenRouter call failed: {e}")
        return None
