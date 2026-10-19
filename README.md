# math-router

[![ci](https://github.com/oguirado/math-router/actions/workflows/ci.yml/badge.svg)](https://github.com/oguirado/math-router/actions/workflows/ci.yml) [![license: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

A structured, routable edition of the 719 mathematical preprints in [OpenAI's math repository](https://github.com/openai/math) (Apache-2.0), plus a small offline router that returns the few statements most likely to answer a question, in at most 2,000 bytes.

**Not affiliated with or endorsed by OpenAI.** The mathematics belongs to its authors; see `NOTICE` for attribution and the changes made.

## Quick start

```bash
git clone https://github.com/oguirado/math-router.git && cd math-router
python3 tools/route_v2.py --q "irrationality of Catalan's constant" --index out/index --params out/params.json
python3 tools/build_index_v2.py --root . --out out/index --check
```

Python 3 standard library only, no network. The answer is one JSON line: ranked `[paper_id, anchor, score]` rows and an abstention flag. Map an id to its file with `catalogue/routes.tsv`, then open the paper at the anchor (`<a id="..."></a>`). Agents: read `llms.txt` and `AGENTS.md`.

## What is in the repository

| Path | Content |
|---|---|
| `papers/` | 719 self-contained Markdown papers: original statements and proofs, repaired citations, reading maps, structured JSON blocks |
| `catalogue/`, `Catalogo_Math.md` | subject shards, families, graph edges, routes, per-paper records |
| `tools/` | router, index builder, evaluation, gates, privacy/release lint |
| `standards/` | JSON schemas, router vocabulary/thesaurus, parameter grid |
| `out/` | built index (`index/`), tuned parameters, v1 baseline index, DEV receipts |
| `eval/`, `test_eval/` | benchmark with final graded labels (DEV 90 queries, TEST 72) and TEST receipts |
| `tests/` | unit and fixture tests |

## How routing works

1. The query is tokenised (case-folded, stop words dropped) into terms.
2. Each paper statement is indexed in weighted zones (trigger, task, Q&A, title, synonyms, purpose, keywords, outputs, prerequisites).
3. Scoring is integer-only (no floats), so results are bit-reproducible across machines.
4. A small thesaurus adds a few expansion terms when the query shares none with a statement.
5. Phrase matches and the paper's subject domain add bounded boosts.
6. Query intent (method, bound, prerequisite, ...) shifts weight toward the matching zone.
7. Candidates are ranked per statement and returned with the best anchor of each paper.
8. Coverage and peak-score thresholds decide whether to abstain.
9. Rows are packed under the byte budget, best first.
10. The index is built deterministically from `papers/` and `catalogue/`; `build_index_v2.py --check` proves the shipped index is byte-identical to a rebuild.

## Benchmark (TEST split, single run, frozen before evaluation)

72 queries written blind to the router, 39 answerable and 33 not answerable from the corpus; relevance labels graded by two independent model graders, disagreements adjudicated by a third (Cohen's kappa 0.89 on pooled pairs). Metrics are over the 39 answerable queries.

| System | R@1 | R@5 | MRR | nDCG@5 | Answer bytes p50 / max | Abstention F1 |
|---|---|---|---|---|---|---|
| **math-router v2.0.1** | 0.222 | 0.516 | 0.596 | 0.463 | 1,077 / 1,167 | 0.647 |
| v1 (budgeted to 2,000 B) | 0.090 | 0.114 | 0.256 | 0.128 | 2,246 / 2,801 | - |
| v1 (unbudgeted) | 0.090 | 0.266 | 0.352 | 0.250 | 18,180 / 22,181 | - |
| B1 (v1 lexical-only baseline) | 0.052 | 0.156 | 0.234 | 0.156 | - | 0.350 |

All 14 release gates pass. Reproduce: `sh tools/reproduce_test.sh`. Honest limits: recall at rank 1 is 22%; abstention precision is 63%; most topic classes have fewer than 10 answerable test queries, so per-class numbers are anecdotal. See `docs/RESULTS.md`.

## Reproduce the numbers

`sh tools/reproduce_test.sh` re-runs the TEST split from the shipped files and compares the `systems` section, the benchmark hash and the index hash with the shipped receipt `test_eval/test_run_v2.0.1.json`; it prints `TEST metrics reproduced` or `MISMATCH`. CI runs it on every push.

## What is measured vs claimed

Measured, with receipts in this repository: the ranking metrics, answer sizes and abstention figures above (`test_eval/test_run_v2.0.1.json`), the DEV run (`out/run_DEV_v2.0.1.json`) and the 14 gates (`out/gates_v2.0.1.json`). Claimed, not measured here: the mathematical correctness of the distilled papers and the label quality beyond the stated grader agreement; both rest on model graders plus deterministic gates, not on human expert review. One DEV pair (query W-R12, paper PM-101.1) was never judged and is listed in `out/unjudged_pairs.jsonl`; no judgement was invented for it (see `docs/RESULTS.md`).

## Verify

```bash
python3 tools/build_index_v2.py --root . --out out/index --check
python3 tools/gates_v2.py --all --root "$PWD" --index out/index --params out/params.json --dev eval/dev.jsonl --out /tmp/gates.json
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/claims_check.py
```

The same checks, plus a secret scan, run in `.github/workflows/ci.yml`. See `CONTRIBUTING.md`.

## How this was built

Gemini 3.8 Flash, Gemini 4 Argon, GPT-6.1 Sol, GPT-6 Luna, Claude Opus 5.5 and Claude Sonnet 5.5 (model versions as of 2026-10), under deterministic, model-free gates. Mathematical text is unchanged in meaning; generated sections are labelled. Contact: [Contact.md](Contact.md).

## License

Apache-2.0 (see `LICENSE`, `NOTICE`).
