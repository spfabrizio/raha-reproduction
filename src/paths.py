
from itertools import islice
import networkx as nx
from src.topology import load_cogentco


def generate_paths(graph: nx.Graph, source: str, target: str, num_primary: int = 4, num_backup: int = 1,) -> tuple[list[list[str]], list[list[str]]]:
    if num_primary < 1 or num_backup < 0:
        raise ValueError("Invalid number of paths")

    if graph.is_multigraph():
        raise ValueError("Expected a simple Graph or DiGraph")

    if source not in graph or target not in graph:
        raise nx.NodeNotFound("Source or target not in graph")

    if source == target:
        raise ValueError("Source and target must differ")

    try:
        paths = list(islice(nx.shortest_simple_paths(graph, source, target), num_primary + num_backup,))
    except nx.NetworkXNoPath:
        paths = []

    primary = paths[:num_primary]
    backup = paths[num_primary:]

    return primary, backup

if __name__ == "__main__":
    graph = load_cogentco()

    nodes = list(graph.nodes)
    source, target = nodes[0], nodes[-1]

    primary, backup = generate_paths(graph, source, target)

    print(f"Source: {source}")
    print(f"Target: {target}")
    print(f"Primary paths: {primary}")
    print(f"Backup paths: {backup}")
