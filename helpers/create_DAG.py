import networkx as nx
from collections import defaultdict
from helpers.contracts import TOOL_CONTRACTS

def build_execution_dag(plan):
    """
    Build a conservative DAG from an LLM-generated plan using safe assumptions.

    Assumptions:
    1. Plan only contains db_server (CRUD ops), file_server (read/write), or both.
    2. If a file write/read happens after a DB write in the plan and content might include DB objects, serialize it.
    """
    G = nx.DiGraph()

    # Step 1: compute dynamic reads/writes for each node
    node_reads = []
    node_writes = []
    contracts = []
    for step in plan:
        tool = step.get("tool")
        contract = TOOL_CONTRACTS.get(tool)
        contracts.append(contract)

        if not contract:
            node_reads.append(set())
            node_writes.append(set())
            continue

        # Use dynamic state resolver if present
        if contract.state_resolver:
            state = contract.state_resolver(step.get("arguments", {}))
            node_reads.append(state.get("reads", set()))
            node_writes.append(state.get("writes", set()))
        else:
            node_reads.append(contract.reads)
            node_writes.append(contract.writes)

    # Step 2: add nodes
    for i, step in enumerate(plan):
        G.add_node(i, step=step)

    # Step 3: add edges based on conflicts and safe assumptions
    n = len(plan)
    for i in range(n):
        for j in range(i + 1, n):
            contract_i = contracts[i]
            contract_j = contracts[j]

            if not contract_i or not contract_j:
                continue

            # write/write conflict: only block if not commutative
            conflict = node_writes[i] & node_writes[j]
            if conflict and (not contract_i.commutative or not contract_j.commutative):
                G.add_edge(i, j)

            # read-after-write hazard
            raw = node_writes[i] & node_reads[j]
            if raw:
                G.add_edge(i, j)

            # New: heuristic to serialize file ops that might depend on DB writes
            # If step j is a file write/read and step i is a DB write
            server_i = plan[i].get("server")
            server_j = plan[j].get("server")
            if server_i == "db" and server_j == "file":
                G.add_edge(i, j)  # serialize conservatively

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
