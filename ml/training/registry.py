from __future__ import annotations

from pathlib import Path


def list_model_artifacts(model_registry_dir: str | Path) -> list[Path]:
    root = Path(model_registry_dir)
    if not root.exists():
        return []
    return sorted(root.glob("*.pkl"))

