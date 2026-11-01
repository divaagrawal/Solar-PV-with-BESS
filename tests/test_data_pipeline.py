"""Tests for configuration consistency and the stage 2 data pipeline."""
import pytest

from src.config import load_config
from src.load_profile import build_load_profile
from src.solar_resource import pv_ac_output


@pytest.fixture(scope="module")
def cfg():
    return load_config()


def test_config_roof_and_capacity_consistent(cfg):
    b, pv = cfg["building"], cfg["pv"]
    assert b["usable_roof_area_m2"] == pytest.approx(350.0)
    assert pv["max_capacity_kwp"] == pytest.approx(35.0)


def test_load_has_8760_hours_and_matches_annual_target(cfg):
    load = build_load_profile(cfg)
    assert len(load) == 8760
    target = cfg["load"]["annual_intensity_kwh_per_m2"] * cfg["building"]["floor_area_m2"]
    assert load.sum() == pytest.approx(target, rel=1e-9)
    assert (load > 0).all()


def test_load_is_deterministic_for_fixed_seed(cfg):
    a = build_load_profile(cfg)
    b = build_load_profile(cfg)
    assert a.equals(b)


def test_pv_has_zero_output_at_night_and_is_nonnegative(cfg):
    pv = pv_ac_output(cfg)
    assert len(pv) == 8760
    assert (pv >= 0).all()
    night = pv[(pv.index.hour < 5) | (pv.index.hour > 19)]
    assert night.sum() == pytest.approx(0.0, abs=1e-6)


def test_pv_annual_yield_is_in_plausible_range(cfg):
    """Sanity band only: confirms the model is not off by an order of magnitude."""
    pv = pv_ac_output(cfg)
    yield_kwh_per_kwp = pv.sum() / cfg["pv"]["max_capacity_kwp"]
    assert 800 < yield_kwh_per_kwp < 2000


def test_pv_peak_does_not_exceed_dc_rating(cfg):
    pv = pv_ac_output(cfg)
    dc_limit = cfg["pv"]["max_capacity_kwp"] * (1 - cfg["pv"]["system_loss_fraction"]) * 1.1
    assert pv.max() <= dc_limit
