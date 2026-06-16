"""
database.py — PostgreSQL schema and connection factory for Supabase.
"""
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def get_connection():
    db_url = os.getenv("SUPABASE_DATABASE_URL")
    if not db_url:
        raise ValueError("SUPABASE_DATABASE_URL is missing. Please set it in your .env file.")
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    return conn


def init_db() -> None:
    """Create all tables. Safe to call repeatedly (IF NOT EXISTS guards)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS fixtures (
                    id                BIGINT PRIMARY KEY,
                    home_team         TEXT NOT NULL,
                    away_team         TEXT NOT NULL,
                    match_date        TEXT NOT NULL,
                    real_home_score   INTEGER,
                    real_away_score   INTEGER,
                    status            TEXT DEFAULT 'NS'
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    id            SERIAL PRIMARY KEY,
                    player_name   TEXT NOT NULL,
                    team_name     TEXT NOT NULL,
                    position      TEXT,
                    rating        REAL DEFAULT 7.0,
                    goals         INTEGER DEFAULT 0,
                    xG            REAL DEFAULT 0.0,
                    xA            REAL DEFAULT 0.0,
                    save_pct      REAL DEFAULT 0.0,
                    tackles       REAL DEFAULT 0.0,
                    form_metric   REAL DEFAULT 6.0,
                    UNIQUE(player_name, team_name)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id                     SERIAL PRIMARY KEY,
                    fixture_id             BIGINT NOT NULL,
                    model_name             TEXT NOT NULL,
                    predicted_home_score   INTEGER NOT NULL,
                    predicted_away_score   INTEGER NOT NULL,
                    points_awarded         INTEGER,
                    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(fixture_id) REFERENCES fixtures(id) ON DELETE CASCADE,
                    UNIQUE(fixture_id, model_name)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS leaderboard (
                    model_name           TEXT PRIMARY KEY,
                    total_points         INTEGER DEFAULT 0,
                    exact_scores_count   INTEGER DEFAULT 0,
                    correct_winner_count INTEGER DEFAULT 0,
                    wrong_count          INTEGER DEFAULT 0
                );
            """)

            # Key-Value cache for Agent 1's expensive tactical analyses
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key         TEXT PRIMARY KEY,
                    value       TEXT NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

        conn.commit()
        logger.info("Database tables initialized successfully (PostgreSQL).")
    finally:
        conn.close()


def get_team_players(team_name: str) -> list[dict]:
    """Fetch cached player stats for a specific team."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM player_stats WHERE team_name = %s", (team_name,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def upsert_player(player_name: str, team_name: str, rating: float, goals: int, xG: float, xA: float=0.0, save_pct: float=0.0, tackles: float=0.0, position: str="MF") -> None:
    """Insert or update player stats."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO player_stats (player_name, team_name, position, rating, goals, xG, xA, save_pct, tackles)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(player_name, team_name) DO UPDATE SET
                    position = EXCLUDED.position,
                    rating = EXCLUDED.rating,
                    goals = EXCLUDED.goals,
                    xG = EXCLUDED.xG,
                    xA = EXCLUDED.xA,
                    save_pct = EXCLUDED.save_pct,
                    tackles = EXCLUDED.tackles
            """, (player_name, team_name, position, rating, goals, xG, xA, save_pct, tackles))
        conn.commit()
    finally:
        conn.close()


def get_recent_predictions(limit: int = 15) -> list[dict]:
    """Fetch the most recent predictions from the database."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    f.home_team, f.away_team, f.match_date,
                    f.real_home_score, f.real_away_score,
                    p.model_name,
                    p.predicted_home_score, p.predicted_away_score,
                    p.points_awarded
                FROM predictions p
                JOIN fixtures f ON f.id = p.fixture_id
                ORDER BY f.match_date DESC, p.created_at DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
