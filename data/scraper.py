"""
scraper.py — Fixtures and player data fetcher.

Data sources (priority order):
  1. openfootball/worldcup.json (GitHub, free, 104 matches with real scores)
  2. worldcup26.ir REST API    (free, live scores, no auth for read)
  3. API-Football              (if API_FOOTBALL_KEY set)
  4. Baseline fallback         (always works, zero API cost)
"""
import os, json, logging, requests, hashlib
from datetime import datetime, timedelta, timezone
from data.database import get_connection

logger = logging.getLogger(__name__)
API_KEY  = os.getenv("API_FOOTBALL_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY, "x-rapidapi-host": "v3.football.api-sports.io"}

OPENFOOTBALL_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
WORLDCUP26_URL   = "https://worldcup26.ir/get/games"

# ─── TEAM BASELINES ────────────────────────────────────────────────────────
TEAM_BASELINES: dict[str, dict] = {
    "Brazil": {"avg_goals_scored": 2.1, "avg_goals_conceded": 0.8, "xG": 1.9, "form": 7.5, "elo": 2015},
    "Argentina": {"avg_goals_scored": 2.3, "avg_goals_conceded": 0.9, "xG": 2.1, "form": 8.2, "elo": 2090},
    "France": {"avg_goals_scored": 2.0, "avg_goals_conceded": 0.9, "xG": 1.9, "form": 7.8, "elo": 2035},
    "Germany": {"avg_goals_scored": 1.8, "avg_goals_conceded": 1.1, "xG": 1.7, "form": 7.0, "elo": 1935},
    "England": {"avg_goals_scored": 1.9, "avg_goals_conceded": 0.9, "xG": 1.8, "form": 7.4, "elo": 1990},
    "Spain": {"avg_goals_scored": 2.0, "avg_goals_conceded": 0.8, "xG": 1.9, "form": 7.6, "elo": 2020},
    "Portugal": {"avg_goals_scored": 2.1, "avg_goals_conceded": 1.0, "xG": 1.9, "form": 7.3, "elo": 1985},
    "Netherlands": {"avg_goals_scored": 1.9, "avg_goals_conceded": 1.0, "xG": 1.8, "form": 7.2, "elo": 1965},
    "Belgium": {"avg_goals_scored": 1.8, "avg_goals_conceded": 1.1, "xG": 1.7, "form": 6.9, "elo": 1925},
    "Italy": {"avg_goals_scored": 1.6, "avg_goals_conceded": 0.9, "xG": 1.5, "form": 6.8, "elo": 1915},
    "Croatia": {"avg_goals_scored": 1.5, "avg_goals_conceded": 1.0, "xG": 1.4, "form": 6.5, "elo": 1875},
    "Uruguay": {"avg_goals_scored": 1.7, "avg_goals_conceded": 1.0, "xG": 1.6, "form": 6.8, "elo": 1915},
    "Colombia": {"avg_goals_scored": 1.6, "avg_goals_conceded": 1.1, "xG": 1.5, "form": 6.7, "elo": 1895},
    "Mexico": {"avg_goals_scored": 1.5, "avg_goals_conceded": 1.2, "xG": 1.4, "form": 6.3, "elo": 1845},
    "USA": {"avg_goals_scored": 1.4, "avg_goals_conceded": 1.2, "xG": 1.3, "form": 6.2, "elo": 1830},
    "United States": {"avg_goals_scored": 1.4, "avg_goals_conceded": 1.2, "xG": 1.3, "form": 6.2, "elo": 1830},
    "Canada": {"avg_goals_scored": 1.3, "avg_goals_conceded": 1.3, "xG": 1.2, "form": 6.0, "elo": 1800},
    "Japan": {"avg_goals_scored": 1.5, "avg_goals_conceded": 1.1, "xG": 1.4, "form": 6.5, "elo": 1870},
    "South Korea": {"avg_goals_scored": 1.4, "avg_goals_conceded": 1.2, "xG": 1.3, "form": 6.2, "elo": 1830},
    "Australia": {"avg_goals_scored": 1.2, "avg_goals_conceded": 1.3, "xG": 1.1, "form": 5.8, "elo": 1775},
    "Morocco": {"avg_goals_scored": 1.4, "avg_goals_conceded": 0.9, "xG": 1.3, "form": 6.4, "elo": 1865},
    "Senegal": {"avg_goals_scored": 1.3, "avg_goals_conceded": 1.1, "xG": 1.2, "form": 6.1, "elo": 1820},
    "Nigeria": {"avg_goals_scored": 1.3, "avg_goals_conceded": 1.2, "xG": 1.2, "form": 6.0, "elo": 1805},
    "Ghana": {"avg_goals_scored": 1.2, "avg_goals_conceded": 1.3, "xG": 1.1, "form": 5.7, "elo": 1765},
    "Switzerland": {"avg_goals_scored": 1.5, "avg_goals_conceded": 1.0, "xG": 1.4, "form": 6.4, "elo": 1865},
    "Denmark": {"avg_goals_scored": 1.6, "avg_goals_conceded": 1.0, "xG": 1.5, "form": 6.6, "elo": 1890},
    "Poland": {"avg_goals_scored": 1.4, "avg_goals_conceded": 1.2, "xG": 1.3, "form": 6.2, "elo": 1830},
    "Ukraine": {"avg_goals_scored": 1.3, "avg_goals_conceded": 1.2, "xG": 1.2, "form": 6.0, "elo": 1805},
    "Serbia": {"avg_goals_scored": 1.4, "avg_goals_conceded": 1.2, "xG": 1.3, "form": 6.1, "elo": 1820},
    "Ecuador": {"avg_goals_scored": 1.3, "avg_goals_conceded": 1.2, "xG": 1.2, "form": 6.0, "elo": 1805},
    "Saudi Arabia": {"avg_goals_scored": 1.1, "avg_goals_conceded": 1.4, "xG": 1.0, "form": 5.5, "elo": 1735},
    "Iran": {"avg_goals_scored": 1.1, "avg_goals_conceded": 1.3, "xG": 1.0, "form": 5.6, "elo": 1750},
    "Cameroon": {"avg_goals_scored": 1.2, "avg_goals_conceded": 1.3, "xG": 1.1, "form": 5.7, "elo": 1765},
    "Sweden": {"avg_goals_scored": 1.7, "avg_goals_conceded": 1.0, "xG": 1.6, "form": 7.0, "elo": 1935},
    "Tunisia": {"avg_goals_scored": 1.1, "avg_goals_conceded": 1.3, "xG": 1.0, "form": 5.6, "elo": 1750},
    "Turkey": {"avg_goals_scored": 1.4, "avg_goals_conceded": 1.2, "xG": 1.3, "form": 6.2, "elo": 1830},
    "Paraguay": {"avg_goals_scored": 1.2, "avg_goals_conceded": 1.3, "xG": 1.1, "form": 5.8, "elo": 1775},
    "South Africa": {"avg_goals_scored": 1.1, "avg_goals_conceded": 1.4, "xG": 1.0, "form": 5.5, "elo": 1735},
    "Czech Republic": {"avg_goals_scored": 1.3, "avg_goals_conceded": 1.2, "xG": 1.2, "form": 6.0, "elo": 1805},
    "Qatar": {"avg_goals_scored": 1.0, "avg_goals_conceded": 1.5, "xG": 0.9, "form": 5.3, "elo": 1705},
    "Bosnia & Herzegovina": {"avg_goals_scored": 1.2, "avg_goals_conceded": 1.3, "xG": 1.1, "form": 5.8, "elo": 1775},
    "Bosnia and Herzegovina": {"avg_goals_scored": 1.2, "avg_goals_conceded": 1.3, "xG": 1.1, "form": 5.8, "elo": 1775},
    "Scotland": {"avg_goals_scored": 1.2, "avg_goals_conceded": 1.2, "xG": 1.1, "form": 5.9, "elo": 1790},
    "Haiti": {"avg_goals_scored": 0.9, "avg_goals_conceded": 1.6, "xG": 0.8, "form": 5.0, "elo": 1665},
    "Curaçao": {"avg_goals_scored": 0.8, "avg_goals_conceded": 1.8, "xG": 0.7, "form": 4.8, "elo": 1630},
    "Ivory Coast": {"avg_goals_scored": 1.4, "avg_goals_conceded": 1.1, "xG": 1.3, "form": 6.3, "elo": 1845},
    "Egypt": {"avg_goals_scored": 1.3, "avg_goals_conceded": 1.1, "xG": 1.2, "form": 6.1, "elo": 1820},
    "New Zealand": {"avg_goals_scored": 1.0, "avg_goals_conceded": 1.5, "xG": 0.9, "form": 5.2, "elo": 1695},
    "Cape Verde": {"avg_goals_scored": 0.9, "avg_goals_conceded": 1.5, "xG": 0.8, "form": 5.0, "elo": 1670},
    "Iraq": {"avg_goals_scored": 1.1, "avg_goals_conceded": 1.3, "xG": 1.0, "form": 5.6, "elo": 1750},
    "Norway": {"avg_goals_scored": 1.5, "avg_goals_conceded": 1.1, "xG": 1.4, "form": 6.4, "elo": 1860},
    "Algeria": {"avg_goals_scored": 1.2, "avg_goals_conceded": 1.2, "xG": 1.1, "form": 5.9, "elo": 1790},
    "Austria": {"avg_goals_scored": 1.5, "avg_goals_conceded": 1.1, "xG": 1.4, "form": 6.4, "elo": 1860},
    "Jordan": {"avg_goals_scored": 1.0, "avg_goals_conceded": 1.4, "xG": 0.9, "form": 5.3, "elo": 1710},
    "DR Congo": {"avg_goals_scored": 1.1, "avg_goals_conceded": 1.4, "xG": 1.0, "form": 5.5, "elo": 1735},
    "Democratic Republic of the Congo": {"avg_goals_scored": 1.1, "avg_goals_conceded": 1.4, "xG": 1.0, "form": 5.5, "elo": 1735},
    "Uzbekistan": {"avg_goals_scored": 1.2, "avg_goals_conceded": 1.3, "xG": 1.1, "form": 5.7, "elo": 1765},
    "Panama": {"avg_goals_scored": 1.0, "avg_goals_conceded": 1.4, "xG": 0.9, "form": 5.3, "elo": 1710},
    "Default": {"avg_goals_scored": 1.2, "avg_goals_conceded": 1.2, "xG": 1.1, "form": 6.0, "elo": 1800},
}

_POSITIONS = ["GK", "CB", "CB", "LB", "RB", "CDM", "CM", "LW", "RW", "CAM", "ST"]


# ─── BASELINE SQUAD BUILDER ────────────────────────────────────────────────

def _baseline_squad(team_name: str) -> list[dict]:
    b = TEAM_BASELINES.get(team_name, TEAM_BASELINES["Default"])
    attacking = {"ST", "LW", "RW", "CAM"}
    defending = {"CB", "LB", "RB", "CDM"}
    players = []
    for i, pos in enumerate(_POSITIONS):
        is_attacker = pos in attacking
        is_defender = pos in defending
        is_gk = pos == "GK"
        is_mid = pos in {"CM", "CAM", "LW", "RW"}
        
        players.append({
            "player_name": f"{team_name} {pos}", "team_name": team_name, "position": pos,
            "rating": round(b["form"] * 0.9 + (i % 3) * 0.1, 1),
            "goals":  round(b["avg_goals_scored"] / 3 if is_attacker else 0.05, 2),
            "xG":     round(b["xG"] / 3.5 if is_attacker else 0.03, 3),
            "xA":     round(b["xG"] / 4.0 if is_mid else 0.02, 3),
            "save_pct": 75.0 + (b["form"] * 1.5) if is_gk else 0.0,
            "tackles": round(2.5 + (b["form"] * 0.2) if is_defender else 0.5, 1),
            "form_metric": b["form"], "source": "baseline_fallback",
        })
    return players


# ─── FIXTURE SOURCES ───────────────────────────────────────────────────────

def _stable_id(team1: str, team2: str, date: str) -> int:
    """Generate a deterministic fixture ID from team names + date."""
    raw = f"{team1}|{team2}|{date}"
    return int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)


