# Interview Preparation

This file prepares you to explain and defend the project. Every number here comes from saved model outputs. Where a result depends on an assumption or a placeholder, the answer says so. Interviewers reward candour about limits more than confident claims that fall apart under a follow-up question.

---

## 1. The 60-second explanation

I built a model of a rooftop solar and battery system for a hypothetical office building in Mumbai. It uses one year of hourly irradiance from NASA, converts that to PV output on a tilted roof, and combines it with an hourly load and Maharashtra's time-of-day tariff. A linear program, solved with HiGHS, chooses the PV size, the battery size, and every hour's dispatch to minimize the annualized cost of electricity. I compared grid-only, PV-only, and PV-plus-battery, then calculated NPV, payback, and lifecycle cost, including battery replacement and PV salvage. Under my base assumptions, a 35 kWp PV system pays back in about 3.3 years and gives an NPV of about ₹26 lakh over 20 years. The battery is not economic at the assumed cost, and I tested the conditions under which it would be. The load is synthetic and some costs are placeholders, so I present the battery result as the least reliable part of the study.

## 2. The five-minute explanation

**The problem.** A commercial building pays a time-of-day tariff. Electricity is more expensive in the evening peak (17:00–24:00) and cheaper at midday, when rooftop solar produces. The questions are how much PV to install on a limited roof, and whether a battery should move midday solar into the evening peak.

**The data.** I used NASA POWER hourly irradiance and temperature for Mumbai in 2025. Annual GHI is 1,763 kWh/m². Irradiance drops sharply in the monsoon. I converted the horizontal irradiance to the irradiance on a 15° south-facing panel, using the sun's zenith angle and the Erbs decomposition, which splits GHI into beam and diffuse parts. The PV output follows from the panel irradiance, cell temperature, and system losses. For 35 kWp the model gives 51.1 MWh per year.

**The load.** I didn't have measured data, so I built a synthetic office profile of 220 MWh per year with a daytime peak. This is the main weakness, and I say so.

**The tariff.** I used the ToD structure from MERC's order in Case No. 75 of 2025: a 25% surcharge in the evening peak, and a rebate on midday energy that is bigger in winter. The original base tables retain a legacy ₹12.16/kVAh energy-only comparator. A separate public-tariff hypothetical case uses the official ₹14.89/kVAh energy, ₹1.52/kVAh wheeling, and ₹550/kVA/month demand schedule; its PF and demand basis are clearly assumed.

**The optimization.** The problem is linear: every term is a constant times a decision variable. So a linear program finds the global optimum. The variables are the PV capacity, the battery energy, and for each of 8,760 hours the grid import, PV used, battery charge, discharge, and state of charge. The constraints are the hourly energy balance, the state-of-charge dynamics with losses, the power and capacity limits, a cyclic condition so the battery ends where it started, and no export. I didn't need binary variables, because simultaneous charge and discharge only wastes energy. I checked that the solutions contain none.

**The finance.** Each scenario is converted to a lifecycle cost at a 10% discount rate over 20 years, with the battery replaced at year 10 and PV salvaged at year 20. The annualized cost the optimizer minimizes reproduces exactly from the lifecycle calculation, which I tested.

**Results.** Under base assumptions the optimal PV is the 35 kWp roof limit and the optimal battery is zero. PV-only has an NPV of ₹26.3 lakh against grid-only, a simple payback of 3.25 years, and a discounted payback of 4.12 years. The battery only becomes preferable at much lower energy cost (about ₹5,000/kWh or below at base tariff), higher tariffs, or a larger roof. Given the roof, the battery pays only once midday surplus exists to store.

**Limits.** The load is synthetic, the battery cost rests on an unsourced system-cost factor, and the tariff's base rate is unverified. I haven't validated the irradiance against ground data. I describe the results as model outputs under stated assumptions, not as validated findings.

## 3. Twenty technical questions with model answers

**Q1. Why a linear program and not a nonlinear or heuristic method?**
Every term in the objective and constraints is linear: prices times energy, PV output as a fixed profile times capacity, and state-of-charge equations with constant efficiency. A linear program has a global optimum, a solver proves it, and it runs in seconds here. A heuristic would give a good answer with no guarantee. I used binaries nowhere, because simultaneous charge and discharge is never optimal.

