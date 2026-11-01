# Learning Guide: The Concepts Behind the Project

This guide explains each idea in the project from first principles, using the project's own numbers as examples. Read it before INTERVIEW_PREPARATION.md. The aim is that you can explain every equation without looking at the code.

---

## 1. Irradiance: how much sunlight arrives

**Irradiance** is the power of sunlight per square metre, measured in W/m². Energy is irradiance summed over time, measured in Wh/m² or kWh/m².

- **GHI (global horizontal irradiance)** is the total sunlight on a flat surface. It has two parts:
  - **DNI** (direct normal): the beam from the sun, measured on a surface facing it.
  - **DHI** (diffuse horizontal): light scattered by the sky and clouds.
- GHI = DHI + DNI × cos(zenith angle).

The **zenith angle** is the angle between the sun and straight overhead. Zenith 0° means the sun is directly overhead; 90° means it is on the horizon. Sunlight is weakest when the zenith is large, because the same beam is spread over more ground.

**Project example.** The NASA file gives 1,763 kWh/m² of GHI for Mumbai in 2025. The monsoon months give about 107–132 kWh/m² per month, against about 200 kWh/m² in March–April.

**Why this matters.** Solar output depends on irradiance at the panel, not on the horizontal surface. So the model must convert GHI into what falls on the tilted panel.

## 2. Plane-of-array irradiance and angle of incidence

A tilted panel receives sunlight at an angle. Two quantities matter:

- **Angle of incidence (AOI)**: the angle between the sun and the panel's normal (the line perpendicular to its surface). Beam power on the panel is proportional to cos(AOI). AOI 0° means the sun hits the panel head-on.
- **Plane-of-array (POA) irradiance**: the total irradiance on the tilted surface. It is the beam part times cos(AOI), plus the diffuse part (adjusted for the tilt), plus ground reflection.

For a south-facing panel tilted at angle β with sun zenith Z, the AOI at solar noon is |Z − β|. You can check this in the project: in December at Mumbai's latitude the noon zenith is about 42.5°, so with a 15° tilt the AOI is about 27.5°.

**Erbs decomposition.** NASA gives only GHI. To get DNI and DHI we use the Erbs model, which estimates the diffuse fraction from the clearness index (the ratio of GHI to the extraterrestrial irradiance). This is a standard empirical method, not a measurement.

**Project example.** The POA irradiance is about 210 W/m² on average across the year, which is higher than the mean GHI because the tilted panel receives more beam light than a flat surface at this latitude.

## 3. From irradiance to electricity

PV power is roughly proportional to POA irradiance:

$$
P_{\mathrm{DC}} = P_{\mathrm{rated}} \cdot \frac{G_{\mathrm{POA}}}{1000\ \mathrm{W/m^2}} \cdot \big[1 + \gamma\,(T_{\mathrm{cell}} - 25^\circ\mathrm{C})\big]
$$

- **P_rated** is the nameplate capacity, in kWp. It is the output at 1,000 W/m² and 25 °C cell temperature.
- **γ** is the temperature coefficient of power, about −0.35%/°C for crystalline silicon. Hot panels produce less.
- **T_cell** is the cell temperature. A simple estimate is ambient temperature plus about 20 °C × (POA/800 W/m²).

Then AC output is DC output times (1 − losses). The model uses 14% losses for wiring, inverter, soiling, and mismatch. This is a planning value, not a measured one.

**Energy per kWp.** Annual energy divided by capacity gives the specific yield. The project gives about 1,460 kWh/kWp per year. A rough sanity check, which is my own heuristic and not a sourced benchmark: 1,763 kWh/m² of GHI, adjusted for the POA gain and for temperature and losses, should give a yield of order 1,300–1,600 kWh/kWp. The model's 1,460 kWh/kWp falls inside that band, but that is a consistency check, not validation.

## 4. The battery state-of-charge equation

A battery stores energy. Its **state of charge (SOC)** is the energy currently stored, in kWh. Over one hour:

$$
s_{t+1} = s_t + \eta\, c_t - \frac{d_t}{\eta}
$$

- c_t is energy put in (charging), measured on the AC side.
- d_t is energy taken out (discharging), on the AC side.
- η is the one-way efficiency. If the round-trip efficiency is 90%, then η = √0.90 ≈ 0.949. Energy is lost on the way in and on the way out.