def _fetch_openfootball() -> list[dict] | None:
    """Fetch all 104 matches from openfootball GitHub JSON."""
    try:
        r = requests.get(OPENFOOTBALL_URL, timeout=15)
        r.raise_for_status()
        data = r.json()
        matches = data.get("matches", [])
        logger.info(f"openfootball: fetched {len(matches)} matches.")
        return matches
    except Exception as e:
        logger.warning(f"openfootball fetch failed: {e}")
        return None


def _fetch_worldcup26ir() -> list[dict] | None:
    """Fetch matches from worldcup26.ir REST API."""
    try:
        r = requests.get(WORLDCUP26_URL, timeout=15)
        r.raise_for_status()
        data = r.json()
        games = data.get("games", [])
        logger.info(f"worldcup26.ir: fetched {len(games)} games.")
        return games
    except Exception as e:
        logger.warning(f"worldcup26.ir fetch failed: {e}")
        return None


def _parse_openfootball_status(match: dict) -> tuple[int | None, int | None, str]:
    """Extract score and status from openfootball format."""
    score = match.get("score", {})
    ft = score.get("ft")
    if ft and len(ft) == 2:
        return ft[0], ft[1], "FT"
    return None, None, "NS"


def fetch_and_store_fixtures() -> int:
    """
    Fetch real WC 2026 fixtures. Priority:
      1. openfootball JSON (complete schedule + scores)
      2. worldcup26.ir API (live scores)
      3. Mock fixtures (if both fail)
    """
    # Try openfootball first (most reliable, has full schedule)
    matches = _fetch_openfootball()
    if matches:
        return _store_openfootball(matches)

    # Fallback: worldcup26.ir
    games = _fetch_worldcup26ir()
    if games:
        return _store_worldcup26ir(games)

    # Last resort: mock
    logger.warning("Both data sources failed — seeding mock fixtures.")
    return _insert_mock_fixtures()


