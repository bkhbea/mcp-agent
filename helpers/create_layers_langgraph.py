import networkx as nx

def build_execution_layers(dag, plan):
    """
    Return execution layers respecting DAG dependencies.
    Each layer contains steps that can run in parallel.
    """

    layers = []
    # Compute in-degree for all nodes
    in_degree = {n: dag.in_degree(n) for n in dag.nodes}
    # Nodes with zero in-degree are ready to run
    ready = [n for n, deg in in_degree.items() if deg == 0]

    while ready:
        # Add current ready nodes as a layer
        layers.append(ready.copy())
        next_ready = []

        # Remove edges from ready nodes and find next ready nodes
        for node in ready:
            for succ in dag.successors(node):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    next_ready.append(succ)

        ready = next_ready

    # Print layers nicely
    for i, layer in enumerate(layers):
        layer_tools = [f"{n}:{plan[n]['tool']}" for n in layer]
        print(f"Layer {i}: {layer_tools}")

    return layers
