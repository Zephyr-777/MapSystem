from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import math
import re
import zipfile

import pandas as pd

HEIHE_DATASET_ID = "heihe-soil-respiration"
HEIHE_DEVICE_NAME = "Li-8100"
HEIHE_TABLE_NAME = "heihe_soil_respiration"
HEIHE_DATASET_DIR = Path(
    "/Volumes/固态硬盘/毕设文件/黑河生态水文遥感试验：黑河下游Li-8100观测土壤呼吸数据集（2014年7月-8月）"
)
HEIHE_WORKBOOK_PATH = HEIHE_DATASET_DIR / "野外土壤呼吸实验表.xls"
HEIHE_ARCHIVE_NAME = "heihe_soil_respiration_raw_dataset.zip"


@dataclass(slots=True)
class FileMetadata:
    file_stem: str
    site_name: str
    site_key: str
    lon: float | None
    lat: float | None
    observation_label: str | None
    weather: str | None
    observer: str | None


def get_dataset_directory() -> Path:
    return HEIHE_DATASET_DIR


def get_workbook_path() -> Path:
    return HEIHE_WORKBOOK_PATH


def assert_dataset_files_exist() -> None:
    if not HEIHE_DATASET_DIR.exists():
        raise FileNotFoundError(f"Heihe dataset directory not found: {HEIHE_DATASET_DIR}")
    if not HEIHE_WORKBOOK_PATH.exists():
        raise FileNotFoundError(f"Heihe workbook not found: {HEIHE_WORKBOOK_PATH}")


def raw_dataset_files() -> list[Path]:
    assert_dataset_files_exist()
    return sorted(path for path in HEIHE_DATASET_DIR.iterdir() if path.is_file())


