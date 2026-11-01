"""Generate figures. Every plotted value comes from a saved results table or a fresh model solve.

Run from the project root:  python scripts/make_figures.py
"""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import load_config  # noqa: E402
from src.financials import lifecycle  # noqa: E402
from src.optimize import solve_scenario  # noqa: E402

TABLES = ROOT / "results" / "tables"
FIGS = ROOT / "results" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 200, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
SCEN_LABEL = {"grid_only": "A: grid only", "pv_only": "B: PV only", "pv_battery": "C: PV + battery"}


def save(fig, name):
    path = FIGS / name
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print("wrote", path.name)


def base_results(cfg):
    A = solve_scenario(cfg, "grid_only")
    B = solve_scenario(cfg, "pv_only")
    C = solve_scenario(cfg, "pv_battery")
    fA = lifecycle(cfg, A, A["annual_grid_energy_cost_rs"])
    rows = []
    for name, r in [("grid_only", A), ("pv_only", B), ("pv_battery", C)]:
        f = lifecycle(cfg, r, A["annual_grid_energy_cost_rs"])
        rows.append({
            "scenario": SCEN_LABEL[name], "pv_kwp": r["pv_kwp"], "battery_kwh": r["battery_kwh"],
            "capital_om_annualized_rs": r["annualized_capital_om_rs"],
            "grid_cost_rs": r["annual_grid_energy_cost_rs"],
            "annualized_total_rs": r["annualized_total_cost_rs"],
            "npv_rs": f["npv_rs"],
            "simple_payback_y": f["simple_payback_years"],
            "discounted_payback_y": f["discounted_payback_years"],
        })
    return pd.DataFrame(rows), C


def fig_sizing_and_cost(df):
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    labels = df.scenario.tolist()
    x = np.arange(len(labels))
    ax.bar(x - 0.2, df.pv_kwp, 0.4, label="PV (kWp)", color="#e0a800")
    ax.bar(x + 0.2, df.battery_kwh, 0.4, label="Battery energy (kWh)", color="#2b7bba")
    for i, (p, b) in enumerate(zip(df.pv_kwp, df.battery_kwh)):
        ax.text(i - 0.2, p + 0.8, f"{p:.1f}", ha="center", fontsize=8)
        ax.text(i + 0.2, b + 0.8, f"{b:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Installed capacity")
    ax.set_title("Optimal sizing, base case (35 kWp roof limit, base costs)")
    ax.legend(frameon=False)
    save(fig, "fig01_optimal_sizing_base.png")


def fig_annualized_cost(df):
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    x = np.arange(len(df))
    cap = df.capital_om_annualized_rs / 1e5
    grid = df.grid_cost_rs / 1e5
    ax.bar(x, grid, label="Grid energy cost", color="#8c8c8c")
    ax.bar(x, cap, bottom=grid, label="Annualized capital + O&M", color="#2e8b57")
    for i, t in enumerate(df.annualized_total_rs / 1e5):
        ax.text(i, t + 0.05, f"₹{t:.2f} lakh", ha="center", fontsize=9)
    ax.set_xticks(x, df.scenario)
    ax.set_ylabel("₹ lakh per year")
    ax.set_title("Annualized system cost by scenario (base case)")
    ax.legend(frameon=False, loc="upper right")
    save(fig, "fig02_annualized_cost_base.png")


