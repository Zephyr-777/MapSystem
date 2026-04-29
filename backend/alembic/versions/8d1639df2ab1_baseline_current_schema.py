"""baseline_current_schema

Revision ID: 8d1639df2ab1
Revises:
Create Date: 2026-04-21 15:45:56.243053

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8d1639df2ab1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the full baseline schema for a fresh or partially restored DB."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'guest',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS geo_assets (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            file_path VARCHAR(500) NOT NULL,
            file_type VARCHAR(50) NOT NULL DEFAULT '栅格',
            sub_type VARCHAR(50),
            is_sidecar BOOLEAN DEFAULT false,
            parent_id INTEGER REFERENCES geo_assets(id),
            extent VARCHAR(50),
            srid INTEGER DEFAULT 4326,
            extent_min_x DOUBLE PRECISION,
            extent_min_y DOUBLE PRECISION,
            extent_max_x DOUBLE PRECISION,
            extent_max_y DOUBLE PRECISION,
            center_x DOUBLE PRECISION,
            center_y DOUBLE PRECISION,
            width INTEGER,
            height INTEGER,
            resolution_x DOUBLE PRECISION,
            resolution_y DOUBLE PRECISION,
            description VARCHAR(500),
            image_path VARCHAR(500),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_geo_assets_id ON geo_assets (id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_geo_assets_name ON geo_assets (name);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS attachments (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_type VARCHAR(50),
            geo_asset_id INTEGER NOT NULL REFERENCES geo_assets(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_attachments_id ON attachments (id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS geologic_features (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(50) NOT NULL,
            properties JSONB,
            geometry TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_geologic_features_id ON geologic_features (id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS boreholes (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            elevation DOUBLE PRECISION,
            depth DOUBLE PRECISION,
            properties JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_boreholes_id ON boreholes (id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_boreholes_name ON boreholes (name);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS attachments;")
    op.execute("DROP TABLE IF EXISTS boreholes;")
    op.execute("DROP TABLE IF EXISTS geologic_features;")
    op.execute("DROP TABLE IF EXISTS geo_assets;")
    op.execute("DROP TABLE IF EXISTS users;")
