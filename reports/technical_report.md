# Techno-Economic Optimization of Rooftop Solar PV and Battery Energy Storage for a Commercial Building in Mumbai

**Status.** This is a model-based study with placeholder and secondary-source inputs. It has not been externally validated. Figures quoted here come from saved model outputs in `results/tables/`. Each input's verification status is in `ASSUMPTIONS_AND_SOURCES.md`.

## 1. Abstract

We model a hypothetical four-storey, 2,000 m² office in Mumbai, with 350 m² of usable roof. Hourly dispatch over one representative year (2025) is optimized with a linear program solved by HiGHS through Pyomo. Three scenarios are compared: grid only (A), PV only (B), and PV with battery (C). Under base assumptions, the optimal PV capacity is the 35 kWp roof limit, and the optimal battery is zero. PV-only has an NPV of ₹26.3 lakh over 20 years against grid-only, with a simple payback of 3.25 years and a discounted payback of 4.12 years at a 10% discount rate. A battery becomes preferable only when its energy cost is low, the tariff is high, or the roof is large enough to produce midday surplus. The result depends most on the synthetic load and on the placeholder battery cost, so the battery conclusion is the least reliable part of the study.

## 2. Introduction and motivation

Commercial buildings in India pay time-of-day (ToD) tariffs that charge more in the evening than at midday. Rooftop PV generates at midday, and a battery could move that energy into the evening peak. The question is whether, under current costs and tariffs, a building should install a battery alongside PV, and how large each should be. The study is designed as an internship-level techno-economic model: it links a physical resource model, a dispatch optimization, and a lifecycle financial analysis, and it reports which conclusions are supported by sourced inputs and which depend on assumptions.

## 3. Literature and industry context

The study follows standard practice for distributed-energy sizing: an hourly energy balance, a lifecycle cost objective with replacements and salvage, and sensitivity analysis on the uncertain inputs. We did not perform a formal literature review. The industry context used for inputs is limited to the sources listed in Section 5 and in `ASSUMPTIONS_AND_SOURCES.md`. Those sources are a Maharashtra regulatory order, a state-level rooftop benchmark rate, a US utility-scale cost baseline, and a regulatory discount-rate reference, each with its verification status. No academic references are cited for model structure.

## 4. System description

- **Building.** Four storeys, 2,000 m² floor area, 500 m² gross roof, 70% usable (350 m²). Hypothetical.
- **PV.** Fixed tilt 15° facing south. Capacity is limited to 35 kWp, which is 350 m² at an all-in allowance of 10 m² per kWp. The allowance covers modules, spacing, and access, and is applied once.
- **Battery.** Lithium iron phosphate assumed. Energy-to-power ratio fixed at 0.5 C (a 2-hour battery). Operating range 10–95% state of charge. Round-trip efficiency 90% in the base case.
- **Grid.** Connection available. Export not permitted. Curtailment allowed.
- **Tariff.** Maharashtra LT non-residential above 50 kW, with ToD windows, a peak surcharge, and a solar-hour rebate.

## 5. Data and assumptions

**Solar resource.** Hourly 2025 GHI, air temperature, and wind speed from NASA POWER for 19.07 N, 72.88 E. The file is included in `data/raw/`. Annual GHI is 1,763 kWh/m². Irradiance is much lower in the monsoon (June–September, about 107–132 kWh/m² per month) than in March–April (about 200 kWh/m² per month). The data are satellite and reanalysis-derived and were not checked against ground measurements. NASA's hourly labels are treated as the start of an averaging hour; this was inferred from the data, not documented.

**Load.** A synthetic office profile with annual demand of 220 MWh (110 kWh/m² × 2,000 m²). Peak demand is about 64 kW. Weekdays are weighted to daytime, weekends at half weight, with a night base of 30% of the average. **This is not measured consumption.** It is the largest source of uncertainty in the battery and self-consumption results.

