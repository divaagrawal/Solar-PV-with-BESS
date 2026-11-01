"""Integrity checks for saved dispatch tables, figures, and the dashboard."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "results" / "tables"
FIGS = ROOT / "results" / "figures"


@pytest.fixture(scope="module")
def dispatch():
    return pd.read_csv(TABLES / "dispatch_pv_only_base.csv", parse_dates=["timestamp"])


def test_pv_only_energy_balance_every_hour(dispatch):
    residual = dispatch.pv_used_kwh + dispatch.grid_import_kwh - dispatch.load_kwh
    assert np.max(np.abs(residual)) < 1e-3


def test_pv_split_is_consistent_every_hour(dispatch):
    residual = dispatch.pv_used_kwh + dispatch.pv_curtailed_kwh - dispatch.pv_gen_kwh
    assert np.max(np.abs(residual)) < 1e-3
    assert (dispatch.pv_curtailed_kwh >= -1e-6).all()


def test_monthly_table_sums_to_annual_totals(dispatch):
    monthly = pd.read_csv(TABLES / "monthly_pv_base.csv")
    assert monthly.pv_gen_kwh.sum() == pytest.approx(dispatch.pv_gen_kwh.sum() / 1000, rel=1e-4)
    assert monthly.grid_import_kwh.sum() == pytest.approx(dispatch.grid_import_kwh.sum() / 1000, rel=1e-4)
    assert monthly.load_kwh.sum() == pytest.approx(dispatch.load_kwh.sum() / 1000, rel=1e-4)


def test_annual_pv_matches_scenario_summary(dispatch):
    summary = pd.read_csv(TABLES / "scenario_summary.csv")
    pv_row = summary[summary.scenario.str.startswith("B")].iloc[0]
    assert pv_row.pv_generation_mwh == pytest.approx(dispatch.pv_gen_kwh.sum() / 1000, abs=0.01)


EXPECTED_FIGS = [f"fig{i:02d}_" for i in range(1, 15)]


def test_all_fourteen_figures_exist_and_are_nonempty():
    names = sorted(p.name for p in FIGS.glob("fig*.png"))
    for prefix in EXPECTED_FIGS:
        matches = [n for n in names if n.startswith(prefix)]
        assert len(matches) == 1, f"missing or duplicate figure {prefix}"
        assert (FIGS / matches[0]).stat().st_size > 10_000, matches[0]


def test_dashboard_is_self_contained():
    html = (ROOT / "results" / "dashboard.html").read_text(encoding="utf-8")
    assert "<script src=" not in html
    # Plotly 6 embeds one internal reference to Plotly.newPlot in its bundled
    # JavaScript. Count rendered graph containers, not library implementation text.
    assert html.count("plotly-graph-div") == 4


def test_no_sensitivity_table_has_failed_rows():
    for f in TABLES.glob("sens_*.csv"):
        if "_0p" in f.name or "_1p" in f.name:
            continue  # per-tariff parts are merged into sens_grid_2d.csv
        d = pd.read_csv(f)
        assert (d["status"] == "optimal").all(), f.name
