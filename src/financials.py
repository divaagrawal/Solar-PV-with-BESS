"""Lifecycle financial analysis for an optimized system.

All results are incremental to the grid-only scenario (A), so grid-only has NPV = 0.
Cash flows are real and constant, with tariffs not escalated. The same discount rate,
horizon, capital costs, replacement schedule and salvage rule are used as in the
optimizer, so the lifecycle cost times the capital recovery factor reproduces the
optimizer's annualized total cost. Tests check this.

Sign convention: costs are positive numbers in the lifecycle cost; cash flows are
negative for outflows and positive for inflows.
"""
import numpy as np

from src.tariff import annual_escalation_equivalent


def _asset_schedule(capex, life, horizon):
    """Return (install_times, salvage_fraction_at_horizon) for one asset.

    The asset is bought at t = 0 and replaced at each multiple of its life that is
    before the horizon. Remaining life at the horizon is credited, pro-rated.
    """
    if capex == 0:
        return [], 0.0
    installs = []
    k = 0
    while k * life < horizon:
        installs.append(k * life)
        k += 1
    last_end = installs[-1] + life
    remaining = max(0.0, (last_end - horizon) / life)
    return installs, remaining


def lifecycle(cfg, result, grid_only_cost_rs):
    """Return a dict with capex, replacements, salvage, PV costs, NPV, paybacks.

    result: output of optimize.solve_scenario (uses pv_kwp, battery_kwh, grid cost).
    grid_only_cost_rs: annual grid energy cost of scenario A (no PV, no battery).
    """
    c = cfg["costs"]
    pv_cfg = cfg["pv"]
    N = cfg["project"]["evaluation_years"]
    r = c["discount_rate"]
    c_rate = c["battery_c_rate"]

    x = float(result["pv_kwp"])
    E = float(result["battery_kwh"])
    capex_pv = x * c["pv_capex_per_kwp"]
    batt_total_per_kwh = c["battery_capex_per_kwh"] + c_rate * c["battery_power_capex_per_kw"]
    capex_batt = E * batt_total_per_kwh

    pv_installs, pv_rem = _asset_schedule(capex_pv, pv_cfg["lifetime_years"], N)
    b_installs, b_rem = _asset_schedule(capex_batt, c["battery_life_years"], N)

    # Replacement cash outflows (exclude the initial purchase at t = 0).
    years = np.arange(0, N + 1)
    cf = np.zeros(N + 1)
    cf[0] -= capex_pv + capex_batt
    for t in b_installs[1:]:
        cf[int(t)] -= capex_batt
    for t in pv_installs[1:]:
        cf[int(t)] -= capex_pv
    salvage = capex_pv * pv_rem + capex_batt * b_rem
    cf[N] += salvage

    annual_om = x * c["pv_om_per_kwp_year"] + c["battery_om_fraction_of_capex"] * batt_total_per_kwh * E
    grid_cost = float(result["annual_grid_energy_cost_rs"])
    degradation_cost = float(result.get("annual_cycle_degradation_cost_rs", 0.0))
    annual_savings = grid_only_cost_rs - grid_cost - annual_om - degradation_cost
    escalation = cfg["tariff"].get("tariff_escalation", {})
    growth = float(escalation.get("annual_fraction", 0.0)) if escalation.get("enabled", False) else 0.0
    # Grid-related bill components escalate from year 2.  Capital O&M and the
    # cycle-wear reserve remain in real terms; their treatment is explicit here.
    operating_flows = np.array([
        (grid_only_cost_rs - grid_cost) * (1 + growth) ** (year - 1) - annual_om - degradation_cost
        for year in range(1, N + 1)
    ])
    cf[1:] += operating_flows

    disc = 1.0 / (1 + r) ** years
    npv = float(np.sum(cf * disc))

    # Lifecycle cost (present value of all costs, grid energy and O&M included)
    af = (1 - (1 + r) ** -N) / r  # present value of a level annuity of 1 per year
    pv_repl = sum(capex_batt / (1 + r) ** t for t in b_installs[1:]) + \
        sum(capex_pv / (1 + r) ** t for t in pv_installs[1:])
    pv_salv = salvage / (1 + r) ** N
    grid_pv = grid_cost * af * annual_escalation_equivalent(cfg)
    lcc = capex_pv + capex_batt + pv_repl - pv_salv + (annual_om + degradation_cost) * af + grid_pv

    return {
        "pv_kwp": x,
        "battery_kwh": E,
        "capex_pv_rs": capex_pv,
        "capex_battery_rs": capex_batt,
        "capex_total_rs": capex_pv + capex_batt,
        "pv_replacement_pv_rs": sum(capex_pv / (1 + r) ** t for t in pv_installs[1:]),
        "battery_replacement_pv_rs": sum(capex_batt / (1 + r) ** t for t in b_installs[1:]),
        "salvage_value_rs": salvage,
        "salvage_pv_rs": pv_salv,
        "annual_om_rs": annual_om,
        "annual_grid_cost_rs": grid_cost,
        "annual_cycle_degradation_cost_rs": degradation_cost,
        "annual_grid_savings_rs": grid_only_cost_rs - grid_cost,
        "annual_net_savings_rs": annual_savings,
        "npv_rs": npv,
        "simple_payback_years": _payback(cf, undiscounted=True, horizon=N, capex=capex_pv + capex_batt),
        "discounted_payback_years": _payback(cf, undiscounted=False, horizon=N, capex=capex_pv + capex_batt, rate=r),
        "lifecycle_cost_pv_rs": lcc,
        "annualized_lifecycle_cost_rs": lcc * (r * (1 + r) ** N) / ((1 + r) ** N - 1) if r > 0 else lcc / N,
        "_cash_flows": cf,
    }


def _payback(cf, undiscounted, horizon, capex, rate=0.0):
    """Payback in years. The cumulative cash flow must become non-negative and stay there.

    Returns None if the investment has no payback within the horizon, or if there is no
    investment (not applicable).
    """
    if capex == 0:
        return None  # no investment, so payback is not applicable
    flows = cf.copy()
    if not undiscounted:
        flows = flows / (1 + rate) ** np.arange(len(cf))
    cum = np.cumsum(flows)
    if cum[-1] < 0:
        return None
    last_negative = np.where(cum < 0)[0]
    if len(last_negative) == 0:
        return 0.0
    t = int(last_negative[-1])
    if t >= horizon:
        return None
    # linear interpolation within the year after the last negative cumulative value
    return t + (-cum[t]) / (cum[t + 1] - cum[t])
