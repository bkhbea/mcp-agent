import asyncio
import json
import requests
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
import time

# ----------------- Database server parameters -----------------
DB_PARAMS = StdioServerParameters(
    name="db",
    command="python3",
    args=["servers/db_server.py"]  # adjust path as needed
)
FILE_PARAMS = StdioServerParameters(
    name="file",
    command="python3",
    args=["servers/file_server.py"])  # adjust path as needed

# ----------------- LLaMA HTTP API call -----------------
#def ask_llama(prompt: str) -> dict:
def ask_llama(prompt: str, max_retries: int = 3) -> dict:   
    last_error = None
    """Call local LLaMA model via Ollama HTTP API and parse JSON output."""
    for attempt in range(1, max_retries + 1):
      try:
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
              timeout=600,
         )
         response.raise_for_status()
         response_text = response.json()["response"].strip()
         print(f"LLM Plan:\n {response_text}")
         
         
         return json.loads(response.json()["response"]) 
      except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as e:
            last_error = f"HTTP error: {e}"

      except json.JSONDecodeError as e:
            last_error = f"Invalid JSON: {e}"

      print(f"LLM call failed (attempt {attempt}): {last_error}")
      time.sleep(2 * attempt)  # backoff      
    
    raise RuntimeError(f"LLM failed after {max_retries} attempts: {last_error}")  

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
#User request: create a new user name:Hebah email:hebah@example.com. Once created, get all users
#User request: Find user with id 4
#User request: Read docs/readme.txt
#User request: Create a user named "Smith" with email "smith@example.com", then list all users, write the list to 'user_list.json', then read it back.
            
            # Ask Ollama to plan tool calls
            plan = ask_llama(prompt)
            # Execute each tool call via MCP
            list_users_result = None
            for step in plan:
                try:
                    if step["type"] == "tool":
            # ---------------- DB tools ----------------
                       if step["server"] == "db":
                           result = await db_session.call_tool(step["tool"], arguments=step["arguments"])
                           if step["tool"] == "list_users":
                               #list_users_result = [json.loads(c.text) for c in result.content]
                               list_users_result = json.loads(result.content[0].text)
            # ---------------- File tools ----------------
                       elif step["server"] == "file":
                           # Inject list_users output if needed
                           if step["tool"] == "write_file" and step["arguments"]["path"] == "user_list.json":
                               step["arguments"]["content"] = json.dumps(list_users_result or [])
                           result = await file_session.call_tool(step["tool"], arguments=step["arguments"])
                       # Print results
                       formatted = [json.loads(c.text) for c in result.content] if step["type"] == "tool" else result  
                       print(f"Result for {step.get('tool') or step.get('uri')}:\n", json.dumps(formatted, indent=2))
            # ---------------- Resource reads ----------------
                    elif step["type"] == "resource":           
                       content = await file_session.read_resource(step["uri"])
                       print(f"File Content from {step['uri']}:\n", content.contents[0].text)
                
                except Exception as e:
                  print(f"Error executing step {step}: {e}")    

# ----------------- Run -----------------
if __name__ == "__main__":
    asyncio.run(llm_db_test())