def _store_openfootball(matches: list[dict]) -> int:
    """Parse and store openfootball matches into fixtures table."""
    conn = get_connection()
    inserted = 0
    try:
        with conn.cursor() as cur:
            for m in matches:
                team1 = m.get("team1", "")
                team2 = m.get("team2", "")
                raw_date = m.get("date", "")
                time_str = m.get("time", "")
                
                # Combine date and time if available
                date = f"{raw_date} {time_str}".strip() if raw_date else ""
                
                group = m.get("group", "")
                ground = m.get("ground", "")

                # Skip knockout placeholder matches (e.g. "W74", "2A")
                if not team1 or not team2:
                    continue
                if any(c.isdigit() for c in team1) and len(team1) <= 5:
                    continue

                fid = _stable_id(team1, team2, date)
                home_score, away_score, status = _parse_openfootball_status(m)

                cur.execute("""
                    INSERT INTO fixtures
                        (id, home_team, away_team, match_date, real_home_score, real_away_score, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(id) DO UPDATE SET
                        real_home_score = COALESCE(EXCLUDED.real_home_score, fixtures.real_home_score),
                        real_away_score = COALESCE(EXCLUDED.real_away_score, fixtures.real_away_score),
                        status = CASE WHEN EXCLUDED.status = 'FT' THEN 'FT' ELSE fixtures.status END
                """, (fid, team1, team2, date, home_score, away_score, status))
                if cur.rowcount > 0:
                    inserted += 1

        conn.commit()
        logger.info(f"openfootball: {inserted} fixtures stored/updated.")
    finally:
        conn.close()
    return inserted


