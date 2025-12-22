import asyncio
import json
import requests
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
import time

# --- ADDITIONAL IMPORTS FOR DAG VISUALIZATION ---
import networkx as nx
import matplotlib.pyplot as plt

# ----------------- Database server parameters -----------------
DB_PARAMS = StdioServerParameters(
    name="db",
    command="python3",
    args=["servers/db_server.py"]  # adjust path as needed
)

FILE_PARAMS = StdioServerParameters(
    name="file",
    command="python3",
    args=["servers/file_server.py"]  # adjust path as needed
)

# ----------------- LLaMA HTTP API call -----------------
def ask_llama(prompt: str, max_retries: int = 3) -> dict:
    """
    Call local LLaMA model via Ollama HTTP API and parse JSON output.
    """
    last_error = None
    print("Calling LLM with prompt:\n")
    print(prompt)

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 512
                    }
                },
                timeout=1200,
            )
            response.raise_for_status()
            response_text = response.json()["response"].strip()
            print(f"LLM Plan:\n {response_text}")
            return json.loads(response_text)

        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as e:
            last_error = f"HTTP error: {e}"

        except json.JSONDecodeError as e:
            last_error = f"Invalid JSON: {e}"

        print(f"LLM call failed (attempt {attempt}): {last_error}")
        time.sleep(2 * attempt)

    raise RuntimeError(f"LLM failed after {max_retries} attempts: {last_error}")

# ----------------- NEW: parallel execution helper -----------------
async def execute_db_tool(db_session, step):
    """
    Execute a single DB tool call.
    SAFE to run in parallel with other DB calls.
    """
    print(f"[PARALLEL][DB] Executing {step['tool']} with args {step['arguments']}")
    result = await db_session.call_tool(step["tool"], arguments=step["arguments"])
    parsed = json.loads(result.content[0].text)
    print(f"[PARALLEL][DB] Result for {step['tool']}: {parsed}")
    return step["tool"], parsed

# ----------------- NEW: parallel plan executor with improved logging -----------------
async def execute_plan_parallel(plan, db_session, file_session):
    """
    Execute plan with safe parallelism.
    - DB create/update/delete can run in parallel
    - list_users, file operations remain sequential
    """
    print("\n=== Executing Plan (PARALLEL MODE) ===")

    # --- STATE ---
    list_users_result = None

    # --- PHASE 1: parallel DB mutations ---
    db_parallel_tasks = []
    parallel_steps = set()  # TRACK TO SKIP IN SEQUENTIAL LOG

    for step in plan:
        if step["type"] == "tool" and step["server"] == "db":
            if step["tool"] in {"create_user", "update_user", "delete_user"}:
                db_parallel_tasks.append(
                    execute_db_tool(db_session, step)
                )
                parallel_steps.add(id(step))  # MARK STEP AS PARALLEL

    if db_parallel_tasks:
        print(f"\n[PARALLEL] Running {len(db_parallel_tasks)} DB mutation tasks concurrently")
        results = await asyncio.gather(*db_parallel_tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                print("[PARALLEL][DB] ERROR:", r)
            else:
                tool_name, payload = r
                print(f"[PARALLEL][DB] Completed {tool_name}: {payload}")

    # --- PHASE 2: sequential dependency steps ---
    for i, step in enumerate(plan, 1):
        # --- SKIP LOGGING OF PARALLEL STEPS ---
        if id(step) in parallel_steps:
            continue

        print(f"\n--- Step {i} (SEQUENTIAL) ---")
        print(step)

        try:
            # ---------------- DB tools ----------------
            if step["type"] == "tool" and step["server"] == "db":

                if step["tool"] == "list_users":
                    print("[SEQ][DB] Calling list_users")
                    result = await db_session.call_tool("list_users", arguments=step["arguments"])

                    # --- FIX: aggregate all chunks returned by MCP ---
                    all_users = []
                    for chunk in result.content:
                        try:
                            data = json.loads(chunk.text)
                            if isinstance(data, list):
                                all_users.extend(data)
                            elif isinstance(data, dict):
                                all_users.append(data)
                            else:
                                print("[SEQ][DB] WARNING: Unexpected data type from list_users:", type(data))
                        except Exception as e:
                            print("[SEQ][DB] ERROR parsing chunk:", chunk.text, e)

                    list_users_result = all_users
                    print("[SEQ][DB] list_users output (aggregated):")
                    print(json.dumps(list_users_result, indent=2))

            # ---------------- File tools ----------------
            elif step["type"] == "tool" and step["server"] == "file":

                if step["tool"] == "write_file":
                    print("[SEQ][FILE] Preparing write_file")

                    # Inject DB state (THIS IS THE KEY)
                    if step["arguments"]["path"] == "user_list.json":
                        step["arguments"]["content"] = json.dumps(list_users_result or [])

                    result = await file_session.call_tool(
                        step["tool"],
                        arguments=step["arguments"]
                    )

                    print("[SEQ][FILE] write_file result:",
                          json.loads(result.content[0].text))

            # ---------------- Resource reads ----------------
            elif step["type"] == "resource":
                print(f"[SEQ][FILE] Reading resource {step['uri']}")
                content = await file_session.read_resource(step["uri"])
                print("[SEQ][FILE] Resource content:")
                print(content.contents[0].text)

        except Exception as e:
            print(f"!!! Error executing step {step}: {e}")

# ----------------- HELPER: Visualize DAG -----------------
# ----------------- HELPER: Visualize DAG & parallel clusters -----------------
def visualize_plan_dag(plan, save_path="plan_dag.png"):
    """
    Draw a DAG of the plan using networkx & matplotlib.
    Steps that can run in parallel are highlighted in green.
    Also prints textual parallel clusters.
    """
    G = nx.DiGraph()
    last_db_parallel_node = None
    parallel_clusters = []   # collect clusters of parallel steps
    current_cluster = []

    for i, step in enumerate(plan):
        node_label = f"{i}: {step['tool'] if step.get('tool') else 'resource'}"
        G.add_node(node_label)

        # --- Create dependencies & track parallel clusters ---
        if step["type"] == "tool" and step["server"] == "db" and step["tool"] in {"create_user", "update_user", "delete_user"}:
            # Can run in parallel: add to current cluster
            current_cluster.append(node_label)
            last_db_parallel_node = node_label
        else:
            # If current_cluster has parallel nodes, save it
            if current_cluster:
                parallel_clusters.append(list(current_cluster))
                current_cluster = []

            # All other steps depend on last DB parallel node
            if last_db_parallel_node:
                G.add_edge(last_db_parallel_node, node_label)
            # Also depend on previous sequential step
            if i > 0:
                prev_label = f"{i-1}: {plan[i-1]['tool'] if plan[i-1].get('tool') else 'resource'}"
                G.add_edge(prev_label, node_label)

    # Catch any remaining cluster at the end
    if current_cluster:
        parallel_clusters.append(list(current_cluster))

    # --- Draw the DAG ---
    pos = nx.spring_layout(G)
    plt.figure(figsize=(12, 6))
    node_colors = []
    for node in G.nodes():
        if any(name in node for name in ["create_user", "update_user", "delete_user"]):
            node_colors.append("lightgreen")  # parallel safe
        else:
            node_colors.append("lightblue")   # sequential

    nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=2000, font_size=10, arrowsize=20)
    plt.title("Plan DAG with Parallelism Highlights")
    
    # --- Save to file and show ---
    plt.savefig(save_path)
    print(f"[VISUALIZATION] DAG saved to {save_path}")
    plt.show()

    # --- Print textual parallel clusters ---
    if parallel_clusters:
        print("\n[PARALLEL CLUSTERS] Steps that can run in parallel:")
        for idx, cluster in enumerate(parallel_clusters, 1):
            print(f"Cluster {idx}: {', '.join(cluster)}")
    else:
        print("\n[PARALLEL CLUSTERS] No parallel steps detected.")


