#!/usr/bin/env python3
"""
Create demo GeoTIFF assets with colorful previews so they can be clicked on the
map and displayed in the right-side panel.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.geo_asset import GeoAsset
from utils.optimize_tif import optimize_asset_preview


@dataclass(frozen=True)
class DemoAssetSpec:
    name: str
    description: str
    center_x: float
    center_y: float
    lon_span: float
    lat_span: float
    palette: str


DEMO_ASSETS: list[DemoAssetSpec] = [
    DemoAssetSpec(
        name="测试遥感影像_北部断层",
        description="用于前端联调的彩色 GeoTIFF 预览图，模拟北部断层带遥感影像。",
        center_x=116.4050,
        center_y=39.9340,
        lon_span=0.0600,
        lat_span=0.0400,
        palette="terrain",
    ),
    DemoAssetSpec(
        name="测试遥感影像_城区地貌",
        description="用于点选预览的城市地貌测试影像。",
        center_x=116.4380,
        center_y=39.9050,
        lon_span=0.0550,
        lat_span=0.0350,
        palette="sunset",
    ),
    DemoAssetSpec(
        name="测试遥感影像_南部水系",
        description="用于右侧图片面板测试的南部水系影像。",
        center_x=116.3720,
        center_y=39.8720,
        lon_span=0.0500,
        lat_span=0.0320,
        palette="water",
    ),
]


def build_rgb_array(width: int, height: int, palette: str) -> np.ndarray:
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)
    xx, yy = np.meshgrid(x, y)

    ridge = np.sin(xx * np.pi * 4.0) * 0.5 + 0.5
    waves = np.cos(yy * np.pi * 3.0) * 0.5 + 0.5
    blend = np.clip((ridge * 0.55 + waves * 0.45), 0.0, 1.0)

    if palette == "terrain":
        red = 90 + blend * 120 + yy * 30
        green = 70 + blend * 100 + xx * 60
        blue = 40 + waves * 70
    elif palette == "sunset":
        red = 150 + xx * 90
        green = 60 + blend * 90
        blue = 90 + (1.0 - yy) * 110
    else:
        red = 40 + ridge * 40
        green = 100 + blend * 80
        blue = 140 + xx * 90

    rgb = np.stack([red, green, blue], axis=0)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def write_geotiff(output_path: Path, spec: DemoAssetSpec, width: int = 512, height: int = 384) -> tuple[int, int, float, float, float, float]:
    left = spec.center_x - spec.lon_span / 2
    right = spec.center_x + spec.lon_span / 2
    bottom = spec.center_y - spec.lat_span / 2
    top = spec.center_y + spec.lat_span / 2
    transform = from_bounds(left, bottom, right, top, width, height)
    data = build_rgb_array(width, height, spec.palette)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=3,
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data)

    return width, height, left, bottom, right, top


def upsert_demo_asset(db, spec: DemoAssetSpec) -> tuple[GeoAsset, bool]:
    batch_dir = settings.RASTER_DIR / "demo_samples"
    tif_path = batch_dir / f"{spec.name}.tif"
    width, height, left, bottom, right, top = write_geotiff(tif_path, spec)
    relative_path = tif_path.relative_to(settings.STORAGE_DIR).as_posix()

    asset = db.query(GeoAsset).filter(GeoAsset.name == spec.name).first()
    created = asset is None
    if asset is None:
        asset = GeoAsset(name=spec.name, file_path=relative_path, file_type="栅格", sub_type="GeoTIFF")
        db.add(asset)

    asset.file_path = relative_path
    asset.file_type = "栅格"
    asset.sub_type = "GeoTIFF"
    asset.description = spec.description
    asset.width = width
    asset.height = height
    asset.srid = 4326
    asset.extent_min_x = left
    asset.extent_min_y = bottom
    asset.extent_max_x = right
    asset.extent_max_y = top
    asset.center_x = spec.center_x
    asset.center_y = spec.center_y

    db.commit()
    db.refresh(asset)

    preview_path = optimize_asset_preview(tif_path, settings.STORAGE_DIR, asset.id)
    asset.image_path = preview_path
    db.commit()
    db.refresh(asset)

    try:
        db.execute(
            text(
                "UPDATE geo_assets "
                "SET extent = ST_SetSRID(ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326), 4326) "
                "WHERE id = :id"
            ),
            {"minx": left, "miny": bottom, "maxx": right, "maxy": top, "id": asset.id},
        )
        db.commit()
    except Exception:
        db.rollback()

    return asset, created


def main() -> int:
    db = SessionLocal()
    created_count = 0
    updated_count = 0

    try:
        print(f"Storage dir: {settings.STORAGE_DIR}")
        db.execute(text("ALTER TABLE geo_assets ADD COLUMN IF NOT EXISTS image_path VARCHAR(500)"))
        db.commit()

        for spec in DEMO_ASSETS:
            asset, created = upsert_demo_asset(db, spec)
            if created:
                created_count += 1
            else:
                updated_count += 1
            print(
                f"[{'created' if created else 'updated'}] "
                f"id={asset.id} name={asset.name} center=({asset.center_x}, {asset.center_y}) image_path={asset.image_path}"
            )

        print(f"Done. created={created_count} updated={updated_count}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
