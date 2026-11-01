"""Synthetic hourly electricity load for a commercial office building.

This is an ILLUSTRATIVE profile, not measured consumption. Annual energy is
set as intensity (kWh/m2/yr) times floor area. The shape gives weekday daytime
peaks, lower weekends, and a night-time base load.
"""
import numpy as np
import pandas as pd
from pathlib import Path


def _hourly_shape(index):
    """Relative hourly shape (unnormalised) for an office, by hour and weekday."""
    hour = index.hour.values
    weekday = index.day_of_week.values < 5

    # Daytime occupancy curve, 09:00 to 18:00, peaking early afternoon.
    occupancy = np.exp(-0.5 * ((hour - 13.5) / 3.0) ** 2)
    occupancy[(hour < 8) | (hour > 19)] = 0.0
    return occupancy, weekday


def _expected_index(cfg):
    year = cfg["project"]["simulation_year"]
    return pd.date_range(f"{year}-01-01 00:00", periods=8760, freq="h",
                         tz=cfg["site"]["timezone"])


def load_hourly_csv(cfg):
    """Load a measured/utility-verified hourly CSV selected in the configuration.

    This deliberately validates rather than fills gaps: invented interpolation would
    undermine the purpose of replacing the illustrative profile.
    """
    c = cfg["load"]
    filename = c.get("hourly_csv_file")
    if not filename:
        raise ValueError("load.hourly_csv_file is required when source is hourly_csv")
    path = Path(filename)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    if not path.exists():
        raise FileNotFoundError(f"hourly load file not found: {path}")
    frame = pd.read_csv(path)
    ts_col, load_col = c.get("timestamp_column", "timestamp"), c.get("load_column", "load_kwh")
    missing = {ts_col, load_col} - set(frame.columns)
    if missing:
        raise ValueError(f"hourly load file missing required columns: {sorted(missing)}")
    ts = pd.to_datetime(frame[ts_col], errors="raise")
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize(cfg["site"]["timezone"], ambiguous="raise", nonexistent="raise")
    else:
        ts = ts.dt.tz_convert(cfg["site"]["timezone"])
    values = pd.to_numeric(frame[load_col], errors="raise")
    if values.isna().any() or (values < 0).any():
        raise ValueError("hourly load values must be present and non-negative")
    series = pd.Series(values.to_numpy(dtype=float), index=ts, name="load_kwh")
    if series.index.has_duplicates:
        raise ValueError("hourly load timestamps must not contain duplicates")
    expected = _expected_index(cfg)
    if not series.index.equals(expected):
        raise ValueError("hourly load timestamps must be exactly the simulation year's 8,760 local hours")
    return series


def build_load_profile(cfg):
    """Return an 8760-hour pandas Series of load in kWh per hour.

    The profile is deterministic for a given random_seed.
    """
    load_cfg = cfg["load"]
    if load_cfg.get("source") == "hourly_csv":
        return load_hourly_csv(cfg)
    if load_cfg.get("source") != "synthetic_office_profile":
        raise ValueError("load.source must be synthetic_office_profile or hourly_csv")
    year = cfg["project"]["simulation_year"]
    floor_area = cfg["building"]["floor_area_m2"]

    index = _expected_index(cfg)
    occupancy, weekday = _hourly_shape(index)

    base = load_cfg["base_load_fraction"]
    weekend_factor = 0.5
    shape = base + (1 - base) * occupancy
    shape = shape * np.where(weekday, 1.0, weekend_factor)

    rng = np.random.default_rng(load_cfg["random_seed"])
    noise = 1 + load_cfg["noise_std_fraction"] * rng.standard_normal(len(index))
    shape = np.clip(shape * noise, 0.01, None)

    annual_kwh = load_cfg["annual_intensity_kwh_per_m2"] * floor_area
    hourly_kwh = shape * (annual_kwh / shape.sum())
    return pd.Series(hourly_kwh, index=index, name="load_kwh")
