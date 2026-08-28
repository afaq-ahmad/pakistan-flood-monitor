import os
import sys
from pathlib import Path

# Unit and integration tests may use deterministic fixtures, but the runtime
# still labels them. Individual integrity tests explicitly exercise demo and
# operational modes.
os.environ.setdefault("APP_MODE", "test")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
