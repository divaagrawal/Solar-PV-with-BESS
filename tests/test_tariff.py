"""Tests for ToD tariff logic and baseline bill calculations."""
import numpy as np
import pandas as pd
import pytest

from src.config import load_config
from src.load_profile import build_load_profile
from src.solar_resource import pv_ac_output
from src.tariff import baseline_bills, hourly_tariff


@pytest.fixture(scope="module")
def cfg():
    return load_config()


def _rate_at(cfg, ts):
    idx = pd.DatetimeIndex([pd.Timestamp(ts, tz=cfg["site"]["timezone"])])
    return float(hourly_tariff(cfg, idx).iloc[0])


def test_peak_surcharge_applies_17_to_24(cfg):
    base = cfg["tariff"]["base_energy_rate_rs_per_kwh"]
    assert _rate_at(cfg, "2026-01-15 17:00") == pytest.approx(base * 1.25)
    assert _rate_at(cfg, "2026-01-15 23:00") == pytest.approx(base * 1.25)


def test_solar_rebate_summer_and_winter(cfg):
    base = cfg["tariff"]["base_energy_rate_rs_per_kwh"]
    assert _rate_at(cfg, "2026-06-15 12:00") == pytest.approx(base * (1 - 0.15))
    assert _rate_at(cfg, "2026-01-15 12:00") == pytest.approx(base * (1 - 0.25))


def test_normal_hours_at_base_rate(cfg):
    base = cfg["tariff"]["base_energy_rate_rs_per_kwh"]
    assert _rate_at(cfg, "2026-06-15 03:00") == pytest.approx(base)
    assert _rate_at(cfg, "2026-06-15 08:00") == pytest.approx(base)


def test_grid_only_bill_equals_load_times_rate(cfg):
    load = build_load_profile(cfg)
    pv = pd.Series(0.0, index=load.index)
    res = baseline_bills(cfg, load, pv)
    manual = float(np.sum(load.values * hourly_tariff(cfg, load.index).values))
    assert res["grid_only_bill_rs"] == pytest.approx(manual)
    assert res["pv_only_bill_rs"] == pytest.approx(manual)
    assert res["annual_savings_rs"] == pytest.approx(0.0, abs=1e-6)


def test_energy_balance_closes_with_pv(cfg):
    load = build_load_profile(cfg)
    pv = pv_ac_output(cfg)
    res = baseline_bills(cfg, load, pv)
    assert res["pv_self_consumed_kwh"] + res["pv_curtailed_kwh"] == pytest.approx(res["pv_generation_kwh"], rel=1e-9)
    assert res["pv_self_consumed_kwh"] + res["pv_only_grid_kwh"] == pytest.approx(res["grid_only_kwh"], rel=1e-9)
    assert 0 <= res["self_consumption_fraction"] <= 1


def test_no_export_means_curtailment_never_negative(cfg):
    load = build_load_profile(cfg)
    pv = pv_ac_output(cfg)
    res = baseline_bills(cfg, load, pv)
    assert res["pv_curtailed_kwh"] >= 0


def test_gsc_off_by_default(cfg):
    assert cfg["tariff"]["grid_support_charge"]["enabled"] is False
    load = build_load_profile(cfg)
    pv = pv_ac_output(cfg)
    assert baseline_bills(cfg, load, pv)["gsc_cost_rs"] == 0.0
