import networkx as nx
from contracts import TOOL_CONTRACTS

def build_execution_dag(plan):
    """
    Build a DAG where edges represent required ordering
    based on tool contracts.
    """
    G = nx.DiGraph()
    
    # Add nodes
    for i, step in enumerate(plan):
        G.add_node(i, step=step)
        
    print(f"=========== Number of Tasks {i+1} ===========")
    # Add edges
    for i, step_i in enumerate(plan):
        print(f"Step A - {i} - {step_i}")
        c1 = TOOL_CONTRACTS[step_i["tool"]]
        #print(f{step_i["tool"]}")
        for j in range(i + 1, len(plan)):
            step_j = plan[j]
            print(f"Step B - {j} - {step_j}")
            c2 = TOOL_CONTRACTS[step_j["tool"]]
            #print(f"{c2}")
            conflict = (
                not c1.writes.isdisjoint(c2.writes)
                and not (c1.commutative and c2.commutative)
            )

            read_after_write = (
                c1.writes & c2.reads
            )

            if conflict or read_after_write:
                G.add_edge(i, j)
    print(G)
    return G

def build_reverse_edges(dag):
    """
    Build reverse adjacency list: node -> incoming nodes
    """
    incoming = {node: set() for node in dag.nodes}
    for src, dsts in dag.edges.items():
        for dst in dsts:
            incoming[dst].add(src)
    return incoming


def print_ascii_dag(dag):
    """
    Pretty ASCII visualization of the DAG.
    """
    incoming = build_reverse_edges(dag)

    print("\nASCII DAG:")
    for node in sorted(dag.nodes):
        deps = sorted(incoming[node])
        if deps:
            deps_str = ", ".join(str(d) for d in deps)
            print(f"  [{deps_str}] --> ({node})")
        else:
            print(f"  (root) --> ({node})")

