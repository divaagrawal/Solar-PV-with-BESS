"""Lifecycle cost helpers used by the optimizer.

All costs are real and constant over the evaluation horizon. Energy tariffs are not
escalated. The horizon N is the project evaluation period (20 years by default).
"""


def crf(rate, years):
    """Capital recovery factor: converts a present value into a level annual payment."""
    if rate == 0:
        return 1.0 / years
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)


def present_cost_over_horizon(capex, life, horizon, rate):
    """Present value of an asset's capital cost over the horizon, including replacements.

    The asset is bought at t = 0 and again at each multiple of its life that falls before
    the horizon ends. Any remaining life at the horizon end is credited as salvage value,
    pro-rated linearly by remaining life. The salvage credit is discounted from year N.
    """
    if life <= 0 or horizon <= 0:
        raise ValueError("life and horizon must be positive")
    pv = 0.0
    k = 0
    while k * life < horizon:
        pv += capex / (1 + rate) ** (k * life)
        last_install = k * life
        k += 1
    end_of_last_life = last_install + life
    remaining_fraction = max(0.0, (end_of_last_life - horizon) / life)
    pv -= capex * remaining_fraction / (1 + rate) ** horizon
    return pv


def annualized_capex(capex, life, horizon, rate):
    """Annualized capital cost of one asset over the horizon."""
    return crf(rate, horizon) * present_cost_over_horizon(capex, life, horizon, rate)
