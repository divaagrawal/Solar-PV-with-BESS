# Assumptions and Sources

This file lists every important model input, its value and unit, where it came from, and how far it has been verified. It is the reference for the external-use caveats in the README.

**Status key**

- **VERIFIED**: read from a primary document in this project.
- **SOURCED (secondary)**: taken from a secondary source (news article, summary page, vendor blog). The primary document was not opened or could not be checked.
- **DERIVED**: calculated from sourced inputs with a stated assumption.
- **ASSUMPTION**: a modelling choice with no external source. Sensitivity-tested where marked.
- **PLACEHOLDER**: a stand-in value with no source. Treat as unknown.

Sensitivity tests are in `results/tables/sens_*.csv`.

## 1. Site and solar resource

| Input | Value | Unit | Source | Status | Sensitivity |
|---|---|---|---|---|---|
| Location | 19.07 N, 72.88 E, Mumbai | deg | Site choice | ASSUMPTION | none |
| Solar irradiance (GHI) | 1,763 | kWh/m²/yr (2025) | NASA POWER hourly, `ALLSKY_SFC_SW_DWN`, 2025, uploaded file `data/raw/nasa_power_mumbai_2025_hourly.csv` | SOURCED (satellite and reanalysis-derived; no ground-measurement check) | none (single year) |
| Ambient temperature | hourly from file; annual mean 26.6 | deg C | NASA POWER `T2M`, same file | SOURCED (same caveat) | none |
| Hourly timing convention | Values treated as averages over the hour starting at the timestamp; sun position evaluated at the hour midpoint | n/a | **Inferred from data**: irradiance first appears 1–2 hours before the sun is above the horizon at the timestamp. NASA does not document this convention in the file. | DERIVED (inference) | none |
| Dawn-hour rule | Plane-of-array irradiance set to zero when the midpoint sun is below the horizon | n/a | Approximation. Removes 77 kWh/yr (0.15%) | ASSUMPTION | none |
| Time zone | Asia/Kolkata (IST, UTC+05:30) | n/a | NASA file labels times as LST; IST matches Mumbai | VERIFIED (file header) | none |
| Clear-sky placeholder | Not used in final results | n/a | pvlib Ineichen model with placeholder cloudiness factors | PLACEHOLDER (retained as fallback only) | n/a |

## 2. PV system

| Input | Value | Unit | Source | Status | Sensitivity |
|---|---|---|---|---|---|
| Usable roof area | 350 (500 gross × 70%) | m² | Hypothetical building | ASSUMPTION | roof limit 25–150 kWp |
| Area per kWp (all-in: modules, spacing, access) | 10 | m²/kWp | Modelling allowance, applied once | ASSUMPTION | roof limit sweep |
| PV capacity limit | 35 | kWp | = 350 ÷ 10 | DERIVED | roof limit sweep |
| Tilt / azimuth | 15° / 180° (south) | deg | Near-latitude tilt | ASSUMPTION | none |
| System losses (DC to AC, soiling, wiring) | 14 | % | NREL Annual Technology Baseline 2022 Commercial PV table reports 14.3% AC & DC losses for its 2019 base case. The model rounds this US benchmark to 14%; it is not Mumbai-specific. | SOURCED (primary proxy) | none |
| Temperature coefficient of power | -0.35 | %/°C | NREL System Advisor Model Help, PVWatts module-type table: premium crystalline-silicon module, -0.35%/°C. Module selection for this office remains unverified. | SOURCED (primary proxy) | none |
| Cell temperature rise | 20 °C at 800 W/m² | n/a | Simplified NOCT-style estimate | ASSUMPTION | none |
| PV capital cost | 45,450 | Rs/kWp | Maharashtra rooftop solar benchmark rate, Rs 45,450/kW, reported by CSIS Indian States tracker (March 2026). Primary notification not opened. | SOURCED (secondary) | discount rate, roof limit |
| PV O&M | 500 | Rs/kWp/yr | No source found | PLACEHOLDER | none (small effect) |
| PV lifetime | 25 | years | Common planning value, not sourced | ASSUMPTION | none (salvage credit depends on it) |
| PV salvage | Linear over remaining life, valued at year 20 | n/a | Modelling convention | ASSUMPTION | none |

## 3. Electricity tariff (MSEDCL, LT non-residential, above 50 kW)

