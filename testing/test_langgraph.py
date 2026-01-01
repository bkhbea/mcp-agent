
#source ~/venvs/py310/bin/activate
from helpers.langgraph_validator import validate_plan
from helpers.plans import get_plan
from helpers.create_DAG_langgraph import build_execution_dag
from helpers.create_layers_langgraph import build_execution_layers
from longraph.longraph_agent import execute_plan_parallel_safe 
#from helpers.normalize_results import normalize_results

#from helpers.create_DAG import build_execution_dag
#from helpers.initial_RAG_creation import build_execution_dag
#from helpers.create_layers import build_execution_layers
#from helpers.initial_create_layers import build_execution_layers
#from hybrid.mcp_agent_hybrid_phase2b import execute_plan


import json
from pprint import pprint
import asyncio
plan =  get_plan()
async def main():

   
   
   print("------------ Validating plan----------")
   valid = validate_plan(plan)
   print(f"Plan valid ? {valid}")
   
   print("----------- Generating DAG ---------")
   dag = build_execution_dag(plan)
  
   print("----------- Generating Execuion Layers -------")
   layers = build_execution_layers(dag,plan)
   #print_layered_dag(layers)
   
   #print("------- Running the simplest agent --------")
   #await execute_plan(plan)

   #print("------- Running the Agent utilizing DAGand and Execution Layers --------")
   #result = await execute_plan_parallel_safe(plan)

   print("------- Running Longraph as the execution engine")
   result = await execute_plan_parallel_safe(plan)
   
   

if __name__ == "__main__":
    asyncio.run(main())