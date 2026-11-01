"""Interactive Plotly dashboard built only from saved results tables.

Output: results/dashboard.html (self-contained, works offline).
Run from the project root:  python scripts/make_dashboard.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
from plotly.subplots import make_subplots  # noqa: E402

TABLES = ROOT / "results" / "tables"
OUT = ROOT / "results" / "dashboard.html"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fig_monthly_day_explorer():
    d = pd.read_csv(TABLES / "dispatch_pv_only_base.csv", parse_dates=["timestamp"])
    d["month"] = d.timestamp.dt.month
    d["hour"] = d.timestamp.dt.hour
    fig = go.Figure()
    for i, mo in enumerate(range(1, 13)):
        p = d[d.month == mo].groupby("hour").mean(numeric_only=True)
        vis = i == 2  # default March
        fig.add_trace(go.Scatter(x=p.index, y=p.load_kwh, name="Load", mode="lines",
                                 line=dict(color="#333333"), visible=vis, legendgroup="l", showlegend=vis))
        fig.add_trace(go.Scatter(x=p.index, y=p.pv_gen_kwh, name="PV generation", mode="lines",
                                 line=dict(color="#e0a800"), visible=vis, legendgroup="p", showlegend=vis))
        fig.add_trace(go.Scatter(x=p.index, y=p.grid_import_kwh, name="Grid import", mode="lines",
                                 line=dict(color="#c0392b"), visible=vis, legendgroup="g", showlegend=vis))
    buttons = []
    for i, mo in enumerate(MONTHS):
        vis = [False] * 36
        for k in range(3):
            vis[i * 3 + k] = True
        buttons.append(dict(label=mo, method="update", args=[{"visible": vis},
                            {"title": f"Average hourly profile, {mo}: base case (35 kWp, no battery)"}]))
    fig.update_layout(
        title="Average hourly profile by month: base case (35 kWp, no battery)",
        xaxis_title="Hour of day (IST)", yaxis_title="Energy per hour (kWh, monthly average)",
        updatemenus=[dict(active=2, buttons=buttons, x=0, y=1.15, xanchor="left", direction="right")],
        height=460, template="simple_white",
    )
    return fig


def fig_monthly_pv():
    m = pd.read_csv(TABLES / "monthly_pv_base.csv")
    fig = go.Figure()
    fig.add_bar(x=MONTHS, y=m.pv_gen_kwh, name="PV generation (MWh)", marker_color="#e0a800")
    fig.add_bar(x=MONTHS, y=m.pv_used_kwh, name="PV used on site (MWh)", marker_color="#2e8b57")
    fig.add_bar(x=MONTHS, y=m.grid_import_kwh, name="Grid import (MWh)", marker_color="#c0392b")
    fig.update_layout(barmode="group", title="Monthly PV generation, on-site use, and grid import (base case)",
                      yaxis_title="MWh per month", height=380, template="simple_white")
    return fig


def fig_sensitivity_pair():
    fig = make_subplots(rows=1, cols=3, subplot_titles=(
        "Discount rate: NPV (PV only)", "Tariff: NPV (PV only)", "Battery cost: optimal battery (kWh)"))
    disc = pd.read_csv(TABLES / "sens_discount.csv")
    b = disc[disc.scenario.str.startswith("B")].sort_values("value")
    fig.add_scatter(x=b.value * 100, y=b.npv_vs_grid_only_rs / 1e5, mode="lines+markers",
                    name="Discount rate", row=1, col=1, showlegend=False)
    tar = pd.read_csv(TABLES / "sens_tariff.csv")
    t = tar[tar.scenario.str.startswith("B")].sort_values("value")
    fig.add_scatter(x=t.value * 100, y=t.npv_vs_grid_only_rs / 1e5, mode="lines+markers",
                    name="Tariff", row=1, col=2, showlegend=False)
    bc = pd.read_csv(TABLES / "sens_battery_cost.csv")
    c = bc[bc.scenario.str.startswith("C")].sort_values("value")
    fig.add_scatter(x=c.value * 100, y=c.battery_kwh, mode="lines+markers",
                    name="Battery", row=1, col=3, showlegend=False)
    fig.update_xaxes(title_text="Discount rate (%)", row=1, col=1)
    fig.update_xaxes(title_text="Tariff vs base (%)", row=1, col=2)
    fig.update_xaxes(title_text="Battery cost vs base (%)", row=1, col=3)
    fig.update_yaxes(title_text="NPV (Rs lakh)", row=1, col=1)
    fig.update_yaxes(title_text="NPV (Rs lakh)", row=1, col=2)
    fig.update_yaxes(title_text="kWh", row=1, col=3)
    fig.update_layout(height=380, template="simple_white", title="Sensitivity sweeps (all re-optimized)")
    return fig


def fig_heatmap():
    d = pd.read_csv(TABLES / "sens_grid_2d.csv")
    c = d[d.scenario.str.startswith("C")].copy()
    c["tariff"] = c.value.str.extract(r"tariff=([\d.]+)")[0].astype(float)
    c["capex"] = c.value.str.extract(r"batt_energy_capex=(\d+)")[0].astype(int)
    kwh = c.pivot(index="tariff", columns="capex", values="battery_kwh")
    adv = c.pivot(index="tariff", columns="capex", values="battery_advantage_vs_pv_only_rs")
    text = [[f"{v:.0f} kWh" + (" *" if a > 0 else "") for v, a in zip(rv, ra)]
            for rv, ra in zip(kwh.values, adv.values)]
    fig = go.Figure(go.Heatmap(z=kwh.values, x=[str(x) for x in kwh.columns],
                               y=[f"{v:.2f}x" for v in kwh.index], colorscale="Blues",
                               text=text, texttemplate="%{text}", colorbar=dict(title="kWh")))
    fig.update_layout(title="Battery economic viability: optimal battery energy by tariff and battery cost "
                            "(* = battery preferable to PV only)",
                      xaxis_title="Battery energy capex (Rs/kWh), power capex held at Rs 4,000/kW",
                      yaxis_title="Tariff vs base", height=460, template="simple_white")
    return fig


if __name__ == "__main__":
    parts = [fig_monthly_day_explorer(), fig_monthly_pv(), fig_sensitivity_pair(), fig_heatmap()]
    html = ["<html><head><meta charset='utf-8'><title>Solar PV + BESS dashboard</title></head><body>",
            "<h2>Techno-economic dashboard: rooftop PV and battery, Mumbai office (placeholder costs and synthetic load)</h2>",
            "<p>All values are read from results/tables produced by the model. Costs, tariffs and load are "
            "illustrative; see ASSUMPTIONS_AND_SOURCES.md before interpreting.</p>"]
    for i, f in enumerate(parts):
        html.append(f.to_html(full_html=False, include_plotlyjs=(i == 0)))
    html.append("</body></html>")
    OUT.write_text("\n".join(html), encoding="utf-8")
    print("wrote", OUT, f"({OUT.stat().st_size/1e6:.2f} MB)")
