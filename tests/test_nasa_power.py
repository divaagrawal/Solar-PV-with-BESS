"""Tests for the NASA POWER loader using the uploaded 2025 Mumbai export."""
from pathlib import Path

import pytest

from src.nasa_power import read_nasa_power_hourly

FILE = Path(__file__).resolve().parent.parent / "data/raw/nasa_power_mumbai_2025_hourly.csv"


@pytest.fixture(scope="module")
def res():
    return read_nasa_power_hourly(FILE)


def test_loads_full_year_hourly(res):
    assert len(res) == 8760
    assert res.index.tz is not None
    assert str(res.index.tz) == "Asia/Kolkata"


def test_no_missing_values_or_sentinel(res):
    assert res.notna().all().all()
    assert (res != -999).all().all()


def test_ghi_nonnegative_and_zero_at_night(res):
    assert (res["GHI_WM2"] >= 0).all()
    night = res[(res.index.hour < 4) | (res.index.hour > 19)]
    assert night["GHI_WM2"].sum() == pytest.approx(0.0, abs=1e-6)


def test_annual_ghi_in_plausible_range(res):
    """Sanity band for Mumbai (about 1,700 to 2,000 kWh/m2/yr). Not a validation against truth."""
    annual = res["GHI_WM2"].sum() / 1000.0
    assert 1500 < annual < 2200


def test_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_nasa_power_hourly(tmp_path / "nope.csv")


def test_rejects_file_without_header_marker(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("YEAR,MO,DY,HR\n2025,1,1,0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="END HEADER"):
        read_nasa_power_hourly(bad)