def _store_worldcup26ir(games: list[dict]) -> int:
    """Parse and store worldcup26.ir API matches."""
    conn = get_connection()
    inserted = 0
    try:
        with conn.cursor() as cur:
            for g in games:
                home = g.get("home_team_name_en", "")
                away = g.get("away_team_name_en", "")
                if not home or not away:
                    # Knockout placeholder
                    continue

                date_str = g.get("local_date", "")
                # Parse "06/13/2026 18:00" → "2026-06-13"
                try:
                    dt = datetime.strptime(date_str, "%m/%d/%Y %H:%M")
                    iso_date = dt.strftime("%Y-%m-%d")
                except Exception:
                    iso_date = date_str

                fid = _stable_id(home, away, iso_date)
                finished = g.get("finished", "FALSE") == "TRUE"
                home_score = int(g["home_score"]) if finished else None
                away_score = int(g["away_score"]) if finished else None
                status = "FT" if finished else "NS"

                cur.execute("""
                    INSERT INTO fixtures
                        (id, home_team, away_team, match_date, real_home_score, real_away_score, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(id) DO UPDATE SET
                        real_home_score = COALESCE(EXCLUDED.real_home_score, fixtures.real_home_score),
                        real_away_score = COALESCE(EXCLUDED.real_away_score, fixtures.real_away_score),
                        status = CASE WHEN EXCLUDED.status = 'FT' THEN 'FT' ELSE fixtures.status END
                """, (fid, home, away, iso_date, home_score, away_score, status))
                if cur.rowcount > 0:
                    inserted += 1

        conn.commit()
        logger.info(f"worldcup26.ir: {inserted} fixtures stored/updated.")
    finally:
        conn.close()
    return inserted


