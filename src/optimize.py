"""Joint PV and battery sizing with hourly dispatch (LP, solved with HiGHS via Pyomo).

Scenarios
  grid_only    : no PV, no battery. The building buys all electricity.
  pv_only      : PV capacity optimized, no battery.
  pv_battery   : PV capacity and battery energy optimized jointly.

Decision variables
  x            PV capacity (kWp), 0 <= x <= rooftop limit
  E            battery energy capacity (kWh), E >= 0; power = c_rate x E (fixed ratio)
  g[t]         grid import in hour t (kWh); no export
  u[t]         PV energy used in hour t (kWh); curtailment = available - used
  c[t], d[t]   battery charge and discharge in hour t (kWh, AC side)
  soc[t]       battery state of charge at the start of hour t (kWh), t = 0..T

Objective: annualized system cost = PV and battery capital and O&M (annualized over the
evaluation horizon, including replacements and salvage) + annual grid energy cost
(+ optional grid support charge on PV generation).

Simultaneous charge and discharge is not forbidden with binaries. It is never needed:
with round-trip losses it wastes energy and cannot lower the cost. The solution is
checked after solving (see tests).
"""
import numpy as np
import pyomo.environ as pyo

from src.finance import annualized_capex, crf
from src.load_profile import build_load_profile
from src.solar_resource import solar_geometry_and_pv
from src.tariff import annual_escalation_equivalent, annual_network_charges, hourly_tariff

SCENARIOS = ("grid_only", "pv_only", "pv_battery")


def _inputs(cfg):
    """Hourly inputs for the optimizer, all on the same 8760-hour index."""
    geo = solar_geometry_and_pv(cfg)
    cap = cfg["pv"]["max_capacity_kwp"]
    prof_per_kwp = (geo["pv_kwh"] / cap).values  # kWh per kWp in each hour
    load = build_load_profile(cfg).values
    rate = hourly_tariff(cfg, geo.index).values
    return geo.index, prof_per_kwp, load, rate


def annualized_coefficients(cfg):
    """Return (A_pv_per_kwp, A_batt_per_kwh) annual Rs coefficients for the objective."""
    c = cfg["costs"]
    pv = cfg["pv"]
    N = cfg["project"]["evaluation_years"]
    r = c["discount_rate"]
    c_rate = c["battery_c_rate"]

    a_pv = annualized_capex(c["pv_capex_per_kwp"], pv["lifetime_years"], N, r) + c["pv_om_per_kwp_year"]
    # Battery energy and power are costed together per kWh of energy, with power = c_rate x E.
    batt_capex_per_kwh = c["battery_capex_per_kwh"] + c_rate * c["battery_power_capex_per_kw"]
    batt_om_per_kwh = c["battery_om_fraction_of_capex"] * batt_capex_per_kwh
    a_batt = annualized_capex(batt_capex_per_kwh, c["battery_life_years"], N, r) + batt_om_per_kwh
    return a_pv, a_batt


def cycle_degradation_cost_per_kwh(cfg):
    """Marginal reserve for cycle-induced battery wear, or zero when disabled.

    The reserve is proportional to AC discharge.  It does not claim to simulate
    electrochemical capacity fade; it makes the financial consequence of consuming
    a finite, configurable cycle-life budget visible in a linear optimisation.
    """
    deg = cfg["costs"].get("cycle_degradation", {})
    if not deg.get("enabled", False):
        return 0.0
    life = float(deg["cycle_life_at_usable_depth"])
    usable = cfg["costs"]["battery_max_soc_fraction"] - cfg["costs"]["battery_min_soc_fraction"]
    if life <= 0 or usable <= 0:
        raise ValueError("cycle-life and usable depth must be positive")
    c = cfg["costs"]
    capex_per_kwh = c["battery_capex_per_kwh"] + c["battery_c_rate"] * c["battery_power_capex_per_kw"]
    return capex_per_kwh / (life * usable)


