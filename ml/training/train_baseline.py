from __future__ import annotations

from ml.training.utils import ensure_backend_on_path

ensure_backend_on_path()

from app.workers.retrain_worker import main  # noqa: E402


if __name__ == "__main__":
    main()

