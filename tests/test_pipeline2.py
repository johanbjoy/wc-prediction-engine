import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from orchestrator import run_pipeline
from data.database import get_connection

# Clear cache for the next upcoming match
conn = get_connection()
with conn.cursor() as cur:
    cur.execute("DELETE FROM predictions WHERE fixture_id=3051414273 AND model_name='nexus_v2'")
    cur.execute("DELETE FROM cache WHERE key='tactical_3051414273'")
conn.commit()
conn.close()

print("Running pipeline...")
res = run_pipeline(3051414273)
import json
print(json.dumps(res, indent=2))
