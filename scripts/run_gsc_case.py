"""Model run with the grid support charge switched on (base inputs otherwise).

Writes results/tables/gsc_on_case.csv so the figure quoted in the report is traceable.
Run from the project root:  python scripts/run_gsc_case.py
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

if __name__ == "__main__":
    base = load_config()
    on = copy.deepcopy(base)
    on["tariff"]["grid_support_charge"]["enabled"] = True
    rows = []
    for label, cfg in [("GSC off (base)", base), ("GSC on", on)]:
        A = solve_scenario(cfg, "grid_only")
        B = solve_scenario(cfg, "pv_only")
        f = lifecycle(cfg, B, A["annual_grid_energy_cost_rs"])
        rows.append({
            "case": label,
            "pv_kwp": round(B["pv_kwp"], 2),
            "annual_grid_cost_rs": round(B["annual_grid_energy_cost_rs"]),
            "annual_net_savings_rs": round(f["annual_net_savings_rs"]),
            "npv_vs_grid_only_rs": round(f["npv_rs"]),
            "simple_payback_years": round(f["simple_payback_years"], 2),
            "discounted_payback_years": round(f["discounted_payback_years"], 2),
            "status": "optimal",
        })
    out = ROOT / "results" / "tables" / "gsc_on_case.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(pd.DataFrame(rows).to_string(index=False))
