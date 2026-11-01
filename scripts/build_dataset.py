"""Rebuild the processed hourly dataset with sun geometry and irradiance columns.

Run from the project root:  python scripts/build_dataset.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.config import load_config  # noqa: E402
from src.load_profile import build_load_profile  # noqa: E402
from src.solar_resource import load_resource, solar_geometry_and_pv  # noqa: E402


def build(out_path=ROOT / "data/processed/hourly_mumbai_office_nasa2025_geometry.csv"):
    cfg = load_config()
    geo = solar_geometry_and_pv(cfg)
    res = load_resource(cfg)
    load = build_load_profile(cfg)

    df = pd.DataFrame(index=geo.index)
    df.index.name = "timestamp"
    df["load_kwh"] = load.values
    df["ghi_wm2"] = res["GHI_WM2"].values
    df["t_ambient_c"] = res["T_AMB_C"].values
    for col in ["zenith_deg", "apparent_zenith_deg", "azimuth_deg", "aoi_deg",
                "dni_wm2", "dhi_wm2", "poa_wm2", "t_cell_c", "pv_kwh"]:
        df[col] = geo[col].values
    df.to_csv(out_path, float_format="%.4f")
    return df


if __name__ == "__main__":
    d = build()
    print(f"wrote {len(d)} rows, {len(d.columns)} columns")
