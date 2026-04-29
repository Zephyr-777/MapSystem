from __future__ import annotations

from pathlib import Path
from typing import Any


SOUTHWEST_TEMPERATURE_DATASET_ID = "southwest-china-temperature-90ka"
SOUTHWEST_TEMPERATURE_ROOT = Path("/Volumes/固态硬盘/毕设文件") / "中国西南地区过去9万年以来定量温度数据集"
SOUTHWEST_TEMPERATURE_FILE = (
    SOUTHWEST_TEMPERATURE_ROOT
    / "Possible obliquity-forced warmth in southern Asia during the last glacial stage.xlsx"
)


def build_southwest_temperature_dataset_response() -> dict[str, Any]:
    if not SOUTHWEST_TEMPERATURE_FILE.exists():
        raise FileNotFoundError(f"Southwest temperature dataset not found: {SOUTHWEST_TEMPERATURE_FILE}")

    return {
        "dataset_id": SOUTHWEST_TEMPERATURE_DATASET_ID,
        "name": "中国西南地区过去9万年以来定量温度数据集",
        "description": "Excel 表格数据，仅提供索引点定位与原始文件下载，不在地图上做栅格或矢量可视化。",
        "center_x": 103.5,
        "center_y": 27.8,
        "srid": 4326,
        "bbox": [97.0, 21.0, 110.0, 34.0],
        "download_url": "/api/download/southwest-temperature",
        "file_name": SOUTHWEST_TEMPERATURE_FILE.name,
        "file_size": SOUTHWEST_TEMPERATURE_FILE.stat().st_size,
        "time_range": "过去9万年以来",
        "metadata": {
            "dataset_name": "中国西南地区过去9万年以来定量温度数据集",
            "source_file_name": SOUTHWEST_TEMPERATURE_FILE.name,
            "time_range": "过去9万年以来",
            "format": "Excel",
        },
    }
