import requests
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

response = requests.post(
  "http://localhost:11434/api/chat",
  json={
    "model": "llama3",
    "prompt": prompt,
    "stream": False
  }
)
print(response)
