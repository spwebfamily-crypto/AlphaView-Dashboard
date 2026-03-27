from __future__ import annotations

import json
from pathlib import Path


def load_backtest_report(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

