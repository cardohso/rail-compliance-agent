"""The compliance agent: a LangGraph loop in which the model chooses the tools.

    plan --> begin --> agent <--> tools --> settle --+--> begin (next parameter)
              ^                                      |
              +--------------------------------------+--> END

`plan` is code: parameters the spec does not supply are `needs_human` without a search. For each
other parameter the model runs a short tool loop (search_regulation, extract_requirement, check,
needs_human). The model never handles numbers it could mis-copy: the runtime resolves passage
text and spec values itself, and rejects a `check` call whose `spec_value` differs from the spec
(the rejection is recorded, so the evaluation can score argument correctness). The parameter's
verdict is then computed by code from the checks that ran, never written by the model.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError

from rail_compliance.llm import AgentLLM
from rail_compliance.models import (
    CheckResult,
    Citation,
    HumanReason,
    HumanReview,
    Passage,
    Requirement,
)
from rail_compliance.parameters import CHECKED_PARAMETERS
from rail_compliance.report import (
    ParameterResult,
    Report,
    Stats,
    ToolCall,
    describe_rule,
)
from rail_compliance.retry import LLMUnavailable
from rail_compliance.spec import TrainSpec, parameter_info, spec_values, unit_of
from rail_compliance.tools.check import check as check_tool
from rail_compliance.tools.extract import StructuredLLM, StructuredOutputError
from rail_compliance.tools.extract import extract_requirement as extract_tool
from rail_compliance.tools.needs_human import needs_human as needs_human_tool
from rail_compliance.tools.search import SearchBackend, SearchError
from rail_compliance.tools.search import search_regulation as search_tool

SYSTEM_PROMPT = """\
You check one parameter of a train design spec against the EU PRM TSI (Regulation (EU) No
1300/2014, accessibility; for trains, point 4.2.2). You work through tools and you never decide a
verdict yourself.

Procedure:
1. search_regulation(question): find passages of the regulation. Ask a specific question about the
   parameter. If the passages do not contain the rule, search again with a different question.
2. extract_requirement(passage_ids, parameter, focus): get the numeric rule as a typed
   requirement. A parameter can have more than one rule (a general minimum, and a stricter one for
   some cases such as a speed or a door type). Extract each rule that could apply, one call per
   rule, using `focus` to say which rule you want.
3. check(parameter, spec_value, requirement_id): compare the spec with a requirement. Pass the
   spec value exactly as given. A result of not_applicable means that rule's conditions are false
   for this spec: that is not a failure, so look for the other rule that applies.
4. needs_human(reason, category): call this, and then stop, when the law is ambiguous or has an
   exception you cannot evaluate from the spec (ambiguous_law), when the rule depends on data the
   spec does not supply (missing_data), or when extraction fails, the citation is weak or the rule
   sits in an external standard (weak_citation).
