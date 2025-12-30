#Phase 1 — Skeleton Agent (No MCP Yet)
#Goal:
#Prove that llama can reliably output a valid plan.
#source ~/venvs/py310/bin/activate
import json
import requests
import time
import asyncio
#from hybrid.mcp_agent_hybrid_phase2a import validate_plan
from helpers.validaters import validate_plan
from hybrid.mcp_agent_hybrid_phase2b import execute_plan  # import Phase 2 executor
#from helpers.create_DAG import build_execution_dag
#from helpers.create_layers import build_execution_layers
from hybrid.mcp_agent_hybrid_phase2b_para import execute_plan_parallel_safe

#from contracts import TOOL_CONTRACTS


# ----------------- LLaMA HTTP API call -----------------
# The below defintions is need to make sure that teh response is cleaned from any
# comments that may be added by LLM
def extract_json_array(raw: str):
    start = raw.find("[")
    end = raw.rfind("]")

    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON array found in LLM output:\n{raw}")

    json_text = raw[start:end + 1]
    return json.loads(json_text)


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
            """
            text = response.json()["response"].strip()

            if not is_json_complete(text):
                raise ValueError("Incomplete JSON")

            plan = json.loads(text)
            #print(">>> LLM PLAN RECEIVED")
            #print(json.dumps(plan, indent=2))
            return plan
            """
            response.raise_for_status()
            raw = response.json()["response"]
            plan = extract_json_array(raw)
            print("LLM Plan (JSON):", json.dumps(plan, indent=2))
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
    
    print('-------------- Phase 2 - LLM generated plan validation ---------')
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


