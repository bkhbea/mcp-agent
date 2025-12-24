import asyncio
import json
from contracts import TOOL_CONTRACTS
from mcp_agent_hybrid_phase3a import build_execution_dag
from mcp_agent_hybrid_phase3b import build_execution_layers
from 

#=======================================
async def execute_step(step, session, max_retries=3):
    tool_name = step["tool"]
    contract = TOOL_CONTRACTS[tool_name]
    attempt = 0
    while True:
        attempt += 1
        try:
            print(f"[DB] Executing tool '{tool_name}' with arguments: {step.get('arguments', {})}")
            result = await session.call_tool(tool_name,
                arguments=step.get("arguments", {}))
            
            # Pretty-print results
            i = 0
            if len(result.content) > 1:
                print(f"[DB] Result for '{tool_name}':\n") 
                for i in range (len(result.content)):
                   print(f"{result.content[i].text}")
                   i = i + 1
            else:    
                print(f"[DB] Result for '{tool_name}': {result.content[0].text}")
            return result
        
        except Exception as e:
            if contract.idempotent and attempt < max_retries:
                print(f"[DB] Retry {attempt}/{max_retries} for tool '{tool_name}' due to error: {e}")
                await asyncio.sleep(0.1)
                continue
            # Non-idempotent or retries exhausted
            raise    

#=======================================
async def execute_step_with_pool(step, pool):
    session, reader, writer = await pool.acquire()
    try:
        result = await execute_step(step, session)
        return result
    finally:
        await pool.release((session, reader, writer))

async def execute_layers_with_pool(plan, layers, pool):
    for layer in layers:
        print(f"Executing layer: {layer}")
        tasks = [
            execute_step_with_pool(plan[i], pool)
            for i in layer
        ]
        await asyncio.gather(*tasks)

async def execute_plan_parallel_pool(plan):
    
    print("------------ Building DAG --------" )
    dag = build_execution_dag(plan)
    print(f"DAG Size: {dag.size}")
    print("------------ Creating execution Layers --------" )
    layers = build_execution_layers(dag)

    pool = MCPConnectionPool(size=4)  # tune this
    await pool.start()

    try:
        await execute_layers_with_pool(plan, layers, pool)
    finally:
       await pool.close()