**Why the split efficiency.** The round-trip efficiency is the fraction of energy you get back after one full charge and discharge. Splitting it as η on charge and 1/η on discharge gives the same loss overall, but keeps the equation linear.

**Bounds.** The SOC must stay between a minimum and a maximum, here 10% and 95% of the battery energy E:

$$
s_{\min} E \le s_t \le s_{\max} E
$$

These limits protect the battery, and they are linear in E, so the optimization stays linear.

**Power limit.** Charge and discharge are limited to a power P. The model fixes P = 0.5 × E, meaning a full battery can empty in 2 hours. This is a "C-rate" of 0.5.

**Cyclic condition.** The battery must end the year where it started, so s_0 = s_T. Without this, the optimizer could drain the battery in the final hour and count the energy for free.

## 5. Linear programming in one page

A **linear program (LP)** minimizes a linear objective subject to linear equalities and inequalities:

$$
\min\; c^\top x \quad \text{subject to}\quad A x \le b,\ \ x \ge 0
$$

**Why it matters here.** Every term in the model is a constant times a variable: cost is a rate times grid energy, the PV output is a constant profile times the capacity, and the SOC equation is linear. So the whole problem is an LP, which a solver can find the global optimum of in seconds. This is why the model does not need heuristics.

**What a "decision variable" is.** A quantity the optimizer chooses: the PV capacity x, the battery energy E, and 8,760 hourly values each of grid import, PV used, charge, discharge, and SOC. That is about 44,000 variables and about 61,000 constraints in the full model (the battery constraints are counted hourly, so the total scales with the 8,760 hours).

**Why no binaries.** Some battery models use binary (yes/no) variables to stop charging and discharging in the same hour. We don't need them: with losses, doing both at once wastes energy and can never reduce cost, so the optimum never does it. We check this after solving.

**Solver status.** A solver reports "optimal" when it has proven the solution is the best possible within tolerance. Any other status means no trustworthy answer, and the project treats it as a failure rather than hiding it.

## 6. Economic dispatch

**Dispatch** means deciding, hour by hour, where each unit of electricity comes from. With PV and a battery, each hour has several choices:

- Use PV directly for the load.
- Send surplus PV into the battery (store it).
- Draw from the grid.
- Discharge the battery to the load.

The **merit order** is to use the cheapest source first. Each hour's grid price depends on the ToD window. The optimizer chooses the schedule that minimizes total cost over the year, subject to the energy balance and the battery limits.

**Energy balance.** In every hour:

$$
g_t + u_t + d_t = L_t + c_t
$$

Supply (grid + PV used + battery discharge) must equal demand (load + battery charge). There is no export, so supply cannot exceed demand by feeding into the grid, and surplus PV must be curtailed.

**Project example.** With PV only, midday PV is used directly and the grid supplies the rest. With no battery, the optimizer has no way to move energy in time, so it can only use PV when it is produced.

## 7. The tariff: why timing matters

Maharashtra's commercial tariff varies by hour:

- **Peak, 17:00–24:00**: the base rate plus a 25% surcharge.
- **Solar hours, 09:00–17:00**: the base rate less a rebate, 15% from April to September and 25% from October to March.
- **Other hours**: the base rate.

A **spread** is the difference between two prices. A battery earns money from the spread between the price it pays to charge and the price it avoids paying when it discharges, after losses:

$$
\text{value per kWh shifted} \approx \eta^2 \cdot p_{\mathrm{peak}} - p_{\mathrm{charge}}
$$

**Project example.** With a base rate of ₹12.16/kWh, a midday rebated price is about ₹9.12 in winter, and the peak price is ₹15.20. Charging at ₹9.12 and discharging at ₹15.20 with 90% round-trip efficiency gives about ₹13.7 per kWh returned, a margin of about ₹4.6 per kWh shifted. That margin must pay for the battery's annualized capital and O&M. At ₹15,000/kWh it does not, which is why the optimum battery is zero.

## 8. Lifecycle cost and annualization

A capital cost is spent once, but its benefits and replacements run for years. To compare options, we convert everything to a common basis.

**Present value** converts a future cash flow to today's value:

$$
\mathrm{PV} = \frac{F}{(1+r)^t}
$$

where r is the discount rate and t the year. A rupee in year 10 is worth less than a rupee today.

