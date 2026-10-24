"""MCP server: the agent's four tools, for any MCP client.

    uv run python -m rail_compliance.mcp_server          # stdio, for Claude Desktop / Claude Code

The tools are the same functions the agent calls. `check` and `needs_human` are pure. The
server builds what the other two need only when they are first called, so listing the tools
works with no API key and no corpus: `search_regulation` needs the rail assistant (the `local`
group and its index, or SEARCH_BACKEND=live) and `extract_requirement` needs a model key.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Callable, Mapping

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from rail_compliance import __version__
from rail_compliance.config import Settings, get_settings
from rail_compliance.factory import make_search_backend
from rail_compliance.llm import ConfigError, LangChainStructuredLLM, make_chat_model
from rail_compliance.models import (
    CheckResult,
    ExtractionResult,
    HumanReason,
    HumanReview,
    Passage,
    Requirement,
    SearchResult,
)
from rail_compliance.parameters import CHECKED_PARAMETERS, SUBJECT_OF, SUBJECTS, accepted_subjects
from rail_compliance.retry import LLMUnavailable
from rail_compliance.spec import parameter_info, parameter_kinds
from rail_compliance.tools.check import check as check_tool
from rail_compliance.tools.extract import StructuredLLM
from rail_compliance.tools.extract import extract_requirement as extract_tool
from rail_compliance.tools.needs_human import needs_human as needs_human_tool
from rail_compliance.tools.search import SearchBackend, SearchError
from rail_compliance.tools.search import search_regulation as search_tool

INSTRUCTIONS = """\
Tools to check a train design against the EU PRM TSI (Regulation (EU) No 1300/2014). Not legal
advice. Typical order: search_regulation, then extract_requirement on the passages it returns,
then check with the spec's value, or needs_human when the law is ambiguous, data is missing or
the citation is weak. The resource rail://parameters lists the parameters and their subjects."""


def anticipated[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """Failures we expect (no key, no corpus, a bad argument) reach the client as readable tool
    errors; the SDK would otherwise reduce any exception to "Error executing tool"."""

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except (ValueError, ConfigError, SearchError, LLMUnavailable) as exc:
            raise ToolError(str(exc)) from exc

    return wrapper


def parameters_table() -> list[dict]:
    info, kinds = parameter_info(), parameter_kinds()
    return [
        {
            "parameter": path,
            "unit": info[path][0],
            "type": kinds[path],
            "description": info[path][1],
            "subject": SUBJECT_OF[path],
            "governed_by_subjects": accepted_subjects(path),
        }
        for path in CHECKED_PARAMETERS
    ]


def create_server(
    search: SearchBackend | None = None,
    extractor: StructuredLLM | None = None,
    settings: Settings | None = None,
) -> MCPServer:
    settings = settings or get_settings()
    built: dict[str, object] = {}
    if search is not None:
        built["search"] = search
    if extractor is not None:
        built["extractor"] = extractor

    def get_search() -> SearchBackend:
        if "search" not in built:
            built["search"] = make_search_backend(settings)
        return built["search"]  # type: ignore[return-value]

    def get_extractor() -> StructuredLLM:
        if "extractor" not in built:
            chat, name = make_chat_model(settings)
            built["extractor"] = LangChainStructuredLLM(chat, name)
        return built["extractor"]  # type: ignore[return-value]

    class LazyExtractor:
        """Builds the model on the first call that actually needs one."""

        def extract(self, system, user, schema):
            return get_extractor().extract(system, user, schema)

    server = MCPServer("rail-compliance", instructions=INSTRUCTIONS, version=__version__)

    @server.tool()
    @anticipated
    def search_regulation(question: str, k: int = 8) -> SearchResult:
        """Search the EU railway regulation for passages that answer a question. Returns the
        passages with their ids, sections, scores and EUR-Lex links."""
        return search_tool(question, get_search(), k)

    @server.tool()
    @anticipated
    def extract_requirement(
        passages: list[Passage], parameter: str, focus: str | None = None
    ) -> ExtractionResult:
        """Extract the numeric rule for one spec parameter from passages (as returned by
        search_regulation). The model's answer is verified: the quote must appear word for word
        in the passage and every number must be in the quote, else status is 'unverified'."""
        return extract_tool(passages, parameter, LazyExtractor(), focus)

    @server.tool()
    @anticipated
    def check(
        spec_value: float | None,
        requirement: Requirement,
        spec_unit: str | None = None,
        context: Mapping[str, float] | None = None,
        intervals: Mapping[str, tuple[float, float]] | None = None,
    ) -> CheckResult:
        """Compare a spec value with a requirement exactly (no model). `context` holds the other
        spec values (dotted path -> number, booleans as 1/0) that conditions and tables refer to;
        `intervals` marks values only known to lie in [low, high]. Verdicts: pass, fail,
        needs_human (data missing or ambiguous), not_applicable (the rule's conditions are
        false)."""
        return check_tool(
            spec_value, requirement, spec_unit=spec_unit, context=context, intervals=intervals
        )

    @server.tool()
    @anticipated
    def needs_human(
        reason: str, parameter: str | None = None, category: HumanReason = "other"
    ) -> HumanReview:
        """Record that a person must decide instead of guessing: the law is ambiguous
        (ambiguous_law), the rule depends on data the spec lacks (missing_data), or the citation
        is weak (weak_citation)."""
        return needs_human_tool(reason, parameter, category)

    @server.resource("rail://parameters", mime_type="application/json")
    def parameters() -> str:
        """The parameters that can be checked: unit, meaning, and the rule subjects that govern
        each (a rule for a broader subject also governs a narrower one)."""
        return json.dumps(
            {"parameters": parameters_table(), "subjects": SUBJECTS}, indent=2, ensure_ascii=False
        )

    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