| Input | Value | Unit | Source | Status | Sensitivity |
|---|---|---|---|---|---|
| Time-of-day windows | Peak 17:00–24:00; solar hours 09:00–17:00; normal otherwise | hours | MERC Order Case No. 75 of 2025 (25 June 2025), Table 7 (read from the order PDF) | VERIFIED | none |
| Peak surcharge | +25% on energy charge | % | MERC Order Case No. 75 of 2025, Table 7 (LT and HT industrial and commercial) | VERIFIED | tariff scale |
| Solar-hour rebate | 15% (April–September), 25% (October–March) | % | MERC Order Case No. 75 of 2025, Table 7 | VERIFIED | none |
| Base energy rate | 12.16 | Rs/kVAh | MERC press note for the MSEDCL MYT Order (28 March 2025), PDF p. 7, FY 2026-27 table, LT-II(C) >50 kW row. It is retained solely as the legacy energy-only comparator used by the saved base tables. The later official review order below gives a different FY 2026-27 schedule. | **SUPERSEDED for tariff-informed case; legacy comparator only** | tariff scale ±30% |
| Grid support charge (LT) | 1.96 | Rs/kWh | MERC Order Case No. 75 of 2025, Table 8. Applies only once Maharashtra rooftop capacity reaches 5,000 MW. Whether that threshold has been reached is unconfirmed. | VERIFIED (value); applicability UNCONFIRMED | Off in base case. If on, savings fall by about Rs 1 lakh/yr. |
| Demand charge | ₹525 available; off by default | Rs/kVA/month | MERC press note (28 March 2025), PDF p. 7, FY 2026-27 LT-II(C) >50 kW row. This is a legacy option; the later official review order below lists ₹550. The option bills monthly maximum hourly grid import at an assumed PF of 1.0; no measured kVA demand/PF is available. | SUPERSEDED rate; ASSUMPTION method | off/on (`sens_demand_fixed_charges`) |
| Fixed charge | ₹0 applied; off by default | Rs/month | The cited LT-II(C) row specifies a demand charge, not a separate fixed charge. Code supports a separately configured fixed charge for a later verified schedule. | VERIFIED absence in cited row | off/on (`sens_demand_fixed_charges`) |
| Tariff escalation | None (constant prices) by default | %/yr | Modelling assumption; optional 3% and 5% sensitivities use equivalent annualized escalating bill cash flows. | ASSUMPTION | 0%, 3%, 5% (`sens_tariff_escalation`) |
| Export | Not permitted; curtailment allowed | n/a | MVP specification | ASSUMPTION (project specification) | none |

### Tariff-informed hypothetical bill case (separate from the legacy base case)

`scripts/run_tariff_informed_hypothetical.py` creates a distinct, illustrative
case using the later official tariff table. It is not a reconstruction of a
customer bill and must not be used to infer a specific office's liability.

| Input | Value | Unit | Source | Status | Treatment |
|---|---|---|---|---|---|
| LT-II(C) >50 kW energy charge, FY 2026-27 | 14.89 | Rs/kVAh | MERC Order Case No. 75 of 2025 (25 June 2025), Annexure II, PDF p. 53, “Summary of LT Tariff for FY 2026-27” | VERIFIED | applied |
| LT-II(C) >50 kW wheeling charge, FY 2026-27 | 1.52 | Rs/kVAh | Same official table, PDF p. 53 | VERIFIED | applied uniformly, separately from ToD energy adjustments |
| LT-II(C) >50 kW demand charge, FY 2026-27 | 550 | Rs/kVA/month | Same official table, PDF p. 53 | VERIFIED | applied to simulated monthly maximum hourly grid import divided by assumed PF |
| Power factor | 0.95 | fraction | No individual bill or utility-verified PF supplied | ASSUMPTION | used only to convert simulated kW to illustrative kVA demand |
| Contract demand | 100 | kVA | No individual bill or connection details supplied | ASSUMPTION / metadata only | not used as a billing floor or a tariff-applicability determination |
| FAC, electricity duty, taxes | Not included | n/a | The opened tariff table does not establish an applicable rate for this hypothetical connection | NOT VERIFIED / NOT MODELED | excluded |
| Grid-support charge | Not included | n/a | Applicability to this hypothetical connection cannot be confirmed without connection and programme facts | NOT VERIFIED / NOT MODELED | excluded |

## 4. Load

| Input | Value | Unit | Source | Status | Sensitivity |
|---|---|---|---|---|---|
| Annual electricity intensity | 110 | kWh/m²/yr | Placeholder for a four-storey office. **Synthetic, not measured.** | PLACEHOLDER | **Not tested. Largest source of uncertainty in the self-consumption and battery results.** |
| Floor area | 2,000 | m² | Hypothetical building | ASSUMPTION | none |
| Annual load | 220 | MWh/yr | = 110 × 2,000 | DERIVED | none |
| Load shape | Weekday daytime peak (08:00–19:00), weekend factor 0.5, night base fraction 0.30, 4% hourly noise | n/a | Illustrative office profile | ASSUMPTION | none |
| Random seed | 42 | n/a | Reproducibility | ASSUMPTION | none |

## 5. Battery

