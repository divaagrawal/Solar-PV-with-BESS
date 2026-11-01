"""Merge the per-tariff grid_2d runs into results/tables/sens_grid_2d.csv.

Run after the five `run_sensitivity.py grid_2d <tariff>` commands.
Fails loudly if any part is missing, so a partial grid is never written silently.
"""
import sys
from pathlib import Path

import pandas as pd

TABLES = Path(__file__).resolve().parent.parent / "results" / "tables"
PARTS = ["0p7", "0p85", "1p0", "1p15", "1p3"]

if __name__ == "__main__":
    frames = []
    for p in PARTS:
        f = TABLES / f"sens_grid_2d_{p}.csv"
        if not f.exists():
            sys.exit(f"missing {f.name}: run the grid_2d case for this tariff first")
        frames.append(pd.read_csv(f))
    merged = pd.concat(frames, ignore_index=True)
    bad = (merged["status"] != "optimal").sum()
    merged.to_csv(TABLES / "sens_grid_2d.csv", index=False)
    print(f"wrote sens_grid_2d.csv: {len(merged)} rows, non-optimal rows: {bad}")