When every rule that applies has been checked, reply with one short sentence and no tool call.
Never use a number from memory: only rules returned by extract_requirement count.
"""


# --- the tools as the model sees them ------------------------------------------------------


class SearchArgs(BaseModel):
    question: str = Field(description="A specific question about the regulation.")


class ExtractArgs(BaseModel):
    passage_ids: list[str] = Field(description="Ids of passages returned by search_regulation.")
    parameter: str = Field(description="The spec parameter being checked.")
    focus: str | None = Field(
        default=None, description="Which rule to extract, if the parameter has several."
    )


class CheckArgs(BaseModel):
    parameter: str = Field(description="The spec parameter being checked.")
    spec_value: float = Field(description="The spec's value for it, exactly as given.")
    requirement_id: str = Field(description="Id returned by extract_requirement, e.g. R1.")


class NeedsHumanArgs(BaseModel):
    reason: str = Field(description="What a person must decide, and why.")
    category: HumanReason = Field(description="ambiguous_law, missing_data, weak_citation, other")


TOOL_ARGS: dict[str, type[BaseModel]] = {
    "search_regulation": SearchArgs,
    "extract_requirement": ExtractArgs,
    "check": CheckArgs,
    "needs_human": NeedsHumanArgs,
}
TOOL_DESCRIPTIONS = {
    "search_regulation": "Search the EU rail regulation for passages that answer a question.",
    "extract_requirement": "Extract the numeric rule for a parameter from passages, as a typed "
    "requirement with its citation. Returns a requirement id, or why no rule was found.",
    "check": "Compare the spec value with an extracted requirement. Deterministic.",
    "needs_human": "Escalate to a person instead of guessing. Ends work on this parameter.",
}


def tool_definitions() -> list[StructuredTool]:
    """Schemas to bind to the chat model. The runtime executes calls itself (see `_Runner`)."""
    return [
        StructuredTool.from_function(
            func=lambda **_: "",
            name=name,
            description=TOOL_DESCRIPTIONS[name],
            args_schema=schema,
        )
        for name, schema in TOOL_ARGS.items()
    ]


# --- per-parameter working state ------------------------------------------------------------


@dataclass
class Scratch:
    parameter: str
    passages: dict[str, Passage] = field(default_factory=dict)
    requirements: dict[str, Requirement] = field(default_factory=dict)
    checks: list[tuple[CheckResult, Requirement]] = field(default_factory=list)
    reviews: list[HumanReview] = field(default_factory=list)
    calls: int = 0
    done: bool = False  # needs_human was called, or the budget ran out


class AgentState(TypedDict, total=False):
    values: dict[str, float]
    queue: list[str]
    idx: int
    messages: list[BaseMessage]
    scratch: Scratch
    results: Annotated[list[ParameterResult], lambda a, b: a + b]
    trace: Annotated[list[ToolCall], lambda a, b: a + b]
    llm_calls: int


def _passages_text(passages: list[Passage]) -> str:
    return "\n\n".join(
        f"[{p.id}] {p.document}, {p.section} (score {p.score:.2f})\n{p.text}" for p in passages
    )


class _Runner:
    """Executes the model's tool calls against the real tools and the spec."""

    def __init__(self, search: SearchBackend, extractor: StructuredLLM, k: int):
        self.search, self.extractor, self.k = search, extractor, k

    def run(
        self, name: str, args: dict, scratch: Scratch, values: dict[str, float]
    ) -> tuple[bool, str]:
        """Return (ok, text for the model). ok is False when the call was rejected."""
        schema = TOOL_ARGS.get(name)
        if schema is None:
            return False, f"unknown tool '{name}'. Tools: {', '.join(TOOL_ARGS)}"
        try:
            parsed = schema.model_validate(args)
        except ValidationError as exc:
            first = exc.errors()[0]
            return False, f"invalid arguments for {name}: {first['msg']} ({first['loc']})"
        return getattr(self, f"_{name}")(parsed, scratch, values)

    def _search_regulation(self, a: SearchArgs, scratch: Scratch, values) -> tuple[bool, str]:
        try:
            result = search_tool(a.question, self.search, self.k)
        except (ValueError, SearchError) as exc:
            return False, f"search failed: {exc}"
        for p in result.passages:
            scratch.passages[p.id] = p
        text = f"{len(result.passages)} passages:\n\n{_passages_text(result.passages)}"
        if result.answer:
            text += f"\n\nThe assistant's own answer (unverified): {result.answer}"
        if result.refused:
            text += "\n\nThe assistant declined to answer: it found nothing relevant."
        return True, text if result.passages else "no passages found. Try a different question."

    def _extract_requirement(self, a: ExtractArgs, scratch: Scratch, values) -> tuple[bool, str]:
        if a.parameter != scratch.parameter:
            return False, f"you are checking {scratch.parameter}, not {a.parameter}"
        if not scratch.passages:
            return False, "no passages yet: call search_regulation first"
        unknown = [i for i in a.passage_ids if i not in scratch.passages]
        if unknown or not a.passage_ids:
            return False, (
                f"unknown passage ids {unknown}. Known ids: {list(scratch.passages)}"
                if unknown
                else "give at least one passage id"
            )
        try:
            result = extract_tool(
                [scratch.passages[i] for i in a.passage_ids], a.parameter, self.extractor, a.focus
            )
        except (ValidationError, StructuredOutputError) as exc:
            return False, f"the extraction model returned an unusable answer: {str(exc)[:300]}"
        if result.status != "found":
            return True, f"{result.status}: {result.reason}"
        req = result.requirement
        rid = f"R{len(scratch.requirements) + 1}"
        scratch.requirements[rid] = req
        rule = (
            f"{len(req.bands)}-row table selected by {req.band_variable}"
            if req.bands
            else describe_rule(req.comparator, req.value, req.unit)
        )
        when = "; ".join(f"{c.variable} {c.op} {c.value:g}" for c in req.conditions) or "always"
        return True, (
            f"found {rid} for {req.parameter}: spec value {rule}. Applies: {when}. "
            f'Source [{req.citation.passage_id}]: "{req.citation.quote}"'
        )

    def _check(self, a: CheckArgs, scratch: Scratch, values) -> tuple[bool, str]:
        req = scratch.requirements.get(a.requirement_id)
        if req is None:
            return (
                False,
                f"unknown requirement id {a.requirement_id}. Known: {list(scratch.requirements)}",
            )
        if a.parameter != scratch.parameter or a.parameter != req.parameter:
            return (
                False,
                f"you are checking {scratch.parameter}; {a.requirement_id} is for {req.parameter}",
            )
        actual = values[scratch.parameter]
        if abs(a.spec_value - actual) > 1e-9:
            unit = unit_of(scratch.parameter) or ""
            return False, (
                f"spec_value {a.spec_value:g} does not match the spec, which has {actual:g} {unit}."
                " Pass the spec's value unchanged."
            )
        result = check_tool(actual, req, spec_unit=unit_of(scratch.parameter), context=values)
        scratch.checks.append((result, req))
        return True, f"{result.verdict}: {result.reason}"

    def _needs_human(self, a: NeedsHumanArgs, scratch: Scratch, values) -> tuple[bool, str]:
        try:
            review = needs_human_tool(a.reason, scratch.parameter, a.category)
        except ValueError as exc:
            return False, str(exc)
        scratch.reviews.append(review)
        scratch.done = True
        return True, "recorded. Work on this parameter ends here."


