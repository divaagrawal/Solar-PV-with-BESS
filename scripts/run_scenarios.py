"""Run the three scenarios, save result tables, and sweep battery cost.

Run from the project root:  python scripts/run_scenarios.py
"""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.config import load_config  # noqa: E402
from src.optimize import solve_scenario  # noqa: E402

TABLES = ROOT / "results" / "tables"
SCENARIO_LABELS = {
    "grid_only": "A: grid only",
    "pv_only": "B: PV only",
    "pv_battery": "C: PV + battery",
}


def summarize(cfg):
    rows = []
    for sc in ("grid_only", "pv_only", "pv_battery"):
        r = solve_scenario(cfg, sc)
        rows.append({
            "scenario": SCENARIO_LABELS[sc],
            "pv_kwp": round(r["pv_kwp"], 2),
            "battery_kwh": round(r["battery_kwh"], 1),
            "battery_kw": round(r["battery_kw"], 1),
            "pv_capex_rs": round(r["pv_capex_rs"]),
            "battery_capex_rs": round(r["battery_capex_rs"]),
            "annualized_capital_om_rs": round(r["annualized_capital_om_rs"]),
            "annual_grid_energy_cost_rs": round(r["annual_grid_energy_cost_rs"]),
            "annualized_total_cost_rs": round(r["annualized_total_cost_rs"]),
            "grid_import_mwh": round(r["grid_import_kwh"] / 1000, 2),
            "pv_generation_mwh": round(r["pv_generation_kwh"] / 1000, 2),
            "pv_self_consumed_pct": round(100 * r["pv_used_kwh"] / r["pv_generation_kwh"], 2) if r["pv_generation_kwh"] > 0 else None,
            "pv_curtailed_mwh": round(r["pv_curtailed_kwh"] / 1000, 3),
            "battery_throughput_mwh": round(r["battery_discharge_kwh"] / 1000, 2),
        })
        if sc == "pv_battery":
            h = r["_hourly"]
            dispatch = pd.DataFrame({
                "load_kwh": h["load"], "pv_gen_kwh": h["pv_gen"], "pv_used_kwh": h["u"],
                "grid_import_kwh": h["g"], "battery_charge_kwh": h["c"],
                "battery_discharge_kwh": h["d"], "soc_kwh": h["soc"][:-1],
            }, index=r["_index"])
            dispatch.index.name = "timestamp"
            dispatch.to_csv(TABLES / "dispatch_pv_battery.csv", float_format="%.4f")
    return pd.DataFrame(rows)


def battery_capex_sweep(cfg, capex_levels):
    """Find the battery energy capex at which a battery first becomes economic."""
    out = []
    for capex in capex_levels:
        c = copy.deepcopy(cfg)
        c["costs"]["battery_capex_per_kwh"] = capex
        r = solve_scenario(c, "pv_battery")
        out.append({
            "battery_capex_per_kwh_rs": capex,
            "optimal_battery_kwh": round(r["battery_kwh"], 1),
            "optimal_pv_kwp": round(r["pv_kwp"], 2),
            "annualized_total_cost_rs": round(r["annualized_total_cost_rs"]),
        })
    return pd.DataFrame(out)


if __name__ == "__main__":
    TABLES.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    summary = summarize(cfg)
    summary.to_csv(TABLES / "scenario_summary.csv", index=False)
    print(summary.T.to_string())

    sweep = battery_capex_sweep(cfg, [15000, 10000, 7500, 5000, 3000])
    sweep.to_csv(TABLES / "battery_capex_sweep.csv", index=False)
    print("\nBattery energy capex sweep (other inputs at base values):")
    print(sweep.to_string(index=False))
