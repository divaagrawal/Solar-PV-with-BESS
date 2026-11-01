"""Re-optimized sensitivity sweeps for scenarios A, B and C.

Every case re-solves all three scenarios from scratch (no fixed capacities are reused).
Solver failures are recorded with status FAILED: <reason> and are not dropped.

Usage (from project root):
  python scripts/run_sensitivity.py discount
  python scripts/run_sensitivity.py tariff
  python scripts/run_sensitivity.py battery_cost
  python scripts/run_sensitivity.py rte
  python scripts/run_sensitivity.py battery_life
  python scripts/run_sensitivity.py grid_2d
"""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.config import load_config  # noqa: E402
from src.financials import lifecycle  # noqa: E402
from src.optimize import solve_scenario  # noqa: E402

TABLES = ROOT / "results" / "tables"
SCEN = {"grid_only": "A: grid only", "pv_only": "B: PV only", "pv_battery": "C: PV + battery"}


def set_discount(cfg, v):
    cfg["costs"]["discount_rate"] = v


def set_tariff_scale(cfg, v):
    cfg["tariff"]["base_energy_rate_rs_per_kwh"] = cfg["tariff"]["base_energy_rate_rs_per_kwh"] * v


def set_battery_cost_scale(cfg, v):
    cfg["costs"]["battery_capex_per_kwh"] = cfg["costs"]["battery_capex_per_kwh"] * v
    cfg["costs"]["battery_power_capex_per_kw"] = cfg["costs"]["battery_power_capex_per_kw"] * v


def set_battery_energy_capex(cfg, v):
    cfg["costs"]["battery_capex_per_kwh"] = v


def set_rte(cfg, v):
    cfg["costs"]["battery_roundtrip_efficiency"] = v


def set_roof_limit(cfg, v):
    cfg["pv"]["max_capacity_kwp"] = v


def set_battery_life(cfg, v):
    cfg["costs"]["battery_life_years"] = v


def set_cycle_degradation(cfg, v):
    cfg["costs"]["cycle_degradation"]["enabled"] = bool(v)


def set_tariff_escalation(cfg, v):
    cfg["tariff"]["tariff_escalation"]["enabled"] = v > 0
    cfg["tariff"]["tariff_escalation"]["annual_fraction"] = v


def set_demand_and_fixed_charges(cfg, v):
    cfg["tariff"]["demand_charge"]["enabled"] = bool(v)
    cfg["tariff"]["fixed_charge"]["enabled"] = bool(v)


def run_case(base_cfg, label, mutate, value_label, family):
    """Run A, B and C under one mutated configuration. Returns a list of rows."""
    cfg = copy.deepcopy(base_cfg)
    mutate(cfg, value_label)
    rows = []
    solved = {}
    for sc in ("grid_only", "pv_only", "pv_battery"):
        try:
            solved[sc] = solve_scenario(cfg, sc)
        except Exception as exc:  # report failures, do not drop them
            solved[sc] = None
            rows.append({"family": family, "case": label, "value": value_label, "scenario": SCEN[sc],
                         "status": f"FAILED: {exc}"})
    grid_a = solved["grid_only"]["annual_grid_energy_cost_rs"] if solved["grid_only"] else None
    for sc in ("grid_only", "pv_only", "pv_battery"):
        r = solved[sc]
        if r is None or grid_a is None:
            continue
        f = lifecycle(cfg, r, grid_a)
        row = {
            "family": family, "case": label, "value": value_label, "scenario": SCEN[sc],
            "status": "optimal",
            "pv_kwp": round(r["pv_kwp"], 3),
            "battery_kwh": round(r["battery_kwh"], 2),
            "annualized_total_cost_rs": round(r["annualized_total_cost_rs"]),
            "annual_grid_cost_rs": round(r["annual_grid_energy_cost_rs"]),
            "capex_total_rs": round(f["capex_total_rs"]),
            "npv_vs_grid_only_rs": round(f["npv_rs"]),
            "simple_payback_years": None if f["simple_payback_years"] is None else round(f["simple_payback_years"], 2),
            "discounted_payback_years": None if f["discounted_payback_years"] is None else round(f["discounted_payback_years"], 2),
            "lifecycle_cost_pv_rs": round(f["lifecycle_cost_pv_rs"]),
        }
        rows.append(row)
    # battery-preferable test: C beats B on annualized cost
    if solved["pv_only"] is not None and solved["pv_battery"] is not None:
        adv = solved["pv_only"]["annualized_total_cost_rs"] - solved["pv_battery"]["annualized_total_cost_rs"]
        for row in rows:
            if row.get("scenario") == SCEN["pv_battery"] and row.get("status") == "optimal":
                row["battery_advantage_vs_pv_only_rs"] = round(adv)
    return rows


FAMILIES = {
    "discount": ("discount_rate", [0.06, 0.08, 0.10, 0.12, 0.14], set_discount),
    "tariff": ("tariff_scale", [0.7, 1.0, 1.3], set_tariff_scale),
    "battery_cost": ("battery_cost_scale", [0.5, 1.0, 1.5], set_battery_cost_scale),
    "rte": ("round_trip_efficiency", [0.80, 0.85, 0.90, 0.95], set_rte),
    "battery_life": ("battery_life_years", [10, 15], set_battery_life),
    "cycle_degradation": ("cycle_degradation_enabled", [False, True], set_cycle_degradation),
    "tariff_escalation": ("tariff_escalation_fraction", [0.0, 0.03, 0.05], set_tariff_escalation),
    "demand_fixed_charges": ("demand_and_fixed_charges_enabled", [False, True], set_demand_and_fixed_charges),
    "roof": ("rooftop_pv_limit_kwp", [25, 35, 50, 75, 100, 150], set_roof_limit),
}


def run_family(name):
    base = load_config()
    if name in FAMILIES:
        family_label, values, mutate = FAMILIES[name]
        rows = []
        for v in values:
            rows += run_case(base, family_label, mutate, v, name)
    elif name == "grid_2d":
        rows = []
        energy_capex = [3000, 5000, 7500, 10000, 12500, 15000, 20000]
        tariff_scales = [0.7, 0.85, 1.0, 1.15, 1.3]
        subset = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else tariff_scales
        for ts in subset:
            for ec in energy_capex:
                def mutate(cfg, _v, ts=ts, ec=ec):
                    set_tariff_scale(cfg, ts)
                    set_battery_energy_capex(cfg, ec)
                rows += run_case(base, "grid_2d", mutate, f"tariff={ts};batt_energy_capex={ec}", "grid_2d")
    else:
        raise SystemExit(f"unknown family {name}")
    df = pd.DataFrame(rows)
    suffix = "_" + sys.argv[2].replace(",", "_").replace(".", "p") if len(sys.argv) > 2 else ""
    out = TABLES / f"sens_{name}{suffix}.csv"
    df.to_csv(out, index=False)
    print(f"wrote {out} ({len(df)} rows)")
    failed = df[df.get("status", "").astype(str).str.startswith("FAILED")] if "status" in df else df.iloc[0:0]
    print(f"failed rows: {len(failed)}")
    return df


if __name__ == "__main__":
    TABLES.mkdir(parents=True, exist_ok=True)
    run_family(sys.argv[1])
