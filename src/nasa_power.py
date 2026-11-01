"""Load an hourly NASA POWER CSV export into a timezone-aware 8760-hour frame.

The export has a text header ending with the line '-END HEADER-', followed by
a normal CSV table with columns YEAR, MO, DY, HR and the requested parameters.
Timestamps are local standard time (LST); for Mumbai this is IST (UTC+05:30).
"""
from io import StringIO

import pandas as pd

HEADER_END = "-END HEADER-"
MISSING_VALUE = -999.0


def read_nasa_power_hourly(path, timezone="Asia/Kolkata"):
    """Return a DataFrame indexed by local time with columns GHI_WM2, T_AMB_C, WS10M_MS.

    Raises ValueError if the file is malformed, has missing values, or does not
    contain exactly one complete year of hourly rows.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()

    try:
        start = lines.index(HEADER_END) + 1
    except ValueError as exc:
        raise ValueError(f"{path}: no '{HEADER_END}' line found") from exc

    raw = pd.read_csv(StringIO("\n".join(lines[start:])))
    required = ["YEAR", "MO", "DY", "HR", "ALLSKY_SFC_SW_DWN", "T2M", "WS10M"]
    missing_cols = [c for c in required if c not in raw.columns]
    if missing_cols:
        raise ValueError(f"{path}: missing columns {missing_cols}")

    if (raw[required[4:]] == MISSING_VALUE).any().any():
        raise ValueError(f"{path}: contains -999 missing-value markers; choose another period")
    if raw[required].isna().any().any():
        raise ValueError(f"{path}: contains empty cells")

    stamp = pd.to_datetime(dict(year=raw.YEAR, month=raw.MO, day=raw.DY, hour=raw.HR))
    out = pd.DataFrame({
        "GHI_WM2": raw["ALLSKY_SFC_SW_DWN"].astype(float).values,
        "T_AMB_C": raw["T2M"].astype(float).values,
        "WS10M_MS": raw["WS10M"].astype(float).values,
    }, index=pd.DatetimeIndex(stamp))
    out.index = out.index.tz_localize(timezone)
    out.index.name = "timestamp"

    if out.index.duplicated().any():
        raise ValueError(f"{path}: duplicated timestamps")
    if len(out) != 8760 and len(out) != 8784:
        raise ValueError(f"{path}: expected 8760 or 8784 hourly rows, found {len(out)}")
    return out
