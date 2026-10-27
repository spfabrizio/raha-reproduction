### P0-A. Topology ingestion and validation

- Import CogentCo graph
- Print actual graph counts, isolated nodes, edge capacity summary, node/edge identifiers, and whether edges are directed or undirected.
- Check the target 197 nodes / 486 edges; if mismatched, record the discrepancy.
- Terminal output or `outputs/topology_summary.json`; optionally an annotated topology figure.

### P0-B. Path generation with backup semantics

- For the demand pairs the current code supports, compute up to five candidate paths using deterministic k-shortest paths; designate four primary and one backup.
- Record missing/disconnected pairs and edge sharing between paths. The fifth path must not be usable while the protected higher-priority primary paths are still available, consistent with the paper's failover policy.
- Sample source–destination pair with its paths, their lengths and shared edges; output path counts.

### P0-C. Healthy vs. failed traffic evaluator
- Define a fixed, explicitly documented demand matrix. Evaluate the healthy topology, then the same demands after one selected edge failure.
- Use an optimization model to maximize total carried demand, subject to per-demand, per-path and link-capacity constraints. If such a model is not implemented yet, report only the structural/failure metrics and do not label them Raha degradation.

### P0-D. Healthy vs. failed traffic evaluator
- Add or adapt one existing command to run a deterministic example and write `outputs/midpoint_results.csv`.
- Recommended CSV columns: `topology,seed,T,max_failures,scenario_method,actual_failure_count,failed_edge_ids,healthy_throughput,failed_throughput,normalized_degradation,runtime_seconds,status`.
- Produce a compact reproduced vs. paper table or plot. Use **N/A** for scenarios not yet executed, and clearly label heuristic/sample-based values rather than claiming global worst-case optima.

### P1. Failure-budget sweep and probability thresholds
- Evaluate one-, two-, and four-failure scenarios, then a probability-constrained arbitrary-failure case.
- Avoid enumerating every four-edge combination on 486 edges; use optimization or a documented approximation/heuristic. For an approximate method, report highest degradation found, not proven maximum degradation.
- Under independent link failures, scenario probability is the product of failed-link probabilities and surviving-link probabilities; the paper enforces the probability constraint in log space. If actual failure probabilities are unavailable, use seeded synthetic probabilities and disclose that limitation.
- At least two k-values side by side; T and seed clearly recorded.

### P2. Eight-cluster demand search, optimization parity, and scale

- Implement the paper's eight-cluster demand approximation and final full-topology failure search if feasible.
- Compare variable-demand versus fixed-demand results.
- A faithful reproduction of Table 4 uses MetaOpt-style joint reasoning about demand and failures, with a suitable optimization solver.
- Track solver status, runtime, timeout, and any optimality gap.