**Tariff.** The ToD windows (peak 17:00–24:00, solar hours 09:00–17:00), the 25% peak surcharge, and the solar-hour rebate (15% April–September, 25% October–March) are taken from MERC Order Case No. 75 of 2025. The original saved base tables retain a legacy ₹12.16/kVAh energy-only comparator. A separate public-tariff hypothetical bill case uses the later official FY 2026-27 LT-II(C) >50 kW schedule in the same order's Annexure II, PDF p. 53: ₹14.89/kVAh energy, ₹1.52/kVAh wheeling, and ₹550/kVA/month demand. It uses assumed PF 0.95 and a simulated monthly maximum; a 100 kVA contract demand is metadata only, not a billing floor. FAC, duty/tax, and grid-support charges are excluded because their connection-specific applicability is not established. Tariffs are held constant in the base case; escalation is an optional illustrative sensitivity.

**Costs.**

| Item | Value | Status |
|---|---|---|
| PV capital cost | ₹45,450/kWp | Secondary: Maharashtra rooftop benchmark (CSIS, March 2026) |
| PV O&M | ₹500/kWp/yr | Placeholder |
| PV life | 25 years, salvage at year 20 | Assumption |
| Battery energy capex | ₹15,000/kWh | Derived from a secondary pack-price anchor and an unsourced system factor |
| Battery power capex (PCS) | ₹4,000/kW | Placeholder |
| Battery O&M | 2.5% of capex per year | Secondary: US utility-scale baseline (NREL ATB 2023) |
| Battery life | 10 years (replacement at year 10) | Warranty-based base; 15 years tested |
| Round-trip efficiency | 90% | Placeholder; 80–95% tested |
| Discount rate | 10% | Assumption; 6–14% tested |
| Horizon | 20 years | Project specification |

## 6. Mathematical formulation

**Decision variables.** PV capacity $x$ (kWp), battery energy $E$ (kWh). Hourly for $t = 0,\dots,T-1$ with $T = 8{,}760$: grid import $g_t \ge 0$, PV used $u_t \ge 0$, battery charge $c_t \ge 0$, battery discharge $d_t \ge 0$, and state of charge $s_t$ for $t = 0,\dots,T$. Battery power is fixed at $P = 0.5E$.

**Objective.** Minimize annualized system cost:

$$
\min \; A_{\mathrm{PV}}\, x + A_{\mathrm{B}}\, E + \sum_{t} \rho_t\, g_t + \gamma \sum_t \bar{p}_t x
$$

where $\rho_t$ is the hourly tariff, $\bar{p}_t$ is PV output per kWp, and $\gamma$ is the grid support charge if enabled (zero in the base case). The annualized coefficients are

$$
A_{\mathrm{PV}} = \mathrm{CRF}_{N}\cdot\mathrm{PC}_{\mathrm{PV}} + m_{\mathrm{PV}}, \qquad
A_{\mathrm{B}} = \mathrm{CRF}_{N}\cdot\mathrm{PC}_{\mathrm{B}} + m_{\mathrm{B}},
$$

with $\mathrm{CRF}_N = r(1+r)^N / ((1+r)^N - 1)$. The present cost $\mathrm{PC}$ of an asset with capex $K$ and life $L$ over horizon $N$ is

$$
\mathrm{PC} = \sum_{k:\,kL<N} \frac{K}{(1+r)^{kL}} \;-\; \frac{K\,f_{\mathrm{rem}}}{(1+r)^N},
\qquad f_{\mathrm{rem}} = \frac{\max(0,\,L_{\mathrm{last}}+L-N)}{L},
$$

which includes replacements and the discounted salvage of the remaining life. Here $m$ is annual O&M. The battery O&M is a fraction of its capex, so $m_{\mathrm B}$ depends on the cost assumptions.

**Constraints.**

$$
\begin{aligned}
& 0 \le x \le \bar{X}, \qquad E \ge 0, \\
& 0 \le u_t \le \bar{p}_t x, \\
& g_t + u_t + d_t = L_t + c_t \quad \text{(energy balance; no export)}, \\
& s_{t+1} = s_t + \eta\, c_t - d_t/\eta, \qquad s_0 = s_T, \\
& s_\min E \le s_t \le s_\max E, \\
& 0 \le c_t \le P, \qquad 0 \le d_t \le P, \qquad P = 0.5E,
\end{aligned}
$$

with $\eta = \sqrt{\text{round-trip efficiency}}$. The PV available in each hour is $\bar{p}_t x$, and curtailment is the difference between that and $u_t$.

**Why no binaries.** Simultaneous charging and discharging would waste energy through losses and cannot lower the cost, so the linear program does not need binary variables to rule it out. The solutions are checked to contain no such hours.

