from __future__ import annotations

from ml.training.utils import ensure_backend_on_path

ensure_backend_on_path()

from app.services.model_service import compute_classification_metrics  # noqa: E402

__all__ = ["compute_classification_metrics"]

