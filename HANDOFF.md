# Handoff: Solar PV + BESS Techno-Economic Model (Mumbai office)

Read this file first. It states what is finished, what is not, and what must not be claimed.

## 1. What the project is

A Python model that sizes rooftop PV and battery storage for a hypothetical 2,000 m² office in Mumbai (350 m² usable roof, 35 kWp limit). It runs hourly dispatch over one year (2025, NASA POWER irradiance) with a Pyomo linear program solved by HiGHS, compares three scenarios (A grid only, B PV only, C PV + battery), and produces NPV, payback, lifecycle cost, and sensitivity sweeps.

Status: model-based study with placeholder and secondary-source inputs. **Not externally validated. Not ready for publication.**

## 2. Completed work

- Data pipeline: NASA POWER loader with validation; sun geometry with midpoint convention; pvlib PV model; synthetic load; configuration with status tags (`configs/base.yaml`).
- ToD tariff module, verified structure from MERC Order Case No. 75 of 2025 (Tables 7 and 8).
- Optimization: scenarios A, B, C; 43,803 variables and 61,323 constraints; all solves optimal.
- Financial analysis: NPV, simple and discounted payback (reported as not achieved when applicable), lifecycle cost, battery replacement at year 10, PV salvage at year 20. Identity verified: lifecycle cost × CRF equals optimizer objective.
- Sensitivities, all re-optimized, all optimal, zero failures: discount rate (6–14%), tariff (±30%), battery cost (±50%), round-trip efficiency (80–95%), battery life (10 / 15 y), rooftop limit (25–150 kWp), 2-D battery energy cost (3,000–20,000 ₹/kWh) × tariff (×0.7–×1.3), grid support charge on/off, uncapped-roof verification.
- 14 figures (`results/figures/fig01`–`fig14`).
- Interactive dashboard, self-contained (`results/dashboard.html`).
- Technical report (13 sections, `reports/technical_report.md`).
- Learning guide, interview preparation (20 Q&A, 60-second and 5-minute explanations, resume bullets), README, ASSUMPTIONS_AND_SOURCES.md.
- 64 automated tests pass in the macOS development environment. Requirements are fixed and ASCII-only; no literal Windows run was performed and it is not a release blocker for this illustrative template.
- A separate tariff-informed hypothetical bill case uses the official FY 2026-27 LT-II(C) >50 kW schedule in MERC Case No. 75 of 2025, Annexure II p. 53: ₹14.89/kVAh energy, ₹1.52/kVAh wheeling and ₹550/kVA/month demand. The legacy ₹12.16 energy-only base remains only to reproduce the original saved comparator tables.
- Optional, off-by-default cycle-throughput wear reserve, tariff escalation, and demand/fixed-charge billing options added. Their unverified inputs remain labelled placeholders/assumptions.

## 3. Key results (illustrative inputs; see caveats)

| Item | Value |
|---|---|
| Base PV (35 kWp) annual output | 51.08 MWh; 99.2% self-consumed |
| Grid-only annual energy cost | ₹25.41 lakh |
| PV-only NPV vs grid-only (10%, 20 y) | ₹26.3 lakh |
| PV-only simple / discounted payback | 3.25 y / 4.12 y |
| Optimal battery, base costs | 0 kWh |
| Battery preferable (base tariff) | energy cost ≲ ₹5,000/kWh (not at ₹7,500) |
| With grid support charge on | NPV ₹17.8 lakh; payback 4.1 y / 5.5 y |

## 4. Deliverables (in `/mnt/user-data/outputs/solar_bess_project/`)

- `README.md`: overview, methodology, reproduction steps, results split into verified / illustrative / uncertain.
- `ASSUMPTIONS_AND_SOURCES.md`: every input with value, unit, source, and status.
- `reports/technical_report.md`, `reports/technical_report.pdf`: technical report and checked PDF.
- `LEARNING_GUIDE.md`, `INTERVIEW_PREPARATION.md`.
- `dashboard.html`: interactive dashboard.
- `figures/`: fig01–fig14 (PNG).
- `tables/`: scenario summary, sensitivity tables, 2-D grid, dispatch, monthly PV, hourly dataset, GSC case, verification table, and tariff-informed hypothetical bill case.
- `requirements.txt`, `HANDOFF.md`.
- `solar_bess_project.zip`: full code, tests, scripts, configs, and results (excludes the virtual environment).

## 5. Remaining work (not done)

### Inputs to replace for a building-specific study

