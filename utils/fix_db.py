from data.database import get_connection

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("""
        UPDATE predictions p
        SET points_awarded = NULL
        FROM fixtures f
        WHERE p.fixture_id = f.id AND f.status NOT IN ('FT', 'AET', 'PEN')
    """)
conn.commit()
conn.close()
print("Fixed DB NULL values!")
