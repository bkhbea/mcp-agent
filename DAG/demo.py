from dag_builder import *
if __name__ == "__main__":
    plan = [
        #{"tool": "list_users"},
        {"tool": "create_user", "arguments": {"name": "Alice"}},
        {"tool": "create_user", "arguments": {"name": "Bob"}},
        {"tool": "create_user", "arguments": {"name": "Charlie"}},
        {"tool": "list_users"},
    ]

    dag = build_dag(plan)

    print("DAG EDGES:")
    print(dag)
    print_ascii_dag(dag)
    
#What this shows
#(root) → no dependencies
#[0,1,2] → (3) → step 3 waits for steps 0,1,2