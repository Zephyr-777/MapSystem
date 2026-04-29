from __future__ import annotations

import json
from pathlib import Path
import sys

from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import engine, init_postgis
from app.services.heihe_dataset import (
    HEIHE_TABLE_NAME,
    build_import_rows,
    get_dataset_directory,
    summarize_import_rows,
)


CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {HEIHE_TABLE_NAME} (
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
    raw_metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    geom geometry(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_heihe_source_file_time_site UNIQUE (source_file_name, observed_at, site_key)
);
"""

CREATE_INDEX_SQL = [
    f"CREATE INDEX IF NOT EXISTS idx_{HEIHE_TABLE_NAME}_geom ON {HEIHE_TABLE_NAME} USING GIST (geom);",
    f"CREATE INDEX IF NOT EXISTS idx_{HEIHE_TABLE_NAME}_site_key ON {HEIHE_TABLE_NAME} (site_key);",
    f"CREATE INDEX IF NOT EXISTS idx_{HEIHE_TABLE_NAME}_observed_at ON {HEIHE_TABLE_NAME} (observed_at);",
]

UPSERT_SQL = text(
    f"""
    INSERT INTO {HEIHE_TABLE_NAME} (
        site_key,
        site_name,
        ring_code,
        observed_at,
        observed_date,
        doy,
        soil_respiration_rate,
        linear_flux,
        fit_status,
        device_name,
        source_file_name,
        source_file_path,
        lon,
        lat,
        location_precision,
        raw_metadata,
        geom
    ) VALUES (
        :site_key,
        :site_name,
        :ring_code,
        :observed_at,
        :observed_date,
        :doy,
        :soil_respiration_rate,
        :linear_flux,
        :fit_status,
        :device_name,
        :source_file_name,
        :source_file_path,
        :lon,
        :lat,
        :location_precision,
        CAST(:raw_metadata AS JSONB),
        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
    )
    ON CONFLICT (source_file_name, observed_at, site_key) DO UPDATE SET
        site_name = EXCLUDED.site_name,
        ring_code = EXCLUDED.ring_code,
        observed_date = EXCLUDED.observed_date,
        doy = EXCLUDED.doy,
        soil_respiration_rate = EXCLUDED.soil_respiration_rate,
        linear_flux = EXCLUDED.linear_flux,
        fit_status = EXCLUDED.fit_status,
        device_name = EXCLUDED.device_name,
        source_file_path = EXCLUDED.source_file_path,
        lon = EXCLUDED.lon,
        lat = EXCLUDED.lat,
        location_precision = EXCLUDED.location_precision,
        raw_metadata = EXCLUDED.raw_metadata,
        geom = EXCLUDED.geom,
        updated_at = now();
    """
)


def ensure_schema() -> None:
    init_postgis()
    with engine.begin() as conn:
        conn.execute(text(CREATE_TABLE_SQL))
        conn.execute(
            text(
                f"""
                ALTER TABLE {HEIHE_TABLE_NAME}
                ALTER COLUMN soil_respiration_rate DROP NOT NULL;
                """
            )
        )
        for statement in CREATE_INDEX_SQL:
            conn.execute(text(statement))


def import_dataset() -> dict:
    rows = build_import_rows(get_dataset_directory())
    summary = summarize_import_rows(rows)

    with engine.begin() as conn:
        for row in rows:
            params = dict(row)
            params["raw_metadata"] = json.dumps(row["raw_metadata"], ensure_ascii=False)
            conn.execute(UPSERT_SQL, params)

    return summary


if __name__ == "__main__":
    dataset_dir = get_dataset_directory()
    if not dataset_dir.exists():
        raise SystemExit(f"Dataset directory does not exist: {dataset_dir}")

    ensure_schema()
    result = import_dataset()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