**Q2. How did you decide the battery power rating?**
I fixed it at 0.5 C, so power is half the energy. That makes the battery a 2-hour system and keeps the model linear. Letting power be a separate variable is also linear, so I could have optimized it, but the fixed ratio is a common commercial design and it avoids an extra degree of freedom I couldn't justify with data. I should be clear that this is an assumption.

**Q3. Walk me through the state-of-charge equation.**
s(t+1) = s(t) + η·c(t) − d(t)/η. Charging adds energy, reduced by one-way efficiency η. Discharging removes energy, grossed up by 1/η, because to deliver d of energy you must remove more from storage. With round-trip efficiency 90%, η is √0.9 ≈ 0.949. The split keeps the equation linear, and the bounds keep SOC between 10% and 95% of capacity.

**Q4. What is the cyclic constraint for?**
Without it, the optimizer can empty the battery in the final hour, which loses no value within the year and so looks free. Requiring s(0) = s(T) means the year's stored energy is accounted for properly. It is the standard fix for annual dispatch.

**Q5. How do you know the energy balance is correct?**
I check it in three ways. The hourly balance g + u + d = L + c is enforced as a constraint, and I test that the residual is below 10⁻⁶ kWh in every hour. Grid-only cost matches an independent tariff calculation exactly. And for PV-only, used plus grid equals load in every hour, which is tested on the saved dispatch.

**Q6. Why isn't simultaneous charging and discharging a problem?**
Charging and discharging in the same hour cycles energy through losses, so the net effect is pure loss. An optimal solution never does it, because you could reduce both by the same amount, keep the balance and the state of charge, and cut losses. I verified the solutions contain no such hours.

**Q7. How is the tariff modelled, and why does it matter?**
The rate is hour-dependent: 25% above base in 17:00–24:00, a rebate of 15% or 25% in 09:00–17:00 depending on season, and base otherwise. That shape is what makes a battery attractive. The battery buys at a rebated midday price and sells at the peak. The margin after losses is only about ₹4.6/kWh at base tariff, which explains why storage is marginal.

**Q8. What is the capital recovery factor and why use it?**
CRF = r(1+r)^N / ((1+r)^N − 1). It turns a present value into a level annual payment over N years. I annualize because it compares directly with the annual grid bill and matches the optimizer's objective. Minimizing the annualized total is the same as minimizing the present value, but easier to read.

**Q9. How did you handle battery replacement?**
A 10-year battery replaced at year 10 is bought twice within the 20-year horizon. The second purchase is discounted by 1/(1+r)^10, so it costs less in present value than the first. I include it in both the optimizer and the financial analysis. Its residual value at year 20 is zero, because its second life ends exactly at the horizon.

**Q10. Why credit salvage for the PV system?**
PV has a 25-year life and the horizon is 20 years, so five years of life remain. Without a salvage credit, PV is penalized for life it still has. I credit 5/25 of the capex at year 20, discounted back. That is worth about ₹0.47 lakh in present value, which is small but correct.

**Q11. How do you avoid double-counting capital?**
Initial capex appears once, at time zero. Replacements appear only at their own year. Salvage is a credit, not a second purchase. I check this by testing that the year-zero cash flow equals minus the total capex, and that the replacement cash flow is exactly the battery capex at year 10.

**Q12. Your payback is 3.25 years. How reliable is that?**
It is a model output, and its reliability is limited by the inputs. It depends most on the tariff's base rate (unverified), the load (synthetic), and the O&M (placeholder). Under a 30% lower tariff it lengthens to 4.7 years, and under a 30% higher tariff it shortens to 2.5. I would quote it as "about 3 to 5 years, depending on the tariff", not as a single figure.

**Q13. What happens if the grid support charge applies?**
It adds ₹1.96/kWh on all PV generation once Maharashtra reaches 5,000 MW of rooftop capacity. That cuts the annual PV saving by about ₹1 lakh. In a model run with the charge switched on, NPV falls to ₹17.8 lakh, simple payback extends to 4.1 years, and discounted payback to 5.5 years (`results/tables/gsc_on_case.csv`). I haven't confirmed whether the threshold has been reached, so it is off in the base case and I show it as a sensitivity.

