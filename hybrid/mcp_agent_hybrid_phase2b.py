#Phase 2 — Execute DB Tools (Still No Files)
import json
import requests
import time
import asyncio

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


# ----------------- Database server parameters -----------------
DB_PARAMS = StdioServerParameters(
    name="db",
    command="python3",
    args=["servers/db_server.py"]  # adjust path as needed
)
# ----------------- Phase 2: Execute plan -----------------
async def execute_plan(plan):
    """
    Execute a list of MCP tool actions asynchronously.
    Plan format example:
    [
      {"tool": "create_user", "arguments": {"name": "Alice", "email": "alice@example.com"}},
      {"tool": "list_users"}
    ]
    """

    print("\n=== Executing Plan (Phase 2) ===")

    async with stdio_client(DB_PARAMS) as (reader, writer):
        async with ClientSession(reader, writer) as db_session:
            await db_session.initialize()

            for step in plan:
                tool = step.get("tool")
                arguments = step.get("arguments", {})

                print(f"[DB] Executing tool '{tool}' with arguments: {arguments}")

                try:
                    # call_tool expects tool name and arguments as a dict
                    result = await db_session.call_tool(tool, arguments=arguments)

                    # parse result chunks to JSON if available
                    #parsed_result = []
                    #for chunk in result.content:
                    #    text = (chunk.text or "").strip()
                    #    if text:
                    #        try:
                    #            parsed_result.append(json.loads(text))
                    #        except json.JSONDecodeError:
                    #            parsed_result.append(text)

                    #print(f"[DB] Result for '{tool}': {parsed_result}")
                    # Pretty-print results
                    i = 0
                    if len(result.content) > 1:
                       print(f"[DB] Result for '{tool}':\n") 
                       for i in range (len(result.content)):
                          print(f"{result.content[i].text}")
                          i = i + 1
                    else:    
                       print(f"[DB] Result for '{tool}': {result.content[0].text}")
               
            
                except Exception as e:
                    print(f"[DB] Tool '{tool}' failed: {e}")

