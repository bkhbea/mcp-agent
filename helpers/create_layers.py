import networkx as nx

def build_execution_layers(dag: nx.DiGraph):
    """
    Convert a DAG into execution layers.

    Each layer is a list of node IDs that:
    - Have no remaining dependencies
    - Can be executed in parallel
    """
    layers = []
    remaining = dag.copy()

    while remaining.nodes:
        # Nodes with no incoming edges (ready to run)
        ready = [
            node for node in remaining.nodes
            if remaining.in_degree(node) == 0
        ]

        if not ready:
            raise RuntimeError("Cycle detected in execution DAG")

        # New: sort nodes to preserve plan order for deterministic execution
        ready.sort()

        layers.append(ready)
        remaining.remove_nodes_from(ready)

    print_layered_dag(layers)
    return layers


def print_layered_dag(layers):
    print("\n### Execution Layers (Parallel View)\n")
    for i, layer in enumerate(layers):
        print(f"Layer {i}: ", "  ".join(str(n) for n in layer))
