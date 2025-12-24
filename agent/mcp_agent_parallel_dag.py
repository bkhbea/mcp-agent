import asyncio
import json
import requests
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
import time

# --- NEW: imports for path normalization ---
import os
import uuid
from pathlib import Path

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

# ----------------- File path policy constants -----------------
# NEW: all agent-generated files live here
GENERATED_DIR = Path("generated")

# NEW: default filename generator
def generate_default_filename() -> str:
    """Generate a default filename using a UUID."""
    return f"agent_generated_{uuid.uuid4().hex}.json"

# ----------------- Path normalization logic -----------------
def normalize_write_path(requested_path: str | None) -> str:
    """
    Enforce agent-owned file write rules:
    - All files go under /generated
    - /generated is created if missing
    - Invalid or missing filenames are replaced
    - .exe files are forbidden
    """

    # ensure /generated exists
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    filename = None

    if requested_path:
        filename = os.path.basename(requested_path)

        if not filename.strip():
            filename = None
        elif filename.lower().endswith(".exe"):
            filename = None

    if not filename:
        filename = generate_default_filename()

    final_path = GENERATED_DIR / filename
    return str(final_path)

# ----------------- JSON completeness check -----------------
def is_json_complete(text: str) -> bool:
    stack = []
    for c in text:
        if c in "{[":
            stack.append(c)
        elif c == "}":
            if not stack or stack[-1] != "{":
                return False
            stack.pop()
        elif c == "]":
            if not stack or stack[-1] != "[":
                return False
            stack.pop()
    return len(stack) == 0

# ----------------- LLaMA HTTP API call (NON-STREAMING, STABLE) -----------------
def ask_llama(prompt: str, max_retries: int = 3, num_predict: int = 512) -> list:
    """
    IMPORTANT DESIGN CHOICE:
    - stream = False
    - LLM returns ONE blob of text
    - No partial JSON
    - No Ollama stream protocol issues
    """

    last_error = None
    print("Calling LLM with prompt:\n", prompt)

    for attempt in range(1, max_retries + 1):
        try:
            print(f">>> LLM CALL STARTED (attempt {attempt}, num_predict={num_predict})")

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": num_predict
                    }
                },
                timeout=600
            )

            response.raise_for_status()

            response_text = response.json()["response"].strip()

            if not is_json_complete(response_text):
                raise ValueError("Incomplete JSON returned by LLM")

            plan = json.loads(response_text)

            # pretty print plan for debugging
            print(f"LLM Plan:\n{json.dumps(plan, indent=2)}")
            print(">>> LLM CALL COMPLETED AND PARSED")

            return plan

        except Exception as e:
            last_error = str(e)
            print(f"LLM call failed (attempt {attempt}): {last_error}")
            time.sleep(2 * attempt)

    raise RuntimeError(f"LLM failed after {max_retries} attempts: {last_error}")

# ----------------- HELPER: Execute DB tool -----------------
async def execute_db_tool(db_session, step):
    print(f"[DB] Executing {step['tool']} with args {step.get('arguments', {})}")

    result = await db_session.call_tool(
        step["tool"],
        arguments=step.get("arguments", {})
    )

    parsed = None
    for chunk in result.content:
        text = (chunk.text or "").strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
            break
        except json.JSONDecodeError:
            continue

    print(f"[DB] Result for {step['tool']}: {parsed}")
    return parsed

# ----------------- HELPER: Execute plan -----------------
async def execute_plan(plan, db_session, file_session):
    print("\n=== Executing Plan (STABLE SEQUENTIAL MODE) ===")

    list_users_result = None
    last_written_file = None

    for step in plan:

        # -------- DB TOOLS --------
        if step["type"] == "tool" and step["server"] == "db":

            if step["tool"] in {"create_user", "update_user", "delete_user"}:
                await execute_db_tool(db_session, step)

            elif step["tool"] == "list_users":
                result = await db_session.call_tool("list_users", arguments={})
                users = []
                for chunk in result.content:
                    users.extend(json.loads(chunk.text))
                list_users_result = users

        # -------- FILE WRITE (AGENT CONTROLLED) --------
        elif step["type"] == "tool" and step["server"] == "file" and step["tool"] == "write_file":

            original_path = step.get("arguments", {}).get("path")
            normalized_path = normalize_write_path(original_path)
            last_written_file = normalized_path

            # IMPORTANT:
            # We DO NOT trust the LLM to provide file content.
            # The agent injects list_users output.
            content = json.dumps(list_users_result or [], indent=2)

            await file_session.call_tool(
                "write_file",
                arguments={
                    "path": normalized_path,
                    "content": content
                }
            )

            print(f"[FILE] Written to {normalized_path}")

        # -------- FILE READ (RESOURCE) --------
        elif step["type"] == "resource" and step["server"] == "file":

            if not last_written_file:
                print("[FILE] Skipping read: no file was written yet")
                continue

            uri = f"file://{last_written_file}/"
            await file_session.read_resource(uri)
            print(f"[FILE] Read from {uri}")

        else:
            # Defensive: ignore malformed or hallucinated steps
            print(f"[WARN] Ignoring unsupported step: {step}")

# ----------------- MCP + LLaMA Test -----------------
async def llm_db_test():
    async with stdio_client(DB_PARAMS) as (reader, writer), \
               stdio_client(FILE_PARAMS) as (file_r, file_w):

        async with ClientSession(reader, writer) as db_session, \
                   ClientSession(file_r, file_w) as file_session:

            await db_session.initialize()
            await file_session.initialize()

            prompt = """
You are an assistant that produces execution plans for an MCP agent.

### Database tools (server: "db"):
- create_user(name, email)
- list_users()

### File tools (server: "file"):
- write_file(path, content)
- read file via resource: file://<path>/

### STRICT RULES:
- Output ONLY valid JSON
- Output a JSON ARRAY of steps
- NO comments
- NO placeholders
- NEVER invent file content
- write_file MUST come before read resource
- The agent will inject database results at runtime

### User request:
Create 3 users:
- Alice (alice@example.com)
- Bob (bon@example.com)
- Charlie (chuck@example.com)
Then list users, write them to a file, and read the file.
"""

            plan = ask_llama(prompt)
            await execute_plan(plan, db_session, file_session)

if __name__ == "__main__":
    asyncio.run(llm_db_test())
