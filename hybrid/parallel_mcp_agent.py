import asyncio
import json
import os
from helpers.contracts import TOOL_CONTRACTS
from helpers.create_DAG import build_execution_dag
from helpers.create_layers import build_execution_layers
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from collections import defaultdict
import networkx as nx

# ----------------- Database server parameters -----------------
DB_PARAMS = StdioServerParameters(
    name="db",
    command="python3",
    args=["servers/db_server.py"]
)

FILE_PARAMS = StdioServerParameters(
    name="file",
    command="python3",
    args=["servers/file_server.py"]
)
# ------------------------------------------------------------

# Global lock: protects MCP ClientSession write stream
tool_call_lock = asyncio.Lock()

# ANSI color codes for terminal
COLOR_RESET = "\033[0m"
COLOR_DB = "\033[94m"    # Blue
COLOR_FILE = "\033[92m"  # Green

# ------------------------------------------------------------
# NEW: server routing helper
# ------------------------------------------------------------
def get_session_for_step(step, db_session, file_session):
    """
    Route execution to the correct MCP session based on step['server'].
    """
    server = step.get("server", "db")
    if server == "db":
        return db_session
    elif server == "file":
        return file_session
    else:
        raise ValueError(f"Unknown server '{server}' in step: {step}")


# ------------------------------------------------------------
# Execute a single step (tool/resource)
# ------------------------------------------------------------
async def execute_step(step, db_session, file_session, max_retries=3):
    """
    Executes a single step (tool or resource) with optional retry.
    """
    def normalize_file_uri(path: str) -> str:
        path = path.rstrip("/")
        if path.startswith("file://"):
            path = path[len("file://"):]
            parts = path.split("/")
            path = parts[-1]
            print(f"=============== file://{path} ===================")
        return f"file://{path}"

    step_type = step.get("type", "tool")
    tool_name = step["tool"]

    session = get_session_for_step(step, db_session, file_session)

    if step_type == "resource":
        max_retries = 1

    attempt = 0
    while True:
        attempt += 1
        try:
            async with tool_call_lock:
                if step_type == "tool":
                    result = await session.call_tool(
                        tool_name,
                        arguments=step.get("arguments", {})
                    )
                elif step_type == "resource":
                    result = await session.read_resource(
                        normalize_file_uri(step["arguments"]["uri"])
                    )
                    print(f"-----------File Content from {step['arguments']['uri']}---------")
                    for resource in result.contents:
                        data = json.loads(resource.text)
                        print(json.dumps(data, indent=2))
                else:
                    raise ValueError(f"Unknown step type: {step_type}")

            return result  # Must return resolved result

        except Exception as e:
            if step_type == "tool" and attempt < max_retries:
                print(f"[RETRY] {tool_name} ({attempt}) due to {e}")
                await asyncio.sleep(0.1)
                continue
            raise


# ------------------------------------------------------------
# Utility: colorize nodes for terminal logging
# ------------------------------------------------------------
def colorize_node(node_idx, step):
    server = step.get("server", "db")
    text = f"{node_idx}: {step['tool']}"
    if server == "db":
        return f"{COLOR_DB}{text}{COLOR_RESET}"
    elif server == "file":
        return f"{COLOR_FILE}{text}{COLOR_RESET}"
    return text


# ------------------------------------------------------------
# Execute the full plan with DAG-level fairness
# ------------------------------------------------------------
async def execute_plan_parallel_safe(plan):
    print("------------ Building DAG --------")
    dag = build_execution_dag(plan)

    print("------------ Creating execution Layers (for reference) --------")
    layers = build_execution_layers(dag)

    async with stdio_client(DB_PARAMS) as (db_r, db_w), \
               stdio_client(FILE_PARAMS) as (file_r, file_w):

        async with ClientSession(db_r, db_w) as db_session, \
                   ClientSession(file_r, file_w) as file_session:

            # Safe pretty-print metadata
            db_metadata = await db_session.initialize()
            file_metadata = await file_session.initialize()
            print("\nDB Server Metadata:")
            print(json.dumps(vars(db_metadata), indent=2, default=str))
            print("\nFile Server Metadata:")
            print(json.dumps(vars(file_metadata), indent=2, default=str))

            # -----------------------------
            # DAG-level execution with live logging
            # -----------------------------
            in_degree = {n: dag.in_degree(n) for n in dag.nodes}
            ready = [n for n, deg in in_degree.items() if deg == 0]
            running_tasks = {}
            results = [None] * len(plan)
            execution_error = None
            layer_counter = 0

            while ready or running_tasks:
                if ready:
                    ready_str = ", ".join(colorize_node(n, plan[n]) for n in ready)
                    print(f"\n[Layer {layer_counter}] Ready to run nodes: {ready_str}")
                    layer_counter += 1

                for node in ready:
                    step_info = colorize_node(node, plan[node])
                    print(f"--> Launching node {step_info}")
                    task = asyncio.create_task(execute_step(plan[node], db_session, file_session))
                    running_tasks[task] = node
                ready = []

                if not running_tasks:
                    break

                done, _ = await asyncio.wait(running_tasks.keys(), return_when=asyncio.FIRST_COMPLETED)

                for task in done:
                    node = running_tasks.pop(task)
                    step_info = colorize_node(node, plan[node])
                    try:
                        results[node] = task.result()
                        print(f"<-- Completed node {step_info}")
                    except Exception as e:
                        print(f"[ERROR] Node {step_info} failed: {e}")
                        execution_error = e
                        break

                    for succ in dag.successors(node):
                        in_degree[succ] -= 1
                        if in_degree[succ] == 0:
                            ready.append(succ)

                running_nodes = [colorize_node(n, plan[n]) for n in running_tasks.values()]
                ready_nodes = [colorize_node(n, plan[n]) for n in ready]
                print(f"Current running tasks: {running_nodes}")
                print(f"Nodes ready for next iteration: {ready_nodes}")

                if execution_error:
                    break

            if execution_error:
                raise execution_error

            return results
