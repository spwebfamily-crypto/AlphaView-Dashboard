from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base


class SessionManager:
    def __init__(self, database_url: str) -> None:
        engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
        if database_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if ":memory:" in database_url:
                engine_kwargs["poolclass"] = StaticPool

        self.engine = create_engine(database_url, **engine_kwargs)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(bind=self.engine)
        self._apply_runtime_migrations()

    def dispose(self) -> None:
        self.engine.dispose()

    def get_session(self) -> Generator[Session, None, None]:
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    def healthcheck(self) -> str:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"

    def _apply_runtime_migrations(self) -> None:
        inspector = inspect(self.engine)
        if "users" not in inspector.get_table_names():
            return

        existing_columns = {column["name"] for column in inspector.get_columns("users")}
        statements = []
        if "password_hash" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''")
        if "password_salt" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN password_salt VARCHAR(255) NOT NULL DEFAULT ''")
        if "role" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'member'")
        if "last_login_at" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP WITH TIME ZONE")
        if "currency" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'usd'")
        if "withdrawable_balance_cents" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN withdrawable_balance_cents INTEGER NOT NULL DEFAULT 0")
        if "stripe_connected_account_id" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN stripe_connected_account_id VARCHAR(255)")
        if "stripe_onboarding_complete" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN stripe_onboarding_complete BOOLEAN NOT NULL DEFAULT false")
        if "stripe_transfers_enabled" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN stripe_transfers_enabled BOOLEAN NOT NULL DEFAULT false")
        if "stripe_customer_id" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(255)")
        if "stripe_subscription_id" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(255)")
        if "billing_status" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN billing_status VARCHAR(64)")
        if "billing_plan_code" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN billing_plan_code VARCHAR(128)")
        if "billing_current_period_end" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN billing_current_period_end TIMESTAMP WITH TIME ZONE")
        if "billing_last_checkout_session_id" not in existing_columns:
            statements.append("ALTER TABLE users ADD COLUMN billing_last_checkout_session_id VARCHAR(255)")

        if not statements:
            return

        with self.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_stripe_connected_account_id "
                    "ON users (stripe_connected_account_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_stripe_customer_id "
                    "ON users (stripe_customer_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_stripe_subscription_id "
                    "ON users (stripe_subscription_id)"
                )
            )

