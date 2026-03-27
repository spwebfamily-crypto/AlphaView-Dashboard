from __future__ import annotations

from ml.training.utils import ensure_backend_on_path

ensure_backend_on_path()

from app.services.feature_service import build_feature_frame  # noqa: E402

__all__ = ["build_feature_frame"]

