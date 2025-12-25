
from hybrid.mcp_agent_hybrid_phase2b_para import execute_plan_parallel_safe
from hybrid.mcp_agent_hybrid_phase2b import execute_plan

 
import asyncio

plan = [
  {
    "tool": "create_user",
    "arguments": {
      "name": "Alice",
      "email": "alice@example.com"
    }
  },
  {
    "tool": "create_user",
    "arguments": {
      "name": "Bob",
      "email": "bon@example.com"
    }
  },
  {
    "tool": "create_user",
    "arguments": {
      "name": "Charlie",
      "email": "chuck@example.com"
    }
  },
  {
    "tool": "list_users"
  }
]
async def main():
   #print("------- Running the simplest agent --------")
   #await execute_plan(plan)
   print("------- Running the Agent utilizing DAGand Execution Layers --------")
   await execute_plan_parallel_safe(plan)
   

if __name__ == "__main__":
    asyncio.run(main())
