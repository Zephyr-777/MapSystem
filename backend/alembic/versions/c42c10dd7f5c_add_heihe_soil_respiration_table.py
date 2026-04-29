"""add_heihe_soil_respiration_table

Revision ID: c42c10dd7f5c
Revises: 8d1639df2ab1
Create Date: 2026-04-22 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c42c10dd7f5c"
down_revision: Union[str, Sequence[str], None] = "8d1639df2ab1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS heihe_soil_respiration (
            id BIGSERIAL PRIMARY KEY,
            site_key TEXT NOT NULL,
            site_name TEXT NOT NULL,
            ring_code TEXT NULL,
            observed_at TIMESTAMP NOT NULL,
            observed_date DATE NOT NULL,
            doy DOUBLE PRECISION NULL,
            soil_respiration_rate DOUBLE PRECISION NULL,
            linear_flux DOUBLE PRECISION NULL,
            fit_status TEXT NULL,
            device_name TEXT NOT NULL DEFAULT 'LI-8100',
            source_file_name TEXT NOT NULL,
            source_file_path TEXT NOT NULL,
            lon DOUBLE PRECISION NOT NULL,
            lat DOUBLE PRECISION NOT NULL,
            location_precision TEXT NOT NULL DEFAULT 'site',
            raw_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            geom geometry(Point, 4326) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_heihe_source_file_time_site UNIQUE (source_file_name, observed_at, site_key)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_heihe_soil_respiration_geom
        ON heihe_soil_respiration USING GIST (geom);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_heihe_soil_respiration_site_key
        ON heihe_soil_respiration (site_key);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_heihe_soil_respiration_observed_at
        ON heihe_soil_respiration (observed_at);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS heihe_soil_respiration;")
