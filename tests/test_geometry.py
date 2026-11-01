"""Physical checks on sun geometry and angle of incidence for Mumbai (19.07 N)."""
import pytest

from src.config import load_config
from src.solar_resource import solar_geometry_and_pv


@pytest.fixture(scope="module")
def geo():
    return solar_geometry_and_pv(load_config())


def _noon_row(geo, month):
    sub = geo[(geo.index.month == month) & (geo.index.hour == 12)]
    return sub.iloc[len(sub) // 2]


def test_zenith_range_and_night(geo):
    assert (geo["zenith_deg"] >= 0).all() and (geo["zenith_deg"] <= 180).all()
    night = geo[geo["ghi_wm2"] == 0] if "ghi_wm2" in geo else geo[geo["poa_wm2"] == 0]
    assert (night["apparent_zenith_deg"] > 85).mean() > 0.9


def _daily_min_zenith(geo, month):
    sub = geo[geo.index.month == month]
    return sub["apparent_zenith_deg"].groupby(sub.index.day).min().mean()


def test_june_minimum_zenith_near_overhead(geo):
    # June solstice: declination about +23.4 deg, so the minimum zenith at 19.07 N is about
    # 4.4 deg. Hourly sampling can miss the exact minimum, so the bound is loose.
    assert _daily_min_zenith(geo, 6) < 9


def test_december_minimum_zenith_matches_geometry(geo):
    # December solstice: declination about -23.4 deg, so the minimum zenith is about
    # 19.07 + 23.4 = 42.5 deg. Hourly sampling makes the daily minimum a little higher.
    z = _daily_min_zenith(geo, 12)
    assert 40 < z < 47


def test_aoi_in_valid_range(geo):
    assert (geo["aoi_deg"] >= 0).all() and (geo["aoi_deg"] <= 180).all()


def test_aoi_matches_zenith_minus_tilt_at_solar_noon(geo):
    # For a south-facing panel, AOI at solar noon is |zenith - tilt|. Take the daily minimum
    # zenith row as the solar-noon proxy and check the identity there.
    tilt = load_config()["pv"]["tilt_deg"]
    day = geo[geo.index.month == 12]
    row = day.loc[day["apparent_zenith_deg"].groupby(day.index.day).idxmin().iloc[15]]
    assert row["aoi_deg"] == pytest.approx(abs(row["apparent_zenith_deg"] - tilt), abs=1.5)


def test_pv_zero_when_sun_below_horizon(geo):
    night = geo[geo["apparent_zenith_deg"] > 90]
    assert (night["pv_kwh"] == 0).all()