# ----------------- MCP + LLaMA Test -----------------
async def llm_db_test():

    async with stdio_client(DB_PARAMS) as (reader, writer), \
               stdio_client(FILE_PARAMS) as (file_r, file_w):

        async with ClientSession(reader, writer) as db_session, \
                   ClientSession(file_r, file_w) as file_session:

            # Initialize MCP session and fetch metadata
            db_metadata = await db_session.initialize()
            print("DB Metadata:", db_metadata)

            file_metadata = await file_session.initialize()
            print("File Metadata:", file_metadata)

            # Prompt LLaMA to choose a tool
            prompt = """
You are an assistant that can call tools via MCP.

### Database tools (all on server "db"):
{
  "get_user_by_id": ["id"],
  "list_users": ["name_filter", "email_filter"],
  "create_user": ["name", "email"],
  "update_user": ["id", "name", "email"],
  "delete_user": ["id"]
}

### File tools (all on server "file"):
- Write a file using the tool: write_file(path: str, content: str)
- Read a file using a resource: file://<path>/

### File write action MUST use:
{
  "type": "tool",
  "server": "file",
  "tool": "write_file",
  "arguments": {
    "path": "<file_path>",
    "content": "<string_content>"
  }
}

### File read action MUST use:
{
  "type": "resource",
  "server": "file",
  "uri": "file://<file_path>/"
}

### Database tool action MUST use:
{
  "type": "tool",
  "server": "db",
  "tool": "<tool_name>",
  "arguments": { ... }
}

### Rules:
- Always respond ONLY in JSON (no explanations, no extra text)
- Respond as a JSON array of actions (tools or resources)
- Never invent directories or files
- Use only these available file paths exactly: 
  - readme.txt
  - welcome.txt
  - notes/todo.txt
- For multi-step tasks, do not embed raw JSON manually; the agent will handle serialization
- Always call `write_file` on server "file"
- Never call `write_file` on the DB server
- Resource actions MUST use `"type": "resource"` and `"server": "file"`
- Tool actions MUST use `"type": "tool"` and `"server"` matching the tool's server
- For list_users output, the agent will capture the output and pass it as `content` to write_file
- Do not include "tool": "resource" anywhere
- The response MUST end with a closing ] character.

### User request:
Create a user named "Robert" with email "rob@example.com", 
then list all users, write the list to 'user_list.json', then read it back. 

"""

            plan = ask_llama(prompt)

            # --- VISUALIZE PLAN DAG ---
            visualize_plan_dag(plan)

            # ---- EXECUTE PLAN ----
            await execute_plan_parallel(plan, db_session, file_session)

# ----------------- Run -----------------
if __name__ == "__main__":
    asyncio.run(llm_db_test())