**Financial consistency.** The lifecycle cost of each scenario is the present value of capital, replacements, O&M, and grid energy, less discounted salvage. Multiplying it by $\mathrm{CRF}_N$ reproduces the optimizer's objective exactly. The NPV against grid-only equals the difference in lifecycle cost. Both identities are tested.

**Solver.** HiGHS 1.15.1 through Pyomo 6.10.1. All runs in this study returned the optimal termination condition.

## 7. Implementation methodology

The pipeline is: load and check configuration (`src/config.py`), load and validate the NASA file (`src/nasa_power.py`), compute sun geometry and PV output (`src/solar_resource.py`), build the synthetic load (`src/load_profile.py`), apply the ToD tariff (`src/tariff.py`), solve the scenarios (`src/optimize.py`), and compute lifecycle and payback (`src/financials.py`). Sensitivity runs re-solve all three scenarios from scratch for each case. Failed solves are recorded with a status and would appear in the tables, not dropped. The full list of reproduction commands is in the README.

Two modelling decisions affect the hourly data and were checked against the data:

- **Sun position at the hour midpoint.** The NASA file shows irradiance appearing one to two hours before the sun is above the horizon at the timestamp, which fits hour-beginning averages. Sun position is therefore evaluated 30 minutes after each label. Plane-of-array irradiance is set to zero when the midpoint sun is below the horizon, which removes 77 kWh per year (0.15% of output).
- **Rooftop allowance applied once.** The 10 m²/kWp figure already includes spacing, so no further setback is subtracted from the usable area.

Testing: 64 automated tests cover configuration consistency, the NASA loader, geometry, tariff logic, the energy balance and state-of-charge constraints, optimality checks, financial identities, and integrity of the saved tables and figures. All pass in a clean virtual environment rebuilt from `requirements.txt`.

## 8. Results and discussion

**Base case (35 kWp roof, base costs).**

| Scenario | PV (kWp) | Battery (kWh) | Annual grid energy cost (₹ lakh) | Annualized total cost (₹ lakh) | Lifecycle cost, PV (₹ lakh) | NPV vs A (₹ lakh) | Simple payback (yr) | Discounted payback (yr) |
|---|---|---|---|---|---|---|---|---|
| A: grid only | 0 | 0 | 25.41 | 25.41 | 216.3 | 0 | n/a | n/a |
| B: PV only | 35.0 | 0 | 20.33 | 22.32 | 190.0 | 26.3 | 3.25 | 4.12 |
| C: PV + battery | 35.0 | 0 | 20.33 | 22.32 | 190.0 | 26.3 | 3.25 | 4.12 |

- PV generates 51.08 MWh per year (about 1,460 kWh per kWp). Of this, 50.68 MWh (99.2%) is used on site and 0.39 MWh is curtailed.
- Annualized capital and O&M for the PV is ₹1.99 lakh per year, against ₹2.54 lakh per year of grid energy saved, so the energy saving is what pays the system back.
- The optimal battery is zero, so C is identical to B.

**Monthly behaviour.** PV output is highest in March and lowest in July–September. Grid imports fall in the sunny months. Figures 10–14 show the monthly profile, average days, the energy balance, and the utilization split.

**Why the battery is zero.** Midday PV at 35 kWp rarely exceeds the building's midday demand, so there is little surplus to store. A battery would have to buy grid energy at midday rebated rates and sell it at the evening peak, which earns only the spread between those rates less round-trip losses. At ₹15,000/kWh, the annualized battery cost is far above that spread.

**Tariff-informed hypothetical bill case.** Under the separate official-schedule case, grid-only's annual bill before FAC, duty and tax is ₹38.75 lakh. PV-only reduces it to ₹30.99 lakh and has an NPV of ₹49.10 lakh versus grid-only. PV plus battery reduces it to ₹30.26 lakh, with 15.289 kWh of battery and NPV ₹51.18 lakh. These figures are from `results/tables/tariff_informed_hypothetical_bill.csv`; they remain illustrative because the load and demand basis are hypothetical.

**Lifecycle detail (PV only).** Initial PV capex is ₹15.91 lakh. No PV replacement falls within 20 years. Salvage at year 20 is ₹3.18 lakh nominal (20% of capex, five years of a 25-year life), worth ₹0.47 lakh in present value. Annual O&M is ₹0.18 lakh.

