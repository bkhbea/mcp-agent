import requests
import json
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
{
  "read_file": ["path"],
  "write_file": ["path", "content"]
}

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
  "tool": "read_file",
  "arguments": {
    "uri": "file://<file_path>/"  
  }
  
}

### Database tool action MUST use:
{
  "type": "tool",
  "server": "db",
  "tool": "<tool_name>",
  "arguments": { ... }
}

### Rules:
- STRICTLY FOLLOW THESE RULES AND IF YOU CANNOT, STOP AND STATE THE REASON 
- Respond ONLY with valid JSON and ONLY JSON 
- Respond as a JSON array of actions (tools or resources)
- Each element MUST contain:
  - "tool"
  - "arguments"
- Do NOT include comments
- Do NOT include explanations
- Do NOT invent tools
- "arguments" MUST be a JSON object with named fields


### User request:
1. Create 3 users:
   - Alice (alice@example.com)
   - Bob (bon@example.com)
   - Charlie (chuck@example.com)
2. Write Alice user and bob user to bob_alice.txt - This should happen ONLY in one step
3. Write Charlie user to charlie.txt
4. list all users
5. Write users list to user_list.json
6. read user_list.json
"""
response = requests.post(
  "http://localhost:11434/api/generate",
  json={
                     "model": "llama3",  # your local model
                     "prompt": prompt,
                     "stream": False,    # simplified for MCP
                     "options": {
                                  "temperature": 0.0,
                                  "num_predict": 512
                                }
                   },
              timeout=1200,
         )
response.raise_for_status()
response_text = response.json()["response"].strip()
print(response_text)
plan = json.loads(response.json()["response"])
print(plan)