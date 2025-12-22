import subprocess
import time
import json
import requests
from pathlib import Path
import sqlite3

# --- Configuration ---
DB_SERVER_PATH = Path("./servers/db_server.py")        # Path to DB server script
FILE_SERVER_PATH = Path("./servers/file_server.py")    # Path to File server script
LLM_API_URL = "http://localhost:11434/api/generate"    # Local LLM endpoint
RETRIES = 3
TIMEOUT = 1200
BASE_DIR = Path(__file__).resolve().parent.parent      # root /mcp_agent
DB_PATH = Path("./servers/users.db")                  # SQLite DB path
ALLOWED_FILES = {"readme.txt", "welcome.txt", "notes/todo.txt", "user_list.json"}

# --- User + LLM prompt ---
LLM_INSTRUCTIONS = """
You are an MCP planning assistant.
### Database tools (server "db"):
{
  "get_user_by_id": ["id"],
  "list_users": ["name_filter", "email_filter"],
  "create_user": ["name", "email"],
  "update_user": ["id", "name", "email"],
  "delete_user": ["id"]
}
### File tools (server "file"):
- write_file(path, content)
- read_file via resource: file://<path>/
### Rules:
- Respond ONLY in JSON
- JSON array of steps (type tool/resource)
- Always include server
- Never assume files exist
- Tool actions MUST include arguments
- Resource actions MUST include arguments {"path": "..."}
- File paths MUST be in the allowed set: readme.txt, welcome.txt, notes/todo.txt, user_list.json
"""

USER_REQUEST = """
Create a user named "Albert" with email "albert@example.com",
then list all users, write the list to 'user_list.json', then read it back.
"""

# --- Helper functions ---
def call_llm(prompt: str) -> str:
    """Call the local LLM API with retries and return raw response text."""
    for attempt in range(1, RETRIES + 1):
        full_prompt = LLM_INSTRUCTIONS + "\n\n### User request:\n" + USER_REQUEST
        print(f">>> Calling LLM (attempt {attempt})...\nPrompt:\n{full_prompt}")
        try:
            response = requests.post(
                LLM_API_URL,
                json={
                    "model": "llama3",
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": 0.0, "num_predict": 512},
                },
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            text = response.json()["response"].strip()
            # Extract JSON array only (ignore any extra text)
            import re
            match = re.search(r'\[.*\]', text, flags=re.DOTALL)
            if match:
                text = match.group(0)
            print(f">>> LLM Plan:\n{text}")
            return text
        except Exception as e:
            print(f"LLM attempt {attempt}/{RETRIES} failed: {e}")
            if attempt == RETRIES:
                raise

def normalize_plan(plan):
    """Ensure every resource/tool step has server and arguments."""
    print("Normalizing plan...")
    for step in plan:
        if "type" not in step:
            # Infer type: if it has 'tool', it's a tool
            step["type"] = "tool" if "tool" in step else "resource"
        if step["type"] == "resource":
            step.setdefault("server", "file")
            if "arguments" not in step and "path" in step:
                step["arguments"] = {"path": step.pop("path")}
        elif step["type"] == "tool":
            step.setdefault("arguments", {})
    return plan

def safe_file_path(path: str) -> Path:
    """Ensure the file path is allowed and resolve full path."""
    filename = Path(path.replace("file://", "")).name
    if filename not in ALLOWED_FILES:
        raise ValueError(f"File not allowed: {filename}")
    return BASE_DIR / filename

def list_all_users():
    """Read all users from SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM users")
    rows = cursor.fetchall()
    conn.close()
    users = [{"id": r[0], "name": r[1], "email": r[2]} for r in rows]
    return users

# --- Main ---
def main():
    # Start servers
    print("Starting servers...")
    print("Starting Database server...")
    db_proc = subprocess.Popen(["python3", str(DB_SERVER_PATH)])
    print("Starting File server...")
    file_proc = subprocess.Popen(["python3", str(FILE_SERVER_PATH)])
    time.sleep(2)  # give servers time to start
    print("Servers started.\n")

    try:
        # --- Call LLM ---
        raw_plan = call_llm(LLM_INSTRUCTIONS + "\n### User request:\n" + USER_REQUEST)
        plan = json.loads(raw_plan)
        plan = normalize_plan(plan)

        # --- Execute steps ---
        print("\n=== Executing Plan ===")
        for i, step in enumerate(plan, 1):
            print(f"\n--- Step {i} ---")
            print(step)
            try:
                if step["type"] == "tool":
                    server = step["server"]
                    tool = step["tool"]
                    args = step["arguments"]
                    if server == "db":
                        print(f">>> Calling DB tool: {tool} with args {args}")
                        # Only implement DB mock locally (SQLite access)
                        if tool == "list_users":
                            users = list_all_users()
                            # Attach the content to be written in next file step
                            step["arguments"]["content"] = json.dumps(users)
                            print(f"DB list_users output: {users}")
                        elif tool == "create_user":
                            # Minimal implementation for test
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)",
                                           (args["name"], args["email"]))
                            conn.commit()
                            user_id = cursor.lastrowid
                            conn.close()
                            print(f"User created: id={user_id}, name={args['name']}, email={args['email']}")
                    elif server == "file":
                        print(f">>> Calling FILE tool: {tool} with args {args}")
                        if tool == "write_file":
                            path = safe_file_path(args["path"])
                            path.write_text(args["content"])
                            print(f"File written: {path}")
                elif step["type"] == "resource":
                    path = safe_file_path(step["arguments"]["path"])
                    print(f">>> Reading resource: {path}")
                    content = path.read_text()
                    print(f"Resource content:\n{content}")
            except Exception as e:
                print(f"!!! Error executing step {i}: {e}")

    finally:
        # Stop servers
        db_proc.terminate()
        file_proc.terminate()
        print("\nServers stopped.")

if __name__ == "__main__":
    main()
