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

# ------------------------------------------------------------
# NEW: server routing helper
# ------------------------------------------------------------
def get_session_for_step(step, db_session, file_session):
    """
    New: Route execution to the correct MCP session based on step['server'].
    """
    server = step.get("server", "db")
    if server == "db":
        return db_session
    elif server == "file":
        return file_session
    else:
        raise ValueError(f"Unknown server '{server}' in step: {step}")


async def execute_step(step, db_session, file_session, max_retries=3):
    """
    Executes a single step (tool or resource) with optional retry.
    Responsibilities:
    - Select correct MCP server (DB / File)
    - Handle retries for idempotent tools
    - Execute exactly ONE step
    - No DAG logic here
      Executes a single step (tool or resource).
    """
    # to avoid any path mismatch and for security reason, the file will be written in 
    # a predefined secure directory. So this routine will extract the file name.
    def normalize_file_uri(path: str) -> str:
        """
        Normalize file URIs for MCP File Server:
        - Strip trailing slash
        - Ensure path is relative to file server root
        - Do NOT convert to absolute filesystem paths
        """
        path = path.rstrip("/")
        if path.startswith("file://"):
            path = path[len("file://"):]
            parts = path.split("/")
            path = parts[-1]
            print(f"=============== file://{path} ===================")
        return f"file://{path}"
  
    # NEW: distinguish execution type
    step_type = step.get("type", "tool")
    tool_name = step["tool"]
    server = step.get("server")

    # NEW: route session
    session = get_session_for_step(step, db_session, file_session)
    
    # NEW: resources are not retried
    if step_type == "resource":
        max_retries = 1
    list_users_result = None
    attempt = 0
# ANSI color codes for terminal
COLOR_RESET = "\033[0m"
COLOR_DB = "\033[94m"    # Blue
COLOR_FILE = "\033[92m"  # Green

def colorize_node(node_idx, step):
    """
    Returns a color-coded string for a node based on its server.
    """
    server = step.get("server", "db")
    text = f"{node_idx}: {step['tool']}"
    if server == "db":
        return f"{COLOR_DB}{text}{COLOR_RESET}"
    elif server == "file":
        return f"{COLOR_FILE}{text}{COLOR_RESET}"
    return text


async def execute_plan_parallel_safe(plan):
    """
    Executes a validated plan while respecting the DAG:
    - DAG defines ordering
    - DAG-level fairness ensures root-to-leaf paths make progress
    - execute_step handles retries + routing
    - New: live, color-coded logging of node execution
    """
    print("------------ Building DAG --------")
    dag = build_execution_dag(plan)

    print("------------ Creating execution Layers (for reference) --------")
    layers = build_execution_layers(dag)

    print("\n---------- Executing Plan Topologically with DAG-level fairness ------")

    async with stdio_client(DB_PARAMS) as (db_r, db_w), \
               stdio_client(FILE_PARAMS) as (file_r, file_w):

        async with ClientSession(db_r, db_w) as db_session, \
                   ClientSession(file_r, file_w) as file_session:

            print("DB Server Metadata:", await db_session.initialize())
            print("File Server Metadata:", await file_session.initialize())

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