def fig_npv_payback(df):
    d = df.iloc[1:]  # scenario A has no investment, so NPV is zero and payback is not applicable
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 4.2))
    x = np.arange(len(d))
    bars = ax1.bar(x, d.npv_rs / 1e5, color="#2e8b57", width=0.5)
    for b, v in zip(bars, d.npv_rs / 1e5):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.3, f"₹{v:.1f} lakh", ha="center", fontsize=9)
    ax1.set_xticks(x, d.scenario, fontsize=9)
    ax1.set_ylabel("NPV vs grid-only (₹ lakh)")
    ax1.set_title("NPV (20 years, 10% discount rate)", fontsize=10)
    w = 0.35
    ax2.bar(x - w / 2, d.simple_payback_y, w, label="Simple payback", color="#c0392b")
    ax2.bar(x + w / 2, d.discounted_payback_y, w, label="Discounted payback", color="#8e44ad")
    for xi, sv, dv in zip(x, d.simple_payback_y, d.discounted_payback_y):
        ax2.text(xi - w / 2, sv + 0.08, f"{sv:.2f}", ha="center", fontsize=8)
        ax2.text(xi + w / 2, dv + 0.08, f"{dv:.2f}", ha="center", fontsize=8)
    ax2.set_xticks(x, d.scenario, fontsize=9)
    ax2.set_ylabel("Payback (years)")
    ax2.set_title("Payback (both achieved within 20 years)", fontsize=10)
    ax2.set_ylim(0, max(d.discounted_payback_y) * 1.3)
    ax2.legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle("Base case financial results (35 kWp roof, base costs). "
                 "The optimal battery is zero, so C equals B.", fontsize=9)
    save(fig, "fig03_npv_payback_base.png")


def dispatch_uncapped(cfg):
    """Solve the uncapped-roof PV + battery case at base costs and return hourly results."""
    u = copy.deepcopy(cfg)
    u["pv"]["max_capacity_kwp"] = 200.0
    r = solve_scenario(u, "pv_battery")
    h = r["_hourly"]
    df = pd.DataFrame({
        "load_kwh": h["load"], "pv_gen_kwh": h["pv_gen"], "pv_used_kwh": h["u"],
        "grid_import_kwh": h["g"], "battery_charge_kwh": h["c"],
        "battery_discharge_kwh": h["d"], "soc_kwh": h["soc"][:-1],
    }, index=r["_index"])
    df.index.name = "timestamp"
    df.to_csv(TABLES / "dispatch_uncapped_roof_base_costs.csv", float_format="%.4f")
    meta = {"pv_kwp": r["pv_kwp"], "battery_kwh": r["battery_kwh"]}
    return df, meta


def fig_dispatch(df, meta):
    fig, axes = plt.subplots(2, 1, figsize=(9, 6.5), sharex=False)
    windows = [("2025-06-16", "2025-06-22", "Summer week (monsoon, 16–22 June 2025)"),
               ("2025-01-13", "2025-01-19", "Winter week (13–19 January 2025)")]
    for ax, (a, b, title) in zip(axes, windows):
        w = df.loc[a:b + " 23:59"]
        t = np.arange(len(w))
        ax.plot(t, w.load_kwh, color="#333333", lw=1.2, label="Load")
        ax.plot(t, w.pv_gen_kwh, color="#e0a800", lw=1.2, label="PV generation")
        ax.plot(t, w.battery_discharge_kwh, color="#2b7bba", lw=1.2, label="Battery discharge")
        ax.plot(t, -w.battery_charge_kwh, color="#2b7bba", lw=1.0, ls=":", label="Battery charge (negative)")
        ax.plot(t, w.grid_import_kwh, color="#c0392b", lw=0.9, alpha=0.7, label="Grid import")
        ax2 = ax.twinx()
        ax2.fill_between(t, 0, w.soc_kwh, color="#2b7bba", alpha=0.12, label="State of charge")
        ax2.set_ylabel("SOC (kWh)")
        ax2.set_ylim(0, max(1.0, meta["battery_kwh"] * 1.1))
        ax2.spines["top"].set_visible(False)
        ax.set_xticks(np.arange(0, len(w), 24), [w.index[i].strftime("%d %b") for i in range(0, len(w), 24)])
        ax.set_ylabel("Energy per hour (kWh)")
        ax.set_title(title, fontsize=10)
    axes[0].legend(frameon=False, fontsize=7, ncol=3, loc="upper left")
    fig.suptitle(f"Hourly dispatch and state of charge: uncapped roof ({meta['pv_kwp']:.0f} kWp PV, "
                 f"{meta['battery_kwh']:.0f} kWh battery, base costs)", fontsize=10)
    save(fig, "fig04_dispatch_soc_uncapped_roof.png")


