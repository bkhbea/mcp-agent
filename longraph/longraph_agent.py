import asyncio
import json
from collections import defaultdict
from helpers.create_DAG import build_execution_dag
from helpers.create_layers import build_execution_layers
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

# ----------------- Server Parameters -----------------

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

# ----------------------------------------------------

tool_call_lock = asyncio.Lock()

# ----------------------------------------------------
# Helpers
# ----------------------------------------------------

def get_session_for_step(step, db_session, file_session):
    server = step.get("server", "db")
    if server == "db":
        return db_session
    if server == "file":
        return file_session
    raise ValueError(f"Unknown server '{server}'")


def resolve_arguments(value, state):
    """
    Recursively resolve arguments. 

    # New: Handles nested dicts/lists where some values may come from $from references.
    # New: If a step has $from=[], it effectively resolves to nothing special and leaves content as-is.
    """
    #print(f'State: {state}')
    if isinstance(value, dict):
        if "$from" in value:
            key = value["$from"]
            # New: Normalize single string to list
            if isinstance(key, str):
                key = [key]
            # New: Gather results from all upstream steps
            results = [state[k] for k in key if k in state]
            return results if len(results) > 1 else (results[0] if results else None)
        return {k: resolve_arguments(v, state) for k, v in value.items()}
    elif isinstance(value, list):
        return [resolve_arguments(v, state) for v in value]
    return value

import json
from mcp.types import TextContent

def normalize_output(values):
    """
    Normalize MCP tool outputs into plain Python data.

    Input:
        values: List[List[Content]]  (fan-in of step outputs)

    Output:
        - dict              (single JSON object)
        - list[dict]        (fan-in)
        - str / list[str]   (fallback)
    """
    normalized = []

    for output in values:
        if not isinstance(output, list):
            raise TypeError(f"Expected list of Content, got {type(output)}")

        for item in output:
            if isinstance(item, TextContent):
                text = item.text.strip()
                try:
                    normalized.append(json.loads(text))
                except json.JSONDecodeError:
                    normalized.append(text)
            else:
                # New: future-proof for other MCP content types
                normalized.append(item)

    # Collapse single value
    if len(normalized) == 1:
        return normalized[0]

    return normalized


# ----------------------------------------------------
# Step Executor (single step only)
# ----------------------------------------------------

async def execute_step(step, db_session, file_session, execution_state):
    step_id = step["id"]
    tool_name = step["tool"]
    step_type = step.get("type", "tool")

    session = get_session_for_step(step, db_session, file_session)

    # New: Resolve all $from references or nested arguments
    resolved_args = resolve_arguments(step.get("arguments", {}), execution_state)
    #print(f"Resolved arguments: {resolved_args}")
    # inject step-level $from outputs
    if step_type == "tool":
        refs = step.get("$from", [])
        if isinstance(refs, str):
           refs = [refs]
        
        if refs:
            values = []
            for ref in refs:
               if ref not in execution_state:
                raise KeyError(f"Missing dependency '{ref}' for step '{step_id}'")
            #print(f"xxxxx {execution_state[ref]}")
               values.append(execution_state[ref])
            # Convention: write into `content`
            normalized_content = normalize_output(values)
            #print(f"Normalized Content: {normalized_content}")
            #resolved_args["content"] = values[0] if len(values) == 1 else values
            resolved_args["content"] = normalized_content 
    
    async with tool_call_lock:
        if step_type == "tool":
            #print(f"Calling tool {tool_name} with {resolved_args}")
            result = await session.call_tool(tool_name, resolved_args)
            #print(f"Result: {result}")
            output = result.content
            
        elif step_type == "resource":
            resource = await session.read_resource(resolved_args["uri"])
            #print(f"Resource: {resource}")
            output = json.loads(resource.contents[0].text)
        else:
            raise ValueError(f"Unknown step type '{step_type}'")

    # New: Always store output keyed by step id in execution_state
    execution_state[step_id] = output

    # Keep existing 'produces' support
    if "produces" in step:
        execution_state[step["produces"]] = output

    return output

# ----------------------------------------------------
# Layer Executor
# ----------------------------------------------------

async def execute_layer(layer, plan, db_session, file_session, execution_state):
    tasks = {}
    for node in layer:
        step = plan[node]
        print(f" ---- Processing Node : {node} -- Task {step} -----" )
        task = asyncio.create_task(
            execute_step(step, db_session, file_session, execution_state)
        )
        tasks[task] = step["id"]

    done, _ = await asyncio.wait(tasks.keys())

    for task in done:
        task.result()  # propagate errors

# ----------------------------------------------------
# Main Plan Executor (DAG-safe)
# ----------------------------------------------------

async def execute_plan_parallel_safe(plan):
    # New: DAG and layers are fully based on $from references
    dag = build_execution_dag(plan)
    layers = build_execution_layers(dag)

    execution_state: dict[str, any] = {}

    async with stdio_client(DB_PARAMS) as (db_r, db_w), \
               stdio_client(FILE_PARAMS) as (file_r, file_w):

        async with ClientSession(db_r, db_w) as db_session, \
                   ClientSession(file_r, file_w) as file_session:

            await db_session.initialize()
            await file_session.initialize()

            for layer_idx, layer in enumerate(layers):
                print(f"\n--- Executing Layer {layer_idx}: tasks {layer} ---")
                await execute_layer(
                    layer,
                    plan,
                    db_session,
                    file_session,
                    execution_state
                )

    # New: execution_state contains output of every step keyed by step id
    return execution_state
