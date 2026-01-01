import networkx as nx

def build_execution_dag(plan):
    """
    Build a DAG from a plan using top-level $from dependencies.
    """

    G = nx.DiGraph()

    # Step 1: map step id to index
    id_to_index = {step["id"]: i for i, step in enumerate(plan)}

    # Step 2: add nodes
    for i, step in enumerate(plan):
        G.add_node(i, step=step)

    # Step 3: add edges from top-level $from
    for i, step in enumerate(plan):
        step_from = step.get("$from", [])
        # Normalize to list
        if isinstance(step_from, str):
            step_from = [step_from]
        elif not isinstance(step_from, list):
            raise ValueError(f"$from must be a string or list in step '{step['id']}'")

        for ref in step_from:
            if ref not in id_to_index:
                raise ValueError(f"Step '{step['id']}' references unknown step '{ref}'")
            dep_idx = id_to_index[ref]
            if dep_idx >= i:
                raise ValueError(
                    f"Step '{step['id']}' references future step '{ref}'"
                )
            # Add DAG edge
            G.add_edge(dep_idx, i)

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