def ensure_dataset_archive(target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_path = target_dir / HEIHE_ARCHIVE_NAME
    source_files = raw_dataset_files()
    latest_source_mtime = max((path.stat().st_mtime for path in source_files), default=0)

    if archive_path.exists() and archive_path.stat().st_mtime >= latest_source_mtime:
        return archive_path

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in source_files:
            zf.write(path, arcname=path.name)
    return archive_path


def canonicalize_site_label(value: str | None) -> str:
    if not value:
        return ""

    text = str(value).strip()
    replacements = {
        "取消：": "",
        "取消:": "",
        "下游": "",
        "样地": "",
        "样方": "",
        "土壤呼吸": "",
        "土壤环": "",
        "呼吸环": "",
        "混交林": "混合",
        "混合林": "混合",
        "胡杨柽柳": "胡柽",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)

    text = (
        text.replace("-", "")
        .replace("（", "")
        .replace("）", "")
        .replace("(", "")
        .replace(")", "")
        .replace("，", "")
        .replace(",", "")
        .replace(" ", "")
    )

    if "农田" in text:
        return "农田"
    if "裸地" in text:
        return "裸地"
    if "胡柽" in text:
        return "胡柽"
    if "胡杨" in text:
        return "胡杨"
    if "柽柳" in text:
        return "柽柳"
    return text


def extract_ring_codes(value: str | None) -> list[str]:
    if not value:
        return []

    text = str(value)
    match = re.search(r"环\s*[（(]([0-9，,、\s]+)[）)]", text)
    if match:
        raw_codes = re.split(r"[，,、\s]+", match.group(1).strip())
        return [code for code in raw_codes if code]

    single_match = re.search(r"环\s*([0-9]+)", text)
    if single_match:
        return [single_match.group(1)]

    return []


def infer_site_name_from_filename(file_stem: str) -> str:
    lowered = canonicalize_site_label(file_stem)
    site_name_map = {
        "农田": "农田样地",
        "裸地": "裸地样地",
        "胡杨": "胡杨样地",
        "柽柳": "柽柳样地",
        "胡柽": "胡杨柽柳混合样地",
    }
    return site_name_map.get(lowered, file_stem)


def load_sheet1_file_metadata(workbook_path: Path | None = None) -> dict[str, FileMetadata]:
    workbook_path = workbook_path or get_workbook_path()
    df = pd.read_excel(workbook_path, sheet_name="Sheet1", header=None)

    current_date: str | None = None
    current_weather: str | None = None
    current_observer: str | None = None
    current_site_name: str | None = None
    current_site_key: str | None = None
    current_lon: float | None = None
    current_lat: float | None = None
    metadata: dict[str, FileMetadata] = {}

    for row in df.itertuples(index=False):
        label = row[0]
        value = row[1]

        if isinstance(label, str) and label.strip() == "观测日期":
            current_date = str(value).strip() if not _is_nan(value) else None
            current_weather = str(row[3]).strip() if len(row) > 3 and not _is_nan(row[3]) else None
            current_observer = str(row[5]).strip() if len(row) > 5 and not _is_nan(row[5]) else None
            continue

        if isinstance(label, str) and label.strip() == "站点":
            current_site_name = str(value).strip() if not _is_nan(value) else None
            current_site_key = canonicalize_site_label(current_site_name)
            current_lon = _to_float(row[3] if len(row) > 3 else None)
            current_lat = _to_float(row[5] if len(row) > 5 else None)
            continue

        if (isinstance(label, str) and label.strip() == "文件名") or (_is_nan(label) and not _is_nan(value)):
            file_stem = str(value).strip()
            metadata[file_stem] = FileMetadata(
                file_stem=file_stem,
                site_name=current_site_name or infer_site_name_from_filename(file_stem),
                site_key=current_site_key or canonicalize_site_label(file_stem),
                lon=current_lon,
                lat=current_lat,
                observation_label=current_date,
                weather=current_weather,
                observer=current_observer,
            )

    return metadata


def load_gps_ring_metadata(workbook_path: Path | None = None) -> dict[tuple[str, str], dict[str, Any]]:
    workbook_path = workbook_path or get_workbook_path()
    df = pd.read_excel(workbook_path, sheet_name="GPS点")

    name_col = "NAME2" if "NAME2" in df.columns else df.columns[-1]
    x_col = "X" if "X" in df.columns else df.columns[1]
    y_col = "Y" if "Y" in df.columns else df.columns[2]

    records: dict[tuple[str, str], dict[str, Any]] = {}
    for row in df.itertuples(index=False):
        name = getattr(row, name_col)
        if _is_nan(name):
            continue

        name_str = str(name).strip()
        if name_str.startswith("取消"):
            continue

        site_key = canonicalize_site_label(name_str)
        ring_codes = extract_ring_codes(name_str)
        if not ring_codes:
            continue

        records[(site_key, ring_codes[0])] = {
            "name": name_str,
            "lon": _to_float(getattr(row, x_col)),
            "lat": _to_float(getattr(row, y_col)),
        }

    return records


def parse_81x_observations(file_path: Path) -> list[dict[str, Any]]:
    lines = file_path.read_text(errors="ignore").splitlines()
    block_indices = [index for index, line in enumerate(lines) if line.startswith("Obs#:")]
    if not block_indices:
        return []

    device_name = _extract_header_value(lines, "Instrument Name") or "LI-8100"
    blocks: list[dict[str, Any]] = []

    for block_number, start_index in enumerate(block_indices):
        end_index = block_indices[block_number + 1] if block_number + 1 < len(block_indices) else len(lines)
        block_lines = lines[start_index:end_index]
        header_index = next((i for i, line in enumerate(block_lines) if line.startswith("Type\t")), None)
        if header_index is None:
            continue

        columns = block_lines[header_index].split("\t")
        data_line = next((line for line in block_lines[header_index + 1 :] if re.match(r"^\d+\t-?\d+", line)), None)
        if not data_line:
            continue

        values = data_line.split("\t")
        row = {columns[i]: values[i] for i in range(min(len(columns), len(values)))}
        summary = _parse_summary_pairs(block_lines)

        observed_at = datetime.fromisoformat(row["Date"])
        blocks.append(
            {
                "obs_number": _extract_obs_number(block_lines[0]),
                "observed_at": observed_at,
                "observed_date": observed_at.date(),
                "doy": _to_float(row.get("DOY")),
                "soil_respiration_rate": _to_float(summary.get("Exp_Flux")),
                "linear_flux": _to_float(summary.get("Lin_Flux")),
                "fit_status": summary.get("CrvFitStatus"),
                "device_name": device_name,
                "tcham": _to_float(row.get("Tcham")),
                "pressure": _to_float(row.get("Pressure")),
                "h2o": _to_float(row.get("H2O")),
                "co2": _to_float(row.get("CO2")),
                "exp_flux_cv": _to_float(summary.get("Exp_FluxCV")),
                "lin_flux_cv": _to_float(summary.get("Lin_FluxCV")),
                "raw_metadata": {
                    "obs_number": _extract_obs_number(block_lines[0]),
                    "date": row.get("Date"),
                    "doy": row.get("DOY"),
                    "tcham": row.get("Tcham"),
                    "pressure": row.get("Pressure"),
                    "h2o": row.get("H2O"),
                    "co2": row.get("CO2"),
                    "cdry": row.get("Cdry"),
                    "hour": row.get("Hour"),
                    "fit_status": summary.get("CrvFitStatus"),
                    "exp_flux": summary.get("Exp_Flux"),
                    "exp_flux_cv": summary.get("Exp_FluxCV"),
                    "lin_flux": summary.get("Lin_Flux"),
                    "lin_flux_cv": summary.get("Lin_FluxCV"),
                },
            }
        )

    return blocks


def build_import_rows(dataset_dir: Path | None = None) -> list[dict[str, Any]]:
    dataset_dir = dataset_dir or get_dataset_directory()
    workbook_path = dataset_dir / HEIHE_WORKBOOK_PATH.name
    file_metadata = load_sheet1_file_metadata(workbook_path)
    gps_metadata = load_gps_ring_metadata(workbook_path)
    site_defaults: dict[str, dict[str, Any]] = {}

    for item in file_metadata.values():
        if item.site_key not in site_defaults and item.lon is not None and item.lat is not None:
            site_defaults[item.site_key] = {
                "site_name": item.site_name,
                "lon": item.lon,
                "lat": item.lat,
            }

    records: list[dict[str, Any]] = []
    missing_coordinates: list[str] = []

    for file_path in sorted(dataset_dir.glob("*.81x")):
        file_stem = file_path.stem
        metadata = file_metadata.get(file_stem)
        site_key = metadata.site_key if metadata else canonicalize_site_label(file_stem)
        site_name = metadata.site_name if metadata else infer_site_name_from_filename(file_stem)
        ring_codes = extract_ring_codes(file_stem)

        observations = parse_81x_observations(file_path)
        for index, observation in enumerate(observations):
            ring_code = _assign_ring_code(ring_codes, index)
            ring_metadata = gps_metadata.get((site_key, ring_code)) if ring_code else None
            site_default = site_defaults.get(site_key)
            resolved_site_name = metadata.site_name if metadata else (site_default["site_name"] if site_default else site_name)

            lon = ring_metadata["lon"] if ring_metadata else (
                metadata.lon if metadata and metadata.lon is not None else (site_default["lon"] if site_default else None)
            )
            lat = ring_metadata["lat"] if ring_metadata else (
                metadata.lat if metadata and metadata.lat is not None else (site_default["lat"] if site_default else None)
            )
            location_precision = "ring" if ring_metadata else "site"

            if lon is None or lat is None:
                missing_coordinates.append(f"{file_stem}#obs{observation['obs_number']}")
                continue

            raw_metadata = dict(observation["raw_metadata"])
            raw_metadata.update(
                {
                    "source_observation_label": metadata.observation_label if metadata else None,
                    "weather": metadata.weather if metadata else None,
                    "observer": metadata.observer if metadata else None,
                    "ring_candidates": ring_codes,
                    "assigned_ring_code": ring_code,
                }
            )

            records.append(
                    {
                        "site_key": site_key,
                        "site_name": resolved_site_name,
                        "ring_code": ring_code,
                    "observed_at": observation["observed_at"],
                    "observed_date": observation["observed_date"],
                    "doy": observation["doy"],
                    "soil_respiration_rate": observation["soil_respiration_rate"],
                    "linear_flux": observation["linear_flux"],
                    "fit_status": observation["fit_status"],
                    "device_name": observation["device_name"],
                    "source_file_name": file_path.name,
                    "source_file_path": str(file_path),
                    "lon": lon,
                    "lat": lat,
                    "location_precision": location_precision,
                    "raw_metadata": raw_metadata,
                }
            )

    if missing_coordinates:
        preview = ", ".join(missing_coordinates[:10])
        suffix = "..." if len(missing_coordinates) > 10 else ""
        raise ValueError(f"Missing machine-readable coordinates for records: {preview}{suffix}")

    if not records:
        raise ValueError("No Heihe soil respiration records were parsed from the dataset directory")

    return records


def summarize_import_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observed_times = sorted(row["observed_at"] for row in rows)
    lons = [row["lon"] for row in rows]
    lats = [row["lat"] for row in rows]
    site_keys = sorted({row["site_key"] for row in rows})

    return {
        "dataset_id": HEIHE_DATASET_ID,
        "record_count": len(rows),
        "site_count": len(site_keys),
        "site_keys": site_keys,
        "time_range": {
            "start": observed_times[0].isoformat() if observed_times else None,
            "end": observed_times[-1].isoformat() if observed_times else None,
        },
        "bbox": [
            min(lons) if lons else None,
            min(lats) if lats else None,
            max(lons) if lons else None,
            max(lats) if lats else None,
        ],
    }


def format_time_range(start: datetime | None, end: datetime | None) -> str | None:
    if not start or not end:
        return None
    if start.date() == end.date():
        return start.strftime("%Y-%m-%d")
    return f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}"


def _assign_ring_code(ring_codes: list[str], observation_index: int) -> str | None:
    if not ring_codes:
        return None
    if len(ring_codes) == 1:
        return ring_codes[0]
    if observation_index < len(ring_codes):
        return ring_codes[observation_index]
    return None


def _extract_header_value(lines: list[str], key: str) -> str | None:
    prefix = f"{key}:"
    for line in lines:
        if line.startswith(prefix):
            parts = line.split("\t", 1)
            return parts[1].strip() if len(parts) > 1 else None
    return None


def _extract_obs_number(line: str) -> int | None:
    match = re.search(r"Obs#:\s*(\d+)", line)
    return int(match.group(1)) if match else None


def _parse_summary_pairs(lines: list[str]) -> dict[str, str]:
    summary: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        summary[key.strip()] = raw_value.strip()
    return summary


def _is_nan(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _to_float(value: Any) -> float | None:
    if _is_nan(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
