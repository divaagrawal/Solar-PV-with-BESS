# Techno-Economic Optimization of Rooftop Solar PV and Battery Storage for a Commercial Building in Mumbai

A Python model that sizes rooftop solar PV and battery storage for a hypothetical four-storey office in Mumbai. It minimizes the annualized cost of electricity supply using hourly dispatch over one year, compares three scenarios, and tests the results across the main inputs. It is an engineering model built for learning and portfolio use.

## Status: what this is and is not

- **Not externally validated.** Several key inputs are placeholders or secondary-source estimates. See `ASSUMPTIONS_AND_SOURCES.md` for each input's status.
- **The load is synthetic.** The building's electricity demand is a generated profile, not measured consumption. This is the largest source of uncertainty in the battery and self-consumption results.
- **Not ready for publication.** The results are model outputs under stated assumptions. They are not a bankable financial assessment and should not be used for investment decisions without the open items in the uncertainties section being resolved.

## Problem

A building owner can meet electricity demand from the grid, from rooftop PV, or from PV with a battery. Under Maharashtra's time-of-day (ToD) tariff, midday solar is cheaper than evening peak electricity, so a battery could shift energy into the peak window. The model asks: how large should PV and a battery be to minimize the annualized cost, and under what conditions does the battery pay?

## Methodology

**Optimization (scripts: `src/optimize.py`).** A linear program solved with HiGHS through Pyomo.

- Decisions: PV capacity `x` (kWp), battery energy `E` (kWh), and hourly grid import, PV use, battery charge, discharge, and state of charge over 8,760 hours.
- Objective: minimize capital and O&M annualized over 20 years, plus annual grid energy cost. Capital includes a battery replacement at year 10 and PV salvage at year 20.
- Constraints: hourly energy balance, PV availability, state of charge bounds with a cyclic condition, charge and discharge limits (0.5 C), no grid export, and a rooftop limit.
- Simultaneous charge and discharge is not blocked with binary variables. It is never beneficial because of round-trip losses, and the solutions are checked to contain none.

**Financial analysis (`src/financials.py`).** NPV, simple and discounted payback, and lifecycle cost are computed relative to grid-only. The lifecycle cost times the capital recovery factor reproduces the optimizer's annualized cost exactly, which is tested.

**Solar resource (`src/nasa_power.py`, `src/solar_resource.py`).** Hourly 2025 irradiance and temperature from NASA POWER for 19.07 N, 72.88 E. Sun position is evaluated at the midpoint of each hour, which is inferred from the data. Plane-of-array irradiance uses pvlib with the Erbs decomposition.

**Tariff (`src/tariff.py`).** Maharashtra LT non-residential above 50 kW. The default is a legacy energy-only comparator, retained to reproduce the saved base-case tables. A separate tariff-informed hypothetical bill case uses the later MERC FY 2026-27 schedule—₹14.89/kVAh energy, ₹1.52/kVAh wheeling, and ₹550/kVA/month demand—while keeping building-specific demand and power factor explicitly assumed.

## Scenarios

- **A: Grid only.** No PV, no battery.
- **B: PV only.** PV capacity optimized, no battery.
- **C: PV + battery.** PV and battery optimized jointly.

## Reproduce

