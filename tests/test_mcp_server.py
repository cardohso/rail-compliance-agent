import asyncio
import json
import sys

import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

from rail_compliance.config import Settings
from rail_compliance.mcp_server import create_server
from rail_compliance.models import RequirementCore, RequirementDraft, SearchResult
from tests.factories import limit, table5
from tests.test_extract import DOOR_PASSAGE, QUOTE_800, FakeLLM

DOOR_RULE = limit("exterior_doors.clear_width_mm", ">=", 800, "mm", subject="exterior_doorway")


def call(server, tool, arguments):
    async def go():
        async with Client(server) as client:
            return await client.call_tool(tool, arguments)

    return asyncio.run(go())


def payload(requirement):
    return json.loads(requirement.model_dump_json())


class FakeSearch:
    name = "fake"

    def search(self, question, k):
        return SearchResult(question=question, passages=[DOOR_PASSAGE], backend="fake")


def test_the_four_tools_are_listed_with_descriptions_and_schemas():
    async def go():
        async with Client(create_server()) as client:
            return (await client.list_tools()).tools

    tools = {t.name: t for t in asyncio.run(go())}
    assert set(tools) == {"search_regulation", "extract_requirement", "check", "needs_human"}
    for tool in tools.values():
        assert tool.description and tool.input_schema["type"] == "object"
    assert "requirement" in tools["check"].input_schema["required"]
    assert "question" in tools["search_regulation"].input_schema["required"]


@pytest.mark.parametrize(("value", "verdict"), [(850, "pass"), (800, "pass"), (799.9, "fail")])
def test_check_is_exact_over_mcp(value, verdict):
    result = call(
        create_server(), "check", {"spec_value": value, "requirement": payload(DOOR_RULE)}
    )
    assert not result.is_error
    assert result.structured_content["verdict"] == verdict


def test_check_applies_tables_conditions_and_intervals_over_mcp():
    args = {
        "spec_value": 2,
        "requirement": payload(table5()),
        "context": {"unit_length_m": 210.0},
        "intervals": {"unit_length_m": [0.0, 210.0]},
    }
    result = call(create_server(), "check", args)
    assert result.structured_content["verdict"] == "needs_human"
    assert "unit_length_m" in result.structured_content["reason"]


def test_needs_human_records_an_escalation_and_rejects_an_empty_reason():
    ok = call(create_server(), "needs_human", {"reason": "The law is ambiguous here.",
                                              "parameter": "steps.internal_step_height_mm",
                                              "category": "ambiguous_law"})  # fmt: skip
    assert ok.structured_content["category"] == "ambiguous_law"
    bad = call(create_server(), "needs_human", {"reason": "   "})
    assert bad.is_error and "reason" in json.dumps(bad.content[0].text)


def test_search_regulation_uses_the_injected_backend():
    result = call(
        create_server(search=FakeSearch()), "search_regulation", {"question": "door width"}
    )
    passages = result.structured_content["passages"]
    assert [p["id"] for p in passages] == [DOOR_PASSAGE.id]
    assert result.structured_content["backend"] == "fake"


def test_extract_requirement_returns_the_verified_requirement_with_its_citation():
    rule = RequirementCore(
        parameter="exterior_doors.clear_width_mm", subject="exterior_doorway",
        comparator=">=", value=800, unit="mm",
    )  # fmt: skip
    draft = RequirementDraft(found=True, passage_id=DOOR_PASSAGE.id, quote=QUOTE_800, rule=rule)
    server = create_server(extractor=FakeLLM(draft))
    args = {
        "passages": [json.loads(DOOR_PASSAGE.model_dump_json())],
        "parameter": "exterior_doors.clear_width_mm",
    }
    out = call(server, "extract_requirement", args).structured_content
    assert out["status"] == "found"
    assert out["requirement"]["citation"]["passage_id"] == DOOR_PASSAGE.id
    assert out["requirement"]["citation"]["url"].startswith("https://eur-lex.europa.eu/")


def test_extract_requirement_reports_an_unverified_quote_instead_of_trusting_the_model():
    rule = RequirementCore(
        parameter="exterior_doors.clear_width_mm", subject="exterior_doorway",
        comparator=">=", value=800, unit="mm",
    )  # fmt: skip
    draft = RequirementDraft(
        found=True, passage_id=DOOR_PASSAGE.id, quote="Doors must be 800 mm wide.", rule=rule
    )
    args = {
        "passages": [json.loads(DOOR_PASSAGE.model_dump_json())],
        "parameter": "exterior_doors.clear_width_mm",
    }
    out = call(create_server(extractor=FakeLLM(draft)), "extract_requirement", args)
    assert out.structured_content["status"] == "unverified"


def test_a_tool_that_needs_something_missing_fails_with_a_message_not_a_crash():
    server = create_server(settings=Settings(_env_file=None, search_backend="replay"))
    result = call(server, "search_regulation", {"question": "door width"})
    assert result.is_error and "replay" in result.content[0].text.lower()
    no_key = create_server(settings=Settings(_env_file=None, gemini_api_key=""))
    args = {"passages": [], "parameter": "exterior_doors.clear_width_mm"}
    out = call(no_key, "extract_requirement", args)
    # no passages short-circuits before a model is needed; with passages it must name the key
    assert out.structured_content["status"] == "not_found"
    args["passages"] = [json.loads(DOOR_PASSAGE.model_dump_json())]
    missing = call(no_key, "extract_requirement", args)
    assert missing.is_error and "GEMINI_API_KEY" in missing.content[0].text


def test_the_parameters_resource_lists_every_checked_parameter_with_its_subjects():
    async def go():
        async with Client(create_server()) as client:
            resources = (await client.list_resources()).resources
            body = await client.read_resource("rail://parameters")
            return resources, body

    resources, body = asyncio.run(go())
    assert [str(r.uri) for r in resources] == ["rail://parameters"]
    data = json.loads(body.contents[0].text)
    rows = {r["parameter"]: r for r in data["parameters"]}
    assert len(rows) == 7
    wheelchair = rows["exterior_doors.wheelchair_door_clear_width_mm"]
    assert wheelchair["governed_by_subjects"] == ["wheelchair_doorway", "exterior_doorway"]
    assert wheelchair["unit"] == "mm" and wheelchair["description"]
    assert "exterior_doorway" in data["subjects"]


def test_the_server_speaks_mcp_over_stdio_from_a_separate_process():
    """What Claude Desktop or Claude Code does: spawn the command and talk over a pipe."""
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "rail_compliance.mcp_server"]
    )

    async def go():
        async with Client(params) as client:
            names = [t.name for t in (await client.list_tools()).tools]
            result = await client.call_tool(
                "check", {"spec_value": 780, "requirement": payload(DOOR_RULE)}
            )
            return names, result

    names, result = asyncio.run(go())
    assert "check" in names and len(names) == 4
    assert result.structured_content["verdict"] == "fail"
    assert result.structured_content["margin"] == -20
