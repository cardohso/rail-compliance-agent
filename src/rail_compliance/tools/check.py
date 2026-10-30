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


Intervals = Mapping[str, tuple[float, float]]
Context = Mapping[str, float | str]  # numbers, flags as 1/0, categories by name


def _interval_state(op: str, threshold: float, lo: float, hi: float) -> bool | None:
    """Does `x op threshold` hold for every x in [lo, hi] (True), for none (False), or for some?"""
    if op == "==":
        if lo == hi:
            return lo == threshold
        return False if (threshold < lo or threshold > hi) else None
    at_lo, at_hi = OPS[op](lo, threshold), OPS[op](hi, threshold)
    return at_lo if at_lo == at_hi else None  # <, <=, >, >= are monotone in x


def _condition_state(cond: Condition, context: Context, intervals: Intervals) -> bool | None:
    """True/False if the condition can be decided, None if its variable is missing or only known
    to lie in an interval that straddles the threshold."""
    if isinstance(cond.value, str):
        return context[cond.variable] == cond.value if cond.variable in context else None
    if cond.variable in intervals:
        return _interval_state(cond.op, cond.value, *intervals[cond.variable])
    if cond.variable not in context:
        return None
    return OPS[cond.op](context[cond.variable], cond.value)


def _decide_over_interval(
    compared: float, comparator: str, requirements: list[float]
) -> tuple[str, float]:
    """Verdict when the required value could be any of `requirements`: pass if the spec value
    meets all of them, fail if none, needs_human if some. Also the requirement to show."""
    outcomes = {OPS[comparator](compared, r) for r in requirements}
    strictest = max(requirements) if comparator in (">=", ">") else min(requirements)
    lenient = min(requirements) if comparator in (">=", ">") else max(requirements)
    if outcomes == {True}:
        return "pass", strictest
    if outcomes == {False}:
        return "fail", lenient
    return "needs_human", strictest


def _describe(cond: Condition) -> str:
    return cond.describe()


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
    context: Context | None = None,
    intervals: Intervals | None = None,
) -> CheckResult:
    """Compare `spec_value` with `requirement`.

    `context` holds the other spec parameters (dotted path -> number, booleans as 1/0, a
    category as its name) that
    conditions and tables refer to; a parameter missing from it is data the spec did not supply.
    `intervals` names parameters whose true value is only known to lie in [low, high] (a length
    that includes a power head is at most the stated one): conditions and tables on them are
    decided over the whole interval, and a verdict that would differ inside it is needs_human.
    """
    context, intervals = context or {}, intervals or {}
    param, cmp_ = requirement.parameter, requirement.comparator

    applies: bool | None = True

    def result(verdict, reason, required=None, margin=None):
        return CheckResult(
            relaxes=requirement.relaxes,
            exempts=cmp_ == "exempt",
            applies=applies,
            parameter=param,
            verdict=verdict,
            reason=reason,
            spec_value=spec_value,
            required_value=required,
            required_max=requirement.value_max,
            comparator=cmp_,
            unit=requirement.unit,
            margin=margin,
            contingency=requirement.contingency,
        )

    states = [(c, _condition_state(c, context, intervals)) for c in requirement.conditions]
    failed = [c for c, ok in states if ok is False]
    if failed:
        applies = False
        return result("not_applicable", f"rule applies only when {_describe(failed[0])}")
    unknown = [c for c, ok in states if ok is None]
    if cmp_ == "exempt":
        where = " and ".join(_describe(c) for c, _ in states)
        if unknown:
            applies = None
            names = ", ".join(c.variable for c in unknown)
            return result("needs_human", f"whether the exemption ({where}) holds depends on "
                          f"{names}, not supplied")  # fmt: skip
        return result("not_applicable", f"compliance is not mandatory: exempt where {where}")
    if unknown:
        applies = None
        missing = [c.variable for c in unknown if c.variable not in intervals]
        ranged = [c.variable for c in unknown if c.variable in intervals]
        why = "; ".join(
            ([f"{', '.join(missing)} not supplied"] if missing else [])
            + ([f"{', '.join(ranged)} only known within a range"] if ranged else [])
        )
        # Judge the value as if the rule applied. If it passes, the outcome does not depend on the
        # unknown: the rule is met if it applies and irrelevant if it does not.
        if_applies = check(
            spec_value,
            requirement.model_copy(update={"conditions": []}),
            spec_unit=spec_unit,
            context=context,
            intervals=intervals,
        )
        if if_applies.verdict == "pass":
            return result(
                "pass",
                f"{if_applies.reason}; whether the rule applies is unknown ({why}), "
                "but the value meets it either way",
                if_applies.required_value,
                if_applies.margin,
            )
        return result("needs_human", f"whether the rule applies depends on {why}")

    if spec_value is None:
        return result("needs_human", f"the spec does not supply {param}")

    compared = spec_value
    if spec_unit and requirement.unit and spec_unit != requirement.unit:
        compared = _unit_to(spec_value, spec_unit, requirement.unit)
        if compared is None:
            return result(
                "needs_human",
                f"cannot compare unit '{spec_unit}' with the requirement's unit "
                f"'{requirement.unit}'",
            )

    if cmp_ == "between":
        lo, hi = requirement.value, requirement.value_max
        ok = lo <= compared <= hi
        # signed distance to the nearer bound: positive inside the range, negative outside
        margin = float(min(Decimal(str(compared)) - Decimal(str(lo)),
                           Decimal(str(hi)) - Decimal(str(compared))))  # fmt: skip
        shown = f"{_fmt(lo)}-{_fmt(hi, requirement.unit)}"
        sign = "is within" if ok else "is outside"
        return result("pass" if ok else "fail", f"{_fmt(compared, requirement.unit)} {sign} "
                      f"{shown}", lo, margin)  # fmt: skip

    if requirement.bands:
        selector = requirement.band_variable
        if selector in intervals:
            lo, hi = intervals[selector]
            rows = [b.value for b in requirement.bands if b.intersects(lo, hi)]
            if not rows:
                return result(
                    "needs_human", f"no band of the table covers {selector} in {lo:g}-{hi:g}"
                )
            verdict, required = _decide_over_interval(compared, cmp_, rows)
            options = ", ".join(f"{r:g}" for r in sorted(set(rows)))
            if verdict == "needs_human":
                reason = (
                    f"{selector} is only known to be between {lo:g} and {hi:g}, so the requirement "
                    f"could be {options}: {_fmt(compared, requirement.unit)} meets some of these "
                    "and not others"
                )
                return result("needs_human", reason, required)
            sign = "meets" if verdict == "pass" else "violates"
            reason = (
                f"{_fmt(compared, requirement.unit)} {sign} {cmp_} {options} "
                f"for every {selector} between {lo:g} and {hi:g}"
            )
            margin = float(Decimal(str(compared)) - Decimal(str(required)))
            return result(verdict, reason, required, margin)
        if selector not in context:
            return result("needs_human", f"the rule depends on {selector}, not supplied")
        band, why = _select_band(requirement.bands, context[selector])
        if band is None:
            return result("needs_human", why)
        required = band.value
    else:
        required = requirement.value

    ok = OPS[cmp_](compared, required)
    margin = float(Decimal(str(compared)) - Decimal(str(required)))
    shown = _fmt(compared, requirement.unit)
    sign = "meets" if ok else "violates"
    reason = f"{shown} {sign} {cmp_} {_fmt(required, requirement.unit)}"
    return result("pass" if ok else "fail", reason, required, margin)
