import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # save figures without a display
import matplotlib.pyplot as plt
import networkx as nx

from src.topology import load_cogentco
from src.traffic import DEMANDS, ARC_CAPACITY, Demand, evaluate_traffic


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FAILED_EDGE = ("7", "8")  # physical link, disabled in both directions
PAPER_AVG_LAG_CAPACITY = 1000.0  # Table 4 denominator, NOT an assigned capacity map


def save_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def validate_shared_capacity():
    toy = nx.Graph()
    toy.add_edges_from([("s", "a"), ("u", "a"), ("a", "t")])
    toy_demands = (
        Demand("s", "t", 1000.0),
        Demand("u", "t", 1000.0),
    )
    result = evaluate_traffic(toy, toy_demands, set(), arc_capacity=1000.0)
    assert abs(result["throughput"] - 1000.0) < 1e-6, result
    assert abs(result["max_arc_utilization"] - 1.0) < 1e-6, result
    print("Shared-capacity LP sanity check: PASS")


def main():
    validate_shared_capacity()
    RESULTS.mkdir(parents=True, exist_ok=True)
    graph = load_cogentco()
    if not graph.has_edge(*FAILED_EDGE):
        raise ValueError(f"Selected link {FAILED_EDGE} is absent")

    # The graph, path selection, demands and capacities are unchanged.
    # The only change is failure of one selected physical link.
    healthy = evaluate_traffic(graph, DEMANDS, failed_edges=set())
    failed = evaluate_traffic(graph, DEMANDS, failed_edges={FAILED_EDGE})

    raw_loss = healthy["throughput"] - failed["throughput"]
    normalized_loss = raw_loss / PAPER_AVG_LAG_CAPACITY

    demand_rows = []
    for i, demand in enumerate(DEMANDS):
        healthy_carried = healthy["served_by_demand"][i]
        failed_carried = failed["served_by_demand"][i]
        demand_rows.append({
            "source": demand.source,
            "target": demand.target,
            "requested": demand.amount,
            "healthy_carried": healthy_carried,
            "failed_carried": failed_carried,
            "throughput_loss": healthy_carried - failed_carried,
        })
    save_csv(
        RESULTS / "traffic_by_demand.csv", demand_rows,
        ["source", "target", "requested", "healthy_carried",
         "failed_carried", "throughput_loss"],
    )

    path_rows = []
    for scenario, result in (("healthy", healthy), ("failed", failed)):
        for path in result["path_allocations"]:
            path_rows.append({"scenario": scenario, **path})
    save_csv(
        RESULTS / "traffic_by_path.csv", path_rows,
        ["scenario", "source", "target", "role", "path_number",
         "eligible", "hops", "carried", "nodes"],
    )

    summary = {
        "experiment": "P0-C illustrative fixed-demand LP; not Raha Table 4",
        "topology": "CogentCo",
        "nodes": graph.number_of_nodes(),
        "undirected_links": graph.number_of_edges(),
        "directed_arcs": 2 * graph.number_of_edges(),
        "demand_matrix": [
            {"source": d.source, "target": d.target, "amount": d.amount}
            for d in DEMANDS
        ],
        "assumptions": {
            "candidate_paths": "4 primary and 1 backup; hop-count shortest",
            "backup": "first backup eligible when any primary fails",
            "arc_capacity_model": "uniform synthetic capacity, independent directions",
            "arc_capacity": ARC_CAPACITY,
            "failure_model": "one undirected physical link disables both arcs",
            "normalization": "paper Table 4 average LAG capacity",
            "normalization_denominator": PAPER_AVG_LAG_CAPACITY,
        },
        "failed_physical_link": list(FAILED_EDGE),
        "healthy": {k: v for k, v in healthy.items() if k != "path_allocations"},
        "failed": {k: v for k, v in failed.items() if k != "path_allocations"},
        "raw_throughput_loss": raw_loss,
        "sample_normalized_throughput_loss": normalized_loss,
        "paper_table4_reproduction": False,
    }
    (RESULTS / "traffic_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    fig, ax = plt.subplots(figsize=(7, 4))
    values = [healthy["requested"], healthy["throughput"], failed["throughput"]]
    bars = ax.bar(["Requested", "Healthy", "Failed"], values)
    ax.bar_label(bars, fmt="%.2f", padding=3)
    ax.set_ylabel("Traffic units")
    ax.set_title("P0-C: fixed demands and synthetic capacities\nNot a Raha Table 4 reproduction")
    ax.set_ylim(0, max(values) * 1.15 if any(values) else 1)
    fig.tight_layout()
    fig.savefig(RESULTS / "traffic_comparison.png", dpi=180)
    plt.close(fig)

    assert healthy["status"] == failed["status"] == "optimal"
    assert abs(sum(healthy["served_by_demand"]) - healthy["throughput"]) < 1e-6
    assert abs(sum(failed["served_by_demand"]) - failed["throughput"]) < 1e-6
    assert healthy["throughput"] <= healthy["requested"] + 1e-6
    assert failed["throughput"] <= failed["requested"] + 1e-6

    print("=== P0-C: healthy vs. failed throughput ===")
    print(f"Topology: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} physical links")
    print(f"Fixed demands: {len(DEMANDS)} x 1000 units")
    print(f"Synthetic capacity: {ARC_CAPACITY:.0f} units / directed arc")
    print(f"Failed physical link: {FAILED_EDGE}")
    print(f"Requested: {healthy['requested']:.2f}")
    print(f"Healthy throughput: {healthy['throughput']:.2f}")
    print(f"Failed throughput: {failed['throughput']:.2f}")
    print(f"Raw throughput loss: {raw_loss:.2f}")
    print(f"Loss / paper normalization (1000): {normalized_loss:.4f}")
    print("\nPer-demand results:")
    for row in demand_rows:
        print(f"  {row['source']} -> {row['target']}: "
              f"healthy={row['healthy_carried']:.2f}, "
              f"failed={row['failed_carried']:.2f}")
    print("\nIllustrative fixed-demand scenario; NOT a Table 4 reproduction.")
    print(f"Outputs saved to {RESULTS}")


if __name__ == "__main__":
    main()