import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from orchestrator import run_pipeline
res = run_pipeline()
print(res)
