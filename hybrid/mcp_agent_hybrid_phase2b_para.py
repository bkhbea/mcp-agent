import asyncio
import json
from hybrid.contracts import TOOL_CONTRACTS
#from hybrid.mcp_agent_hybrid_phase3a import build_execution_dag
#from hybrid.mcp_agent_hybrid_phase3a import print_ascii_dag
#from hybrid.mcp_agent_hybrid_phase3b import build_execution_layers
from helpers.create_DAG import build_execution_dag
from helpers.create_layers import build_execution_layers
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

# ----------------- Database server parameters -----------------
DB_PARAMS = StdioServerParameters(
    name="db",
    command="python3",
    args=["servers/db_server.py"]  # adjust path as needed
)
# ------------------------------------------------------------
# Global lock: protects MCP ClientSession write stream
# ------------------------------------------------------------
tool_call_lock = asyncio.Lock()
# --------------------

async def execute_step(step, db_session, max_retries=3):
    """
    Executes a single step (tool call) with optional retry for idempotent tools.

    Responsibilities:
    - Handles retries for idempotent tools
    - Executes a single tool via MCP session
    - Logging preserved for debugging

    Layer-level parallelism is handled by the scheduler, not here.
    """
    tool_name = step["tool"]
    contract = TOOL_CONTRACTS[tool_name]

    attempt = 0
    while True:
        attempt += 1
        try:
            print(f"[DB] Executing tool '{tool_name}' with arguments: {step.get('arguments', {})}")
            
            # Optional: serialize all MCP calls if needed
            async with tool_call_lock:
              result = await db_session.call_tool(
                tool_name,
                arguments=step.get("arguments", {})
            )

            # Pretty-print results
            i = 0
            if len(result.content) > 1:
                print(f"[DB] Result for '{tool_name}':\n") 
                for i in range (len(result.content)):
                   print(f"{result.content[i].text}")
                   i = i + 1
            else:    
                print(f"[DB] Result for '{tool_name}': {result.content[0].text}")
               
            return result

        except Exception as e:
            if contract.idempotent and attempt < max_retries:
                print(f"[DB] Retry {attempt}/{max_retries} for tool '{tool_name}' due to error: {e}")
                await asyncio.sleep(0.1)
                continue
            # Non-idempotent or retries exhausted
            raise


async def execute_plan_parallel_safe(plan):
    """
    Executes a validated plan while respecting tool contracts:
    - Commutative tools on independent state run concurrently
    - Non-commutative or conflicting tools run sequentially
    - Idempotent tools automatically retried on failure
    """
    
    print("------------ Building DAG --------" )
    dag = build_execution_dag(plan)
    
    print("------------ Creating execution Layers --------" )
    layers = build_execution_layers(dag)
    
    execution_error = None  # <- store errors here
    print("\n---------- Executing Parallel Plan (Phase 2B) ------")
    async with stdio_client(DB_PARAMS) as (reader, writer):
        async with ClientSession(reader, writer) as db_session:
          db_metadata =  await db_session.initialize()
          #print("DB Server Metadata:", db_metadata)
          for layer in layers:
            print(f"Executing layer: {layer}")
            tasks = [execute_step(plan[i], db_session) for i in layer]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                    if isinstance(r, BaseException):
                        print("Captured task error:", repr(r))
                        execution_error = r
                        break
            
            if execution_error:
                  break        

    
        if execution_error:
          raise execution_error  