1. **Replace the synthetic load** with measured or utility-verified hourly data for a Mumbai office if this is used for a particular site. The built-in profile is intentionally reproducible and hypothetical; battery and self-consumption results depend on it most.
2. **Replace the hypothetical bill inputs** with the customer's kVA demand/PF, FAC, duty/tax, and charge applicability if this is used for billing or investment analysis. The public-tariff case is complete only as an illustrative, configurable template.
3. **Confirm whether the grid support charge applies** (5,000 MW rooftop threshold). Currently off.
4. **Source the battery cost.** The ₹15,000/kWh energy cost depends on an unsourced system-cost factor applied to a BNEF pack-price anchor that was read through a vendor blog. Open the primary BNEF source and a dated Indian BESS cost source.
5. **Source PCS (power conversion) cost** (currently ₹4,000/kW, placeholder). Not isolated in sensitivities.
6. **Source battery round-trip efficiency**, PV O&M (₹500/kWp/yr placeholder), PV system losses (14%), temperature coefficient, tilt, and PV life (25 y).
7. **Battery cycle life and degradation.** An optional, off-by-default throughput-wear reserve is modelled using a 6,000-cycle placeholder. Replace that placeholder before treating it as a degradation forecast.
8. **Discount rate.** Choose base value and decide real vs nominal. Currently 10%, assumption; regulatory references 8.8–11.76% (secondary).
9. **Validate irradiance** against ground data for Mumbai, and test more than one year. The NASA hour-labelling convention was inferred from the data and should be confirmed.

### Improvements for a higher-confidence study

10. **Demand and fixed charges** are optional and off by default. The separate public-tariff case applies the verified demand rate; replace its hypothetical PF and billing basis before client-specific use.
11. **Tariff escalation** is zero in the base case; 3% and 5% illustrative sensitivities are available.
12. **Open primary sources** still cited only as summaries: CSIS Maharashtra benchmark notification, NREL ATB 2023 battery page, KERC discussion paper, and BNEF. MERC Case 75 Tables 7–8 and Annexure II p. 53 have been opened.
13. **Review the learning guide, interview preparation, and technical report** line by line with the project owner. They were written by the assistant and must be checked against the code before being presented as the owner's work.
14. **Technical report format.** Markdown and a checked PDF are provided. A DOCX can be generated later if editable Word format is required.
15. **Dashboard browser check.** Completed in Brave: all four panels render and the month selector is visible.

### Platform checks

16. **Windows and VS Code.** Not independently tested. This is optional cross-platform verification, not a release blocker for the illustrative template.
17. **Clean run of the full sensitivity suite.** Each `run_sensitivity.py` family was run once; the full 2-D grid takes several minutes and was run per tariff level. Re-run end to end on the target machine.
18. **GitHub publishing.** Not done. Requires owner approval before any push.

## 6. Known issues and corrections (for transparency)

- **Per-tariff 2-D files** (`sens_grid_2d_0p7.csv` etc.) still show payback 0.0 for scenario A. The merged `sens_grid_2d.csv` and all other sensitivity tables have it blank (not applicable). Use the merged file.
- **Payback for scenario A** is "not applicable", not zero. Check any new table code respects this.
- **Figure 4 (dispatch and SOC)** uses the uncapped-roof case (105 kWp PV, 85 kWh battery at base costs), not the base case, because the base battery is zero. It is labelled as such.
- **Battery cost history.** An earlier draft attributed a $70–75/kWh pack price to Crisil. That was unverified and has been removed. Check no copy of it remains in older files outside this project.
- **Grid support charge payback.** An earlier estimate of 3.9 years was wrong; the model run gives 4.1 years (simple) and 5.5 years (discounted). Documents are corrected.
- **Earlier tariff peak window** (9:00–21:00) was wrong and was corrected to 17:00–24:00 per MERC Table 7.
- **Stray files.** Earlier-stage CSVs may still sit loose in `/mnt/user-data/outputs/` (for example `scenario_summary.csv`, `battery_capex_sweep.csv`, `hourly_mumbai_office_nasa2025_geometry.csv`). The authoritative copies are in `solar_bess_project/`.
- **Runtime figures in the README** are estimates. The full sensitivity suite may take 20–25 minutes.
- **Sun position convention**: evaluated at the hour midpoint; dawn irradiance below the horizon set to zero (removes 0.15% of output). Documented in the report and code; confirm with NASA's documentation if available.

## 7. How to reproduce

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q tests          # expect 64 passed
python scripts/build_dataset.py
python scripts/run_scenarios.py
python scripts/run_sensitivity.py discount
python scripts/run_sensitivity.py tariff
python scripts/run_sensitivity.py battery_cost
python scripts/run_sensitivity.py rte
python scripts/run_sensitivity.py battery_life
python scripts/run_sensitivity.py cycle_degradation
python scripts/run_sensitivity.py tariff_escalation
python scripts/run_sensitivity.py demand_fixed_charges
python scripts/run_tariff_informed_hypothetical.py
python scripts/run_sensitivity.py roof
python scripts/run_sensitivity.py grid_2d 0.7    # repeat for 0.85, 1.0, 1.15, 1.3
python scripts/merge_grid_2d.py
python scripts/run_gsc_case.py
python scripts/make_figures.py
python scripts/make_extra_figures.py
python scripts/make_dashboard.py
```

Input data: `data/raw/nasa_power_mumbai_2025_hourly.csv` (NASA POWER export, unchanged).

## 8. Rules for whoever continues

- Do not present results as validated. Keep the three-way split: verified findings, illustrative model results, uncertainties.
- Every new number in a document must come from a saved output in `results/tables/`.
- Do not silently drop failed solves. Record the status.
- Keep placeholder inputs tagged as placeholders in `configs/base.yaml` and `ASSUMPTIONS_AND_SOURCES.md`.
- Re-run the tests after any change to the model or inputs. Re-run affected sensitivities and figures after changing the load or the tariff.