def _insert_mock_fixtures() -> int:
    """Absolute last resort — hardcoded group stage openers."""
    mock = [
        ("Mexico",    "South Africa",    "2026-06-11"),
        ("South Korea","Czech Republic", "2026-06-11"),
        ("Canada",    "Bosnia & Herzegovina","2026-06-12"),
        ("USA",       "Paraguay",        "2026-06-12"),
        ("Brazil",    "Morocco",         "2026-06-13"),
        ("Haiti",     "Scotland",        "2026-06-13"),
        ("Qatar",     "Switzerland",     "2026-06-13"),
        ("Australia", "Turkey",          "2026-06-13"),
    ]
    conn = get_connection()
    inserted = 0
    try:
        with conn.cursor() as cur:
            for home, away, date in mock:
                fid = _stable_id(home, away, date)
                cur.execute("""
                    INSERT INTO fixtures
                        (id, home_team, away_team, match_date, status)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT(id) DO NOTHING
                """, (fid, home, away, date, "NS"))
                if cur.rowcount > 0:
                    inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted


# ─── FIXTURE QUERIES ───────────────────────────────────────────────────────

def get_upcoming_fixtures(limit: int = 10) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, home_team, away_team, match_date FROM fixtures
                WHERE status IN ('NS','TBD','POSTP') 
                AND SUBSTRING(match_date, 1, 10) = (
                    SELECT SUBSTRING(match_date, 1, 10) FROM fixtures WHERE status IN ('NS','TBD','POSTP') ORDER BY match_date ASC LIMIT 1
                )
                ORDER BY match_date ASC
            """)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def get_completed_fixtures() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, home_team, away_team, match_date, real_home_score, real_away_score
                FROM fixtures WHERE status = 'FT'
                ORDER BY match_date ASC
            """)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


# ─── PLAYER DATA ───────────────────────────────────────────────────────────

def _within_lineup_window(match_date_str: str) -> bool:
    try:
        kickoff = datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        delta = kickoff - now
        return timedelta(minutes=-10) <= delta <= timedelta(minutes=75)
    except Exception:
        return False


def _api_get(endpoint: str, params: dict) -> dict | None:
    if not API_KEY:
        return None
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("errors"):
            logger.warning(f"API-Football error on {endpoint}: {data['errors']}")
            return None
        return data
    except Exception as e:
        logger.warning(f"API-Football GET /{endpoint} failed: {e}")
        return None


def get_starting_xi(team_name: str, fixture_id: int, match_date: str = "") -> list[dict]:
    """Get starting XI for a team. Falls back through API → baseline."""
    if match_date and _within_lineup_window(match_date):
        players = _fetch_confirmed_lineup(team_name, fixture_id)
        if players:
            _upsert_players(players)
            return players

    players = _fetch_player_stats(team_name)
    if players:
        _upsert_players(players)
        return players

    return _baseline_squad(team_name)