**Payback.** Both simple and discounted payback are achieved within the 20-year horizon in every PV case tested. The simple payback uses net annual savings after O&M. The discounted payback is the year after which the cumulative discounted cash flow stays non-negative.

## 9. Financial analysis

NPV, payback, and lifecycle cost are computed relative to grid-only. The conventions are:

- **Capital** is counted once, at year zero. Battery replacement is discounted at $1/(1+r)^{10}$ in the base case.
- **Salvage** is the remaining life of each asset at year 20, valued linearly and discounted from year 20.
- **O&M** is a level annual cost for 20 years.
- **Grid energy** is the year-one cost, held constant (no tariff escalation).
- **Payback not achieved** is reported as "not achieved" if cumulative cash flow never becomes and stays non-negative within the horizon. None of the PV cases tested fell into this category.

The discount-rate sweep, the tariff sweep, and the lifecycle identity tests give confidence that the financial calculations are internally consistent. External validation of the financial assumptions has not been performed.

## 10. Sensitivity analysis

Every case re-optimizes PV and battery. Results are in `results/tables/sens_*.csv`.

**Discount rate (PV only, NPV ₹ lakh; discounted payback years).** 6%: 41.3, 3.72. 8%: 32.9, 3.91. 10%: 26.3, 4.12. 12%: 21.0, 4.37. 14%: 16.8, 4.64. Simple payback is 3.25 years throughout. The battery stays at zero at every rate.

**Optional extensions.** With the cycle-throughput reserve enabled using its 6,000-cycle placeholder, the base solution remains 35 kWp PV and zero battery. A 3% tariff-escalation assumption increases PV-only NPV to ₹36.1 lakh; 5% increases it to ₹44.5 lakh, with zero battery in both cases. The legacy ₹525/kVA/month demand option using assumed PF 1.0 yields a PV-only NPV of ₹32.2 lakh and a PV+battery NPV of ₹33.6 lakh with a 14.1 kWh battery. The separate ₹550/kVA/month tariff-informed case is reported above. Both demand treatments are illustrative, not utility-bill validated.

**Electricity tariff (PV only).** −30%: NPV 13.3 lakh, simple payback 4.71 years, discounted 6.69 years. Base: 26.3, 3.25, 4.12. +30%: 39.2, 2.48, 2.99. The battery stays at zero in this one-dimensional sweep.

**Battery capital cost (scenario C).** At 50% of base, the optimal battery is 5.0 kWh, worth ₹367 per year over PV only. At 100% and 150%, the battery is zero.

**Round-trip efficiency (80, 85, 90, 95%).** The battery is zero at every efficiency tested.

**Battery life (10 and 15 years).** The battery is zero in both cases.

**Rooftop area (scenario C).**

| Roof limit (kWp) | Optimal PV (kWp) | Optimal battery (kWh) | Advantage over PV only (₹/yr) |
|---|---|---|---|
| 25 | 25.0 | 0 | 0 |
| 35 | 35.0 | 0 | 0 |
| 50 | 50.0 | 0 | 0 |
| 75 | 75.0 | 10.0 | 1,958 |
| 100 | 100.0 | 70.7 | 20,120 |
| 150 | 105.2 | 85.1 | 21,150 |

With the roof limit above about 88 kWp, PV only is limited by economics at 88.1 kWp. With a battery, the economic optimum rises to 105.2 kWp, so storage allows more PV. A verification run with the roof limit lifted to 200 kWp gives the same 105.2 kWp, confirming that economics, not the roof, sets the optimum at that point.

**Two-dimensional sweep: battery energy capex by tariff (35 kWp roof).** The battery is preferable to PV only at the following combinations (optimal battery in kWh in brackets):

- Tariff ×0.70: ₹3,000/kWh (15).
- Tariff ×0.85: ₹3,000 (99), ₹5,000 (7).
- Tariff ×1.00: ₹3,000 (193), ₹5,000 (17).
- Tariff ×1.15: ₹3,000 (196), ₹5,000 (98), ₹7,500 (7).
- Tariff ×1.30: ₹3,000 (197), ₹5,000 (179), ₹7,500 (13), ₹10,000 (1).

