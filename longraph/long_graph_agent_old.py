import asyncio
import json
from helpers.contracts import TOOL_CONTRACTS
from helpers.create_DAG import build_execution_dag
from helpers.create_layers import build_execution_layers
from helpers.normalize_results import normalize_results
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from pprint import pprint

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

# ---------------------- ANSI color codes ----------------------
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

# ---------------------- Session Routing ----------------------
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
#------------ Clean up user lis

def pretty_print_result(result):
    print("I am in clean user")
    print(type(result))
    for item in result:  # your list
      print("Item")
      json_text = item.content[0].text
      data = json.loads(json_text)
      print(json.dumps(data, indent=2))
    return (json.loads(json_text))

# ---------------------- Step Execution ----------------------
async def execute_step(step, db_session, file_session, max_retries=3):
    """
    Executes a single step (tool or resource) with optional retry.
    """
    # Normalize file URIs
    def normalize_file_uri(path: str) -> str:
        path = path.rstrip("/")
        if path.startswith("file://"):
            path = path[len("file://"):]
            path = path.split("/")[-1]
            print(f"=============== file://{path} ===================")
        return f"file://{path}"

    step_type = step.get("type", "tool")
    tool_name = step["tool"]
    session = get_session_for_step(step, db_session, file_session)

    if step_type == "resource":
        max_retries = 1

    attempt = 0
    users = {}
    while True:
        attempt += 1
        try:
            async with tool_call_lock:
                if step_type == "tool":
                    if tool_name ==  'list_users':
                        result = await session.call_tool(
                        tool_name,
                        arguments=step.get("arguments", {}))
                        #users = clean_user_list(result)
                        users = result
                        
                        #print(f"User List:\n {users}")    
                    else:
                        result = await session.call_tool(
                        tool_name,
                        arguments=step.get("arguments", {})
                    )
                    if step["tool"] == "write_file" and step["arguments"]["content"] == "...":
                        print("============ Write_File ============")
                        #step["arguments"]["content"] = clean_user_list(users)
                        #print(f"User List:\n {users}")   
                        step["arguments"]["content"] =json.dumps({"users": users})
                        print(f"-------------- STEP ------------- \n {step}")
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

            print(f"[{step.get('server','db').upper()}:{step_type}] {tool_name} OK")
            return result

        except Exception as e:
            if step_type == "tool" and attempt < max_retries:
                print(f"[RETRY] {tool_name} ({attempt}) due to {e}")
                await asyncio.sleep(0.1)
                continue
            raise

# ---------------------- Layer Execution ----------------------
async def execute_layer(layer, plan, db_session, file_session):
    """
    Executes all nodes in a single layer concurrently.
    """
    tasks = {}
    results = [None] * len(plan)
    
    for node in layer:
        step_info = colorize_node(node, plan[node])
        print(f"--> Launching node {step_info}")
        task = asyncio.create_task(execute_step(plan[node], db_session, file_session))
        tasks[task] = node

    done, _ = await asyncio.wait(tasks.keys(), return_when=asyncio.ALL_COMPLETED)

    for task in done:
        node = tasks[task]
        step_info = colorize_node(node, plan[node])
        try:
            results[node] = task.result()
            print(f"<-- Completed node {step_info}")
        except Exception as e:
            print(f"[ERROR] Node {step_info} failed: {e}")
            raise e

    return results

# ---------------------- Plan Execution ----------------------
async def execute_plan_parallel_safe(plan):
    """
    Executes a validated plan respecting DAG dependencies:
    - DAG defines ordering
    - Layers define parallelism
    - execute_step handles retries + routing
    - Color-coded logging per server
    """
    print("------------ Building DAG --------")
    dag = build_execution_dag(plan)

    print("------------ Creating execution Layers --------")
    layers = build_execution_layers(dag)

    async with stdio_client(DB_PARAMS) as (db_r, db_w), \
               stdio_client(FILE_PARAMS) as (file_r, file_w):

        async with ClientSession(db_r, db_w) as db_session, \
                   ClientSession(file_r, file_w) as file_session:

            #print("DB Server Metadata:", await db_session.initialize())
            #print("File Server Metadata:", await file_session.initialize())
            db_metadata =  await db_session.initialize()
            file_metadata = await file_session.initialize()

            print("DB Metadata:\n")
            pprint(vars(db_metadata))
            print("\nFile Metadata:\n")
            pprint(vars(file_metadata))
            results = [None] * len(plan)
            for layer_idx, layer in enumerate(layers):
                print(f"\n=== Executing layer {layer_idx}: {[colorize_node(n, plan[n]) for n in layer]} ===")
                layer_result = await execute_layer(layer, plan, db_session, file_session)
                normalized = normalize_results(layer_result)
                print(normalized)
                #print(f"Layer Result:\n {pretty_print_result(normalized)}")
                # Merge layer results
                for idx, res in enumerate(layer_result):
                    if res is not None:
                        results[idx] = res

            return results
