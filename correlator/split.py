from correlator.graph import hop_distance, adjacency

def should_split(a: list[dict], b: list[dict], edges: list[dict], max_hop: int = 4) -> bool:
    g = adjacency(edges)
    nodes_a = {s["node_id"] for s in a}
    nodes_b = {s["node_id"] for s in b}
    for na in nodes_a:
        for nb in nodes_b:
            if hop_distance(g, na, nb, max_hop) <= max_hop:
                return False
    return True  # disjoint on graph → keep as separate incidents