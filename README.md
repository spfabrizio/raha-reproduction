# Raha Reproduction

Reproduction project targeting the CogentCo experiement (Table 4) from Raha (SIGCOMM 2025).

## Development environment

We use **Python 3.14** in **WSL2 / Ubuntu**. Keep the repository in the Linux filesystem.

```bash
cd ~/projects/raha-reproduction
uv venv --python 3.14 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Topology ingestion and validation (P0-A)

From the repository root, with the environment activated:

```bash
python -m src.topology
```

This prints a compact summary and writes `outputs/topology_summary.json`, including
all node IDs and labels, edge IDs and endpoints, isolated node IDs, capacity
statistics, and discrepancies against the target **197 nodes / 486 edges**.
Use `--input path/to/topology.graphml` to inspect a local file and
`--output path/to/summary.json` to change the report destination. The default
CogentCo file is downloaded only if it is absent; explicit input paths are local.

The bundled GraphML contains **197 nodes and 245 undirected edges**, including
two parallel-edge pairs: nodes `143`/`42` and `80`/`81`. Preserving every edge
yields **490 directed arcs**. Collapsing parallel edges gives **243 simple
undirected links / 486 directed arcs**, matching the target counts. The report
records the source discrepancy, parallel-edge groups, and both representations.
These are structural counts; capacity sharing and failure semantics still need
to be defined for subsequent experiments.

The summary command loads every source edge. For compatibility with path
generation, `load_cogentco()` continues to return a simple graph by default;
`load_cogentco(simplify=False)` preserves parallel edges. Both preserve source
directionality. Simplification does not aggregate capacities.

The dataset supplies **no edge capacities**. The report leaves them as `null`
and records 245 missing values; it does not assign defaults. Capacity statistics
use only finite, nonnegative numbers in the exact `capacity` attribute, including
GraphML defaults. Units remain unspecified. Invalid capacities are counted
separately and represented as `null` in edge records.

Node `id` values are the GraphML node identifiers. Edge `source_id` values retain
the source `id` attribute (or `null` when absent), and `key` distinguishes parallel
edges. Report IDs (`edge_0000`, etc.) are assigned in sorted endpoint/key order
for deterministic output. These report IDs are stable for
the same topology, but can change when its edge set changes. The JSON lists
source undirected edges once; `directed_arc_count` preserves parallel edges and
`simplified_directed_arc_count` records the simple directed representation.
Count mismatches are recorded without assertions so a report is still produced.

Run the validation tests with:

```bash
python -m pytest
```

## Branch and PR policy

- `main` is the integration branch. Do not commit or push directly to `main`.
- Make one branch per logical change, starting from the latest `main`.
- Open a Pull Request (PR) into `main` for each change.
- The other contributor reviews the PR; aim for one approval and passing automated checks before merging.
- Either contributor may merge an approved PR when required checks pass.
- Multiple independent branches/PRs can be open simultaneously. Editing different files reduces merge conflicts, but does not guarantee that combined changes work correctly.

### Branch names and PR titles

| Change | Branch example | PR title example |
| --- | --- | --- |
| Project maintenance | `chore/add-requirements` | `chore: add Python dependencies` |
| New feature | `feat/topology-loader` | `feat: load CogentCo topology` |
| Tests | `test/topology-loader` | `test: validate topology loading` |
| Bug fix | `fix/directed-edges` | `fix: correct directed edge conversion` |
| Documentation | `docs/setup-guide` | `docs: document local setup` |
| CI | `ci/run-pytest` | `ci: run tests on pull requests` |

Keep PRs small, with descriptive titles and a short explanation of what changed and how it was tested.

## Standard workflow: one feature or fix

1. Start from the latest `main`. Check for uncommitted changes first (`git status`); commit or stash them before switching if needed.

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/topology-loader
```

2. Make the change and run relevant tests. Once tests exist, run:

```bash
python -m pytest
```

3. Stage and review only the files you intend to commit.

```bash
git status
git add path/to/changed_file.py
git diff --cached --stat
git diff --cached
```

Use `git add .` only after checking that unrelated files, virtual environments, outputs, and secrets will not be included.

4. Commit and push the feature branch.

```bash
git commit -m "feat: load CogentCo topology"
git push -u origin feat/topology-loader
```

5. On GitHub, create the PR. Choose `base: main` and `compare: feat/topology-loader`. Request the other contributor as a reviewer. Use a Draft PR if the work is still in progress; mark it Ready for review when complete.

6. Review and merge. The reviewer checks the code, tests, and assumptions, then approves or requests changes. After approval and required checks, merge into `main` on GitHub.

7. Update the local repository and clean up.

```bash
git switch main
git pull --ff-only origin main
git branch -d feat/topology-loader
```

Optionally delete the merged branch on GitHub as well.
