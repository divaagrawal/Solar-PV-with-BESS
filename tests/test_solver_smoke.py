"""Smoke test: confirms the Pyomo + HiGHS toolchain solves a tiny LP."""
import pyomo.environ as pyo


def test_highs_solves_small_lp():
    m = pyo.ConcreteModel()
    m.x = pyo.Var(domain=pyo.NonNegativeReals)
    m.y = pyo.Var(domain=pyo.NonNegativeReals)
    m.c = pyo.Constraint(expr=m.x + 2 * m.y >= 4)
    m.obj = pyo.Objective(expr=3 * m.x + 5 * m.y, sense=pyo.minimize)
    res = pyo.SolverFactory("highs").solve(m)
    assert res.solver.termination_condition == pyo.TerminationCondition.optimal
    assert abs(pyo.value(m.obj) - 10.0) < 1e-6  # optimum at x=0, y=2
