import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from src.topology import load_cogentco
from src.paths import generate_paths, usable_paths, path_edges


RESULTS = Path("results")

def validate_paths(graph, source, target, primary, backup):
    assert source != target
    assert len(primary) <= 4
    assert len(backup) <= 1

    paths = primary + backup
    assert len(paths) == len({tuple(p) for p in paths})

    for path in paths:
        assert path[0] == source
        assert path[-1] == target
        assert len(path) == len(set(path))

        for u, v in zip(path, path[1:]):
            assert graph.has_edge(u, v)

    active_primary, active_backup = usable_paths(graph, primary, backup, set())

    assert len(active_primary) == len(primary)
    assert len(active_backup) == 0

    print("Path validity: PASS")
    print("No-failure backup policy: PASS")


def export_path_table(graph, primary, backup):
    backup_edges = (path_edges(graph, backup[0]) if backup else set())

    rows = []

    for index, path in enumerate(primary + backup):
        is_backup = index >= len(primary)
        edges = path_edges(graph, path)

        rows.append({
            "path": (
                f"Backup {index - len(primary) + 1}"
                if is_backup else f"Primary {index + 1}"
            ),
            "hops": len(path) - 1,
            "shared_with_backup": (
                "" if is_backup
                else len(edges & backup_edges)
            ),
            "nodes": " -> ".join(map(str, path)),
        })

    with open(RESULTS / "path_validation.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print("\nPath measurements:")
    for row in rows:
        print(f"{row['path']}: {row['hops']} hops, " f"shared with backup: {row['shared_with_backup']}")


def validate_failover(graph, primary, backup):
    no_failure_primary, no_failure_backup = usable_paths(graph, primary, backup, set())

    result = {
        "no_failure": {
            "usable_primary": len(no_failure_primary),
            "usable_backup": len(no_failure_backup),
        }
    }

    backup_edges = (path_edges(graph, backup[0]) if backup else set())

    candidate_edges = set()

    for path in primary:
        candidate_edges.update(path_edges(graph, path) - backup_edges)

    candidates = sorted(candidate_edges, key=lambda e: (str(e[0]), str(e[1])))

    selected = None

    for edge in candidates:
        active_primary, active_backup = usable_paths(graph, primary, backup, {edge})

        if (len(active_primary) == len(primary) - 1 and len(active_backup) == 1):
            selected = (edge, active_primary, active_backup)
            break

    if selected is None:
        for edge in candidates:
            active_primary, active_backup = usable_paths(graph, primary, backup, {edge})

            if len(active_primary) < len(primary) and active_backup:
                selected = (edge, active_primary, active_backup)
                break

    if selected is not None:
        edge, active_primary, active_backup = selected

        result["single_edge_failure"] = {
            "failed_edge": list(edge),
            "usable_primary": len(active_primary),
            "usable_backup": len(active_backup),
        }

        assert len(active_backup) == 1

        print("\nFailover validation: PASS")
        print(f"Failed edge: {edge}")
        print(f"Usable primary paths: {len(active_primary)}")
        print(f"Usable backup paths: {len(active_backup)}")

    else:
        result["single_edge_failure"] = {
            "status": "No qualifying single-edge failure found"
        }
        print("\nNo qualifying single-edge failover scenario found")

    with open(RESULTS / "failover_validation.json", "w") as f:
        json.dump(result, f, indent=2)


def audit_pairs(graph, source, target, count=10):
    nodes = sorted(graph.nodes, key=str)
    pairs = [(source, target)]

    for i in range(len(nodes) // 2):
        pair = (nodes[i], nodes[-1 - i])
        if pair[0] != pair[1] and pair not in pairs:
            pairs.append(pair)
        if len(pairs) >= count:
            break

    rows = []

    for s, t in pairs:
        primary, backup = generate_paths(graph, s, t)

        rows.append({
            "source": s,
            "target": t,
            "primary_count": len(primary),
            "backup_count": len(backup),
            "status": (
                "disconnected" if not primary
                else "insufficient_paths"
                if len(primary) + len(backup) < 5
                else "complete"
            ),
        })

    with open(RESULTS / "pair_audit.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nAudited {len(rows)} demand pairs")
    for row in rows:
        print(
            f"{row['source']} -> {row['target']}: "
            f"{row['primary_count']} primary, "
            f"{row['backup_count']} backup "
            f"({row['status']})"
        )


def audit_disconnected_pairs(graph):
    nodes = sorted(graph.nodes, key=str)
    missing = 0

    with open( RESULTS / "disconnected_pairs.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target"])

        for source in nodes:
            reachable = nx.descendants(graph, source)

            for target in nodes:
                if source != target and target not in reachable:
                    writer.writerow([source, target])
                    missing += 1

    print(f"\nUnreachable ordered demand pairs: {missing}")


def visualize_paths(graph, source, target, primary, backup):
    primary_edges = set()
    backup_edges = set()

    for path in primary:
        primary_edges.update(path_edges(graph, path))

    for path in backup:
        backup_edges.update(path_edges(graph, path))

    shared = primary_edges & backup_edges
    primary_only = primary_edges - backup_edges
    backup_only = backup_edges - primary_edges

    subgraph = (
        nx.DiGraph() if graph.is_directed()
        else nx.Graph()
    )

    subgraph.add_edges_from(
        sorted(
            primary_edges | backup_edges,
            key=lambda e: (str(e[0]), str(e[1]))
        )
    )

    positions = nx.spring_layout(subgraph, seed=42)

    fig, ax = plt.subplots(figsize=(13, 8))

    nx.draw_networkx_nodes(
        subgraph, positions,
        node_size=350, node_color="lightgray", ax=ax
    )

    nx.draw_networkx_labels(
        subgraph, positions, font_size=8, ax=ax
    )

    groups = [
        (primary_only, "steelblue", "solid", "Primary only"),
        (backup_only, "darkorange", "dashed", "Backup only"),
        (shared, "purple", "solid", "Shared"),
    ]

    from matplotlib.lines import Line2D
    legend = []

    for edges, color, style, label in groups:
        if edges:
            nx.draw_networkx_edges(
                subgraph, positions,
                edgelist=sorted(edges, key=str),
                edge_color=color,
                style=style,
                width=2.5,
                arrows=graph.is_directed(),
                ax=ax,
            )
            legend.append(
                Line2D(
                    [0], [0], color=color,
                    linestyle=style, linewidth=2.5,
                    label=label
                )
            )

    ax.legend(handles=legend, loc="upper right")
    ax.set_title(
        f"CogentCo Candidate Paths: {source} to {target}\n"
        f"{len(primary)} Primary, {len(backup)} Backup"
    )
    ax.axis("off")

    fig.tight_layout()
    fig.savefig(RESULTS / "path_visualization.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    print("\nSaved path visualization")


def main():
    RESULTS.mkdir(exist_ok=True)

    graph = load_cogentco()

    print(
        f"Topology: {graph.number_of_nodes()} nodes, "
        f"{graph.number_of_edges()} edges"
    )

    print(f"Undirected links: {graph.number_of_edges()}")
    print(f"Directed arcs: {graph.to_directed().number_of_edges()}")

    source, target = "0", "196"

    primary, backup = generate_paths(graph, source, target)

    if not primary:
        raise RuntimeError("No path exists for sample pair")

    print(f"\nSource: {source}")
    print(f"Target: {target}")
    print(f"Primary paths: {len(primary)}")
    print(f"Backup paths: {len(backup)}\n")

    validate_paths(graph, source, target, primary, backup)
    export_path_table(graph, primary, backup)
    validate_failover(graph, primary, backup)
    audit_pairs(graph, source, target)
    audit_disconnected_pairs(graph)
    visualize_paths(graph, source, target, primary, backup)

    print("\nP0-B validation complete. Results saved to results/")


if __name__ == "__main__":
    main()
