import argparse
import json
import math
from numbers import Real
from pathlib import Path
from statistics import mean

import networkx as nx
import requests

TOPOLOGY_URL = (
    "https://raw.githubusercontent.com/"
    "mroughan/InternetTopologyZoo/main/"
    "graphml/Cogentco.graphml"
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "Cogentco.graphml"
OUTPUT_PATH = DATA_PATH.parent.parent / "outputs" / "topology_summary.json"
TARGET_NODES = 197
TARGET_EDGES = 486


def load_cogentco(data_path: Path | None = None, *, simplify: bool = True) -> nx.Graph:
    """Read GraphML, optionally retaining parallel edges for source validation.

    Download the default dataset if absent. Explicit paths are always local.
    The default simple graph preserves compatibility with path generation.
    Simplification collapses parallel edges without aggregating capacities.
    """
    path = DATA_PATH if data_path is None else Path(data_path)
    if data_path is None and not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(TOPOLOGY_URL, timeout=30)
        response.raise_for_status()
        path.write_bytes(response.content)

    graph = nx.read_graphml(path)
    # NetworkX stores GraphML defaults separately from individual attributes.
    for _, attributes in graph.nodes(data=True):
        for key, value in graph.graph.get("node_default", {}).items():
            attributes.setdefault(key, value)
    for _, _, attributes in graph.edges(data=True):
        for key, value in graph.graph.get("edge_default", {}).items():
            attributes.setdefault(key, value)
    if simplify:
        return nx.DiGraph(graph) if graph.is_directed() else nx.Graph(graph)
    return graph


def summarize_topology(graph: nx.Graph) -> dict:
    """Summarize a source topology; capacities use the exact `capacity` key.

    Report IDs are assigned in sorted endpoint/key order. Source edge IDs are
    retained separately, since GraphML need not supply unique edge IDs.
    """
    edges = []
    source_edges = (
        graph.edges(keys=True, data=True) if graph.is_multigraph()
        else ((u, v, None, data) for u, v, data in graph.edges(data=True))
    )
    for source, target, key, attributes in source_edges:
        if not graph.is_directed():
            source, target = sorted((source, target), key=str)
        edges.append((source, target, key, attributes))
    edges.sort(key=lambda edge: (str(edge[0]), str(edge[1]), str(edge[2])))

    edge_records = []
    capacities = []
    missing_capacity_count = 0
    invalid_capacity_count = 0
    endpoint_groups = {}
    for index, (source, target, key, attributes) in enumerate(edges):
        capacity = attributes.get("capacity")
        if "capacity" not in attributes:
            capacity_status = "missing"
            missing_capacity_count += 1
        elif (
            isinstance(capacity, Real)
            and not isinstance(capacity, bool)
            and math.isfinite(capacity)
            and capacity >= 0
        ):
            capacity_status = "valid"
            capacities.append(capacity)
        else:
            capacity_status = "invalid"
            invalid_capacity_count += 1
        edge_records.append({
            "id": f"edge_{index:04d}",
            "source_id": attributes.get("id"),
            "key": key,
            "source": source,
            "target": target,
            "capacity": capacity if capacity_status == "valid" else None,
            "capacity_status": capacity_status,
        })
        endpoint_groups.setdefault((source, target), []).append(edge_records[-1]["id"])

    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    # Self-loops produce only one arc, so multiplying edge_count by two is unsafe.
    directed_arc_count = graph.to_directed().number_of_edges()
    simplified = nx.DiGraph(graph) if graph.is_directed() else nx.Graph(graph)
    simplified_directed_arc_count = simplified.to_directed().number_of_edges()
    discrepancies = []
    if node_count != TARGET_NODES:
        discrepancies.append(f"Source has {node_count} nodes; target is {TARGET_NODES}.")
    if edge_count != TARGET_EDGES:
        discrepancies.append(
            f"Source has {edge_count} {'directed' if graph.is_directed() else 'undirected'} "
            f"edges; target is {TARGET_EDGES}."
        )

    return {
        "topology": "CogentCo",
        "directed": graph.is_directed(),
        "multigraph": graph.is_multigraph(),
        "node_count": node_count,
        "edge_count": edge_count,
        "directed_arc_count": directed_arc_count,
        "simplified_edge_count": simplified.number_of_edges(),
        "simplified_directed_arc_count": simplified_directed_arc_count,
        "parallel_edge_count": edge_count - simplified.number_of_edges(),
        "parallel_edge_groups": [
            {"source": source, "target": target, "edge_ids": ids}
            for (source, target), ids in endpoint_groups.items() if len(ids) > 1
        ],
        "isolated_node_ids": sorted(nx.isolates(graph), key=str),
        "nodes": [
            {"id": node, "label": attributes.get("label")}
            for node, attributes in sorted(graph.nodes(data=True), key=lambda item: str(item[0]))
        ],
        "edges": edge_records,
        "capacity_summary": {
            "attribute": "capacity",
            "units": "unspecified",
            "valid_edge_count": len(capacities),
            "missing_edge_count": missing_capacity_count,
            "invalid_edge_count": invalid_capacity_count,
            "min": min(capacities) if capacities else None,
            "max": max(capacities) if capacities else None,
            "mean": mean(capacities) if capacities else None,
            "note": "No capacities are inferred or assigned; statistics use valid capacities only.",
        },
        "target_validation": {
            "expected_node_count": TARGET_NODES,
            "expected_edge_count": TARGET_EDGES,
            "source_counts_match": node_count == TARGET_NODES and edge_count == TARGET_EDGES,
            "directed_counts_match": node_count == TARGET_NODES and directed_arc_count == TARGET_EDGES,
            "simplified_directed_counts_match": (
                node_count == TARGET_NODES and simplified_directed_arc_count == TARGET_EDGES
            ),
            "discrepancies": discrepancies,
            "edge_count_note": (
                "Directed arc count uses the source graph as directed, or replaces each "
                "undirected link with both orientations. Matching this count does not "
                "establish the paper's capacity or failure semantics."
            ),
            "simplification_note": (
                "The path loader defaults to a simple graph, collapsing parallel edges. "
                "Simplified counts are structural only; capacities are not aggregated."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load and validate the CogentCo topology.")
    parser.add_argument("--input", type=Path, help="Local GraphML file (default: bundled Cogentco).")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Summary JSON destination.")
    args = parser.parse_args()
    summary = summarize_topology(load_cogentco(args.input, simplify=False))
    summary["source_file"] = str(args.input) if args.input else "data/Cogentco.graphml"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    direction = "directed" if summary["directed"] else "undirected"
    print(f"CogentCo: {summary['node_count']} nodes, {summary['edge_count']} {direction} edges")
    print(f"Directed arcs: {summary['directed_arc_count']}")
    print(
        f"Simple graph: {summary['simplified_edge_count']} edges, "
        f"{summary['simplified_directed_arc_count']} directed arcs "
        f"({summary['parallel_edge_count']} parallel edges collapsed)"
    )
    for group in summary["parallel_edge_groups"]:
        connector = "->" if summary["directed"] else "--"
        print(f"Parallel edges: {group['source']} {connector} {group['target']}: {group['edge_ids']}")
    print(f"Isolated nodes ({len(summary['isolated_node_ids'])}): {summary['isolated_node_ids']}")
    capacity = summary["capacity_summary"]
    print(
        f"Capacities: {capacity['valid_edge_count']} valid, {capacity['missing_edge_count']} missing, "
        f"{capacity['invalid_edge_count']} invalid; "
        f"min/max/mean: {capacity['min']}/{capacity['max']}/{capacity['mean']} (units unspecified)"
    )
    validation = summary["target_validation"]
    print(f"Target: {TARGET_NODES} nodes / {TARGET_EDGES} edges")
    for discrepancy in validation["discrepancies"]:
        print(f"Discrepancy: {discrepancy}")
    print(f"Directed representation matches target: {validation['directed_counts_match']}")
    print(f"Simplified directed representation matches target: {validation['simplified_directed_counts_match']}")
    print(f"Full node/edge identifiers and validation details: {args.output}")


if __name__ == "__main__":
    main()
