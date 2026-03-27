from __future__ import annotations

from pathlib import Path
import sys


def ensure_backend_on_path() -> Path:
    backend_dir = Path(__file__).resolve().parents[2] / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    return backend_dir