def sens_plot(path, xcol, xlabel, title, fname, scale=1.0):
    d = pd.read_csv(path)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))
    styles = {"A": ("#7f7f7f", "-", "o"), "B": ("#2b7bba", "--", "s"), "C": ("#2e8b57", "-", "^")}
    for sc, sub in d.groupby("scenario"):
        sub = sub.sort_values(xcol)
        col, ls, mk = styles[sc[0]]
        ax1.plot(sub[xcol] * scale, sub.npv_vs_grid_only_rs / 1e5, ls=ls, marker=mk, color=col, label=sc)
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel("NPV vs grid-only (₹ lakh)")
    ax1.set_title("NPV (B and C coincide where the optimal battery is zero)", fontsize=9)
    ax1.legend(frameon=False, fontsize=8)
    c = d[d.scenario.str.startswith("C")].sort_values(xcol)
    x = c[xcol] * scale
    w = (x.max() - x.min()) / 30 if len(x) > 1 else 0.05
    ax2.bar(x - w / 2, c.pv_kwp, w, color="#e0a800", label="PV (kWp)")
    ax2.bar(x + w / 2, c.battery_kwh, w, color="#2b7bba", label="Battery (kWh)")
    ax2.set_xlabel(xlabel)
    ax2.set_ylabel("Optimal capacity")
    pv_rng = f"{c.pv_kwp.min():.1f}–{c.pv_kwp.max():.1f} kWp"
    bt_rng = f"{c.battery_kwh.min():.1f}–{c.battery_kwh.max():.1f} kWh"
    ax2.set_title(f"Optimal sizes, scenario C: PV {pv_rng}; battery {bt_rng}", fontsize=9)
    ax2.legend(frameon=False, fontsize=8)
    fig.suptitle(title, fontsize=10)
    save(fig, fname)


def fig_discount_payback(path):
    d = pd.read_csv(path)
    b = d[d.scenario.str.startswith("B")].sort_values("value")
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(b.value * 100, b.discounted_payback_years, "o-", label="Discounted payback (years)", color="#8e44ad")
    ax.plot(b.value * 100, b.simple_payback_years, "s--", label="Simple payback (years)", color="#c0392b")
    ax.set_xlabel("Discount rate (%)")
    ax.set_ylabel("Payback (years)")
    ax2 = ax.twinx()
    ax2.plot(b.value * 100, b.npv_vs_grid_only_rs / 1e5, "^-", color="#2e8b57", label="NPV (₹ lakh)")
    ax2.set_ylabel("NPV vs grid-only (₹ lakh)")
    ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8, loc="center right")
    ax.set_title("Discount-rate sensitivity, PV only (re-optimized; PV at 35 kWp roof limit)", fontsize=10)
    save(fig, "fig05_discount_rate_sensitivity.png")


