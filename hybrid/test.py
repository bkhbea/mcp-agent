from mcp_agent_hybrid_phase2a import validate_plan
from mcp_agent_hybrid_phase2b_para import execute_plan_parallel_safe
from mcp_agent_hybrid_phase2b import execute_plan
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
   print('-------------- Phase 2A - LLM generated plan validation ---------')
   print("We validate the generated plan against the defined contract")
   validate_plan(plan)
   print("LLM Plan validation done")     

   print("-------------- Phase 2B - DB tools execution -------------------")
   print("\n>>> Passing validated plan to Phase 2 for execution...\n")
    # --- Call Phase 2 ---
   await execute_plan(plan)
   #await execute_plan_parallel_safe(plan)

if __name__ == "__main__":
    asyncio.run(main())