def build_model(cfg, scenario):
    """Build the Pyomo model for one scenario. Returns (model, index)."""
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario}")

    index, prof, load, rate = _inputs(cfg)
    T = len(index)
    cap = cfg["pv"]["max_capacity_kwp"]
    c = cfg["costs"]
    eta = np.sqrt(c["battery_roundtrip_efficiency"])  # one-way efficiency
    smin, smax = c["battery_min_soc_fraction"], c["battery_max_soc_fraction"]
    c_rate = c["battery_c_rate"]
    gsc = cfg["tariff"]["grid_support_charge"]
    gsc_rate = gsc["rs_per_kwh"] if gsc["enabled"] else 0.0
    a_pv, a_batt = annualized_coefficients(cfg)
    demand_cfg = cfg["tariff"].get("demand_charge", {})
    fixed_cfg = cfg["tariff"].get("fixed_charge", {})
    pf = float(demand_cfg.get("assumed_power_factor", 1.0))
    if demand_cfg.get("enabled", False) and not 0 < pf <= 1:
        raise ValueError("demand_charge.assumed_power_factor must be in (0, 1]")

    m = pyo.ConcreteModel(name=scenario)
    m.T = pyo.RangeSet(0, T - 1)
    m.S = pyo.RangeSet(0, T)  # SOC has T+1 points for the cyclic condition

    m.x = pyo.Var(bounds=(0, cap))
    m.E = pyo.Var(bounds=(0, None))
    m.g = pyo.Var(m.T, bounds=(0, None))           # grid import only (no export)
    m.u = pyo.Var(m.T, bounds=(0, None))           # PV used
    m.c = pyo.Var(m.T, bounds=(0, None))           # battery charge
    m.d = pyo.Var(m.T, bounds=(0, None))           # battery discharge
    m.soc = pyo.Var(m.S, bounds=(0, None))
    m.M = pyo.RangeSet(1, 12)
    m.monthly_peak = pyo.Var(m.M, bounds=(0, None))

    if scenario == "grid_only":
        m.x.fix(0.0)
        m.E.fix(0.0)
    elif scenario == "pv_only":
        m.E.fix(0.0)

    m.pv_avail = pyo.Expression(m.T, rule=lambda m, t: float(prof[t]) * m.x)
    m.pv_limit = pyo.Constraint(m.T, rule=lambda m, t: m.u[t] <= m.pv_avail[t])
    m.balance = pyo.Constraint(
        m.T, rule=lambda m, t: m.g[t] + m.u[t] + m.d[t] == float(load[t]) + m.c[t])
    m.soc_dyn = pyo.Constraint(
        m.T, rule=lambda m, t: m.soc[t + 1] == m.soc[t] + eta * m.c[t] - m.d[t] / eta)
    m.soc_cyclic = pyo.Constraint(expr=m.soc[0] == m.soc[T])
    m.soc_min = pyo.Constraint(m.S, rule=lambda m, t: m.soc[t] >= smin * m.E)
    m.soc_max = pyo.Constraint(m.S, rule=lambda m, t: m.soc[t] <= smax * m.E)
    m.charge_power = pyo.Constraint(m.T, rule=lambda m, t: m.c[t] <= c_rate * m.E)
    m.discharge_power = pyo.Constraint(m.T, rule=lambda m, t: m.d[t] <= c_rate * m.E)
    month_of_t = index.month.to_numpy()
    m.monthly_peak_limit = pyo.Constraint(
        m.T, rule=lambda m, t: m.g[t] <= m.monthly_peak[int(month_of_t[t])] * pf)

    energy_cost = sum(float(rate[t]) * m.g[t] for t in range(T))
    gsc_cost = gsc_rate * sum(float(prof[t]) * m.x for t in range(T))
    demand_cost = (float(demand_cfg.get("rs_per_kva_month", 0.0)) * sum(m.monthly_peak[j] for j in m.M)
                   if demand_cfg.get("enabled", False) else 0.0)
    fixed_cost = (12.0 * float(fixed_cfg.get("rs_per_month", 0.0))
                  if fixed_cfg.get("enabled", False) else 0.0)
    degradation_cost = cycle_degradation_cost_per_kwh(cfg) * sum(m.d[t] for t in m.T)
    bill_equivalent = annual_escalation_equivalent(cfg) * (energy_cost + gsc_cost + demand_cost + fixed_cost)
    m.total_cost = pyo.Objective(
        expr=a_pv * m.x + a_batt * m.E + bill_equivalent + degradation_cost, sense=pyo.minimize)
    return m, index


