from dataclasses import dataclass
from math import isfinite

import networkx as nx
import numpy as np
from scipy.optimize import linprog

from src.paths import generate_paths, usable_paths


@dataclass(frozen=True)
class Demand:
    source: str
    target: str
    amount: float


# Fixed, synthetic traffic matrix. Identical in healthy/failed experiments.
DEMANDS = (
    Demand("0", "196", 1000.0),
    Demand("10", "97", 1000.0),
    Demand("100", "96", 1000.0),
)

# Uniform *synthetic* directed-arc capacity, not measured per-link data.
ARC_CAPACITY = 1000.0


def evaluate_traffic(graph: nx.Graph, demands: list[Demand] | tuple[Demand, ...], failed_edges: set[tuple[str, str]], arc_capacity: float = ARC_CAPACITY) -> dict:
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError("Expected the simple undirected CogentCo graph")
    if not isfinite(arc_capacity) or arc_capacity <= 0:
        raise ValueError("arc_capacity must be finite and positive")

    for demand in demands:
        if demand.source not in graph or demand.target not in graph:
            raise ValueError("Demand endpoint missing from topology")
        if demand.source == demand.target:
            raise ValueError("Demand endpoints must differ")
        if not isfinite(demand.amount) or demand.amount < 0:
            raise ValueError("Demand must be finite and nonnegative")

    for u, v in failed_edges:
        if not graph.has_edge(u, v):
            raise ValueError(f"Failed physical link ({u}, {v}) not in graph")

    failed_links = {frozenset((u, v)) for u, v in failed_edges}
    paths = []
    active_counts = []

    for demand_id, demand in enumerate(demands):
        primary, backup = generate_paths(graph, demand.source, demand.target, num_primary=4, num_backup=1,)
        active_primary, active_backup = usable_paths(graph, primary, backup, failed_edges)
        eligible_paths = {tuple(p) for p in active_primary + active_backup}
        active_counts.append(len(eligible_paths))

        for i, path in enumerate(primary + backup):
            paths.append({
                "demand_id": demand_id,
                "source": demand.source,
                "target": demand.target,
                "role": "primary" if i < len(primary) else "backup",
                "path_number": i + 1,
                "nodes": path,
                "arcs": list(zip(path, path[1:])),
                "eligible": tuple(path) in eligible_paths,
            })

    requested = float(sum(d.amount for d in demands))
    if not paths:
        return {
            "status": "optimal",
            "requested": requested,
            "throughput": 0.0,
            "served_by_demand": [0.0] * len(demands),
            "eligible_path_counts": active_counts,
            "path_variables": 0,
            "max_arc_utilization": 0.0,
            "path_allocations": [],
        }

    used_arcs = sorted(
        {arc for path in paths for arc in path["arcs"]},
        key=lambda arc: (str(arc[0]), str(arc[1])),
    )
    arc_row = {arc: i + len(demands) for i, arc in enumerate(used_arcs)}

    # Demand constraints: sum_p x[d,p] <= D[d].
    # Arc constraints: sum_{d,p containing arc} x[d,p] <= C[arc].
    A = np.zeros((len(demands) + len(used_arcs), len(paths)))
    rhs = np.array(
        [d.amount for d in demands]
        + [
            0.0 if frozenset(arc) in failed_links else arc_capacity
            for arc in used_arcs
        ],
        dtype=float,
    )

    bounds = []
    for j, path in enumerate(paths):
        demand_id = path["demand_id"]
        A[demand_id, j] = 1.0
        for arc in path["arcs"]:
            A[arc_row[arc], j] = 1.0
        # Path-extension capacity: demand if eligible, otherwise zero.
        bounds.append((0.0, demands[demand_id].amount if path["eligible"] else 0.0))

    solution = linprog(
        c=-np.ones(len(paths)),  # maximize throughput
        A_ub=A,
        b_ub=rhs,
        bounds=bounds,
        method="highs",
    )
    if not solution.success:
        raise RuntimeError(f"Traffic LP failed: {solution.message}")

    tolerance = 1e-6
    if np.any(A @ solution.x > rhs + tolerance):
        raise AssertionError("LP violates demand or arc capacity constraints")
    for j, (_, upper) in enumerate(bounds):
        if solution.x[j] > upper + tolerance or solution.x[j] < -tolerance:
            raise AssertionError("LP violates a per-path flow bound")

    served = [0.0] * len(demands)
    allocated_paths = []
    for path, amount in zip(paths, solution.x):
        amount = 0.0 if abs(float(amount)) < 1e-9 else float(amount)
        served[path["demand_id"]] += amount
        allocated_paths.append({
            "source": path["source"],
            "target": path["target"],
            "role": path["role"],
            "path_number": path["path_number"],
            "eligible": path["eligible"],
            "hops": len(path["arcs"]),
            "carried": amount,
            "nodes": " -> ".join(map(str, path["nodes"])),
        })

    loads = A[len(demands):] @ solution.x
    capacities = rhs[len(demands):]
    utilizations = [
        float(load / cap) for load, cap in zip(loads, capacities)
        if cap > 0
    ]

    return {
        "status": "optimal",
        "requested": requested,
        "throughput": float(sum(served)),
        "served_by_demand": served,
        "eligible_path_counts": active_counts,
        "path_variables": len(paths),
        "max_arc_utilization": max(utilizations, default=0.0),
        "path_allocations": allocated_paths,
    }