The project was executed and tested on macOS with Python 3.9. The requirements are fixed and ASCII-only. A literal Windows run has not been performed; it is optional cross-platform verification, not a condition for using this illustrative template.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m pytest -q tests                 # 64 tests
python scripts/build_dataset.py           # hourly dataset with geometry columns
python scripts/run_scenarios.py           # scenario summary and dispatch
python scripts/run_sensitivity.py discount
python scripts/run_sensitivity.py tariff
python scripts/run_sensitivity.py battery_cost
python scripts/run_sensitivity.py rte
python scripts/run_sensitivity.py battery_life
python scripts/run_sensitivity.py cycle_degradation
python scripts/run_sensitivity.py tariff_escalation
python scripts/run_sensitivity.py demand_fixed_charges
python scripts/run_tariff_informed_hypothetical.py  # separate illustrative bill case
python scripts/run_sensitivity.py roof
python scripts/run_sensitivity.py grid_2d 0.7   # one tariff level at a time
python scripts/run_sensitivity.py grid_2d 0.85  # (run each level separately;
python scripts/run_sensitivity.py grid_2d 1.0   #  the full grid takes several minutes)
python scripts/run_sensitivity.py grid_2d 1.15
python scripts/run_sensitivity.py grid_2d 1.3
python scripts/merge_grid_2d.py           # merge the five tariff-level grid runs
python scripts/make_figures.py            # figures from saved tables and model solves
python scripts/make_extra_figures.py     # monthly, load-vs-solar, energy-balance and utilization figures
python scripts/make_dashboard.py         # interactive dashboard (results/dashboard.html)
python scripts/run_gsc_case.py           # grid support charge on/off comparison
```

Runtime: each scenario solve takes about 6–10 seconds on a laptop. The full sensitivity suite takes roughly 20–25 minutes.

Note: `results/tables/sens_grid_2d.csv` is written by `merge_grid_2d.py` from the five tariff-level runs. Payback cells for scenario A are blank, since there is no investment.

## Project structure

```
configs/base.yaml              all inputs, each tagged with its status
data/raw/                      NASA POWER hourly 2025 file (input, unchanged)
data/processed/                hourly dataset with geometry columns
src/config.py                  load and check the configuration
src/nasa_power.py              NASA POWER loader with validation
src/solar_resource.py          sun geometry, irradiance, PV output
src/load_profile.py            synthetic office load (placeholder)
src/tariff.py                  ToD tariff and baseline bills
src/finance.py                 capital recovery and replacement helpers
src/optimize.py                Pyomo model and scenario solver
src/financials.py              NPV, payback, lifecycle cost
scripts/                       reproduction scripts (run_scenarios, run_sensitivity, merge_grid_2d, make_figures, build_dataset)
tests/                         64 automated tests
results/tables/                scenario summary, sensitivity tables, dispatch
results/figures/               14 figures (fig01–fig14)
results/dashboard.html         interactive Plotly dashboard (self-contained)
reports/technical_report.md    technical report (13 sections)
LEARNING_GUIDE.md              concepts from first principles, with project examples
INTERVIEW_PREPARATION.md       60-second and 5-minute explanations, 20 Q&A, resume bullets
ASSUMPTIONS_AND_SOURCES.md     every input, its value, source, and status
```

## Results

### Verified findings (based on sourced inputs)

These depend only on the ToD tariff structure and on the NASA irradiance data. They don't depend on the battery cost or the synthetic load, but the energy values do depend on the load shape.

- **Tariff structure.** The peak window is 17:00–24:00 with a 25% surcharge. The solar-hour window is 09:00–17:00 with a rebate of 15% (April–September) or 25% (October–March). Source: MERC Order Case No. 75 of 2025, Table 7.
- **Grid support charge.** Rs 1.96/kWh for LT consumers, once Maharashtra's rooftop capacity reaches 5,000 MW. Source: MERC Table 8. Whether that threshold has been reached is unconfirmed, so the charge is off in the base case. With it on, NPV falls to Rs 17.8 lakh and simple payback extends to 4.1 years (`results/tables/gsc_on_case.csv`).
- **Solar resource.** Annual GHI at the site is 1,763 kWh/m² for 2025. Irradiance is much lower during the monsoon (June–September, about 107–132 kWh/m² per month) than in March–April (about 200 kWh/m² per month).

### Model results (illustrative assumptions)

These depend on the synthetic load and placeholder costs. The base tables use a legacy ₹12.16/kVAh energy-only comparator; they do not represent a complete bill. The separate tariff-informed hypothetical case applies the later official FY 2026-27 schedule but still has no measured demand or power-factor data.

**Base case, 35 kWp roof limit, base costs:**

| Scenario | PV (kWp) | Battery (kWh) | Annual grid cost (Rs lakh) | Annualized total (Rs lakh) | NPV vs grid-only (Rs lakh) | Simple payback (yr) | Discounted payback (yr) |
|---|---|---|---|---|---|---|---|
| A: Grid only | 0 | 0 | 25.41 | 25.41 | 0 | n/a | n/a |
| B: PV only | 35.0 | 0 | 20.33 | 22.32 | 26.3 | 3.25 | 4.12 |
| C: PV + battery | 35.0 | 0 | 20.33 | 22.32 | 26.3 | 3.25 | 4.12 |

- PV output is 51.1 MWh/yr. Self-consumption is 99.2%, and curtailment is 0.39 MWh/yr.
- **The optimal battery is zero in the base case.** At Rs 15,000/kWh it does not pay, because the 35 kWp roof leaves little midday PV surplus for a battery to store.

**Discount rate (PV only, re-optimized, 35 kWp):**

| Discount rate | NPV (Rs lakh) | Simple payback (yr) | Discounted payback (yr) |
|---|---|---|---|
| 6% | 41.3 | 3.25 | 3.72 |
| 8% | 32.9 | 3.25 | 3.91 |
| 10% | 26.3 | 3.25 | 4.12 |
| 12% | 21.0 | 3.25 | 4.37 |
| 14% | 16.8 | 3.25 | 4.64 |

The battery stays at zero at every discount rate.

**Electricity tariff (re-optimized, 35 kWp):**

| Tariff vs base | NPV (Rs lakh) | Simple payback (yr) | Discounted payback (yr) |
|---|---|---|---|
| -30% | 13.3 | 4.71 | 6.69 |
| base | 26.3 | 3.25 | 4.12 |
| +30% | 39.2 | 2.48 | 2.99 |

The battery stays at zero at every tariff level in this one-dimensional sweep. The two-dimensional sweep below shows it does appear at some combinations.

**New optional-model sensitivities (all illustrative; saved in `results/tables/`):** cycle-throughput wear, using the disabled-by-default 6,000-cycle placeholder, leaves the base 35 kWp solution at zero battery and NPV ₹26.3 lakh. With energy-tariff escalation switched on, PV-only NPV is ₹36.1 lakh at 3%/yr and ₹44.5 lakh at 5%/yr; the battery remains zero. With the verified ₹525/kVA/month demand rate enabled and the model's assumed PF of 1.0, PV-only NPV is ₹32.2 lakh and PV+battery is ₹33.6 lakh with a 14.1 kWh battery. This latter result is especially conditional on the synthetic load and assumed demand treatment.

**Battery capital cost (scenario C re-optimized, 35 kWp):**

| Battery cost vs base | Optimal battery (kWh) | Advantage over PV only (Rs/yr) |
|---|---|---|
| 50% | 5.0 | 367 |
| 100% | 0 | 0 |
| 150% | 0 | 0 |

Round-trip efficiency (80–95%) and battery life (10 or 15 years) do not make the battery worthwhile at base cost.

**Battery viability by tariff and battery energy cost (35 kWp roof).** Optimal battery size and whether the battery beats PV only:

| Tariff vs base | Rs 3,000/kWh | Rs 5,000/kWh | Rs 7,500/kWh | Rs 10,000/kWh and above |
|---|---|---|---|---|
| 0.70 | 15 kWh (preferred) | 0 | 0 | 0 |
| 0.85 | 99 kWh (preferred) | 7 kWh (preferred) | 0 | 0 |
| 1.00 | 193 kWh (preferred) | 17 kWh (preferred) | 0 | 0 |
| 1.15 | 196 kWh (preferred) | 98 kWh (preferred) | 7 kWh (preferred) | 0 |
| 1.30 | 197 kWh (preferred) | 179 kWh (preferred) | 13 kWh (preferred) | 1 kWh (preferred) |

At base tariff, the battery is preferable up to about Rs 5,000/kWh of energy capex and not at Rs 7,500/kWh. At +30% tariff, the threshold is roughly Rs 10,000–12,500/kWh. The Rs 3,000/kWh column is well below current indicative costs and is shown only to map the boundary.

**Rooftop area (scenario C re-optimized, base battery cost):**

| Roof limit (kWp) | Optimal PV (kWp) | Optimal battery (kWh) | Advantage over PV only (Rs/yr) |
|---|---|---|---|
| 25 | 25.0 | 0 | 0 |
| 35 | 35.0 | 0 | 0 |
| 50 | 50.0 | 0 | 0 |
| 75 | 75.0 | 10.0 | 1,958 |
| 100 | 100.0 | 70.7 | 20,120 |
| 150 | 105.2 | 85.1 | 21,150 |

With a battery, the economic PV optimum rises from 88 kWp (PV only) to 105 kWp. The battery absorbs midday surplus that would otherwise be curtailed, so it allows more PV, not just storage.

**Verification run with the roof limit lifted (200 kWp):** PV only optimum is 88.1 kWp, and PV + battery is 105.2 kWp with an 85 kWh battery. This matches the 150 kWp roof result, which confirms that economics, not the roof, limits PV at about 105 kWp under these assumptions.

### Conditions under which the battery beats solar-only

The battery pays when its energy cost is low enough to cover the spread between midday and evening ToD rates, and when there is enough midday PV surplus to store. At the 35 kWp roof, the battery is preferable only at low energy cost, about Rs 5,000/kWh or below at base tariff (not at Rs 7,500/kWh), and only if the tariff is higher. It becomes preferable at base costs once the roof is large enough to produce midday surplus, around 75 kWp.

### Uncertainties still to investigate

1. **Synthetic load.** The built-in profile is a reproducible hypothetical default, not measured consumption. The load shape drives self-consumption and the value of storage; replace it with measured data before making a building-specific decision.
2. **Bill completeness.** The legacy energy-only base uses ₹12.16/kVAh and is not a complete bill. A separate public-tariff case applies the later official ₹14.89/kVAh energy, ₹1.52/kVAh wheeling, and ₹550/kVA/month demand schedule, but actual kVA demand, PF, FAC, duty/tax and charge applicability have not been supplied.
3. **Battery cost.** The Rs 15,000/kWh energy cost depends on an unsourced system-cost factor. The power conversion (PCS) cost is a placeholder and is not isolated in the sensitivity tests.
4. **Battery cycle life and efficiency.** A disabled-by-default throughput-wear option has been added, but its 6,000-cycle input is a placeholder. Round-trip efficiency remains a placeholder.
5. **Tariff escalation.** Constant prices remain the base case; optional 3% and 5% escalation sensitivities are illustrative assumptions.
6. **Grid support charge and demand charges.** The grid support charge (off in the base case) would reduce PV savings by about Rs 1 lakh/yr if it applies. The verified demand rate is available as an option, but its treatment is limited by no measured kVA/PF data.
7. **Discount rate.** Whether the discount rate should be real or nominal has not been determined.
8. **Irradiance.** NASA POWER has not been validated against ground measurements for Mumbai, and only one year was used.
9. **Timing convention.** The NASA hour-labelling convention is inferred from the data, not documented.

## Limitations

- Single representative year; no interannual variability.
- No inverter sizing, no reactive power, no network constraints.
- No export; demand charges are optional and use an assumed PF of 1.0, so neither should be read as a utility-bill validation.
- The battery is modelled as a 0.5 C system with fixed efficiency and no temperature effects.
- The rooftop model uses a simple temperature and loss model, not a detailed module model.

## Acknowledgments and sources

See `ASSUMPTIONS_AND_SOURCES.md` for the full list of sources and their status. Main sources: MERC Order Case No. 75 of 2025; NREL Annual Technology Baseline 2023; NASA POWER; a Maharashtra rooftop benchmark rate reported by CSIS; and the open-source tools pvlib, Pyomo, and HiGHS.