**Q14. Why does the battery never appear in the base case?**
At ₹15,000/kWh energy cost, the annualized battery cost is much larger than the arbitrage margin of about ₹4.6/kWh per cycle. The battery would also need surplus midday PV to store, and at 35 kWp there is little. At base tariff the battery becomes preferable only at an energy cost of about ₹5,000/kWh or below; it is not preferable at ₹7,500/kWh. Note that PCS cost is also a placeholder.

**Q15. When would a battery become economic?**
Three conditions combine. The energy cost has to fall low enough, to about ₹5,000/kWh or below at base tariff; the tariff has to be higher, pushing the threshold to about ₹10,000–12,500/kWh at +30%; or the roof has to be large enough to produce midday surplus, which happens from about 75 kWp. With a larger roof, the battery also lets the economic PV optimum rise from 88 to 105 kWp.

**Q16. Why does the roof limit matter so much?**
The optimizer chooses PV up to the roof limit when more PV is profitable. At 35 kWp the roof binds, so PV is at the limit and there is little surplus for storage. When I lift the limit, PV-only settles at about 88 kWp, where the economics stops favouring more PV. A battery then lets the system go to about 105 kWp, because it absorbs midday output that would otherwise be curtailed.

**Q17. How do you verify that sensitivities are re-optimized, not just recalculated?**
Each case re-solves all three scenarios from scratch. The results show it: battery size responds to battery cost, and PV size responds to the roof limit once economics binds. A fixed-capacity recalculation would not change those capacities. Also, the roof sweep shows PV-only at 88 kWp for limits of 100 and 150 kWp, which is the economic optimum rather than the limit.

**Q18. What happens if a sensitivity case fails to solve?**
The solver status is recorded in the table, and the test suite fails if any row is not optimal. I found no failures across 105 grid cases and the other sweeps. A failed case would appear as an explicit status, not be dropped.

**Q19. Why do you use NASA POWER data, and what are its weaknesses?**
It is a free, consistent, hourly global dataset, which makes the project reproducible. The weakness is that it is derived from satellite and reanalysis, not ground measurements, and I used only one year. I inferred its hour-labelling convention from the data, since it isn't documented in the file. A real project would validate it against a local pyranometer.

**Q20. What would you do next to make this rigorous?**
For a building-specific study, replace the reproducible synthetic load and hypothetical bill inputs with measured data. Source the PCS cost and the battery system-cost factor. The model now has optional cycle-wear and escalation sensitivities, but their inputs remain illustrative. Validate irradiance against ground data, then re-run sensitivities.

## 4. Explaining every major equation

- **GHI = DHI + DNI·cos(Z).** Total horizontal irradiance is diffuse plus the beam projected onto the horizontal. Z is the apparent zenith.
- **AOI at solar noon = |Z − β|** for a south-facing panel tilted β. The angle between the sun and the panel's normal.
- **P_DC = P_rated · (G_POA/1000) · [1 + γ(T_cell − 25)].** Output scales with irradiance, falls with cell temperature, and is referenced to standard test conditions.
- **s(t+1) = s(t) + η·c(t) − d(t)/η.** State-of-charge dynamics with split efficiency.
- **g + u + d = L + c.** Hourly energy balance with no export.
- **CRF = r(1+r)^N / ((1+r)^N − 1).** Converts a present value to a level annual payment.
- **PC = Σ K/(1+r)^{kL} − K·ρ_rem/(1+r)^N.** Present cost of an asset with replacements and discounted salvage.
- **NPV = −I₀ + Σ CF_t/(1+r)^t.** Net present value, here relative to grid-only.
- **Simple payback ≈ I₀ / net annual savings.** Years to recover the initial investment, ignoring discounting.
- **Lifecycle cost × CRF = annualized optimizer objective.** The consistency identity that ties the optimizer to the finance.

## 5. Code architecture

The project is modular: each file has one job, and the optimizer, finance, and tests all read the same configuration.

