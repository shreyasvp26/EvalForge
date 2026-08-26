# EvalForge Coding Benchmark v1

Canonical multi-case coding benchmark for reproducible agent evaluation.

Each task is a small, deterministic Python package with intentional bugs and
pytest coverage. Benchmark CaseVersions pin this repository at an exact SHA and
set `subdirectory` to the task path.

## Tasks

| Key               | Path                      | Category  | Skill               |
| ----------------- | ------------------------- | --------- | ------------------- |
| 01-calculator-add | `tasks/01-calculator-add` | bugfix    | arithmetic repair   |
| 02-fibonacci      | `tasks/02-fibonacci`      | bugfix    | off-by-one          |
| 03-merge-dicts    | `tasks/03-merge-dicts`    | feature   | data transformation |
| 04-parse-csv      | `tasks/04-parse-csv`      | edge-case | CSV parsing         |
| 05-clamp          | `tasks/05-clamp`          | bugfix    | boundary conditions |

## Grading

Every task is graded with workspace pytest:

```
python3 -m pytest tests/ -q
```

Do not modify test files.

## Publishing

Publish this directory as a public Git repository and pin the broken-state commit
SHA in EvalForge CaseVersions. Never pin `main`/`latest`.
