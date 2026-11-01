"""Validation of the joint PV and battery dispatch optimization."""
import numpy as np
import pyomo.environ as pyo
import pytest

from src.config import load_config
from src.optimize import build_model, solve_scenario
from src.tariff import baseline_bills
from src.load_profile import build_load_profile
from src.solar_resource import solar_geometry_and_pv


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def results(cfg):
    return {sc: solve_scenario(cfg, sc) for sc in ("grid_only", "pv_only", "pv_battery")}


def test_all_scenarios_optimal(results):
    for r in results.values():
        assert r["termination"] == "optimal"


def test_grid_only_matches_independent_tariff_bill(cfg, results):
    geo = solar_geometry_and_pv(cfg)
    bills = baseline_bills(cfg, build_load_profile(cfg), geo["pv_kwh"] * 0)
    assert results["grid_only"]["annual_grid_energy_cost_rs"] == pytest.approx(
        bills["grid_only_bill_rs"], rel=1e-6)
    assert results["grid_only"]["pv_kwp"] == 0 and results["grid_only"]["battery_kwh"] == 0


def test_energy_balance_closes_every_hour(results):
    for name, r in results.items():
        h = r["_hourly"]
        residual = h["g"] + h["u"] + h["d"] - h["load"] - h["c"]
        assert np.max(np.abs(residual)) < 1e-6, name


def test_pv_use_never_exceeds_available(results):
    for r in results.values():
        h = r["_hourly"]
        assert np.all(h["u"] <= h["pv_gen"] + 1e-6)
        assert np.all(h["u"] >= -1e-9)


def test_no_grid_export(results):
    for r in results.values():
        assert np.all(r["_hourly"]["g"] >= -1e-9)


def test_soc_within_bounds_and_cyclic(cfg, results):
    smin = cfg["costs"]["battery_min_soc_fraction"]
    smax = cfg["costs"]["battery_max_soc_fraction"]
    r = results["pv_battery"]
    E = r["battery_kwh"]
    soc = r["_hourly"]["soc"]
    tol = 1e-6
    assert np.all(soc >= smin * E - tol)
    assert np.all(soc <= smax * E + tol)
    assert soc[0] == pytest.approx(soc[-1], abs=1e-6)


def test_battery_power_limits(cfg, results):
    c_rate = cfg["costs"]["battery_c_rate"]
    for r in results.values():
        E = r["battery_kwh"]
        h = r["_hourly"]
        assert np.all(h["c"] <= c_rate * E + 1e-6)
        assert np.all(h["d"] <= c_rate * E + 1e-6)


def test_battery_zero_when_uneconomic(results):
    # Under the base assumptions the battery does not pay back. Keeping this as an
    # explicit check makes a change in the economics visible.
    assert results["pv_battery"]["battery_kwh"] == pytest.approx(0.0, abs=1e-3)


def test_pv_battery_never_costs_more_than_pv_only(results):
    assert results["pv_battery"]["annualized_total_cost_rs"] <= \
        results["pv_only"]["annualized_total_cost_rs"] + 1e-3


def test_forced_battery_is_not_better(cfg, results):
    """Optimality check: force a 100 kWh battery and confirm it costs at least as much."""
    m, _ = build_model(cfg, "pv_battery")
    m.E.fix(100.0)
    res = pyo.SolverFactory("highs").solve(m)
    assert str(res.solver.termination_condition) == "optimal"
    forced = pyo.value(m.total_cost)
    assert forced >= results["pv_battery"]["annualized_total_cost_rs"] - 1e-3


def test_no_simultaneous_charge_discharge_in_solution(results):
    """Charge and discharge should not both be positive in the same hour."""
    for name, r in results.items():
        h = r["_hourly"]
        overlap = np.minimum(h["c"], h["d"])
        assert overlap.max() < 1e-3, name
