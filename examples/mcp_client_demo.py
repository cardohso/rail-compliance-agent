"""Talk to the MCP server the way Claude Desktop or Claude Code does: start it as a subprocess
and call its tools over stdio. No API key and no corpus are needed for `check`.

    uv run python examples/mcp_client_demo.py
"""

import asyncio
import json
import sys

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

# PRM TSI 4.2.2.3.2(1): all exterior passenger doorways need a clear useable width of 800 mm
REQUIREMENT = {
    "parameter": "exterior_doors.clear_width_mm",
    "subject": "exterior_doorway",
    "comparator": ">=",
    "value": 800,
    "unit": "mm",
    "citation": {
        "passage_id": "tsi-prm:Annex §4.2.2.3.2#1",
        "doc_id": "tsi-prm",
        "document": "PRM TSI",
        "section": "Annex §4.2.2.3.2",
        "quote": (
            "All exterior passenger doorways shall have a minimum clear useable width of 800 mm"
        ),
    },
}


async def main() -> None:
    server = StdioServerParameters(
        command=sys.executable, args=["-m", "rail_compliance.mcp_server"]
    )
    async with Client(server) as client:
        tools = (await client.list_tools()).tools
        print("tools:", ", ".join(t.name for t in tools))
        for value in (780, 800):
            result = await client.call_tool(
                "check", {"spec_value": value, "requirement": REQUIREMENT}
            )
            r = result.structured_content
            print(f"check({value} mm): {r['verdict']}, {r['reason']}")
        result = await client.call_tool(
            "needs_human",
            {"reason": "The rule points to an external standard.", "category": "weak_citation"},
        )
        print("needs_human:", json.dumps(result.structured_content))
        body = await client.read_resource("rail://parameters")
        rows = json.loads(body.contents[0].text)["parameters"]
        print(f"rail://parameters: {len(rows)} parameters, first: {rows[0]['parameter']}")


asyncio.run(main())
