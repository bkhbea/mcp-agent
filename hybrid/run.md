you will need to first run the whole cycle by invoking:
1. source ~/venvs/py310/bin/activate - under development/mcp - This assume you alresdy have
   a '.venv' environment
2, cd mcp_agent
3. Keep in mind the following:
    A. Ollama must be running (open a terminal and 'ollama serve'
    B. Depending om the machine you r working on, the full cycle might take ~30 minutes'
    C. Once you run it one, all you need is the plan generated. Any testing can then be done
       by running test.py.     
3. python ./hybrid/mcp_agent_hybrid_phase1.py
4. When the LLM generated plan copy it and paste it to 'testing/test.py' in the 'plan' variable' 
5. By default, 'test.py' invokes 'await execute_plan(plan)' which has no schedular or DAG.
6. If you want to experience parallism  comment 'await execute_plan(plan)' and uncomment
   'await execute_plan_parallel_safe(plan)'. This uses 'contracts.py' which is used to validate the LLM genrated plan. It also uses DAG and proper schedualing. 
