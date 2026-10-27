
from itertools import islice
import networkx as nx


def generate_paths(graph: nx.Graph, source: str, target: str, num_primary: int = 4, num_backup: int = 1) -> tuple[list[list[str]], list[list[str]]]:

    if num_primary < 1 or num_backup < 0:
        raise ValueError("Invalid number of paths")

    if graph.is_multigraph():
        raise ValueError("Expected a simple Graph or DiGraph")

    if source not in graph or target not in graph:
        raise nx.NodeNotFound("Source or target not in graph")

    if source == target:
        raise ValueError("Source and target must differ")

    # Insert nodes and edges in sorted order for deterministic
    # tie-breaking when multiple paths have equal hop counts.
    ordered = nx.DiGraph() if graph.is_directed() else nx.Graph()
    ordered.add_nodes_from(sorted(graph.nodes, key=str))

    edges = list(graph.edges())
    if not graph.is_directed():
        edges = [tuple(sorted(e, key=str)) for e in edges]

    ordered.add_edges_from(sorted(edges, key=lambda e: (str(e[0]), str(e[1]))))

    try:
        paths = list(islice(
            nx.shortest_simple_paths(ordered, source, target),
            num_primary + num_backup
        ))
    except nx.NetworkXNoPath:
        paths = []

    primary = paths[:num_primary]
    backup = paths[num_primary:]

    return primary, backup


def path_edges(graph: nx.Graph, path: list[str]) -> set[tuple]:
    if graph.is_directed():
        return set(zip(path, path[1:]))

    return {
        tuple(sorted((u, v), key=str))
        for u, v in zip(path, path[1:])
    }


def usable_paths(graph: nx.Graph, primary: list[list[str]], backup: list[list[str]], failed_edges: set[tuple[str, str]]) -> tuple[list[list[str]], list[list[str]]]:
    if len(backup) > 1:
        raise NotImplementedError("Only one backup is supported")

    # Normalize undirected edges so (A,B) == (B,A).
    failed = set()
    for u, v in failed_edges:
        failed.update(path_edges(graph, [u, v]))

    def survives(path):
        return not (path_edges(graph, path) & failed)

    available_primary = [path for path in primary if survives(path)]

    # The first backup is only eligible after a primary fails.
    primary_failed = len(available_primary) < len(primary)

    available_backup = [path for path in backup if primary_failed and survives(path)]

    return available_primary, available_backup
