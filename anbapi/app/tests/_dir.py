import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] 
p = str(APP_DIR)
if p not in sys.path:
    sys.path.insert(0, p)