**Capital recovery factor (CRF)** converts a present value into a level annual payment over N years:

$$
\mathrm{CRF}_N = \frac{r(1+r)^N}{(1+r)^N - 1}
$$

**Annualized cost** = present value × CRF. The optimizer minimizes annualized cost, which is the same as minimizing present value, but expressed per year so it compares directly with the annual grid bill.

**Replacements.** A battery with a 10-year life bought at year 0 must be replaced at year 10 to last the 20-year horizon. Its replacement cost is discounted by 1/(1+r)^10, so it is worth less than the first purchase.

**Salvage.** A PV system with a 25-year life still has 5 years left at year 20. Its remaining value is credited, pro-rated by remaining life and discounted back from year 20. Without salvage, the model would penalize PV for life it still has.

**Double counting.** The initial purchase is counted once, at time zero. Replacements count only at their own year. Salvage is a credit, not a second purchase.

## 9. Net present value and payback

**NPV** is the sum of all discounted cash flows, with the initial investment as a negative flow:

$$
\mathrm{NPV} = -I_0 + \sum_{t=1}^{N} \frac{CF_t}{(1+r)^t}
$$

Here the project's cash flow is the grid bill saved each year, minus O&M, with replacements and salvage included. NPV is measured relative to grid-only, so grid-only has NPV zero.

**Simple payback** is the years until undiscounted cumulative cash flow turns positive:

$$
\text{simple payback} \approx \frac{I_0}{\text{net annual savings}}
$$

**Discounted payback** uses discounted cash flows, so it is always longer than simple payback at a positive discount rate.

**Project example.** Initial PV capex is ₹15.91 lakh. Net annual savings after O&M are about ₹4.90 lakh. Simple payback is 15.91 ÷ 4.90 ≈ 3.25 years, matching the model. Discounted payback at 10% is about 4.12 years.

**Not achieved.** If cumulative cash flow never turns positive within the horizon, the honest answer is "no payback within the project life". The project reports this rather than extending the horizon.

## 10. Sensitivity analysis

A **sensitivity analysis** asks how the answer changes when an uncertain input changes. Here each input is varied across a range, and the whole model is re-solved each time.

**Why re-optimize.** If you only recalculated cost with the old capacities, you would miss the main effect: a cheaper battery might be worth building, and a higher tariff might change the best PV size. The project re-solves every case from scratch, so the answers reflect the best design for each condition.

**Two-dimensional sensitivity.** Varying two inputs together (here battery cost and tariff) shows where a decision flips. The boundary between "battery preferable" and "battery not preferable" is the most useful output for a decision-maker.

**What a sensitivity cannot show.** It shows how sensitive an answer is to the inputs you varied. It cannot reveal an error in inputs you did not vary, such as a wrong load profile. That is why the uncertainties in the README matter.

## 11. Interpreting results

Four questions to ask of any result:

1. **Where does the number come from?** Check the status in ASSUMPTIONS_AND_SOURCES.md. A number built on a placeholder is a sensitivity case, not a fact.
2. **Does it respond to the inputs it should?** The battery size falls as its cost rises. The PV size is capped by the roof. Test these before trusting the model.
3. **Is it internally consistent?** The lifecycle cost times CRF equals the optimizer's annual cost. The energy balance closes every hour. These are tested.
4. **What would change the answer?** The battery result depends on the load shape and the battery cost. Know which inputs are weakest.

**A common mistake.** Reporting a payback as if it were certain. A payback of 3.25 years depends on the tariff and the O&M assumptions. Quote it with its conditions.

## 12. Glossary

- **AOI**: angle of incidence, between the sun and the panel's normal.
- **C-rate**: power divided by energy capacity. 0.5 C means a 2-hour battery.
- **CRF**: capital recovery factor.
- **DHI / DNI / GHI**: diffuse, direct-normal, and global horizontal irradiance.
- **Discounted payback**: years until cumulative discounted cash flow turns positive.
- **LP**: linear program.
- **NPV**: net present value.
- **POA**: plane-of-array irradiance on the tilted panel.
- **Salvage**: residual value of an asset at the end of the horizon.
- **SOC**: state of charge.
- **Spread**: difference between a buy price and a sell price.
- **ToD**: time of day.
- **Zenith angle**: angle between the sun and the vertical.
