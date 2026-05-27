import pulp
from typing import TypeAlias


Valued: TypeAlias = pulp.LpVariable | pulp.LpAffineExpression


def value_of(x: Valued) -> float:
    value = x.value()
    assert value is not None, "f{x} has no value - Is the problem solved?"
    return value
