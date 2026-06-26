from __future__ import annotations

import sys
from pathlib import Path


DATA_CONVERTER_DIR = Path(__file__).resolve().parents[1]
if str(DATA_CONVERTER_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_CONVERTER_DIR))