def solve_scenario(cfg, scenario, solver="highs"):
    """Solve one scenario and return a results dictionary."""
    m, index = build_model(cfg, scenario)
    res = pyo.SolverFactory(solver).solve(m, load_solutions=True)
    status = str(res.solver.termination_condition)
    if status != "optimal":
        raise RuntimeError(f"{scenario}: solver ended with {status}")

    T = len(index)
    _, prof, load, rate = _inputs(cfg)
    x = pyo.value(m.x)
    E = pyo.value(m.E)
    g = np.array([pyo.value(m.g[t]) for t in range(T)])
    u = np.array([pyo.value(m.u[t]) for t in range(T)])
    c_ = np.array([pyo.value(m.c[t]) for t in range(T)])
    d = np.array([pyo.value(m.d[t]) for t in range(T)])
    soc = np.array([pyo.value(m.soc[t]) for t in range(T + 1)])
    pv_gen = prof * x
    gsc = cfg["tariff"]["grid_support_charge"]
    gsc_rate = gsc["rs_per_kwh"] if gsc["enabled"] else 0.0

    a_pv, a_batt = annualized_coefficients(cfg)
    demand_cost, fixed_cost = annual_network_charges(cfg, g, index)
    energy_cost = float(np.sum(g * rate))
    annual_grid_cost = energy_cost + gsc_rate * pv_gen.sum() + demand_cost + fixed_cost
    degradation_cost = cycle_degradation_cost_per_kwh(cfg) * float(d.sum())
    capital_om_annualized = a_pv * x + a_batt * E
    capex_pv = x * cfg["costs"]["pv_capex_per_kwp"]
    capex_batt = E * (cfg["costs"]["battery_capex_per_kwh"] + c_rate_val(cfg) * cfg["costs"]["battery_power_capex_per_kw"])

    return {
        "scenario": scenario,
        "termination": status,
        "pv_kwp": x,
        "battery_kwh": E,
        "battery_kw": c_rate_val(cfg) * E,
        "pv_capex_rs": capex_pv,
        "battery_capex_rs": capex_batt,
        "annualized_capital_om_rs": capital_om_annualized,
        "annual_grid_energy_cost_rs": annual_grid_cost,
        "annual_energy_cost_rs": energy_cost,
        "annual_demand_charge_rs": demand_cost,
        "annual_fixed_charge_rs": fixed_cost,
        "annual_cycle_degradation_cost_rs": degradation_cost,
        "annual_grid_energy_cost_rs": annual_grid_cost,
        "annualized_total_cost_rs": capital_om_annualized + annual_escalation_equivalent(cfg) * annual_grid_cost + degradation_cost,
        "grid_import_kwh": float(g.sum()),
        "pv_generation_kwh": float(pv_gen.sum()),
        "pv_used_kwh": float(u.sum()),
        "pv_curtailed_kwh": float(pv_gen.sum() - u.sum()),
        "battery_charge_kwh": float(c_.sum()),
        "battery_discharge_kwh": float(d.sum()),
        "_hourly": {"g": g, "u": u, "c": c_, "d": d, "soc": soc, "pv_gen": pv_gen, "load": load},
        "_index": index,
    }


def c_rate_val(cfg):
    return cfg["costs"]["battery_c_rate"]
