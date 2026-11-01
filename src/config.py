"""Load and validate the YAML configuration used by all model modules."""
from pathlib import Path

import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "base.yaml"


def load_config(path=DEFAULT_CONFIG):
    """Return the configuration dictionary after basic consistency checks.

    Raises ValueError if the rooftop capacity or the load settings are inconsistent.
    """
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    b, pv = cfg["building"], cfg["pv"]
    expected_usable = b["gross_roof_area_m2"] * b["usable_roof_fraction"]
    if abs(expected_usable - b["usable_roof_area_m2"]) > 1e-6:
        raise ValueError(
            f"usable_roof_area_m2 ({b['usable_roof_area_m2']}) does not match "
            f"gross x fraction ({expected_usable})."
        )
    expected_cap = b["usable_roof_area_m2"] / pv["area_per_kwp_m2"]
    if abs(expected_cap - pv["max_capacity_kwp"]) > 1e-6:
        raise ValueError(
            f"max_capacity_kwp ({pv['max_capacity_kwp']}) does not match "
            f"usable area / area_per_kwp ({expected_cap})."
        )
    if not 0 < cfg["load"]["base_load_fraction"] < 1:
        raise ValueError("base_load_fraction must be between 0 and 1.")
    return cfg
