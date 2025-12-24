# agent/plan_graph.py

import networkx as nx
from contracts import TOOL_CONTRACTS, get_server_for_tool

def build_dependency_graph(plan):
    """
    Given a MCP plan (list of steps), build a dependency DAG based on contracts.
    Returns a networkx DiGraph.
    """

    G = nx.DiGraph()
    step_nodes = []

    # --- Assign node IDs ---
    for idx, step in enumerate(plan):
        # node ID: index + tool/resource name
        node_id = f"{idx}_{step.get('tool','resource')}"
        step_nodes.append((node_id, step))

        # Add node with metadata
        server = step.get("server") or (get_server_for_tool(step.get("tool")) if step.get("tool") else None)
        G.add_node(node_id, step=step, server=server)

    # --- Compute edges ---
    for i, (node_i, step_i) in enumerate(step_nodes):
        # Fetch contract for tool if type=tool
        contract_i = TOOL_CONTRACTS.get(step_i.get("tool")) if step_i.get("type") == "tool" else None

        for j, (node_j, step_j) in enumerate(step_nodes):
            if i == j:
                continue

            # Tool → Tool dependencies
            contract_j = TOOL_CONTRACTS.get(step_j.get("tool")) if step_j.get("type") == "tool" else None
            if contract_i and contract_j:
                # i writes what j reads → j depends on i
                if contract_i.writes & contract_j.reads:
                    G.add_edge(node_i, node_j)
                # i writes what j writes → avoid race
                if contract_i.writes & contract_j.writes:
                    G.add_edge(node_i, node_j)

            # Tool → Resource dependencies
            if contract_i and step_j.get("type") == "resource":
                resource_path = step_j.get("uri", "").replace("file://","").rstrip("/")
                if resource_path in contract_i.writes or "file" in contract_i.writes:
                    G.add_edge(node_i, node_j)

    return G

# --- Optional: Visualize DAG ---
def visualize_plan_dag(G, save_path="plan_dag.png"):
    import matplotlib.pyplot as plt

    pos = nx.spring_layout(G)
    node_colors = []

    for node in G.nodes():
        step_type = G.nodes[node]["step"].get("type")
        if step_type == "tool" and G.nodes[node]["server"] == "db":
            node_colors.append("lightgreen")  # parallel safe
        else:
            node_colors.append("lightblue")   # sequential / file

    plt.figure(figsize=(12, 6))
    nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=2000, font_size=10, arrowsize=20)
    plt.title("Plan DAG with Parallelism Highlights")
    plt.savefig(save_path)
    plt.show()
    print(f"[VISUALIZATION] DAG saved to {save_path}")

    # Print textual parallel clusters
    parallel_clusters = []
    cluster = []
    for node in G.nodes():
        if G.nodes[node]["step"].get("type") == "tool" and G.nodes[node]["server"] == "db":
            cluster.append(node)
        else:
            if cluster:
                parallel_clusters.append(list(cluster))
                cluster = []
    if cluster:
        parallel_clusters.append(cluster)

    if parallel_clusters:
        print("\n[PARALLEL CLUSTERS] Steps that can run in parallel:")
        for idx, c in enumerate(parallel_clusters, 1):
            print(f"Cluster {idx}: {', '.join(c)}")
    else:
        print("\n[PARALLEL CLUSTERS] No parallel steps detected.")

# --- Quick test ---
if __name__ == "__main__":
    sample_plan = [
        {"type":"tool","server":"db","tool":"create_user","arguments":{"name":"Alice","email":"alice@example.com"}},
        {"type":"tool","server":"db","tool":"create_user","arguments":{"name":"Bob","email":"bob@example.com"}},
        {"type":"tool","server":"db","tool":"list_users","arguments":{}},
        {"type":"tool","server":"file","tool":"write_file","arguments":{"path":"users_list.json","content":"[...]"}},
        {"type":"resource","server":"file","uri":"file://users_list.json/"}
    ]
    G = build_dependency_graph(sample_plan)
    visualize_plan_dag(G)