| Input | Value | Unit | Source | Status | Sensitivity |
|---|---|---|---|---|---|
| Energy capital cost | 15,000 | Rs/kWh | Derived: about USD 170/kWh system cost. Anchor is BloombergNEF's 2025 global LFP pack average of USD 81/kWh (cited via a vendor blog; BNEF not opened), times an assumed system-cost factor of about 2.1. **The system-cost factor is not sourced.** An earlier draft cited Crisil for a USD 70–75/kWh price; that was not verified and has been removed. | DERIVED (anchor SOURCED secondary; factor ASSUMPTION) | ±50% (`sens_battery_cost`); 3,000 to 20,000 Rs/kWh (`sens_grid_2d`) |
| Power capital cost (PCS and inverter) | 4,000 | Rs/kW | **No credible source found.** | PLACEHOLDER | Scaled with energy cost in the ±50% sweep. Not isolated. |
| Power-to-energy ratio | 0.5 C (2-hour battery) | 1/h | Modelling choice, kept fixed so the model stays linear | ASSUMPTION | none |
| Round-trip efficiency | 90 | % | No source found. Used as the planning value. | PLACEHOLDER | 80, 85, 90, 95% (`sens_rte`) |
| Operating range (SOC) | 10% to 95% | % of energy | Modelling convention | ASSUMPTION | none |
| Fixed O&M | 2.5 | % of capital cost per year | NREL 2024 Annual Technology Baseline, Utility-Scale Battery Storage page: FOM is estimated at 2.5% of capital cost and includes augmentation. US utility-scale proxy, not India-specific. | SOURCED (primary proxy) | none. Included in the ±50% sweep through capital cost. |
| Lifetime (replacement interval) | 10 | years | Base case uses a 10-year interval, consistent with the common 10-year warranty term. NREL ATB 2023 uses 15 years for utility-scale storage. | SOURCED RANGE (warranty-based base; NREL alternative) | 10 and 15 years (`sens_battery_life`) |
| Cycle life | 6,000 only when option is enabled | cycles at usable depth | Placeholder used by the optional linear throughput-wear reserve. No dated commercial LFP warranty curve for the selected system was verified; it must not be treated as a validated life claim. Calendar replacement remains the default. | PLACEHOLDER | off/on (`sens_cycle_degradation`) |
| Replacement cost | Same real cost as initial purchase | Rs | Modelling simplification. No cost decline assumed. | ASSUMPTION | Replacement timing is in the life sensitivity |
| Residual value | 0 | Rs | With a 10-year life and 20-year horizon, the second battery is fully used by year 20 | DERIVED | none |
| Charging source | Grid or PV | n/a | Dispatch is optimized | MODEL OUTPUT | n/a |

## 6. Financial

| Input | Value | Unit | Source | Status | Sensitivity |
|---|---|---|---|---|---|
| Discount rate | 10 | % | Base assumption. Karnataka regulator's 2026-29 discussion paper uses 11.76% WACC for utility-scale solar (reported by Energetica India, June 2026). A normative WACC of about 8.8% appears in a PV-Tech guest article. The discount rate is an assumption in the range 8–12%, not a sourced value. Whether the rate is real or nominal was not determined. | ASSUMPTION (regulatory references SOURCED secondary) | 6, 8, 10, 12, 14% (`sens_discount`) |
| Evaluation horizon | 20 | years | Project specification | ASSUMPTION (project specification) | none |
| Currency conversion | 88.8 | Rs/USD | Implied by one Indian BESS tender report (Rs 1.775 lakh/MW/month = USD 1,999.45/MW/month). Not a dated RBI rate. | DERIVED (secondary) | none |
| Grid-only comparison | Scenario A | n/a | Definition | ASSUMPTION | n/a |
| Payback | Simple and discounted; reported as "not achieved" if not reached within the horizon | years | Standard definitions, implemented in `src/financials.py` | MODEL METHOD | n/a |

## 7. Software and methods

| Item | Version or reference | Status |
|---|---|---|
| Optimization solver | HiGHS 1.15.1 through Pyomo 6.10.1 | Software (verified by test suite) |
| Solar geometry and irradiance | pvlib 0.16.1 (solar position, Erbs decomposition, plane-of-array transposition) | Software |
| Tests | 64 automated tests (`tests/`), all passing in this environment | Verification |

## 8. Items not yet sourced or verified

These need work before any external use:

1. Official FY 2026-27 MSEDCL base energy rate for LT non-residential above 50 kW.
2. Whether the 5,000 MW rooftop threshold for the grid support charge has been reached.
3. Battery system-cost factor and power-conversion (PCS) cost, both for India and dated.
4. Battery round-trip efficiency for commercial LFP systems.
5. Battery cycle life and cycle-based degradation.
6. PV and battery O&M costs in India.
7. Discount rate: whether it should be real or nominal, and what a commercial buyer's cost of capital is.
8. A measured or utility-verified load profile for a Mumbai office building.
9. Validation of NASA POWER irradiance against ground measurements for Mumbai.
