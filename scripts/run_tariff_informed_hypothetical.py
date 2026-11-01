"""Run a tariff-informed, explicitly hypothetical Mumbai-office bill case.

Source: MERC Case No. 75 of 2025, 25 June 2025, Annexure II, PDF p. 53:
LT-II(C) >50 kW FY 2026-27: Rs 550/kVA/month demand, Rs 14.89/kVAh
energy and Rs 1.52/kVAh wheeling.  The office load, PF and contract demand
are assumptions, not a customer bill. FAC, duty/taxes and GSC are excluded.
"""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.config import load_config
from src.financials import lifecycle
from src.optimize import solve_scenario


def hypothetical_config():
    cfg = copy.deepcopy(load_config())
    t = cfg["tariff"]
    t["base_energy_rate_rs_per_kwh"] = 14.89
    t["wheeling_charge"] = {"enabled": True, "rs_per_kvah": 1.52}
    t["demand_charge"] = {
        "enabled": True,
        "rs_per_kva_month": 550.0,
        "assumed_power_factor": 0.95,
        "hypothetical_contract_demand_kva": 100.0,
    }
    t["fixed_charge"]["enabled"] = False
    t["grid_support_charge"]["enabled"] = False
    return cfg


if __name__ == "__main__":
    cfg = hypothetical_config()
    solved = {s: solve_scenario(cfg, s) for s in ("grid_only", "pv_only", "pv_battery")}
    grid_a = solved["grid_only"]["annual_grid_energy_cost_rs"]
    rows = []
    for s, r in solved.items():
        f = lifecycle(cfg, r, grid_a)
        rows.append({
            "scenario": s, "status": r["termination"],
            "pv_kwp": round(r["pv_kwp"], 3), "battery_kwh": round(r["battery_kwh"], 3),
            "annual_energy_and_wheeling_rs": round(r["annual_energy_cost_rs"]),
            "annual_demand_charge_rs": round(r["annual_demand_charge_rs"]),
            "annual_bill_before_fac_duty_tax_rs": round(r["annual_grid_energy_cost_rs"]),
            "npv_vs_grid_only_rs": round(f["npv_rs"]),
            "assumed_pf": 0.95, "hypothetical_contract_demand_kva": 100.0,
            "demand_billing_basis": "monthly maximum simulated hourly grid import / assumed PF; no contract-demand floor",
            "fac_duty_tax_included": False, "grid_support_charge_included": False,
        })
    out = ROOT / "results" / "tables" / "tariff_informed_hypothetical_bill.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    print("wrote", out)
