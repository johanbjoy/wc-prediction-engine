from data.database import get_connection
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT home_team, away_team, real_home_score, status FROM fixtures WHERE tournament LIKE '%World Cup 2026%' LIMIT 5")
print(cur.fetchall())
