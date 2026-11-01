"""Financial consistency and sensitivity-table integrity checks."""
import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import load_config
from src.financials import lifecycle
from src.optimize import solve_scenario

TABLES = Path(__file__).resolve().parent.parent / "results" / "tables"


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def solved(cfg):
    return {sc: solve_scenario(cfg, sc) for sc in ("grid_only", "pv_only", "pv_battery")}


@pytest.fixture(scope="module")
def fin(cfg, solved):
    grid_a = solved["grid_only"]["annual_grid_energy_cost_rs"]
    return {sc: lifecycle(cfg, r, grid_a) for sc, r in solved.items()}


def test_annualized_lcc_equals_optimizer_objective(cfg, solved, fin):
    """Lifecycle cost x CRF must reproduce the optimizer's annualized total cost exactly."""
    for sc in solved:
        assert fin[sc]["annualized_lifecycle_cost_rs"] == pytest.approx(
            solved[sc]["annualized_total_cost_rs"], rel=1e-6), sc


def test_npv_equals_lcc_difference_against_grid_only(fin):
    lcc_a = fin["grid_only"]["lifecycle_cost_pv_rs"]
    for sc in ("pv_only", "pv_battery"):
        assert fin[sc]["npv_rs"] == pytest.approx(lcc_a - fin[sc]["lifecycle_cost_pv_rs"], rel=1e-9)


def test_grid_only_has_zero_npv_and_no_capex(fin):
    assert fin["grid_only"]["npv_rs"] == pytest.approx(0.0, abs=1e-6)
    assert fin["grid_only"]["capex_total_rs"] == 0.0


def test_capital_counted_once_at_time_zero(cfg, fin):
    """Initial capex must appear exactly once, at t = 0, with no double counting."""
    f = fin["pv_only"]
    cf = f["_cash_flows"]
    assert cf[0] == pytest.approx(-f["capex_total_rs"], rel=1e-12)


def test_pv_salvage_matches_remaining_life(cfg, fin):
    """PV has a 25-year life and the horizon is 20 years, so 5/25 of its capex is salvaged."""
    f = fin["pv_only"]
    r = cfg["costs"]["discount_rate"]
    N = cfg["project"]["evaluation_years"]
    expected = f["capex_pv_rs"] * (25 - N) / 25
    assert f["salvage_value_rs"] == pytest.approx(expected, rel=1e-9)
    assert f["salvage_pv_rs"] == pytest.approx(expected / (1 + r) ** N, rel=1e-9)


def test_battery_replacement_is_discounted_at_year_10(cfg):
    """Battery replacement at year 10 is discounted by 1/(1+r)^10 relative to the initial buy."""
    c = copy.deepcopy(cfg)
    c["costs"]["battery_capex_per_kwh"] = 15000.0
    fake = {"pv_kwp": 0.0, "battery_kwh": 100.0, "annual_grid_energy_cost_rs": 1.0e6}
    f = lifecycle(c, fake, 1.0e6)
    r = c["costs"]["discount_rate"]
    capex_b = f["capex_battery_rs"]
    assert f["battery_replacement_pv_rs"] == pytest.approx(capex_b / (1 + r) ** 10, rel=1e-9)
    cf = f["_cash_flows"]
    # cash flow in year 10 = operating net flow (no grid saving here, only O&M) minus the replacement
    assert cf[10] - f["annual_net_savings_rs"] == pytest.approx(-capex_b, rel=1e-9)


def test_simple_payback_matches_definition(fin):
    f = fin["pv_only"]
    assert f["simple_payback_years"] == pytest.approx(
        f["capex_total_rs"] / (f["annual_net_savings_rs"]), rel=0.01)


def test_no_payback_is_reported_as_none(cfg, solved):
    """When capex is far above savings, payback must be reported as None (not achieved)."""
    c = copy.deepcopy(cfg)
    c["costs"]["pv_capex_per_kwp"] = 1.0e7
    grid_a = solved["grid_only"]["annual_grid_energy_cost_rs"]
    f = lifecycle(c, solved["pv_only"], grid_a)
    assert f["simple_payback_years"] is None
    assert f["discounted_payback_years"] is None


# ----- sensitivity table integrity -----

def _load(name):
    return pd.read_csv(TABLES / name)


@pytest.mark.parametrize("name", ["sens_discount.csv", "sens_tariff.csv", "sens_battery_cost.csv",
                                  "sens_rte.csv", "sens_battery_life.csv", "sens_roof.csv",
                                  "sens_grid_2d.csv"])
def test_sensitivity_tables_have_no_failed_solves(name):
    d = _load(name)
    assert (d["status"] == "optimal").all(), f"{name} contains non-optimal rows"


def test_sensitivity_has_three_scenarios_per_case():
    for name in ["sens_discount.csv", "sens_tariff.csv", "sens_battery_cost.csv"]:
        d = _load(name)
        counts = d.groupby(["value"]).scenario.nunique()
        assert (counts == 3).all(), name


def test_battery_cost_sweep_actually_reoptimizes():
    """Battery size must respond to battery cost: a cheap battery is built, a dear one is not."""
    d = _load("sens_battery_cost.csv")
    c = d[d.scenario.str.startswith("C")].set_index("value")
    assert c.loc[0.5, "battery_kwh"] > 1.0
    assert c.loc[1.0, "battery_kwh"] == pytest.approx(0.0, abs=1e-3)


def test_grid_2d_battery_size_responds_to_both_axes():
    d = _load("sens_grid_2d.csv")
    c = d[d.scenario.str.startswith("C")].copy()
    c["tariff"] = c.value.str.extract(r"tariff=([\d.]+)")[0].astype(float)
    c["capex"] = c.value.str.extract(r"batt_energy_capex=(\d+)")[0].astype(int)
    piv = c.pivot(index="tariff", columns="capex", values="battery_kwh")
    assert piv.values.max() > 100 and piv.values.min() == pytest.approx(0.0, abs=1e-3)
    # monotone: cheaper battery never reduces optimal size at a given tariff
    for t in piv.index:
        row = piv.loc[t].values
        assert np.all(np.diff(row) <= 1e-6), f"non-monotone at tariff {t}"


def test_roof_sweep_pv_binds_only_below_economic_optimum():
    """PV equals the roof limit when the roof binds, and stays below it when economics binds."""
    d = _load("sens_roof.csv")
    b = d[d.scenario.str.startswith("B")].sort_values("value")
    assert np.all(b.pv_kwp.values <= b.value.values + 1e-6)
    # small roofs bind: PV equals the limit
    small = b[b.value <= 50]
    assert np.allclose(small.pv_kwp.values, small.value.values, atol=1e-6)
    # large roofs do not bind: the optimum is below the limit and does not change with the limit
    large = b[b.value >= 100]
    assert (large.pv_kwp.values < large.value.values - 1e-6).all()
    assert np.allclose(large.pv_kwp.values, large.pv_kwp.values[0], atol=1e-3)


def test_discount_rate_changes_npv_and_payback():
    d = _load("sens_discount.csv")
    b = d[d.scenario.str.startswith("B")].sort_values("value")
    assert b.npv_vs_grid_only_rs.is_monotonic_decreasing
    assert b.discounted_payback_years.is_monotonic_increasing
