from pathlib import Path

import pytest

from app.services.heihe_dataset import (
    build_import_rows,
    extract_ring_codes,
    get_dataset_directory,
    load_gps_ring_metadata,
    load_sheet1_file_metadata,
    parse_81x_observations,
)


DATASET_DIR = get_dataset_directory()


pytestmark = pytest.mark.skipif(not DATASET_DIR.exists(), reason="Heihe dataset is not available on this machine")


def test_parse_single_81x_contains_multiple_observations():
    sample = DATASET_DIR / "7.20下游胡杨样地-土壤环1.81x"
    observations = parse_81x_observations(sample)

    assert len(observations) > 1
    assert observations[0]["observed_at"].year == 2014
    assert observations[0]["soil_respiration_rate"] is not None
    assert observations[0]["linear_flux"] is not None


def test_sheet1_metadata_maps_file_to_site_context():
    metadata = load_sheet1_file_metadata(DATASET_DIR / "野外土壤呼吸实验表.xls")
    sample = metadata["7.20下游胡杨样地-土壤环1"]

    assert sample.site_key == "胡杨"
    assert sample.site_name == "胡杨样方"
    assert sample.lon == pytest.approx(101.12319)
    assert sample.lat == pytest.approx(41.9919)


def test_gps_sheet_provides_ring_level_coordinates():
    gps = load_gps_ring_metadata(DATASET_DIR / "野外土壤呼吸实验表.xls")
    ring = gps[("胡杨", "1")]

    assert ring["lon"] == pytest.approx(101.12274)
    assert ring["lat"] == pytest.approx(41.99267)


def test_grouped_ring_filename_is_exploded():
    assert extract_ring_codes("7.23下游农田样地-土壤环（1，2，3，4）") == ["1", "2", "3", "4"]


def test_import_rows_include_ring_or_site_precision():
    rows = build_import_rows(DATASET_DIR)
    precisions = {row["location_precision"] for row in rows}

    assert rows
    assert "ring" in precisions
    assert precisions.issubset({"ring", "site"})