def _task_message(parameter: str, values: dict[str, float]) -> str:
    info = parameter_info()
    unit, description = info[parameter]
    supplied = {k: v for k, v in values.items() if k != parameter}
    missing = [k for k in info if k not in values]
    lines = [
        f"Parameter to check: {parameter}" + (f" ({unit})" if unit else ""),
        f"Meaning: {description}",
        f"Spec value: {values[parameter]:g}" + (f" {unit}" if unit else ""),
        "",
        "Other values the spec supplies (booleans as 1/0; the runtime applies them automatically "
        "to rules with conditions or tables): "
        + (", ".join(f"{k}={v:g}" for k, v in supplied.items()) or "none"),
        "Not supplied: " + (", ".join(m for m in missing if m != parameter) or "nothing"),
    ]
    return "\n".join(lines)


def _settle(scratch: Scratch, values: dict[str, float]) -> ParameterResult:
    """The parameter's verdict, computed from the checks that ran: fail beats needs_human beats
    pass; if every rule was not_applicable the parameter is too."""
    parameter = scratch.parameter
    checks = [c for c, _ in scratch.checks]
    reviews = list(scratch.reviews)
    by = {v: [c for c in checks if c.verdict == v] for v in ("fail", "needs_human", "pass")}

    if by["fail"]:
        verdict, reason = "fail", "; ".join(c.reason for c in by["fail"])
    elif reviews or by["needs_human"]:
        verdict = "needs_human"
        reason = "; ".join([r.reason for r in reviews] + [c.reason for c in by["needs_human"]])
    elif by["pass"]:
        verdict, reason = "pass", "; ".join(c.reason for c in by["pass"])
    elif checks:
        verdict, reason = "not_applicable", "; ".join(c.reason for c in checks)
    else:
        verdict = "needs_human"
        reason = "the agent finished without checking a rule or escalating"
        reviews.append(HumanReview(parameter=parameter, category="other", reason=reason))

    rules = [
        describe_rule(c.comparator, c.required_value, c.unit)
        for c in checks
        if c.verdict in ("pass", "fail")
    ]
    citations: list[Citation] = []
    for _, req in scratch.checks:
        if req.citation not in citations:
            citations.append(req.citation)
    return ParameterResult(
        parameter=parameter,
        verdict=verdict,
        spec_value=values[parameter],
        unit=unit_of(parameter),
        requirement="; ".join(dict.fromkeys(rules)) or None,
        reason=reason,
        checks=checks,
        reviews=reviews,
        citations=citations,
        consulted=list(scratch.passages),
    )


