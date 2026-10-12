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
