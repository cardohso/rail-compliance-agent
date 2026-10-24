"""`check`: compare a spec value with a requirement. Deterministic, no LLM, no network.

Order of decisions: (1) conditions, (2) is the spec value there, (3) which value applies (a
table lookup if the rule has bands), (4) units, (5) the comparison. Anything the data does not
settle ends in `needs_human` with the reason, never a guess.
"""

from __future__ import annotations

import operator
from collections.abc import Callable, Mapping
from decimal import Decimal

from rail_compliance.models import Band, CheckResult, Condition, Requirement

OPS: dict[str, Callable[[float, float], bool]] = {
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    ">": operator.gt,
    "<": operator.lt,
}
# Length units that can be converted into each other exactly (as strings, to stay in Decimal).
LENGTH_IN_METRES = {"mm": Decimal("0.001"), "m": Decimal(1), "km": Decimal(1000)}


def _fmt(x: float, unit: str | None = None) -> str:
    text = f"{x:g}"
    return f"{text} {unit}" if unit else text


def _unit_to(value: float, from_unit: str, to_unit: str) -> float | None:
    """Convert exactly between length units; None if they cannot be converted."""
    if from_unit == to_unit:
        return value
    if from_unit in LENGTH_IN_METRES and to_unit in LENGTH_IN_METRES:
        converted = Decimal(str(value)) * LENGTH_IN_METRES[from_unit] / LENGTH_IN_METRES[to_unit]
        return float(converted)
    return None


def _condition_state(cond: Condition, context: Mapping[str, float]) -> bool | None:
    """True/False if the condition can be decided, None if its variable is not in the context."""
    if cond.variable not in context:
        return None
    return OPS[cond.op](context[cond.variable], cond.value)


def _describe(cond: Condition) -> str:
    return f"{cond.variable} {cond.op} {cond.value:g}"


def _select_band(bands: list[Band], x: float) -> tuple[Band | None, str]:
    matching = [b for b in bands if b.contains(x)]
    if not matching:
        return None, f"no band of the table covers {x:g}"
    if len(matching) > 1:
        return None, f"{len(matching)} bands of the table cover {x:g}: the table is ambiguous"
    return matching[0], ""


def check(
    spec_value: float | None,
    requirement: Requirement,
    *,
    spec_unit: str | None = None,
    context: Mapping[str, float] | None = None,
) -> CheckResult:
    """Compare `spec_value` with `requirement`.

    `context` holds the other spec parameters (dotted path -> number, booleans as 1/0) that
    conditions and tables refer to; a parameter missing from it is data the spec did not supply.
    """
    context = context or {}
    param, cmp_ = requirement.parameter, requirement.comparator

    def result(verdict, reason, required=None, margin=None):
        return CheckResult(
            parameter=param,
            verdict=verdict,
            reason=reason,
            spec_value=spec_value,
            required_value=required,
            comparator=cmp_,
            unit=requirement.unit,
            margin=margin,
        )

    states = [(c, _condition_state(c, context)) for c in requirement.conditions]
    failed = [c for c, ok in states if ok is False]
    if failed:
        return result("not_applicable", f"rule applies only when {_describe(failed[0])}")
    unknown = [c for c, ok in states if ok is None]
    if unknown:
        names = ", ".join(c.variable for c in unknown)
        return result("needs_human", f"whether the rule applies depends on {names}, not supplied")

    if spec_value is None:
        return result("needs_human", f"the spec does not supply {param}")

    if requirement.bands:
        selector = requirement.band_variable
        if selector not in context:
            return result("needs_human", f"the rule depends on {selector}, not supplied")
        band, why = _select_band(requirement.bands, context[selector])
        if band is None:
            return result("needs_human", why)
        required = band.value
    else:
        required = requirement.value

    compared = spec_value
    if spec_unit and requirement.unit and spec_unit != requirement.unit:
        compared = _unit_to(spec_value, spec_unit, requirement.unit)
        if compared is None:
            return result(
                "needs_human",
                f"cannot compare unit '{spec_unit}' with the requirement's unit "
                f"'{requirement.unit}'",
                required,
            )

    ok = OPS[cmp_](compared, required)
    margin = float(Decimal(str(compared)) - Decimal(str(required)))
    shown = _fmt(compared, requirement.unit)
    sign = "meets" if ok else "violates"
    reason = f"{shown} {sign} {cmp_} {_fmt(required, requirement.unit)}"
    return result("pass" if ok else "fail", reason, required, margin)
