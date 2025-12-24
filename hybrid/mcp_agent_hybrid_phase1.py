#Phase 1 — Skeleton Agent (No MCP Yet)
#Goal:
#Prove that llama can reliably output a valid plan.
#source ~/venvs/py310/bin/activate
import json
import requests
import time
import asyncio
from mcp_agent_hybrid_phase2a import validate_plan
from mcp_agent_hybrid_phase2b import execute_plan  # import Phase 2 executor
from mcp_agent_hybrid_phase2b_para import execute_plan_parallel_safe

#from contracts import TOOL_CONTRACTS


# ----------------- LLaMA HTTP API call -----------------
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


def ask_llama_plan(prompt: str, max_retries: int = 3,token_size: int = 512):
    last_error = None
    print(f"LLM Prompt :\m {prompt}") 
    for attempt in range(1, max_retries + 1):
        try:
            print(f">>> LLM CALL STARTED (attempt {attempt}, tokem size {token_size})")

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": token_size
                    }
                },
                timeout=600
            )

            response.raise_for_status()
            text = response.json()["response"].strip()

            if not is_json_complete(text):
                raise ValueError("Incomplete JSON")

            plan = json.loads(text)
            #print(">>> LLM PLAN RECEIVED")
            #print(json.dumps(plan, indent=2))
            return plan

        except Exception as e:
            last_error = str(e)
            print(f"LLM call failed (attempt {attempt}): {last_error}")
            time.sleep(2 * attempt)

    raise RuntimeError(f"LLM failed after {max_retries} attempts: {last_error}")

# ----------------- Run -----------------
prompt= """
You are an assistant that and that can call tools via MCP..

### Database tools (all on server "db"):
    {
      "get_user_by_id": ["id"],
      "list_users": ["name_filter", "email_filter"],
      "create_user": ["name", "email"],
      "update_user": ["id", "name", "email"],
      "delete_user": ["id"]
    }

### Rules:
- Respond ONLY with valid JSON
- Output a JSON array
- Each element MUST contain:
  - "tool"
  - "arguments"
- Do NOT include comments
- Do NOT include explanations
- Do NOT invent tools
- "arguments" MUST be a JSON object with named fields

### User request:
Create 3 users:
- Alice (alice@example.com)
- Bob (bon@example.com)
- Charlie (chuck@example.com)
Then list all users
"""
async def main():
    
    print("-------------  Phase 1 - Skeleton Agent (No MCP Yet) -----------")
    print("Prove that llama can reliably output a valid plan.")
    plan = ask_llama_plan(prompt)
    print("\nFINAL PLAN:")
    print(json.dumps(plan, indent=2))
    
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

"""
Phase 1  ──►  LLM Plan
Phase 2A ──►  Contract Validation
Phase 3A ──►  DAG Construction   ✅ (new)
Phase 3B ──►  Scheduler (layers)
Phase 2B ──►  Executor (MCP calls)

| Phase | Responsibility                 | Code type         |
| ----- | ------------------------------ | ----------------- |
| 3A    | Build DAG from contracts       | Graph logic       |
| 3B    | Convert DAG → execution layers | Topological logic |
| 2B    | Execute layers                 | MCP / async       |

"""
