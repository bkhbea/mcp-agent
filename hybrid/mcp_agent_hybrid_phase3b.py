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
        # Nodes with no incoming edges
        ready = [
            node for node in remaining.nodes
            if remaining.in_degree(node) == 0
        ]

        if not ready:
            raise RuntimeError("Cycle detected in execution DAG")

        layers.append(ready)
        remaining.remove_nodes_from(ready)
    print(layers)
    return layers