- **`configs/base.yaml`**: every input, each tagged with its verification status. Change inputs here, not in code.
- **`src/config.py`**: loads the configuration and checks it, for example that the usable roof area and the PV capacity agree.
- **`src/nasa_power.py`**: reads the NASA file, skips the header, and rejects missing values, duplicates, and wrong lengths.
- **`src/solar_resource.py`**: sun geometry (`solar_geometry_and_pv`), with the midpoint convention and the dawn rule. Returns zenith, AOI, irradiance, cell temperature, and PV output for each hour.
- **`src/load_profile.py`**: the synthetic office load. Deterministic for a given seed.
- **`src/tariff.py`**: the hourly ToD rate and the baseline grid-only and PV-only bills.
- **`src/finance.py`**: capital recovery and present cost with replacements and salvage.
- **`src/optimize.py`**: builds and solves the Pyomo model for each scenario, and returns the hourly dispatch.
- **`src/financials.py`**: NPV, simple and discounted payback, cash flows, and lifecycle cost.
- **`scripts/`**: reproduction scripts. `run_scenarios.py` for the base case, `run_sensitivity.py` for each sweep, `merge_grid_2d.py` to combine the 2-D grid, `make_figures.py`, `make_extra_figures.py`, and `make_dashboard.py` for outputs, and `build_dataset.py` for the hourly dataset.
- **`tests/`**: 64 automated tests grouped by concern: data, tariff, geometry, optimization constraints, financial identities, sensitivity integrity, and output integrity.

The data flows one way: configuration and raw data go into the model, the model writes tables, and the figures and dashboard read only those tables. That is why every plotted number traces back to a saved model output.

## 6. Limitations and improvements

**Limitations (state these before the interviewer does).**
- The load is synthetic, so the battery and self-consumption results are the least reliable.
- The battery cost (₹15,000/kWh) rests on an unsourced system-cost factor. PCS cost is a placeholder.
- The base tables use a legacy energy-only comparator. The separate public-tariff case includes energy, wheeling and demand rates, but its PF, demand basis and excluded bill components remain hypothetical.
- Prices are constant: no escalation.
- Battery degradation is calendar-based. Cycle-based fade is not modelled.
- One year of irradiance. No validation against ground data.
- No inverter sizing, reactive power, or network constraints; demand treatment remains hypothetical.

**Improvements, in priority order.** Replace the default load and bill assumptions for a specific building. Source the PCS and battery system costs with dates. Confirm grid-support applicability. Validate the irradiance. Refine demand treatment using a customer bill.

## 7. Resume bullets (verified claims only)

These claims are supported by the saved outputs and the test suite. Each one states that the inputs are illustrative. Do not drop that qualifier.

**Bullet 1.** Built a hourly linear-programming model in Python (Pyomo, HiGHS) that jointly sizes rooftop PV and battery storage for a Mumbai commercial building over 8,760 hours, with 64 automated tests, including checks that the lifecycle cost reproduces the optimizer's objective exactly.

**Bullet 2.** Under illustrative inputs and Maharashtra's time-of-day tariff structure, a 35 kWp rooftop system gave an NPV of ₹26.3 lakh over 20 years against grid-only (3.3-year simple payback at 10%), and a battery at ₹15,000/kWh was not economic; sensitivity analysis across discount rate, tariff, battery cost, efficiency and rooftop area found the battery preferable only at much lower cost or with a larger roof.

**Shorter version if space is tight.** Modelled rooftop PV and battery dispatch for a Mumbai office with an hourly linear program (Pyomo/HiGHS) and 20-year lifecycle finance; findings are conditional on synthetic load and unverified tariff inputs.

**Do not claim.** That the results are validated or publication-ready. That the battery is uneconomic in India in general (the result applies to these inputs). That the model matches measured building consumption. Windows execution was not independently tested.

## 8. Questions an interviewer may press on

- **"Is the battery conclusion robust?"** Not fully. It holds across every sensitivity I ran at base battery cost, but it depends on the synthetic load and the unsourced battery cost. The conclusion that matters most is the boundary: how cheap the battery must become. That boundary is the real output.
- **"Why trust a model with placeholder inputs?"** I don't treat it as a forecast. It is a tool for showing which inputs decide the answer, and where the decision flips. Those are the inputs to measure first.
- **"What would you change if you had a week more?"** Obtain a measured load for a Mumbai office and the official tariff, since those two decide the answer.
- **"Is there anything you got wrong and fixed?"** Yes. The early tariff peak window was wrong and I corrected it against the official order. I also found the NASA hour convention and moved the sun position to the hour midpoint, which removed a small error at dawn and dusk. I also corrected a battery-cost attribution that I could not verify.
