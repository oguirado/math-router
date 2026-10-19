# Changelog

## Lineage

math-router v1 and v2.0.0 were internal versions and were never published; their history is not part of this repository. This repository has one root commit, `fee4236`, created fresh for publication from a clean export (no earlier history was imported); every later commit is a public one. CI scans the full history with gitleaks, so a credential in any commit would fail it. v2.0.1 is the first public release and the first tagged one. The frozen v1 router and index are kept (`v1_frozen/`, `out/v1_index/`) only as the comparison baseline of the benchmark.

## v2.0.1

First tagged release of math-router: 719 structured papers derived from openai/math (Apache-2.0) and an offline router that answers in at most 2,000 bytes.

### Added
- `.github/workflows/ci.yml`: index byte-identity check, the 14 router gates, TEST reproduction, DEV tuning reproduction, unit tests, documentation claims check, publication lint and a secret scan; Python 3.10 to 3.13, standard library only; actions pinned to commit SHAs and the gitleaks binary verified by sha256.
- `tools/claims_check.py`: fails when a README, ARCHITECTURE, AGENTS or `docs/` file names a path, tool or flag that does not exist, or quotes a benchmark number, hash or gate count that differs from the receipts.
- `tools/bootstrap_ci.py` and `test_eval/bootstrap_ci_TEST.json`: deterministic 95% bootstrap intervals and paired differences for R@1, R@5, MRR, hit@1 and hit@5; CI recomputes them and requires `docs/RESULTS.md` to match.
- `docs/receipt_regeneration.json`: the exact fields (hashes only) that changed when the receipts were regenerated after a label rename.
- CI: the fresh gates run is compared byte for byte with `out/gates_v2.0.1.json`.
- `tools/publication_lint.py`: generic publication lint (home-directory paths, e-mail addresses outside `Contact.md`, private-key headers, token shapes; non-English file names as warnings).
- `tools/reproduce_dev.sh`: re-runs the DEV tuning and compares the parameters, tuning report and unjudged pairs with the shipped files.
- `out/census.json` (so the census unit test runs), `CODE_OF_CONDUCT.md`, `CATALOGUE.md`, `docs/DESIGN.md`.
- Community files: `CONTRIBUTING.md`, `SECURITY.md`, `CITATION.cff`, pull request and bug report templates.
- Documentation: metric definitions, the abstention counts, corpus status field meanings and the explanation of the v1 row budget in `docs/RESULTS.md`; badges, quick start and "What is measured vs claimed" in the README.

### Changed
- `ARCHITECTURE.md` now describes only the shipped system (real tree, data flow, the 14 router gate ids); the design that is not fully implemented moved to `docs/DESIGN.md`.
- `.gitleaks.toml` no longer excludes `papers/` by path (gitleaks 8.18.4 cannot combine a path and a regex in one allowlist). It skips only whole, anchored lines of three forms (`"key": "<citation key>"`, `"<name>sha256": "<64 hex>"` / `"expected"`, `"coordinate"` / `"source_coordinate"`) and findings whose secret value contains the Lean namespace prefix `oai.editapproximation.` or one of three access-anchor ids. CI plants three credentials that must all be detected (see `SECURITY.md`).
- The maintainer-only release scan (it needed an external policy file, so nobody else could run it) is no longer in the public tree; `tools/publication_lint.py` is the public check.
- `tools/route_v2.py`: `--index` and `--params` default to `out/index` and `out/params.json` of the repository (an explicit `--index` without `--params` keeps the built-in defaults, as before); `--paths` adds a `files` map from returned ids to `papers/<file>#<anchor>`.
- `out/protocol.json` and `standards/schemas/ctx.protocol.v2.schema.json` name the mount of this repository (`out/index`, `out/params.json`).
- `AGENTS.md`: a set abstain flag means weak lexical support; inspect the top rows before concluding there is no match.
- `.gitignore` covers virtual environments, caches and build output; model versions in the README are dated (as of 2026-10); `NOTICE` has a copyright line and states which sections are upstream text and which are generated.

### Removed
- catalogue/graph.jsonl (empty, read by no tool or test) and its entry in `release/manifest.json`; the relations the router reads live in `out/index/edges.json`.

### Measured (from `test_eval/test_run_v2.0.1.json`, `test_eval/cold_latency_TEST.json`, `out/gates_v2.0.1.json`)
- TEST, 72 queries (39 answerable, 33 not): R@1 0.2220, R@5 0.5160, MRR 0.5958, nDCG@5 0.4627; answer bytes p50 1,077, max 1,167; abstention precision 0.6286, recall 0.6667, F1 0.6471.
- v1 with a 2,000 B row budget: R@1 0.0904, R@5 0.1139 (its whole answers reach 2,801 B); v1 unbudgeted: R@1 0.0904, R@5 0.2662, answers up to 22,181 bytes.
- Cold latency p50 58.0 ms (v2) vs 87.2 ms (v1), 30 runs; the measuring environment (CPU, operating system, Python version, cache state) was not recorded, so read it as a relative figure.
- 95% bootstrap intervals (39 answerable queries): v2.0.1 R@1 0.222 [0.122, 0.335], R@5 0.516 [0.410, 0.625], MRR 0.596 [0.477, 0.713].
- Gates: 14 of 14 pass. Unit tests: 100 (all run, none skipped).
- Index sha256 `2c1459766a263fdc954a10976198cfb6c441155fac78f0217e2dac3fc2c248a1`, parameters sha256 `ad1c42c79dad98fadd867cd9649f12f3096cb08be93cdc208f3872f10dbf06de`.

### Known limits
R@1 is 0.22; abstention is a lexical heuristic that also flags 33% of answerable queries; per-class numbers are anecdotal; every paper keeps the corpus status fields `DRAFT` and `ASSEMBLED` (see `docs/RESULTS.md`). One DEV pair (W-R12, PM-101.1) is unjudged and disclosed in `docs/RESULTS.md`.
