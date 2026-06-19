import os
import re
import json
import logging
import requests

logger = logging.getLogger(__name__)

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GROK_KEY = os.getenv("GROK_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
GROK_MODEL = "grok-2-latest"

def _validated_mods(mods: dict, fallback: dict) -> dict:
    valid = {}
    for k in fallback:
        try:
            val = float(mods.get(k, 1.0))
            valid[k] = max(0.5, min(val, 2.0))
        except (ValueError, TypeError):
            valid[k] = 1.0
    return valid

def parse_prediction_json(text):
    fallback = {"home_attack_mod": 1.0, "home_defense_mod": 1.0, "away_attack_mod": 1.0, "away_defense_mod": 1.0}
    if not text:
        logger.warning("Agent 2 returned no text — using no modifiers.")
        return fallback
    try:
        return _validated_mods(json.loads(text.strip()), fallback)
    except (json.JSONDecodeError, ValueError):
        pass
    match = re.search(r'\{[^{}]*"home_attack_mod"[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            logger.info("JSON extracted via regex (layer 2).")
            return _validated_mods(json.loads(match.group()), fallback)
        except (json.JSONDecodeError, ValueError):
            pass
    logger.warning("All parse layers failed — using no modifiers.")
    return fallback

def build_prediction_prompt(home_team, away_team, home_players, away_players, tactical_preview, poisson_hint):
    def fmt_players(players):
        return " | ".join(f"{p['player_name']}(xG:{p['xG']:.2f},form:{p['form_metric']:.1f})" for p in players[:11])
    meta = poisson_hint.get("model_meta", {})
    return f"""You are a score prediction engine. Output ONLY valid JSON. No prose. No markdown.

=== RAW PLAYER DATA ===
{home_team}: {fmt_players(home_players)}
{away_team}: {fmt_players(away_players)}

=== TACTICAL CONTEXT ===
{tactical_preview}

=== BASELINE & MARKET CONSENSUS ===
Expected goals (Base Lambdas): {home_team} {meta.get('lam_home', '?')} | {away_team} {meta.get('lam_away', '?')}
Win Probabilities (Blended): {home_team} {meta.get('p_home_win', '?')}% | Draw {meta.get('p_draw', '?')}% | {away_team} {meta.get('p_away_win', '?')}%

Output EXACTLY this JSON and nothing else. Values should be floats representing multipliers (1.0 = no change, 1.1 = 10% boost, 0.9 = 10% reduction).
{{"home_attack_mod": 1.0, "home_defense_mod": 1.0, "away_attack_mod": 1.0, "away_defense_mod": 1.0}}"""

def call_gemini(prompt: str) -> str | None:
    if not GEMINI_KEY:
        logger.warning("GEMINI_API_KEY not set — Agent 2 LLM skipped.")
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return None

def call_grok(prompt: str) -> str | None:
    if not GROK_KEY:
        logger.warning("GROK_API_KEY not set — Agent 2 LLM skipped.")
        return None
    try:
        r = requests.post("https://api.x.ai/v1/chat/completions", headers={
            "Authorization": f"Bearer {GROK_KEY}", "Content-Type": "application/json",
        }, json={"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}]}, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Grok call failed: {e}")
        return None
