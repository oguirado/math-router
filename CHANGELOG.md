# Changelog

## v2.0.1

First tagged release of math-router: 719 structured papers derived from openai/math (Apache-2.0) and an offline router that answers in at most 2,000 bytes.

### Added
- `.github/workflows/ci.yml`: index byte-identity check, the 14 release gates, TEST reproduction, unit tests, documentation claims check and a secret scan (Python 3.11, standard library only).
- `tools/claims_check.py`: fails when a README, ARCHITECTURE, AGENTS or `docs/` file names a path, tool or flag that does not exist.
- Community files: `CONTRIBUTING.md`, `SECURITY.md`, `CITATION.cff`, pull request and bug report templates.
- `catalogue/README.md`: mount path and edge location notes.
- README: badges, three-command quick start, "Reproduce the numbers" and "What is measured vs claimed".

### Changed
- ARCHITECTURE.md describes the shipped tree and the CI exactly; the earlier "local hook and protected CI check" wording is removed.
- `.gitignore` covers virtual environments, caches and build output.
- Model versions in the README are dated (as of 2026-10).

### Removed
- catalogue/graph.jsonl (empty, read by no tool or test) and its entry in `release/manifest.json`; the relations the router uses live in `out/index/edges.json`.

### Measured (from `test_eval/test_run_v2.0.1.json`, `test_eval/cold_latency_TEST.json`, `out/gates_v2.0.1.json`)
- TEST, 72 queries (39 answerable, 33 not): R@1 0.2220, R@5 0.5160, MRR 0.5958, nDCG@5 0.4627; answer bytes p50 1,077, max 1,167; abstention precision 0.6286, recall 0.6667, F1 0.6471.
- v1 budgeted to 2,000 B: R@1 0.0904, R@5 0.1139; v1 unbudgeted: R@1 0.0904, R@5 0.2662, answers up to 22,181 bytes.
- Cold latency p50 58.0 ms (v2) vs 87.2 ms (v1), 30 runs, on the measuring machine.
- Gates: 14 of 14 pass. Unit tests: 93 (1 skipped).
- Index sha256 `2c1459766a263fdc...`, parameters sha256 `ad1c42c79dad98fa...`.

### Known limits
Recall at rank 1 is 0.22; abstention is a lexical heuristic; per-class numbers are anecdotal. One DEV pair (W-R12, PM-101.1) is unjudged and disclosed in `docs/RESULTS.md`.
