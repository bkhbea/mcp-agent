import networkx as nx 
from helpers.contracts import TOOL_CONTRACTS
from collections import defaultdict

def build_execution_dag(plan): 
    """ 
    Build a DAG where edges represent required ordering based on tool contracts. """
    G = nx.DiGraph()

    # Add nodes 
    for i, step in enumerate(plan): 
        G.add_node(i, step=step)
    print(f"=========== Number of Tasks {i+1} ===========")
    # Add edges
    for i, step_i in enumerate(plan):
        #print(f"Step A - {i} - {step_i}") 
        c1 = TOOL_CONTRACTS[step_i["tool"]]
        for j in range(i + 1, len(plan)):
            step_j = plan[j] 
            #print(f"Step B - {j} - {step_j}")
            c2 = TOOL_CONTRACTS[step_j["tool"]]
            conflict = ( 
                not c1.writes.isdisjoint(c2.writes) and not 
                (c1.commutative and c2.commutative) ) 
            read_after_write = ( c1.writes & c2.reads )  
            if conflict or read_after_write:
                G.add_edge(i, j)
    print_dag_nodes(G)
    print_dependency_tree(G) 
    return G

def print_dag_nodes(dag):
    print("\n### DAG Nodes")
    for node in sorted(dag.nodes):
        step = dag.nodes[node]["step"]
        tool = step.get("tool", "<resource>")
        server = step.get("server", "")
        print(f"{node}: {server}.{tool}")

def print_dependency_tree(dag):
    print("\n### Dependency Structure\n")
    for src, dst in sorted(dag.edges):
        print(f"{src} ─▶ {dst}")          