def fig_heatmap(path):
    d = pd.read_csv(path)
    c = d[d.scenario.str.startswith("C")].copy()
    c["tariff"] = c.value.str.extract(r"tariff=([\d.]+)")[0].astype(float)
    c["capex"] = c.value.str.extract(r"batt_energy_capex=(\d+)")[0].astype(int)
    kwh = c.pivot(index="tariff", columns="capex", values="battery_kwh")
    adv = c.pivot(index="tariff", columns="capex", values="battery_advantage_vs_pv_only_rs")
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(kwh.values, origin="lower", aspect="auto", cmap="Blues")
    ax.set_xticks(range(len(kwh.columns)), [f"{v:,}" for v in kwh.columns])
    ax.set_yticks(range(len(kwh.index)), [f"{v:.2f}x" for v in kwh.index])
    for i in range(kwh.shape[0]):
        for j in range(kwh.shape[1]):
            v = kwh.values[i, j]
            ax.text(j, i, f"{v:.0f}" if v >= 0.5 else "0", ha="center", va="center",
                    color="white" if v > 0.5 * np.nanmax(kwh.values) else "black", fontsize=8)
    from matplotlib.patches import Rectangle
    for i in range(kwh.shape[0]):
        for j in range(kwh.shape[1]):
            if adv.values[i, j] > 0:
                ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                       edgecolor="#c0392b", hatch="////", linewidth=0))
                ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                       edgecolor="#c0392b", linewidth=1.5))
    ax.set_xlabel("Battery energy capex (₹/kWh); power capex held at base ₹4,000/kW")
    ax.set_ylabel("Electricity tariff (relative to base)")
    ax.set_title("Battery economic viability: optimal battery energy (kWh) by tariff and battery cost\n"
                 "Hatched cells: battery preferable to solar-only (annualized advantage > 0). PV at 35 kWp roof limit.",
                 fontsize=9)
    fig.colorbar(im, ax=ax, label="Optimal battery energy (kWh)")
    save(fig, "fig08_battery_viability_heatmap.png")


def fig_battery_cost(path):
    d = pd.read_csv(path)
    c = d[d.scenario.str.startswith("C")].sort_values("value")
    b = d[d.scenario.str.startswith("B")].sort_values("value")
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(c.value * 100, c.battery_kwh, "o-", color="#2b7bba", label="Optimal battery (kWh)")
    ax.set_xlabel("Battery capital cost (% of base; energy and power capex scaled together)")
    ax.set_ylabel("Optimal battery energy (kWh)")
    ax2 = ax.twinx()
    ax2.plot(c.value * 100, c.battery_advantage_vs_pv_only_rs, "s--", color="#2e8b57", label="Advantage vs PV-only (₹/yr)")
    ax2.set_ylabel("Annualized advantage vs PV-only (₹/yr)")
    ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8)
    ax.set_title("Battery capital-cost sensitivity (scenario C re-optimized; roof 35 kWp)", fontsize=10)
    save(fig, "fig07_battery_cost_sensitivity.png")


def fig_roof(path):
    d = pd.read_csv(path)
    c = d[d.scenario.str.startswith("C")].sort_values("value")
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(c.value, c.battery_kwh, "s--", color="#2b7bba", label="Optimal battery (kWh)")
    ax.set_xlabel("Rooftop PV limit (kWp)  [= usable roof area / 10 m² per kWp]")
    ax.set_ylabel("Optimal battery energy (kWh)")
    ax2 = ax.twinx()
    ax2.plot(c.value, c.battery_advantage_vs_pv_only_rs, "o-", color="#2e8b57", label="Advantage vs PV-only (₹/yr)")
    ax2.set_ylabel("Annualized advantage vs PV-only (₹/yr)")
    ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8, loc="upper left")
    ax.set_title("Rooftop area sensitivity: battery viability depends on PV surplus (re-optimized)", fontsize=10)
    save(fig, "fig09_roof_area_sensitivity.png")


if __name__ == "__main__":
    cfg = load_config()
    base_df, _ = base_results(cfg)
    base_df.to_csv(TABLES / "base_financial_summary.csv", index=False)
    fig_sizing_and_cost(base_df)
    fig_annualized_cost(base_df)
    fig_npv_payback(base_df)
    dispatch_df, meta = dispatch_uncapped(cfg)
    fig_dispatch(dispatch_df, meta)
    fig_discount_payback(TABLES / "sens_discount.csv")
    sens_plot(TABLES / "sens_tariff.csv", "value", "Tariff scale (1.0 = base)",
              "Electricity tariff sensitivity (re-optimized)", "fig06_tariff_sensitivity.png")
    fig_battery_cost(TABLES / "sens_battery_cost.csv")
    fig_heatmap(TABLES / "sens_grid_2d.csv")
    fig_roof(TABLES / "sens_roof.csv")