At base tariff, the battery is preferable up to about ₹5,000/kWh of energy capex and not at ₹7,500/kWh. At +30% tariff, the threshold is roughly ₹10,000–12,500/kWh. The ₹3,000/kWh column is well below indicative costs and shows the boundary, not a recommendation.

**Where the battery becomes preferable (summary).** Storage pays when the energy cost is low relative to the ToD spread, the tariff is high, and the roof produces enough midday surplus to store. Under current inputs, none of these conditions holds at a 35 kWp roof with the ₹15,000/kWh battery.

## 11. Model limitations

1. **Synthetic load.** Self-consumption and battery value depend on the load shape, which is not measured.
2. **Placeholder battery cost and PCS cost.** The ₹15,000/kWh energy cost rests on an unsourced system-cost factor. PCS cost is a placeholder.
3. **Hypothetical bill model.** The separate official-tariff case includes verified energy, wheeling and demand-rate values, but its PF and demand basis are explicit assumptions and it excludes FAC, duty/tax and grid-support charges.
4. **Constant-price base case.** Tariff escalation is optional and illustrative, not a forecast.
5. **Cycle-degradation uncertainty.** The optional throughput-wear reserve uses a 6,000-cycle placeholder; the default remains calendar replacement.
6. **Single representative year.** No interannual variability in irradiance or load.
7. **Irradiance not validated.** NASA POWER has not been compared against ground measurements for Mumbai, and the hour-labelling convention is inferred.
8. **No inverter, reactive power, or network modelling.** No export; the public-tariff case applies an assumed PF to simulated hourly demand rather than a measured utility-demand method.
9. **Discount rate real or nominal not determined.** The rate is an assumption.
10. **Grid support charge applicability unknown.** Off in the base case; if it applies, PV savings fall by about ₹1 lakh per year.

## 12. Conclusions

Under the legacy base assumptions, a 35 kWp rooftop PV system is economic against grid-only electricity: NPV ₹26.3 lakh, simple payback 3.25 years, discounted payback 4.12 years at 10%. The separate public-tariff hypothetical bill case also selects 35 kWp PV and a 15.289 kWh battery, but that case is not a customer-bill reconstruction. A battery at ₹15,000/kWh is not economic in the legacy base at this roof size, and no tested base sensitivity on discount rate, tariff, round-trip efficiency, or battery life makes it so. These conclusions are conditional on synthetic load, hypothetical bill treatment, and placeholder battery cost; replace the inputs before applying them to a real building.

## 13. References

Only sources that were retrieved in this project are listed. Items marked "not opened" were seen in search results or secondary summaries and were not checked against the original document.

1. Maharashtra Electricity Regulatory Commission. Order in Case No. 75 of 2025, MSEDCL tariff order, 25 June 2025. Tables 7 (ToD), 8 (grid support charge), and Annexure II p. 53 (FY 2026-27 LT-II(C) >50 kW energy, wheeling, and demand schedule) were read from the order PDF.
2. NASA POWER. Hourly 2025 data for 19.07 N, 72.88 E, parameters ALLSKY_SFC_SW_DWN, T2M, WS10M. Supplied as a file; methodology not independently reviewed.
3. CSIS Indian States tracker. Maharashtra rooftop solar benchmark rate of ₹45,450/kW, March 2026. Secondary summary; primary notification not opened.
4. National Renewable Energy Laboratory. Annual Technology Baseline 2023, utility-scale battery storage. Fixed O&M of 2.5% of capital cost and a 15-year lifetime for utility-scale storage. US market; secondary summary read.
5. Karnataka Electricity Regulatory Commission. Solar tariff discussion paper, 2026–29 control period, WACC of about 11.76%. Reported by Energetica India, June 2026; primary not opened.
6. BloombergNEF global LFP battery pack average, 2025 (USD 81/kWh). Cited through a vendor blog; BNEF not opened.
7. Pyomo, pvlib, HiGHS, pandas, matplotlib, plotly. Open-source software; versions in `requirements.txt`.

Not used, but identified as leads: NREL cost projections for utility-scale battery storage (2023 and 2025 updates); World Bank report on battery warranties in developing countries (cited via a secondary blog, not opened). These should be checked before any battery cost claim is strengthened.
