"""reservation_plans baseline

Revision ID: 20260401_0001
Revises:
Create Date: 2026-04-01 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = "20260401_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgresql(connection: Connection) -> bool:
    return connection.dialect.name == "postgresql"


def _index_exists(connection: Connection, table_name: str, index_name: str) -> bool:
    inspector = inspect(connection)
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)

    if "reservation_plans" not in inspector.get_table_names():
        op.create_table(
            "reservation_plans",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.String(length=64), nullable=False),
            sa.Column("destinations", sa.String(), nullable=True),
            sa.Column("departure", sa.String(), nullable=True),
            sa.Column("hotel", sa.String(), nullable=True),
            sa.Column("airlines", sa.String(), nullable=True),
            sa.Column("railway", sa.String(), nullable=True),
            sa.Column("taxi", sa.String(), nullable=True),
            sa.Column("start_date", sa.String(), nullable=True),
            sa.Column("end_date", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_reservation_plans_id", "reservation_plans", ["id"], unique=False)
        op.create_index("ix_reservation_plans_session_id", "reservation_plans", ["session_id"], unique=False)
        return

    column_map = {column["name"]: column for column in inspector.get_columns("reservation_plans")}
    if "session_id" not in column_map:
        if _is_postgresql(connection):
            connection.execute(
                text(
                    "ALTER TABLE reservation_plans "
                    "ADD COLUMN IF NOT EXISTS session_id VARCHAR(64) NOT NULL DEFAULT 'legacy-session'"
                )
            )
            connection.execute(
                text("ALTER TABLE reservation_plans ALTER COLUMN session_id DROP DEFAULT")
            )
        else:
            op.add_column(
                "reservation_plans",
                sa.Column("session_id", sa.String(length=64), nullable=False, server_default="legacy-session"),
            )
            op.alter_column("reservation_plans", "session_id", server_default=None)
    elif _is_postgresql(connection) and column_map["session_id"].get("nullable", True):
        connection.execute(
            text("UPDATE reservation_plans SET session_id = 'legacy-session' WHERE session_id IS NULL")
        )
        connection.execute(text("ALTER TABLE reservation_plans ALTER COLUMN session_id SET NOT NULL"))

    if not _index_exists(connection, "reservation_plans", "ix_reservation_plans_session_id"):
        op.create_index("ix_reservation_plans_session_id", "reservation_plans", ["session_id"], unique=False)

    if not _index_exists(connection, "reservation_plans", "ix_reservation_plans_id"):
        op.create_index("ix_reservation_plans_id", "reservation_plans", ["id"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    if "reservation_plans" not in inspector.get_table_names():
        return

    if _index_exists(connection, "reservation_plans", "ix_reservation_plans_session_id"):
        op.drop_index("ix_reservation_plans_session_id", table_name="reservation_plans")
    if _index_exists(connection, "reservation_plans", "ix_reservation_plans_id"):
        op.drop_index("ix_reservation_plans_id", table_name="reservation_plans")

    columns = {column["name"] for column in inspector.get_columns("reservation_plans")}
    if columns == {
        "id",
        "session_id",
        "destinations",
        "departure",
        "hotel",
        "airlines",
        "railway",
        "taxi",
        "start_date",
        "end_date",
    }:
        op.drop_table("reservation_plans")
        return

    if "session_id" in columns:
        if _is_postgresql(connection):
            connection.execute(text("ALTER TABLE reservation_plans DROP COLUMN IF EXISTS session_id"))
