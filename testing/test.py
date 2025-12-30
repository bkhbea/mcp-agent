
#source ~/venvs/py310/bin/activate
from hybrid.mcp_agent_hybrid_phase2b_para import execute_plan_parallel_safe
from helpers.normalize_results import normalize_results
from helpers.validaters import validate_plan
from helpers.create_DAG import build_execution_dag
#from helpers.initial_RAG_creation import build_execution_dag
from helpers.create_layers import build_execution_layers
#from helpers.initial_create_layers import build_execution_layers
from hybrid.mcp_agent_hybrid_phase2b import execute_plan

import json
from pprint import pprint
"""
=============== this plan was generated using the following prompt ===========
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

 
import asyncio
plan = [
  {
    "type": "tool",
    "server": "db",
    "tool": "create_user",
    "arguments": {
      "name": "Alice",
      "email": "alice@example.com"
    }
  },
  {
    "type": "tool",
    "server": "db",
    "tool": "create_user",
    "arguments": {
      "name": "Bob",
      "email": "bon@example.com"
    }
  },
  {
    "type": "tool",
    "server": "db",
    "tool": "create_user",
    "arguments": {
      "name": "Charlie",
      "email": "chuck@example.com"
    }
  },
  {
    "type": "tool",
    "server": "file",
    "tool": "write_file",
    "arguments": {
      "path": "bob_alice.txt",
      "content": "{\"id\": 1, \"name\": \"Alice\", \"email\": \"alice@example.com\"}\n{\"id\": 2, \"name\": \"Bob\", \"email\": \"bon@example.com\"}"
    }
  },
  {
    "type": "tool",
    "server": "file",
    "tool": "write_file",
    "arguments": {
      "path": "charlie.txt",
      "content": "{\"id\": 3, \"name\": \"Charlie\", \"email\": \"chuck@example.com\"}"
    }
  },
  {
    "type": "tool",
    "server": "db",
    "tool": "list_users",
    "arguments": {}
  },
  {
    "type": "tool",
    "server": "file",
    "tool": "write_file",
    "arguments": {
      "path": "user_list.json",
      "content": "{\"users\": [...]}"
    }
  },
  {
    "type": "resource",
    "server": "file",
    "tool": "read_file",
    "arguments": {
      "uri": "file:///user_list.json/"
    }
  }
]
async def main():
   
   print("------------ Validating plan----------")
   valid = validate_plan(plan)
   print(f"Plan valid ? {valid}")
   print("----------- Generating DAG ---------")
   dag = build_execution_dag(plan)
   #print(f"Generated DAG:")
   #print(print_dag_nodes(dag))
   print("----------- Generating Execuion Layers -------")
   layers = build_execution_layers(dag)
   #print_layered_dag(layers)
   
   #print("------- Running the simplest agent --------")
   #await execute_plan(plan)

   #print("------- Running the Agent utilizing DAGand and Execution Layers --------")
   #result = await execute_plan_parallel_safe(plan)
   
   """
   In this example, result has basically a list of objects, 
   and inside each one the JSON you want is stored as a string at:
   item.content[0].text.
   item
   └── content (list)
      └── [0]
           └── TextContent
                └── text  ← JSON string

    The result may contain:                
      1. CallToolResult.structuredContent
      2. ReadResourceResult.contents[*].text
    So never assume the same attributes exist on every item. 
    Normalize result into one list of dicts, list[dict]
   """  
   """
   normalized_result = normalize_results(result)
   print("============ Final Result ============")
   pprint(normalized_result)
    #      
   
   for item in result:  # your list
    json_text = item.content[0].text
    data = json.loads(json_text)
    print(json.dumps(data, indent=2))
   """  

if __name__ == "__main__":
    asyncio.run(main())