def _fetch_confirmed_lineup(team_name: str, fixture_id: int) -> list[dict] | None:
    data = _api_get("fixtures/lineups", {"fixture": fixture_id})
    if not data:
        return None
    for team_data in data.get("response", []):
        if team_data["team"]["name"].lower() == team_name.lower():
            players = []
            for entry in team_data.get("startXI", [])[:11]:
                p = entry.get("player", {})
                players.append({
                    "player_name": p.get("name", "Unknown"), "team_name": team_name,
                    "position": p.get("pos", "MF"), "rating": 7.0, "goals": 0,
                    "xG": 0.1, "xA": 0.05, "save_pct": 0.0, "tackles": 1.0,
                    "form_metric": 7.0, "source": "confirmed_lineup",
                })
            return players if len(players) == 11 else None
    return None


def _fetch_player_stats(team_name: str) -> list[dict] | None:
    team_data = _api_get("teams", {"name": team_name})
    if not team_data or not team_data.get("response"):
        return None
    team_id = team_data["response"][0]["team"]["id"]
    stats_data = _api_get("players", {"team": team_id, "season": 2024, "page": 1})
    if not stats_data or not stats_data.get("response"):
        return None
    players = []
    for entry in stats_data["response"][:11]:
        p = entry["player"]
        s = entry.get("statistics", [{}])[0]
        g = s.get("goals", {})
        rating = float(s.get("games", {}).get("rating") or 7.0)
        goals  = int(g.get("total") or 0)
        assists = int(g.get("assists") or 0)
        tackles_stat = float(s.get("tackles", {}).get("total") or 0.0)
        save_pct = float(s.get("penalty", {}).get("saved") or 0.0) * 100.0 # Placeholder logic for save pct from API

        players.append({
            "player_name": p.get("name", "Unknown"), "team_name": team_name,
            "position": s.get("games", {}).get("position", "MF"), "rating": rating,
            "goals": goals, "xG": round(goals * 0.85, 3), "xA": round(assists * 0.75, 3),
            "save_pct": save_pct, "tackles": tackles_stat,
            "form_metric": rating, "source": "api_football",
        })
    return players or None


def _upsert_players(players: list[dict]) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for p in players:
                cur.execute("""
                    INSERT INTO player_stats (player_name, team_name, position, rating, goals, xG, xA, save_pct, tackles, form_metric)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(player_name, team_name) DO UPDATE SET
                        position=EXCLUDED.position, rating=EXCLUDED.rating, goals=EXCLUDED.goals,
                        xG=EXCLUDED.xG, xA=EXCLUDED.xA, save_pct=EXCLUDED.save_pct, tackles=EXCLUDED.tackles,
                        form_metric=EXCLUDED.form_metric
                """, (p["player_name"], p["team_name"], p.get("position", "MF"), p["rating"], p["goals"], p["xG"], p.get("xA", 0.0), p.get("save_pct", 0.0), p.get("tackles", 0.0), p["form_metric"]))
        conn.commit()
    finally:
        conn.close()


def fetch_actual_result(fixture_id: int) -> dict | None:
    """Try to get actual result from worldcup26.ir for a fixture."""
    data = _api_get("fixtures", {"id": fixture_id})
    if data and data.get("response"):
        f = data["response"][0]
        status = f["fixture"]["status"]["short"]
        if status in ("FT", "AET", "PEN"):
            goals = f.get("goals", {})
            return {"home_score": goals.get("home", 0), "away_score": goals.get("away", 0), "status": status}
    return None


# ─── ENTRY POINT ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    from database import init_db
    init_db()

    n = fetch_and_store_fixtures()
    print(f"\nFixtures loaded: {n}")

    completed = get_completed_fixtures()
    print(f"Completed matches: {len(completed)}")
    for f in completed:
        print(f"  ✓ {f['home_team']:20} {f['real_home_score']}-{f['real_away_score']}  {f['away_team']}")

    upcoming = get_upcoming_fixtures(8)
    print(f"\nUpcoming matches: {len(upcoming)}")
    for f in upcoming:
        print(f"  ○ {f['home_team']:20} vs  {f['away_team']:20}  {f['match_date']}")