class ComplianceAgent:
    def __init__(
        self,
        llm: AgentLLM,
        extractor: StructuredLLM,
        search: SearchBackend,
        *,
        k: int = 8,
        max_calls: int = 10,
        clock: Callable[[], float] = time.perf_counter,
    ):
        self.llm, self.search, self.max_calls, self.clock = llm, search, max_calls, clock
        self.runner = _Runner(search, extractor, k)
        self.graph = self._build()

    # --- graph ---

    def _build(self):
        def plan(state: AgentState) -> AgentState:
            values, queue, results, trace = state["values"], [], [], []
            for parameter in CHECKED_PARAMETERS:
                if parameter in values:
                    queue.append(parameter)
                    continue
                reason = f"the spec does not supply {parameter}"
                review = HumanReview(parameter=parameter, category="missing_data", reason=reason)
                results.append(
                    ParameterResult(
                        parameter=parameter, verdict="needs_human", reason=reason, reviews=[review]
                    )
                )
                trace.append(
                    ToolCall(
                        index=-1, parameter=parameter, name="needs_human",
                        args={"reason": reason, "category": "missing_data"},
                        ok=True, summary="decided by the runtime: parameter not supplied",
                        seconds=0.0, source="runtime",
                    )
                )  # fmt: skip
            return {"queue": queue, "idx": 0, "results": results, "trace": trace, "llm_calls": 0}

        def begin(state: AgentState) -> AgentState:
            parameter = state["queue"][state["idx"]]
            messages = [
                SystemMessage(SYSTEM_PROMPT),
                HumanMessage(_task_message(parameter, state["values"])),
            ]
            return {"messages": messages, "scratch": Scratch(parameter)}

        def agent(state: AgentState) -> AgentState:
            reply = self.llm.invoke(state["messages"])
            return {"messages": state["messages"] + [reply], "llm_calls": state["llm_calls"] + 1}

        def tools(state: AgentState) -> AgentState:
            last: AIMessage = state["messages"][-1]
            scratch, values = state["scratch"], state["values"]
            out: list[BaseMessage] = []
            calls: list[ToolCall] = []
            for call in last.tool_calls:
                started = self.clock()
                ok, text = self.runner.run(call["name"], call["args"], scratch, values)
                scratch.calls += 1
                out.append(ToolMessage(content=text, tool_call_id=call["id"], name=call["name"]))
                calls.append(
                    ToolCall(
                        index=-1, parameter=scratch.parameter, name=call["name"],
                        args=call["args"], ok=ok, summary=text[:300],
                        seconds=round(self.clock() - started, 4),
                    )
                )  # fmt: skip
            if scratch.calls >= self.max_calls and not scratch.done:
                reason = f"the tool-call budget of {self.max_calls} was used up before a verdict"
                scratch.reviews.append(
                    HumanReview(parameter=scratch.parameter, category="other", reason=reason)
                )
                scratch.done = True
            return {"messages": state["messages"] + out, "trace": calls}

        def settle(state: AgentState) -> AgentState:
            result = _settle(state["scratch"], state["values"])
            return {"results": [result], "idx": state["idx"] + 1}

        def after_plan(state: AgentState) -> str:
            return "begin" if state["queue"] else "end"

        def after_agent(state: AgentState) -> str:
            return "tools" if state["messages"][-1].tool_calls else "settle"

        def after_tools(state: AgentState) -> str:
            return "settle" if state["scratch"].done else "agent"

        def after_settle(state: AgentState) -> str:
            return "begin" if state["idx"] < len(state["queue"]) else "end"

        g = StateGraph(AgentState)
        for name, fn in [
            ("plan", plan),
            ("begin", begin),
            ("agent", agent),
            ("tools", tools),
            ("settle", settle),
        ]:
            g.add_node(name, fn)
        g.add_edge(START, "plan")
        g.add_conditional_edges("plan", after_plan, {"begin": "begin", "end": END})
        g.add_edge("begin", "agent")
        g.add_conditional_edges("agent", after_agent, {"tools": "tools", "settle": "settle"})
        g.add_conditional_edges("tools", after_tools, {"agent": "agent", "settle": "settle"})
        g.add_conditional_edges("settle", after_settle, {"begin": "begin", "end": END})
        return g.compile()

    # --- run ---

    def run(self, spec: TrainSpec) -> Report:
        started = self.clock()
        values = spec_values(spec)
        try:
            final: dict[str, Any] = self.graph.invoke(
                {"values": values}, config={"recursion_limit": 1000}
            )
        except LLMUnavailable:
            raise
        order = {p: i for i, p in enumerate(CHECKED_PARAMETERS)}
        results = sorted(final.get("results", []), key=lambda r: order[r.parameter])
        trace = [t.model_copy(update={"index": i}) for i, t in enumerate(final.get("trace", []))]
        return Report(
            spec_name=spec.name,
            spec=spec.model_dump(mode="json", exclude_none=True),
            results=results,
            trace=trace,
            stats=Stats(
                tool_calls=sum(1 for t in trace if t.source == "agent"),
                llm_calls=final.get("llm_calls", 0),
                seconds=round(self.clock() - started, 3),
                agent_model=self.llm.name,
                search_backend=self.search.name,
            ),
        )
