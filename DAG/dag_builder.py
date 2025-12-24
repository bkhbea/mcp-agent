# This file answers ONE question:
# “Which steps depend on which other steps?”

#Mental model before code
#For every pair of steps (A, B) where A comes before B:
#Add edge A → B if:
    #A writes something B reads
    #OR A writes something B writes

#That’s it. No heuristics.

# DAG/dag_builder.py
from typing import List, Dict, Set
from contracts import TOOL_CONTRACTS


class DAG:
    """
    Minimal DAG representation for Phase 3A.
    Nodes are step indices.
    Each node = one plan step
    Example:
    N1 = create_user(Alice)
    N2 = create_user(Bob)
    N3 = list_users
    Edges represent hard dependencies: A -> B
    """

    def __init__(self):
        self.nodes: Set[int] = set()
        self.edges: Dict[int, Set[int]] = {}  # from -> {to} -- A --> B

    def add_node(self, node: int):
        self.nodes.add(node)
        self.edges.setdefault(node, set())

    def add_edge(self, src: int, dst: int):
        self.edges.setdefault(src, set()).add(dst)

    def __str__(self):
        lines = []
        for src, dsts in self.edges.items():
            for dst in dsts:
                lines.append(f"{src} -> {dst}")
        return "\n".join(lines) if lines else "(no edges)"
    
def build_dag(plan: List[dict]) -> DAG:
    """
    Build a dependency DAG from a validated plan using tool contracts.
    """
    dag = DAG()

    # Register all steps as nodes
    for i in range(len(plan)):
        
        dag.add_node(i) 
    print(f"----- Number of Tasks in the plan: {i} -------") # number of 'tasks'
    # Compare every earlier step with every later step
    for i in range(len(plan)):
        step_i = plan[i]
        print(f"Step A - {i}: {step_i}")
        contract_i = TOOL_CONTRACTS[step_i["tool"]]

        for j in range(i + 1, len(plan)):
            step_j = plan[j]
            print(f"Step B - {j}: {step_j}")
            #print("=============") 
            contract_j = TOOL_CONTRACTS[step_j["tool"]]
            #print(f"Step A: {step_i}")
            #print(f"Step B: {step_j}")
            #print("=============")  
            # Dependency rules:
            # If i writes something j reads → i must run before j
            if contract_i.writes & contract_j.reads:
                dag.add_edge(i, j)
                
                print(f"Step B - {j}: {step_j}")
                print("=============")  

            # If both write the same state → ordering required
            # this could be confusing since I can have 2 create users tasks.
            # The missing distinction (this is the key)
            #There are two different kinds of “writes”
            #1️⃣ Append-like writes (commutative writes)
                    # INSERT INTO users (...)
                    # INSERT INTO users (...)
            #2️⃣ Mutating writes (non-commutative writes)
                    # UPDATE users SET email = ...
                    # DELETE FROM users WHERE id = ...
            # The correct rule is:
            #✅ If two tools write the same state and are not commutative → ordering required

            elif contract_i.writes & contract_j.writes:
                dag.add_edge(i, j)

    return dag

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

