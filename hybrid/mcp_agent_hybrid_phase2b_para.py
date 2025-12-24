import asyncio
from contracts import TOOL_CONTRACTS
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

async def execute_step(step, db_session, tool_call_lock, max_retries=3):
    """
    Executes a single step (tool call) with optional retry for idempotent tools.
    Preserves logging for Phase 2.
    """
    tool_name = step["tool"]
    contract = TOOL_CONTRACTS[tool_name]

    attempt = 0
    while True:
        attempt += 1
        try:
            print(f"[DB] Executing tool '{tool_name}' with arguments: {step.get('arguments', {})}")
            
            # serialize MCP writes
            async with tool_call_lock:
            # Replace this with your actual Phase 2 tool execution
              result = await db_session.call_tool(
                 tool_name, 
                 arguments=step.get("arguments", {})
            ) 

            print(f"[DB] Result for '{tool_name}': {result}")
            return result

        except Exception as e:
            # Retry only if tool is idempotent
            if contract.idempotent and attempt < max_retries:
                print(f"[DB] Retry {attempt}/{max_retries} for tool '{tool_name}' due to error: {e}")
                await asyncio.sleep(0.1)  # small backoff
                continue
            
                # Non-idempotent tool or max retries reached
            raise

async def execute_plan_parallel_safe(plan):
    """
    Executes a validated plan while respecting tool contracts:
    - Commutative tools on independent state run concurrently
    - Non-commutative or conflicting tools run sequentially
    - Idempotent tools automatically retried on failure
    """
    print("\n=== Executing Parallel Plan (Phase 2B) ===")
    async with stdio_client(DB_PARAMS) as (reader, writer):
        async with ClientSession(reader, writer) as db_session:
          db_metadata =  await db_session.initialize()
          print("DB Server Metadata:", db_metadata)
    # Track currently executing tasks
        # keep in mind the following:
        # The parallelism is Scheduler:    ──►  parallel task creation
        # The actual execution is sequantial, why?
        # We are using one client session
        # One ClientSession = one writer = one in-flight request
        executing = [] # serialized MCP calls (by necessity)

    for step in plan:
          contract = TOOL_CONTRACTS[step["tool"]]

        # Check if step can run in parallel with currently executing steps
        # Core logic for parallelism:
        # all(...) checks all currently executing tasks.
        # We can run this step in parallel if:
            # 1. The current tool is commutative (safe to run with others of same type).
            # 2. The states it writes (writes) do not overlap with any currently executing step 
            # (isdisjoint).
        # If any running step conflicts (writes to the same DB state, or non-commutative), 
        # can_parallel becomes False.
          can_parallel = all(
            contract.commutative and contract.writes.isdisjoint(
                TOOL_CONTRACTS[s["step"]["tool"]].writes
            )
            for s in executing
          )
        # If safe to run in parallel:
             #asyncio.create_task(execute_step(step)) schedules the async DB call 
             # (Phase 2) without blocking.
             # Append the step and its task to executing, so future steps can check for conflicts.
          if can_parallel:
             # Launch asynchronously and track the task
            print(f"Parallel execution of \n {step}")
            task = asyncio.create_task(execute_step(step,db_session))
            executing.append({"step": step, "task": task})
        
            # If not safe to run in parallel, we must wait for all currently running steps to finish:
            # asyncio.gather waits for all tasks in executing to complete.
            # Reset executing to empty, since we now have no running parallel tasks.
            # This ensures non-commutative or conflicting steps run sequentially.
          else:
            # Wait for all currently running tasks to finish
            if executing:
                await asyncio.gather(*(s["task"] for s in executing))
                executing = []

            # Execute this step sequentially
            print(f"Sequential execution of \n {step}")
            await execute_step(step)

    # Wait for any remaining parallel tasks
    if executing:
        await asyncio.gather(*(s["task"] for s in executing))
