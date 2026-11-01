"""Hourly PV generation for a fixed-tilt rooftop array.

Resource source is set in configs/base.yaml under resource.source:
  nasa_power          measured-derived hourly GHI and air temperature from the
                      NASA POWER export in resource.nasa_power_file (preferred)
  clearsky_placeholder  pvlib clear-sky GHI scaled by PLACEHOLDER monthly
                      clearness factors (fallback only, not measured data)
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

from src.nasa_power import read_nasa_power_hourly

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _location(cfg):
    site = cfg["site"]
    return pvlib.location.Location(site["latitude"], site["longitude"],
                                   tz=site["timezone"], altitude=site["altitude_m"])


def _clearsky_resource(cfg):
    """Return GHI and ambient temperature from the clear-sky placeholder."""
    site = cfg["site"]
    year = cfg["project"]["simulation_year"]
    index = pd.date_range(f"{year}-01-01 00:00", periods=8760, freq="h", tz=site["timezone"])
    linke = pvlib.clearsky.lookup_linke_turbidity(index, site["latitude"], site["longitude"])
    ghi = _location(cfg).get_clearsky(index, model="ineichen", linke_turbidity=linke)["ghi"].clip(lower=0)
    factors = cfg["resource"]["monthly_clearness_factor"]
    ghi = ghi * ghi.index.month.map(lambda m: factors[m]).to_numpy()
    ambient_monthly = {1: 24, 2: 26, 3: 29, 4: 31, 5: 31, 6: 30,
                       7: 28, 8: 28, 9: 28, 10: 29, 11: 28, 12: 25}  # PLACEHOLDER deg C
    t_amb = pd.Series(index.month.map(ambient_monthly).to_numpy(), index=index, dtype=float)
    return pd.DataFrame({"GHI_WM2": ghi.values, "T_AMB_C": t_amb.values}, index=index)


def load_resource(cfg):
    """Return hourly GHI (W/m2) and ambient temperature (deg C) for the simulation year."""
    source = cfg["resource"]["source"]
    if source == "nasa_power":
        path = PROJECT_ROOT / cfg["resource"]["nasa_power_file"]
        res = read_nasa_power_hourly(path, timezone=cfg["site"]["timezone"])
        if res.index.year.unique().tolist() != [cfg["project"]["simulation_year"]]:
            raise ValueError("NASA POWER file year does not match project.simulation_year")
        return res[["GHI_WM2", "T_AMB_C"]]
    if source == "clearsky_placeholder":
        return _clearsky_resource(cfg)
    raise ValueError(f"Unknown resource.source: {source}")


def solar_geometry_and_pv(cfg):
    """Return an hourly DataFrame of sun geometry, irradiance and PV output.

    Columns:
      zenith_deg           geometric solar zenith (0 = overhead, 90 = horizon)
      apparent_zenith_deg  zenith corrected for atmospheric refraction; used in all
                           irradiance calculations
      azimuth_deg          solar azimuth (180 = south)
      aoi_deg              angle of incidence on the tilted panel; this, not zenith,
                           sets how much beam irradiance reaches the panel
      dni, dhi             beam and diffuse irradiance on horizontal (W/m2)
      poa_wm2              plane-of-array irradiance on the tilted panel (W/m2)
      t_cell_c             estimated cell temperature (deg C)
      pv_kwh               AC energy in the hour (kWh), equal to average kW
    """
    site, pv = cfg["site"], cfg["pv"]
    res = load_resource(cfg)
    index = res.index

    location = _location(cfg)
    # NASA POWER hourly values are averages over the hour that STARTS at the timestamp
    # (checked against sunrise: irradiance first appears one to two hours before the
    # sun is above the horizon at the label). The sun position is therefore evaluated
    # at the midpoint of that hour, 30 minutes after the label.
    midpoint = index + pd.Timedelta(minutes=30)
    solpos = location.get_solarposition(midpoint)
    solpos.index = index
    ghi = res["GHI_WM2"].clip(lower=0)
    zen = solpos["apparent_zenith"]
    decomp = pvlib.irradiance.erbs(ghi, zen, index.day_of_year)
    dni_s = pd.Series(np.asarray(decomp["dni"]), index=index)
    dhi_s = pd.Series(np.asarray(decomp["dhi"]), index=index)
    aoi = pvlib.irradiance.aoi(pv["tilt_deg"], pv["azimuth_deg"],
                               zen, solpos["azimuth"])
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=pv["tilt_deg"], surface_azimuth=pv["azimuth_deg"],
        solar_zenith=zen, solar_azimuth=solpos["azimuth"],
        dni=dni_s, ghi=ghi, dhi=dhi_s,
    )["poa_global"].clip(lower=0)
    # Hours whose midpoint sun is below the horizon get no POA irradiance. This drops
    # about 77 kWh/yr (0.15 % of output) from dawn hours where only a few minutes of
    # sunlight fall inside the averaging window. The approximation is conservative.
    poa = poa.where(zen < 90, 0.0)

    t_cell = res["T_AMB_C"] + 20.0 * poa / 800.0
    dc_kw = pv["max_capacity_kwp"] * (poa / 1000.0) * (1 + pv["temp_coeff_per_c"] * (t_cell - 25.0))
    ac_kwh = dc_kw.clip(lower=0) * (1 - pv["system_loss_fraction"])

    out = pd.DataFrame({
        "zenith_deg": solpos["zenith"],
        "apparent_zenith_deg": zen,
        "azimuth_deg": solpos["azimuth"],
        "aoi_deg": aoi,
        "dni_wm2": dni_s.clip(lower=0),
        "dhi_wm2": dhi_s.clip(lower=0),
        "poa_wm2": poa,
        "t_cell_c": t_cell,
        "pv_kwh": ac_kwh,
    }, index=index)
    return out


def pv_ac_output(cfg):
    """Return hourly PV AC output (kWh per hour). See solar_geometry_and_pv for detail."""
    out = solar_geometry_and_pv(cfg)["pv_kwh"]
    out.name = "pv_kwh"
    return out
