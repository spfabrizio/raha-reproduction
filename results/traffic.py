
from dataclasses import dataclass

import networkx as nx
import numpy as np
from scipy.optimize import linprog

from src.paths import generate_paths, usable_paths, path_edges


@dataclass(frozen=True)
class Demand:
    source: str
    target: str
    amount: float


# Fixed synthetic demands, in traffic units.
DEMANDS = [
    Demand("0", "196", 100.0),
    Demand("10", "97", 100.0),
    Demand("100", "96", 100.0),
]

# Every undirected physical link has this shared capacity.
LINK_CAPACITY = 1000.0


def evaluate_traffic(
    graph: nx.Graph,
    demands: list[Demand],
    failed_edges: set[tuple[str, str]],
    link_capacity: float = LINK_CAPACITY,
) -> dict:
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError("P0-C expects a simple undirected Graph")

    if link_capacity <= 0:
        raise ValueError("Link capacity must be positive")

    if any(d.amount < 0 or d.source == d.target for d in demands):
        raise ValueError("Invalid demand")

    if any(
        d.source not in graph or d.target not in graph
        for d in demands
    ):
        raise ValueError("Demand endpoint not in graph")

    if any(not graph.has_edge(u, v) for u, v in failed_edges):
        raise ValueError("Failed edge not present in graph")

    # Normalize failed edges to match the path representation.
    failed = set().union(*(
        path_edges(graph, [u, v])
        for u, v in failed_edges
    ))

    # Each variable represents the flow on one eligible
    # path for one demand.
    variables = []
    eligible_path_counts = []

    for demand_id, demand in enumerate(demands):
        primary, backup = generate_paths(
            graph, demand.source, demand.target
        )

        active_primary, active_backup = usable_paths(
            graph, primary, backup, failed_edges
        )

        eligible = active_primary + active_backup
        eligible_path_counts.append(len(eligible))

        for path in eligible:
            variables.append((
                demand_id,
                path_edges(graph, path)
            ))

    # No available paths means no traffic can be carried.
    if not variables:
        return {
            "status": "optimal",
            "throughput": 0.0,
            "requested": float(sum(d.amount for d in demands)),
            "served_by_demand": [0.0] * len(demands),
            "eligible_path_counts": eligible_path_counts,
            "path_variables": 0,
        }

    # Create one capacity constraint per used physical link.
    used_edges = sorted(
        {edge for _, edges in variables for edge in edges},
        key=str
    )

    edge_row = {
        edge: i + len(demands)
        for i, edge in enumerate(used_edges)
    }

    # A @ x <= rhs
    A = np.zeros((
        len(demands) + len(used_edges),
        len(variables)
    ))

    rhs = np.array(
        [d.amount for d in demands]
        + [link_capacity] * len(used_edges),
        dtype=float
    )

    for col, (demand_id, edges) in enumerate(variables):
        # Total flow for this demand <= requested amount.
        A[demand_id, col] = 1.0

        # Every link used by this path consumes capacity.
        for edge in edges:
            A[edge_row[edge], col] = 1.0

    # Maximize total flow by minimizing its negative.
    result = linprog(
        c=-np.ones(len(variables)),
        A_ub=A,
        b_ub=rhs,
        bounds=[
            (0.0, demands[demand_id].amount)
            for demand_id, _ in variables
        ],
        method="highs",
    )

    if not result.success:
        raise RuntimeError(f"LP failed: {result.message}")

    # Verify all demand and link-capacity constraints.
    if np.any(A @ result.x > rhs + 1e-6):
        raise AssertionError(
            "LP result violates a demand or link capacity"
        )

    served = [0.0] * len(demands)

    for (demand_id, _), amount in zip(variables, result.x):
        served[demand_id] += float(amount)

    return {
        "status": "optimal",
        "throughput": float(sum(served)),
        "requested": float(sum(d.amount for d in demands)),
        "served_by_demand": served,
        "eligible_path_counts": eligible_path_counts,
        "path_variables": len(variables),
    }
