"""Monthly, load-versus-solar and energy-balance figures for the base PV-only case.

Every plotted value comes from a fresh model solve of scenario B (PV only, base costs).
Run from the project root:  python scripts/make_extra_figures.py
"""
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
from src.optimize import solve_scenario  # noqa: E402

FIGS = ROOT / "results" / "figures"
TABLES = ROOT / "results" / "tables"
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 200, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGS / name)
    plt.close(fig)
    print("wrote", name)


def build_dispatch():
    cfg = load_config()
    r = solve_scenario(cfg, "pv_only")
    h = r["_hourly"]
    df = pd.DataFrame({
        "load_kwh": h["load"], "pv_gen_kwh": h["pv_gen"], "pv_used_kwh": h["u"],
        "grid_import_kwh": h["g"],
    }, index=r["_index"])
    df["pv_curtailed_kwh"] = df.pv_gen_kwh - df.pv_used_kwh
    df.index.name = "timestamp"
    df.to_csv(TABLES / "dispatch_pv_only_base.csv", float_format="%.4f")
    return df, r["pv_kwp"]


def monthly(df):
    m = df.groupby(df.index.month).sum()
    return m / 1000.0  # MWh


def fig_monthly_pv(m):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(MONTHS, m.pv_gen_kwh, color="#e0a800", label="PV generation")
    ax.bar(MONTHS, m.pv_used_kwh, color="#2e8b57", alpha=0.85, width=0.45, label="PV used on site")
    for i, v in enumerate(m.pv_gen_kwh):
        ax.text(i, v + 0.08, f"{v:.2f}", ha="center", fontsize=7)
    ax.set_ylabel("Energy (MWh per month)")
    ax.set_title("Monthly PV generation and on-site use (35 kWp, base case, 2025 irradiance)")
    ax.legend(frameon=False, fontsize=8)
    save(fig, "fig10_monthly_pv_generation.png")


def fig_monthly_grid(m):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(12)
    ax.bar(x - 0.2, m.load_kwh, 0.4, color="#333333", label="Load")
    ax.bar(x + 0.2, m.grid_import_kwh, 0.4, color="#c0392b", label="Grid import with PV")
    ax.set_xticks(x, MONTHS)
    for i, v in enumerate(m.grid_import_kwh):
        ax.text(i + 0.2, v + 0.5, f"{v:.1f}", ha="center", fontsize=7)
    ax.set_ylabel("Energy (MWh per month)")
    ax.set_title("Monthly grid imports with and without PV (base case)")
    ax.legend(frameon=False, fontsize=8)
    save(fig, "fig11_monthly_grid_imports.png")


def typical_day(df, month):
    sub = df[df.index.month == month]
    prof = sub.groupby(sub.index.hour).mean()  # average over the month's days, kWh per hour
    return prof


def fig_load_vs_solar(df):
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8), sharey=True)
    for ax, (mo, name) in zip(axes, [(3, "March"), (6, "June (monsoon)"), (12, "December")]):
        p = typical_day(df, mo)
        ax.plot(p.index, p.load_kwh, color="#333333", label="Load")
        ax.plot(p.index, p.pv_gen_kwh, color="#e0a800", label="PV generation")
        ax.fill_between(p.index, 0, np.minimum(p.load_kwh, p.pv_gen_kwh), color="#2e8b57", alpha=0.25,
                        label="PV used on site")
        ax.set_title(f"Average day, {name}", fontsize=10)
        ax.set_xlabel("Hour of day (IST)")
        ax.set_xticks(range(0, 24, 3))
    axes[0].set_ylabel("Energy per hour (kWh, monthly average)")
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle("Load versus PV generation, average days (base case, 35 kWp)", fontsize=10)
    save(fig, "fig12_load_vs_solar_average_days.png")


def fig_energy_balance(df, month=3):
    p = typical_day(df, month)
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    hours = p.index
    ax.stackplot(hours, p.pv_used_kwh, p.grid_import_kwh,
                 labels=["Load met by PV", "Load met by grid"],
                 colors=["#2e8b57", "#c0392b"], alpha=0.85)
    ax.plot(hours, p.pv_gen_kwh, color="#e0a800", lw=2, label="PV generation")
    ax.plot(hours, p.load_kwh, color="#333333", lw=1.5, ls="--", label="Load")
    ax.set_xlabel("Hour of day (IST)")
    ax.set_ylabel("Energy per hour (kWh, monthly average)")
    ax.set_xticks(range(0, 24, 2))
    ax.set_title(f"Representative daily energy balance, {['','Jan','Feb','March','Apr','May','June','Jul','Aug','Sep','Oct','Nov','Dec'][month]} average day (base case)", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    save(fig, "fig13_daily_energy_balance.png")


def fig_utilization(df):
    gen = df.pv_gen_kwh.sum() / 1000
    used = df.pv_used_kwh.sum() / 1000
    curt = df.pv_curtailed_kwh.sum() / 1000
    load = df.load_kwh.sum() / 1000
    grid = df.grid_import_kwh.sum() / 1000
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 4.0))
    ax1.bar(["PV generated"], [gen], color="#e0a800", width=0.5)
    ax1.bar(["PV generated"], [used], color="#2e8b57", width=0.5, label=f"Used on site ({used:.2f} MWh)")
    ax1.bar(["PV generated"], [curt], bottom=[used], color="#bdbdbd", width=0.5, label=f"Curtailed ({curt:.2f} MWh)")
    ax1.set_ylabel("MWh per year")
    ax1.set_title("Solar energy utilization", fontsize=10)
    ax1.legend(frameon=False, fontsize=8, loc="upper right")
    served_pv = df.pv_used_kwh.sum() / 1000
    ax2.bar(["Annual load"], [load], color="#333333", width=0.5)
    ax2.bar(["Annual load"], [served_pv], color="#2e8b57", width=0.5, label=f"Met by PV ({served_pv:.2f} MWh)")
    ax2.bar(["Annual load"], [grid], bottom=[served_pv], color="#c0392b", width=0.5,
            label=f"Met by grid ({grid:.2f} MWh)")
    ax2.set_ylabel("MWh per year")
    ax2.set_title("Source of electricity for the load", fontsize=10)
    ax2.legend(frameon=False, fontsize=8, loc="upper right")
    fig.suptitle(f"Base case (35 kWp). Self-consumption {100*used/gen:.1f}% of generation", fontsize=10)
    save(fig, "fig14_solar_utilization_breakdown.png")


if __name__ == "__main__":
    df, kwp = build_dispatch()
    m = monthly(df)
    m.to_csv(TABLES / "monthly_pv_base.csv", float_format="%.4f")
    fig_monthly_pv(m)
    fig_monthly_grid(m)
    fig_load_vs_solar(df)
    fig_energy_balance(df, month=3)
    fig_utilization(df)
    print(f"PV size used: {kwp:.2f} kWp; annual PV {df.pv_gen_kwh.sum()/1000:.2f} MWh")
