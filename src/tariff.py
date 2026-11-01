"""Hourly ToD energy tariff and baseline (no-battery) bill calculations.

Tariff structure (see configs/base.yaml, tariff section):
  - 17:00-24:00 peak: base rate x (1 + peak surcharge)
  - 09:00-17:00 solar hours: base rate x (1 - solar rebate), rebate depends on month
  - all other hours: base rate
The energy-only MVP ignores demand and fixed charges.
"""
import numpy as np
import pandas as pd


def hourly_tariff(cfg, index):
    """Return a Series of energy rates (Rs/kWh) for each timestamp in index."""
    t = cfg["tariff"]
    base = t["base_energy_rate_rs_per_kwh"]
    hours = index.hour.values
    months = index.month.values

    peak_lo, peak_hi = t["tod"]["peak_hours"]
    solar_lo, solar_hi = t["tod"]["solar_hours"]
    surcharge = t["tod"]["peak_surcharge_fraction"]
    rebate_summer = t["tod"]["solar_rebate_fraction"]["apr_sep"]
    rebate_winter = t["tod"]["solar_rebate_fraction"]["oct_mar"]

    rate = np.full(len(index), base, dtype=float)
    is_peak = (hours >= peak_lo) & (hours < peak_hi)
    is_solar = (hours >= solar_lo) & (hours < solar_hi)
    summer = (months >= 4) & (months <= 9)
    rebate = np.where(summer, rebate_summer, rebate_winter)

    rate = np.where(is_peak, base * (1 + surcharge), rate)
    rate = np.where(is_solar & ~is_peak, base * (1 - rebate), rate)
    # The published LT schedule lists wheeling separately from energy charge.
    # It is applied uniformly here only when a scenario explicitly enables it.
    wheeling = t.get("wheeling_charge", {})
    if wheeling.get("enabled", False):
        rate = rate + float(wheeling["rs_per_kvah"])
    return pd.Series(rate, index=index, name="rate_rs_per_kwh")


def annual_escalation_equivalent(cfg):
    """Equivalent annual-cost multiplier for an escalating tariff cash-flow stream."""
    esc = cfg["tariff"].get("tariff_escalation", {})
    if not esc.get("enabled", False):
        return 1.0
    growth = float(esc.get("annual_fraction", 0.0))
    r, years = cfg["costs"]["discount_rate"], cfg["project"]["evaluation_years"]
    discount = np.arange(1, years + 1)
    pv_escalating = np.sum((1 + growth) ** (discount - 1) / (1 + r) ** discount)
    pv_level = np.sum(1 / (1 + r) ** discount)
    return float(pv_escalating / pv_level)


def annual_network_charges(cfg, grid_import, index):
    """Return annual demand and fixed charges for a grid-import series.

    Demand uses monthly maximum hourly import converted to kVA using the explicitly
    configured assumed power factor.  It is optional because this study has no
    measured demand or power-factor data.
    """
    t = cfg["tariff"]
    grid = pd.Series(np.asarray(grid_import, dtype=float), index=index)
    demand = t.get("demand_charge", {})
    fixed = t.get("fixed_charge", {})
    demand_rs = 0.0
    if demand.get("enabled", False):
        pf = float(demand.get("assumed_power_factor", 1.0))
        if not 0 < pf <= 1:
            raise ValueError("demand_charge.assumed_power_factor must be in (0, 1]")
        demand_rs = float(grid.groupby(grid.index.month).max().sum() / pf * demand["rs_per_kva_month"])
    fixed_rs = 12.0 * float(fixed.get("rs_per_month", 0.0)) if fixed.get("enabled", False) else 0.0
    return demand_rs, fixed_rs


def baseline_bills(cfg, load, pv):
    """Compare grid-only and PV-only (no battery, no export) annual energy bills.

    load and pv are hourly kWh series on the same index. PV is used first; surplus is
    curtailed, because export is not permitted. The grid supplies any remaining load.
    Returns a dict of annual results in Rs and kWh.
    """
    if not load.index.equals(pv.index):
        raise ValueError("load and pv must share the same index")

    rate = hourly_tariff(cfg, load.index)

    grid_only_kwh = load.values
    grid_only_bill = float(np.sum(grid_only_kwh * rate.values))

    self_used = np.minimum(load.values, pv.values)
    grid_import = load.values - self_used
    curtailed = pv.values - self_used
    pv_only_bill = float(np.sum(grid_import * rate.values))
    demand_a, fixed_a = annual_network_charges(cfg, grid_only_kwh, load.index)
    demand_b, fixed_b = annual_network_charges(cfg, grid_import, load.index)

    gsc = cfg["tariff"]["grid_support_charge"]
    gsc_cost = float(pv.sum() * gsc["rs_per_kwh"]) if gsc["enabled"] else 0.0

    return {
        "grid_only_bill_rs": grid_only_bill + demand_a + fixed_a,
        "grid_only_kwh": float(grid_only_kwh.sum()),
        "pv_only_bill_rs": pv_only_bill + demand_b + fixed_b + gsc_cost,
        "pv_only_grid_kwh": float(grid_import.sum()),
        "pv_generation_kwh": float(pv.sum()),
        "pv_self_consumed_kwh": float(self_used.sum()),
        "pv_curtailed_kwh": float(curtailed.sum()),
        "self_consumption_fraction": float(self_used.sum() / pv.sum()) if pv.sum() > 0 else 0.0,
        "gsc_cost_rs": gsc_cost,
        "annual_savings_rs": grid_only_bill + demand_a + fixed_a - (pv_only_bill + demand_b + fixed_b + gsc_cost),
    }
